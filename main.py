import feedparser
import openai
import os
import random
from elevenlabs import generate, save, set_api_key
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
set_api_key(os.getenv("ELEVENLABS_API_KEY"))
VOICE_IDS = os.getenv("VOICE_IDS").split(",")  # Comma-separated list in .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# RSS Feed List
feeds = [
    # "https://feeds.a.dj.com/rss/RSSWorldNews.xml",  # WSJ World
    # "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
    # "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    # "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cn.wsj.com/zh-hant/rss",  # WSJ 中文網
    # "https://www.scmp.com/rss/2/feed",  # South China Morning Post
    # "https://www.economist.com/finance-and-economics/rss.xml",  # The Economist Finance & Econ
    # "https://www.paperdigest.org/feed/",  # Paper Digest
    # "http://feeds.feedburner.com/nytcn"  # 紐時中文網
]

# Get today's date
TODAY = datetime.utcnow().date()

# Fetch today's entries
def fetch_entries():
    entries = []
    for url in feeds:
        d = feedparser.parse(url)
        for e in d.entries:
            if 'published_parsed' in e:
                pub_date = datetime(*e.published_parsed[:3]).date()
                if pub_date == TODAY:
                    entries.append(e)
    return entries[:30]  # Limit to top 30

# Summarize with GPT
def summarize(title, content):
    prompt = f"請用繁體中文將以下新聞摘要成一段口語化敘述（限80字內，語氣像動森的西施惠）：\n標題：{title}\n內容：{content}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    return response.choices[0].message.content.strip()

# Generate voice
def create_voice(text, filename):
    voice_id = random.choice(VOICE_IDS)
    audio = generate(text=text, voice=voice_id, model="eleven_monolingual_v1")
    save(audio, filename)

# Send to Telegram with link attachment
def send_to_telegram(file_path, summaries_with_links):
    caption_text = "\n".join(summaries_with_links)
    with open(file_path, 'rb') as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption_text[:1024]  # Telegram caption limit
            },
            files={"audio": f}
        )

# Main pipeline
def main():
    entries = fetch_entries()
    summaries = []
    summaries_with_links = []
    for e in entries:
        summary = summarize(e.title, e.summary)
        summaries.append(summary)
        summaries_with_links.append(f"\u2022 {summary}\n{e.link}")

    closing = "今天的新聞就到這裡了唷～祝你有個超棒的一天，啾咪！"
    text_block = "以下是今天的新聞摘要：\n" + "\n".join(summaries) + "\n" + closing
    output_path = f"digest_{TODAY}.mp3"
    create_voice(text_block, output_path)
    send_to_telegram(output_path, summaries_with_links)

if __name__ == "__main__":
    main()
