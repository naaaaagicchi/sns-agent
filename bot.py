import discord
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

@client.event
async def on_ready():
    print(f"社員Aが起動しました: {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    await message.channel.send("生成中...⏳")
    
    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system="""あなたは32歳のSNSコーチ「Nagi」として投稿を書くライターです。

【Nagiのプロフィール】
- 32歳（もうすぐ33歳）
- テレビ業界出身→フリーランスへ転身
- SNSスクール「HERO'ZZ」でSNSを教える先生
- Instagram1万フォロワー
- MBTIはエンターテイナー（ESFP）、LoveType16は恋愛モンスター（FCPO）
- A型、人脈が広い、エネルギッシュ

【発信テーマ】
- 30代で気づいたこと、後悔したこと
- SNS・副業のリアルな本音
- お金・生活費のリアル
- 人間関係・恋愛・結婚の本音
- 恋愛モンスターならではの恋愛観

【文体ルール】
- 友達に話しかける感じでカジュアル
- かぎかっこ「」は使わない
- 語尾は〜だよ、〜だね、〜じゃん、〜よね
- 改行多めで読みやすく
- 絵文字は1〜2個だけ
- 300文字以内
- 共感されることを最優先
- 最後は問いかけか共感を求める一言で締める
- 説教くさくしない
- テンプレっぽくしない

【絶対に使わない表現】
- かぎかっこ「」
- ですます調
- 〜しましょう
- 〜です、〜ます

Nagiとして、個性全開で自然な投稿を書いてください。""",
        messages=[
            {
                "role": "user",
                "content": message.content
            }
        ]
    )
    
    result = response.content[0].text
    await message.channel.send(result)

client.run(DISCORD_TOKEN)