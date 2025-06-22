import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import openai
import telegram

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

METRICS_FILE = "metrics.json"

# Initialize metrics file if it doesn't exist
if not os.path.exists(METRICS_FILE):
    with open(METRICS_FILE, "w") as f:
        json.dump({"user_count": 0, "error_count": 0, "users": []}, f)

def update_metrics(chat_id=None, error=False):
    with open(METRICS_FILE, "r") as f:
        metrics = json.load(f)

    if chat_id is not None and chat_id not in metrics["users"]:
        metrics["users"].append(chat_id)
        metrics["user_count"] = len(metrics["users"])

    if error:
        metrics["error_count"] += 1

    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=2)

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

        # Track user
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

        # Typing indicator
        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)

        # OpenAI GPT response
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
            update_metrics(error=True)
            bot.send_message(
                chat_id=chat_id,
                text="🤖 Sorry, I couldn’t process that right now. Please try again shortly."
            )
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
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No metrics available"}), 404

if __name__ == "__main__":
    print("🚀 TaxWazobia is live and listening on port 5000...")
    app.run(port=5000)
