import feedparser
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build as build_docs
from googleapiclient.discovery import build as build_drive
import openai
import asyncio
from edge_tts import Communicate

# Load environment variables
load_dotenv()

# OpenAI setup
openai.api_key = os.environ["OPENAI_API_KEY"]

# Google API setup
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_INFO = json.loads(
    os.environ["GOOGLE_CREDENTIALS_JSON_CONTENT"])
credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=SCOPES)
docs_service = build_docs('docs', 'v1', credentials=credentials)
drive_service = build_drive('drive', 'v3', credentials=credentials)

# Telegram setup
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
user_email = os.environ.get("GMAIL_SHARE_TO")

TODAY = datetime.utcnow().date()

feeds = [
    # "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    # "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    # "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    # "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cn.wsj.com/zh-hant/rss",
    # "https://www.scmp.com/rss/2/feed",
    # "https://www.economist.com/finance-and-economics/rss.xml",
    # "https://www.paperdigest.org/feed/", "http://feeds.feedburner.com/nytcn"
]


def fetch_entries():
    entries = []
    for url in feeds:
        d = feedparser.parse(url)
        for e in d.entries:
            if 'published_parsed' in e:
                pub_date = datetime(*e.published_parsed[:3]).date()
                if pub_date == TODAY:
                    entries.append(e)
    return entries[:3]


def build_news_text(entries):
    text = "以下是今天的新聞內容彙整：\n\n"
    for i, e in enumerate(entries, 1):
        text += f"[{i}] {e.title}\n"
        text += f"來源：{e.link}\n"
        if hasattr(e, 'summary'):
            text += e.summary.strip() + "\n"
        text += "\n"
    return text


def save_to_google_docs(content):
    user_email = os.environ.get("GMAIL_SHARE_TO")
    title = f"🗞️ AI 新聞摘要 {TODAY}"
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc.get("documentId")
    requests_body = [{
        "insertText": {
            "location": {
                "index": 1
            },
            "text": content
        }
    }]
    docs_service.documents().batchUpdate(documentId=doc_id,
                                         body={
                                             "requests": requests_body
                                         }).execute()
    if user_email:
        drive_service.permissions().create(
            fileId=doc_id,
            body={
                'type': 'user',
                'role': 'writer',
                'emailAddress': user_email
            },
            fields='id',
            sendNotificationEmail=False).execute()
    print(f"📄 Google Docs 建立成功：https://docs.google.com/document/d/{doc_id}")


def summarize_with_openai(text):
    clean_text = '\n'.join(
        line for line in text.split('\n')
        if not line.startswith("來源：") and not line.lower().startswith("http"))
    prompt = f"請根據以下新聞內容，用中文摘要成一段不超過 1000 字的口語播報文字：\n\n{clean_text}"
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                            messages=[{
                                                "role": "user",
                                                "content": prompt
                                            }],
                                            temperature=0.7)
    return response.choices[0].message.content.strip()


def create_voice(text, filename="summary.mp3"):

    async def _run():
        communicate = Communicate(text, voice="zh-HK-HiuMaanNeural")
        await communicate.save(filename)

    asyncio.run(_run())
    return filename


def send_telegram_audio(file_path, caption):
    with open(file_path, "rb") as f:
        requests.post(
            url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption
            },
            files={"audio": f})


def main():
    entries = fetch_entries()
    content = build_news_text(entries)
    save_to_google_docs(content)
    summary = summarize_with_openai(content)
    if summary:
        filename = create_voice(summary)
        send_telegram_audio(filename, caption="🗞️ 今日新聞摘要")
        print("✅ 成功送出語音摘要至 Telegram！")
    print(f"✅ 處理完畢，總共彙整 {len(entries)} 篇新聞。")


# Webhook support for cron-job.org
from flask import Flask, request

app = Flask(__name__)


@app.route("/")
def index():
    return "👋 歡迎來到 AI 西施惠新聞機器人！請使用 /run 路由來觸發每日摘要。"


@app.route("/run")
def run_digest():
    secret = request.args.get("token")
    if secret != os.getenv("RUN_TOKEN"):
        return "Unauthorized", 403
    main()
    return "✅ Done"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
