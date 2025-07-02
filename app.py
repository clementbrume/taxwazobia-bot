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
INDEX_PATH = "knowledge_base/index.faiss"
SOURCES_PATH = "knowledge_base/sources.json"

faiss_index = faiss.read_index(INDEX_PATH)
with open(SOURCES_PATH, "r", encoding="utf-8") as f:
    source_texts = json.load(f)

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

# === Retrieve Context from FAISS ===
def get_context(query, top_k=3):
    query_vec = embed_query(query).reshape(1, -1)
    D, I = faiss_index.search(query_vec, top_k)
    results = [source_texts[i] for i in I[0] if i < len(source_texts)]
    return "\n\n".join(results)

# === Telegram Webhook ===
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def receive_update():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        message = update.message

        if not message or not message.text:
            print("⚠️ No message text received.")
            return "OK"

        chat_id = message.chat.id
        user_text = message.text.strip()
        print(f"📥 Message from {chat_id}: {user_text}")

        update_metrics(chat_id=chat_id)

        if user_text.lower().startswith("/start"):
            welcome_message = (
                "*👋 Welcome to TaxWazobia!*\n\n"
                "🇳🇬 _Your AI-powered tax assistant for Nigerian tax matters._\n\n"
                "*What I can help you with:*\n"
                "• Calculate your *Personal Income Tax (PIT)*\n"
                "• Explain *VAT, PAYE, CIT, etc.*\n"
                "• Guide on FIRS/state rules\n\n"
                "`Try something like:` _How much PIT do I pay on ₦300,000?_"
            )
            bot.send_message(chat_id=chat_id, text=welcome_message, parse_mode="Markdown")
            return "OK"

        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)

        try:
            context = get_context(user_text)
            prompt_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are TaxWazobia, a friendly and professional Nigerian tax assistant chatbot. "
                        "Use Naira (₦), simplify tax terms, and always apply Nigerian tax laws.\n\n"
                        "Refer to the context below when available."
                    )
                }
            ]

            if context:
                prompt_messages.append({
                    "role": "user",
                    "content": f"Use the following context to answer:\n{context}\n\nQuestion: {user_text}"
                })
            else:
                prompt_messages.append({"role": "user", "content": user_text})

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt_messages,
                temperature=0.4,
                max_tokens=700
            )

            reply = response['choices'][0]['message']['content']
            bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
            return "OK"

        except Exception as ai_error:
            print("❌ OpenAI error:", ai_error)
            update_metrics(chat_id=chat_id, error=True)
            bot.send_message(
                chat_id=chat_id,
                text="🤖 Sorry, I couldn’t process that right now. Please try again shortly."
            )
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

# === Local Dev Server ===
if __name__ == "__main__":
    print("🚀 TaxWazobia is running locally on port 5000...")
    app.run(port=5000)
