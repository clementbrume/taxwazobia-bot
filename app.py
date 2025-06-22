import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import openai
import telegram
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Flask App
app = Flask(__name__)

# PostgreSQL connection details
DB_NAME = "taxwazobia_db"
DB_USER = "taxwazobia_db_user"
DB_PASSWORD = "Aecev0c6mWOhxrSqwISXqpRWmhi26ZLX"
DB_HOST = "dpg-d1blorre5dus73eoe5eg-a.frankfurt-postgres.render.com"
DB_PORT = "5432"

def get_db_connection():
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
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT id FROM usage_metrics WHERE chat_id = %s", (chat_id,))
        user = cursor.fetchone()

        if not user:
            cursor.execute(
                "INSERT INTO usage_metrics (chat_id) VALUES (%s)",
                (chat_id,)
            )
        elif error:
            cursor.execute(
                "UPDATE usage_metrics SET error_count = error_count + 1 WHERE chat_id = %s",
                (chat_id,)
            )

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as db_error:
        print("❌ Failed to update metrics:", db_error)

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
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are TaxWazobia, a friendly and professional Nigerian tax assistant chatbot. "
                            "Answer user questions about Nigerian taxes with clear, practical examples. "
                            "Use Naira (₦), break down terms simply, and give reliable tax guidance using Nigerian context."
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
            bot.send_message(chat_id=chat_id, text="🤖 Sorry, I couldn’t process that right now. Please try again shortly.")
            return "OK"

    except Exception as e:
        print("❌ General error:", e)
        update_metrics(error=True)
        return "Error", 500

@app.route("/")
def index():
    return "✅ TaxWazobia bot is running."

@app.route("/metrics")
def metrics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) AS user_count FROM usage_metrics")
        user_count = cursor.fetchone()["user_count"]

        cursor.execute("SELECT SUM(error_count) AS error_count FROM usage_metrics")
        error_count = cursor.fetchone()["error_count"] or 0

        cursor.close()
        conn.close()

        return jsonify({
            "user_count": user_count,
            "error_count": error_count
        })

    except Exception as e:
        print("❌ Failed to fetch metrics:", e)
        return jsonify({"error": "Failed to fetch metrics"}), 500

if __name__ == "__main__":
    print("🚀 TaxWazobia is live and listening on port 5000...")
    app.run(port=5000)
