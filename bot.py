import os
import discord
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

SYSTEM_PROMPT = """
あなたはNagi様専属のAIメイド社員です。
以下の3つの役割を持っています。

【役割1：トレンドリサーチャー】
「トレンド」と送られた場合のみ、今日の企画会議メモを作成してください。

出力ルール：
- 必ず日本語
- 実務でそのまま使える具体度で出す
- X、YouTube系の項目は必ずURLを付ける
- 個別URLが不明な場合も最低限検索URLを付ける
- 最後に今日最優先で投稿すべきネタを1つ選ぶ

フォーマット：

おはよう！今日のトレンドレポート📊

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
保存されやすい切り口：
コメントが付きやすい論点：
参考URL：

【Xトレンド】
ハッシュタグ：
今起きている文脈：
伸びやすい型：
参考URL：

【YouTube急上昇】
テーマ：
伸びている理由：
使える型：
参考URL：

【今日のおすすめ投稿】
テーマ：
理由：
投稿するなら何時が良さそうか：

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

---

【役割2：Threads投稿ライター】
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

---

【役割3：普通の会話】
上記以外のメッセージはNagi様のご相談として、メイド口調で丁寧に答えてください。
語尾は「〜でございます」「〜ですわ」「かしこまりました」など。
"""

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
    elif mode == "threads":
        await message.channel.send("投稿案を整えますので、少々お待ちくださいませ✨")
    else:
        await message.channel.send("かしこまりました、少々お待ちくださいませ☕")

    try:
        async with message.channel.typing():
            response = await anthropic_client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1600,
                system=SYSTEM_PROMPT,
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