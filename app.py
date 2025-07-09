import os
import json
import numpy as np
import faiss
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import openai
import telegram
import psycopg2
from datetime import datetime

# Load environment variables
load_dotenv()

# Env vars
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")

openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

# === Load FAISS index & sources ===
INDEX_PATH = "vector_index/index.faiss"
SOURCES_PATH = "vector_index/sources.json"

faiss_index = faiss.read_index(INDEX_PATH)
with open(SOURCES_PATH, "r", encoding="utf-8") as f:
    source_entries = json.load(f)  # Now a list of dicts with "text" and "source"

# === DB Connection ===
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require"
    )

def update_metrics(chat_id=None, error=False):
    try:
        conn = connect_db()
        cur = conn.cursor()
        if chat_id:
            cur.execute("SELECT id FROM usage_metrics WHERE chat_id = %s;", (chat_id,))
            if cur.fetchone() is None:
                cur.execute(
                    "INSERT INTO usage_metrics (chat_id, first_seen, error_count) VALUES (%s, %s, %s);",
                    (chat_id, datetime.utcnow(), 0)
                )
        if error and chat_id:
            cur.execute("UPDATE usage_metrics SET error_count = error_count + 1 WHERE chat_id = %s;", (chat_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("❌ DB metrics error:", e)

# === Embedding Helper ===
def embed_query(text):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )
    return np.array(response['data'][0]['embedding'], dtype=np.float32)

# === Retrieve Context ===
def get_context(query, top_k=3):
    query_vec = embed_query(query).reshape(1, -1)
    D, I = faiss_index.search(query_vec, top_k)
    results = []
    for i in I[0]:
        if i < len(source_entries):
            entry = source_entries[i]
            results.append(f"From *{entry['source']}*:\n{entry['text']}")
    return "\n\n---\n\n".join(results)

# === Telegram Webhook ===
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def receive_update():
            try:
            context = get_context(user_text)

            if not context.strip():
                print("ℹ️ No legal context found. GPT will answer from knowledge.")

            prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are TaxWazobia, a smart Nigerian legal tax assistant.\n\n"
                        "• When legal context is provided, quote the section and law file it's from.\n"
                        "• If there's no legal context, respond based on your knowledge of Nigerian tax laws.\n"
                        "• Always be concise and use Naira (₦) for tax calculations.\n"
                        "• You may explain PIT, PAYE, VAT, CIT, stamp duty, penalties, deadlines, and reliefs.\n"
                        "• You may perform tax calculations when asked, even without legal text."
                    )
                }
            ]

            if context.strip():
                prompt.append({
                    "role": "user",
                    "content": f"Use the legal context below to answer:\n\n{context}\n\nQuestion: {user_text}"
                })
            else:
                prompt.append({"role": "user", "content": user_text})

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                temperature=0.3,
                max_tokens=700
            )

            reply = response['choices'][0]['message']['content']
            bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
            return "OK"
        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)

        try:
            context = get_context(user_text)
            prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are TaxWazobia, a Nigerian legal tax assistant. "
                        "Respond with accurate interpretations of Nigerian tax laws using sections from provided legal documents. "
                        "Always reference the law and act clearly like a professional tax consultant or lawyer."
                    )
                },
                {
                    "role": "user",
                    "content": f"Use the context below to answer this question.\n\n{context}\n\nQuestion: {user_text}"
                }
            ]

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                temperature=0.3,
                max_tokens=700
            )

            reply = response['choices'][0]['message']['content']
            bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
            return "OK"

        except Exception as ai_error:
            print("❌ OpenAI error:", ai_error)
            update_metrics(chat_id=chat_id, error=True)
            bot.send_message(chat_id=chat_id, text="⚠️ Sorry, I couldn't process your request right now.")
            return "OK"

    except Exception as e:
        print("❌ General error:", e)
        update_metrics(error=True)
        return "Error", 500

# === Health Check ===
@app.route("/")
def index():
    return "✅ TaxWazobia bot is running."

# === Metrics Endpoint ===
@app.route("/metrics")
def metrics():
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usage_metrics;")
        user_count = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(error_count) FROM usage_metrics;")
        error_count = cur.fetchone()[0] or 0
        cur.close()
        conn.close()
        return jsonify({
            "user_count": int(user_count),
            "error_count": int(error_count)
        })
    except Exception as e:
        print("❌ Metrics error:", e)
        return jsonify({"error": "Unable to fetch metrics"}), 500

# === Local Server Dev
if __name__ == "__main__":
    print("🚀 TaxWazobia is running locally on port 5000...")
    app.run(port=5000)
