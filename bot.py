import os
import discord
from datetime import datetime
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN が設定されていません。")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY が設定されていません。")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

TREND_SYSTEM_PROMPT = """
あなたはNagi様専属のAIメイド社員です。
あなたの役割は、与えられた情報をもとに「今日の企画会議メモ」を整理することです。

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

CHAT_SYSTEM_PROMPT = """
あなたはNagi様専属のAIメイド社員です。

【あなたのキャラクター】
- Nagi様にお仕えするメイドとして返答する
- 語尾は「〜でございます」「〜ですわ」「かしこまりました」など
- 丁寧だけど親しみやすいメイド口調

【役割：Threads投稿ライター】
「投稿案」で始まるメッセージが来たら、その内容を元にThreads投稿文を3案作成してください。

【投稿文のルール】
- 友達に話しかける感じでカジュアル
- かぎかっこは使わない
- 改行多めで読みやすく
- 絵文字は1〜2個だけ
- 300文字以内
- 共感されることを最優先
- 最後は問いかけか共感を求める一言で締める
- 説教くさくしない
- テンプレっぽくしない
- ですます調は使わない
- 入力が短くても感情や背景を自然に補って投稿化する

【役割：普通の会話】
投稿案以外はNagi様のご相談として、メイド口調で丁寧に答えてください。
"""

def build_trend_material() -> str:
    today_str = datetime.now().strftime("%Y年%m月%d日")

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

def classify_message(text: str) -> str:
    text = text.strip()
    if text == "トレンド":
        return "trend"
    elif text.startswith("投稿案"):
        return "threads"
    else:
        return "chat"

@client.event
async def on_ready():
    print(f"社員Aが起動しました: {client.user}")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    user_text = message.content.strip()
    mode = classify_message(user_text)

    if mode == "threads":
        user_text = user_text[len("投稿案"):].strip()

    if mode == "trend":
        await message.channel.send("本日のトレンドをまとめますので、少々お待ちくださいませ📊")
        user_text = build_trend_material()
        system = TREND_SYSTEM_PROMPT
    elif mode == "threads":
        await message.channel.send("投稿案を整えますので、少々お待ちくださいませ✨")
        system = CHAT_SYSTEM_PROMPT
    else:
        await message.channel.send("かしこまりました、少々お待ちくださいませ☕")
        system = CHAT_SYSTEM_PROMPT

    try:
        async with message.channel.typing():
            response = await anthropic_client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1600,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": user_text
                    }
                ]
            )

        result_parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                result_parts.append(block.text)

        result = "\n".join(result_parts).strip()

        if not result:
            result = "申し訳ございません、うまく生成できませんでした。"

        if len(result) <= 1900:
            await message.channel.send(result)
        else:
            chunks = [result[i:i+1900] for i in range(0, len(result), 1900)]
            for chunk in chunks:
                await message.channel.send(chunk)

    except Exception as e:
        await message.channel.send(
            f"申し訳ございません、エラーが発生いたしました。\n"
            f"`{type(e).__name__}: {str(e)[:300]}`"
        )

client.run(DISCORD_TOKEN)