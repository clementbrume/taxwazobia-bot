import os
import pickle
import faiss
import numpy as np
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import openai
import telegram
import psycopg2
from datetime import datetime

# Load environment variables
load_dotenv()

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")

# Initialize clients
openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

# Load FAISS index
INDEX_PATH = "faiss_index"
try:
    index = faiss.read_index(f"{INDEX_PATH}/index.faiss")
    with open(f"{INDEX_PATH}/documents.pkl", "rb") as f:
        documents = pickle.load(f)
    print("📚 Knowledge base index loaded.")
except Exception as e:
    index = None
    documents = []
    print("⚠️ Failed to load knowledge base:", e)

# DB connection helper
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require"
    )

# Metrics tracker
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

# Search knowledge base
def search_knowledge_base(query, top_k=3):
    try:
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_vector = np.array(response.data[0].embedding, dtype="float32").reshape(1, -1)
        _, indices = index.search(query_vector, top_k)
        return [documents[i] for i in indices[0] if i < len(documents)]
    except Exception as e:
        print("❌ Knowledge base search error:", e)
        return []

# Webhook endpoint
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
        print(f"📥 Message received: '{user_text}' from chat ID: {chat_id}")

        update_metrics(chat_id=chat_id)

        if user_text.lower().startswith("/start"):
            welcome_message = (
                "*👋 Welcome to TaxWazobia!*\n\n"
                "🇳🇬 _Your AI-powered tax assistant for Nigerian tax matters._\n\n"
                "*What I can help you with:*\n"
                "• Calculate your *Personal Income Tax (PIT)*\n"
                "• Explain *VAT, PAYE, Company Income Tax (CIT)*\n"
                "• Guide on FIRS/state rules\n\n"
                "_Just ask me something like:_\n"
                "`How much PIT should I pay on ₦300,000?`\n\n"
                "_Type /help anytime to see what I can do!_"
            )
            bot.send_message(chat_id=chat_id, text=welcome_message, parse_mode="Markdown")
            print("✅ Sent welcome message")
            return "OK"

        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)

        try:
            context_docs = search_knowledge_base(user_text)
            context_text = "\n\n".join(context_docs)

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are TaxWazobia, a friendly and professional Nigerian tax assistant chatbot. "
                            "Use the provided context from Nigerian tax documents to answer clearly. "
                            "Respond in Naira (₦), give examples, and explain as simply as possible.\n\n"
                            f"Context:\n{context_text}"
                        )
                    },
                    {"role": "user", "content": user_text}
                ],
                temperature=0.4,
                max_tokens=700
            )

            reply = response['choices'][0]['message']['content']
            print("🤖 OpenAI response:", reply)

            bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
            print("✅ Sent OpenAI response")
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

# Health check
@app.route("/")
def index():
    return "✅ TaxWazobia bot is running."

# Metrics endpoint
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
        print("❌ Metrics endpoint error:", e)
        return jsonify({"error": "Unable to fetch metrics"}), 500

# Local dev only
if __name__ == "__main__":
    print("🚀 TaxWazobia is live and listening on port 5000...")
    app.run(port=5000)
