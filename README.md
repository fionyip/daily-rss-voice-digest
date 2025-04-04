# 📰 daily-rss-voice-digest
每天早上自動抓你訂閱的 RSS 新聞 ➜ 用 ChatGPT 摘要 ➜ 用 ElevenLabs 生成語音 ➜ 傳送到你的 Telegram！

而且語氣是…像《動森》的西施惠（真的）。

---

## 🛠 功能介紹

- 支援最多 30 篇新聞，涵蓋 WSJ 中文、NYT、SCMP、Coindesk 等
- ChatGPT 幫你生成 80 字內摘要（口語、自然）
- 語音合成使用 ElevenLabs，可自選 or 隨機聲音
- 自動推送 MP3 到 Telegram Bot
- 最後還會說一句鼓勵話「今天的新聞就到這裡了唷～啾咪！」

---

## 📦 安裝與設定

### 1. 安裝依賴

```bash
pip install -r requirements.txt
