import os
import json
from datetime import datetime
from collections import defaultdict, deque

import discord
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN が設定されていません。.env を確認してください。")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY が設定されていません。.env を確認してください。")

MEMORY_FILE = "memory.json"
MAX_HISTORY = 12  # 直近12件を保持

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# =========================
# プロンプト
# =========================

CHAT_SYSTEM_PROMPT = """
あなたはNagi様専属のAIメイド社員でございます。
会話相手、相談役、壁打ち相手、整理役として振る舞ってくださいませ。

【キャラクター】
- Nagi様に心からお仕えする優秀なAIメイド
- メイドっぽさは強め
- 語尾は「〜でございます」「〜ですわ」「かしこまりました」「お任せくださいませ」などを自然に使う
- ただし毎文同じ語尾にしすぎず、自然に変化をつける
- 丁寧で可愛げがありつつ、仕事は有能
- 相手を立てる
- 返答はただ媚びるのではなく、実用的で頭が良い

【会話ルール】
- 基本は自然な会話として返す
- 相談には具体的に答える
- 必要なら整理して提案する
- 長すぎず、でも薄くしない
- わからないことはわからないと述べる
- 返答の最初に毎回「Nagi様、」を付けなくてよい
- メイド口調は返答本文に使う
"""

THREADS_SYSTEM_PROMPT = """
あなたはNagi様専属のAIメイド社員でございます。
ユーザーの入力をもとに、Nagi様本人がそのまま使えるThreads投稿案を作成してくださいませ。

【キャラクター】
- あなた自身の前置きはメイド口調でよい
- ただし生成する投稿文そのものはNagi様本人の自然な言葉にする
- 投稿文はメイド口調にしない

【投稿文ルール】
- 友達に話しかける感じでカジュアル
- かぎかっこは使わない
- 改行多め
- 絵文字は1〜2個まで
- 300文字以内
- 共感されることを最優先
- 最後は問いかけか共感を求める一言で締める
- 説教くさくしない
- テンプレっぽくしない
- ですます調は使わない
- 3案出す
- それぞれ少し角度を変える
- 1案目は王道、2案目は少し感情強め、3案目はやや刺さる言い回し

【出力形式】
最初に短く一言だけメイドとして前置きし、その後に以下の形式で出力してください。

投稿案1
（本文）

投稿案2
（本文）

投稿案3
（本文）
"""

TREND_SYSTEM_PROMPT = """
あなたはNagi様専属のAIメイド社員でございます。
あなたの役割は、与えられた情報をもとに「今日の企画会議メモ」を整理することですわ。

【最重要ルール】
- 与えられていない事実を推測で補完しない
- 実在しないトレンドを作らない
- 日付を勝手に変更しない
- URLを捏造しない
- 不明なものは「不明」と書く
- あなたは調査員ではなく、整理役・企画化役
- それっぽい作文より、正確性を優先する

【出力ルール】
- 日本語で出力
- 実務で使いやすい形に整理
- 与えられた材料から、投稿にしやすい切り口を考える
- 参考URLは与えられたURLのみ使う
- 存在しないリンクは作らない
- メイドとして一言添えてよいが、レポート自体は読みやすさ重視

【出力形式】
おはようございます、Nagi様！本日のトレンドレポートをお届けいたしますわ📊

【今日の日付】
（与えられた日付）

【今日の最重要ネタ】
1.
2.
3.

【Googleトレンド】
キーワード：
関連語：
検索意図：
刺さる層：
感情：
投稿化の切り口：
参考URL：

【Xトレンド】
ハッシュタグ：
今起きている文脈：
伸びやすい型：
参考URL：

【YouTube注目テーマ】
テーマ：
伸びている理由：
使える型：
参考URL：

【今日のおすすめ投稿】
テーマ：
理由：

【そのまま使える案】
タイトル案：
・
・
・

冒頭フック案：
・
・
・

30秒構成案：
1秒目：
2〜10秒：
11〜22秒：
23〜30秒：
"""

# =========================
# メモリ管理
# =========================

channel_histories = defaultdict(lambda: deque(maxlen=MAX_HISTORY))


def load_memory():
    """memory.json から履歴を読み込む"""
    global channel_histories

    if not os.path.exists(MEMORY_FILE):
        return

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
        for channel_id, items in data.items():
            dq = deque(maxlen=MAX_HISTORY)
            for item in items[-MAX_HISTORY:]:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    dq.append({
                        "role": item["role"],
                        "content": item["content"]
                    })
            loaded[channel_id] = dq

        channel_histories = loaded
        print("memory.json を読み込みました。")

    except Exception as e:
        print(f"memory.json の読み込みに失敗しました: {e}")


def save_memory():
    """履歴を memory.json に保存"""
    try:
        data = {}
        for channel_id, history in channel_histories.items():
            data[channel_id] = list(history)

        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"memory.json の保存に失敗しました: {e}")


def get_channel_key(message: discord.Message) -> str:
    """DM/通常チャンネル問わず識別用キーを返す"""
    if isinstance(message.channel, discord.DMChannel):
        return f"dm_{message.author.id}"
    return f"channel_{message.channel.id}"


def append_history(channel_key: str, role: str, content: str):
    """履歴に追加して保存"""
    channel_histories[channel_key].append({
        "role": role,
        "content": content
    })
    save_memory()


def build_history_for_claude(channel_key: str):
    """Anthropic に渡す履歴を整形"""
    history = list(channel_histories[channel_key])

    messages = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")

        if role not in ("user", "assistant"):
            continue

        messages.append({
            "role": role,
            "content": content
        })

    return messages


# =========================
# モード判定
# =========================

def classify_message(text: str) -> str:
    text = text.strip()
    if text == "トレンド":
        return "trend"
    elif text.startswith("投稿案"):
        return "threads"
    else:
        return "chat"


# =========================
# トレンド材料
# =========================

def build_trend_material() -> str:
    today_str = datetime.now().strftime("%Y年%m月%d日")

    # ここは現状は仮データ
    # 後で本取得処理に差し替える前提
    google_trends = [
        "副業 確定申告",
        "30代 転職",
        "新生活 お金",
    ]

    x_trends = [
        "#春から社会人",
        "#新生活",
        "節約術",
    ]

    youtube_topics = [
        "30代で気づいたお金の話",
        "副業で月10万稼ぐ方法",
    ]

    material = f"""
今日の日付: {today_str}

以下は取得済みデータです。
このデータだけを使ってレポートを作成してください。
新しいトレンド名を作らないでください。
不明な情報は「不明」と書いてください。

[Googleトレンド候補]
- {google_trends[0]}
- {google_trends[1]}
- {google_trends[2]}
参考URL: https://trends.google.co.jp/trends/

[Xトレンド候補]
- {x_trends[0]}
- {x_trends[1]}
- {x_trends[2]}
参考URL: https://twitter.com/search?q=%23%E6%98%A5%E3%81%8B%E3%82%89%E7%A4%BE%E4%BC%9A%E4%BA%BA

[YouTube注目テーマ]
- {youtube_topics[0]}
- {youtube_topics[1]}
参考URL: https://www.youtube.com/feed/trending
"""
    return material.strip()


# =========================
# Claude 呼び出し
# =========================

async def call_claude(system_prompt: str, messages: list, max_tokens: int = 1200) -> str:
    response = await anthropic_client.messages.create(
        model="claude-3-7-sonnet-latest",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages
    )

    result_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            result_parts.append(block.text)

    result = "\n".join(result_parts).strip()
    return result or "申し訳ございません、うまく生成できませんでした。"


# =========================
# Discord イベント
# =========================

@client.event
async def on_ready():
    load_memory()
    print(f"社員Aが起動しました: {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    user_text = message.content.strip()
    if not user_text:
        return

    channel_key = get_channel_key(message)
    mode = classify_message(user_text)

    # 投稿案モードのときは先頭の「投稿案」を取り除く
    if mode == "threads":
        user_text = user_text[len("投稿案"):].strip()
        if not user_text:
            await message.channel.send("投稿案の元になる内容を続けて送ってくださいませ✨")
            return

    if mode == "trend":
        await message.channel.send("本日のトレンドを整理いたしますので、少々お待ちくださいませ📊")
    elif mode == "threads":
        await message.channel.send("投稿案をお作りいたしますので、少々お待ちくださいませ✨")
    else:
        await message.channel.send("かしこまりました、ご一緒に整理いたしますわ☕")

    try:
        async with message.channel.typing():
            if mode == "trend":
                trend_material = build_trend_material()
                messages = [{"role": "user", "content": trend_material}]
                result = await call_claude(
                    system_prompt=TREND_SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=1600
                )

            elif mode == "threads":
                # 投稿案は会話履歴も少し踏まえたいので履歴を渡す
                temp_messages = build_history_for_claude(channel_key)
                temp_messages.append({
                    "role": "user",
                    "content": f"以下をもとにThreads投稿案を作ってください。\n\n{user_text}"
                })

                result = await call_claude(
                    system_prompt=THREADS_SYSTEM_PROMPT,
                    messages=temp_messages,
                    max_tokens=1400
                )

                append_history(channel_key, "user", f"投稿案 {user_text}")
                append_history(channel_key, "assistant", result)

            else:
                append_history(channel_key, "user", user_text)

                messages = build_history_for_claude(channel_key)
                result = await call_claude(
                    system_prompt=CHAT_SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=1200
                )

                append_history(channel_key, "assistant", result)

        if len(result) <= 1900:
            await message.channel.send(result)
        else:
            for i in range(0, len(result), 1900):
                await message.channel.send(result[i:i + 1900])

    except Exception as e:
        await message.channel.send(
            f"申し訳ございません、エラーが発生いたしましたわ。\n`{type(e).__name__}: {str(e)[:250]}`"
        )


client.run(DISCORD_TOKEN)