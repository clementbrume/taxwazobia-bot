import os
from dotenv import load_dotenv
from flask import Flask, request
import openai
import telegram

# Load environment variables
load_dotenv()

# Set up API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Initialize OpenAI and Telegram Bot
openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Set up Flask app
app = Flask(__name__)

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

        # ✅ Handle /start command
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

        # ✅ Typing indicator
        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)

        # ✅ GPT Response
        try:
            gpt_response = openai.ChatCompletion.create(
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
            bot.send_message(
                chat_id=chat_id,
                text="🤖 Sorry, I couldn’t process that right now. Please try again shortly."
            )
            return "OK"

    except Exception as e:
        print("❌ General error:", e)
        return "Error", 500

@app.route("/")
def index():
    return "✅ TaxWazobia bot is running."

if __name__ == "__main__":
    print("🚀 TaxWazobia is live and listening on port 5000...")
    app.run(port=5000)
