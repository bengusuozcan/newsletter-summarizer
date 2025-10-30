# 📰 Newsletter Summarizer

A local-first Python tool that uses OpenAI models to summarize Gmail newsletters into short, structured summaries.

## ✨ Features
- Summarizes emails under any Gmail label or from any sender.
- Produces structured summaries with subject, date, key points.
- Saves as `.jsonl` or converts to phone-friendly `.txt`.
- Can run daily to handle new unread emails automatically.
- Have all the newsletter you want summarized under a Gmail label, and input that in the app.py as instructed
- Recommended to modify app.py for your preferred input setup

## 🧠 Requirements
- Python 3.10+
- OpenAI API key
- (Optional) Gmail API credentials if using Gmail automation

## ⚙️ Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
