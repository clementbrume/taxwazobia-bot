import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)
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
                "👋 *Welcome to TaxWazobia!*\n\n"
                "🇳🇬 Your AI-powered tax assistant for everything Nigerian tax.\n\n"
                "I can help you:\n"
                "• Calculate your Personal Income Tax (PIT)\n"
                "• Understand VAT, PAYE, and Company Income Tax\n"
                "• Stay compliant with FIRS and state regulations\n\n"
                "💬 Just ask me anything, like:\n"
                "How much PIT should I pay on ₦300,000?\n\n"
                "Type /help anytime to see what I can do!"
            )
            bot.send_message(chat_id=chat_id, text=welcome_message, parse_mode="Markdown")
            print("✅ Sent welcome message")
            return "OK"

        # ✅ Handle general AI response
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You're TaxWazobia, a Nigerian tax assistant. Answer questions clearly, using Nigerian examples."},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.4,
                max_tokens=500
            )

            reply = response['choices'][0]['message']['content']
            bot.send_message(chat_id=chat_id, text=reply)
            print("✅ Sent OpenAI reply")
            return "OK"

        except Exception as ai_error:
            print("❌ OpenAI error:", ai_error)
            bot.send_message(chat_id=chat_id, text="Sorry, I had trouble thinking. Try again in a moment.")
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
