from flask import Flask, request
import logging
import os
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv
import requests

# === Load environment variables ===
load_dotenv()

# === Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7852709951:AAFzUb7y80SrAiSr0WoFqmNNhHvYV8eHR1w")
RENDER_URL = os.getenv("RENDER_URL", "https://taxwazobia-bot-3.onrender.com")
WEBHOOK_URL = f"{RENDER_URL}/{BOT_TOKEN}"

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

# === Logging ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Telegram Command Handlers ===
def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="👋 Welcome to TaxWazobia! How can I help you with Nigerian taxes today?")

def help_command(update: Update, context: CallbackContext):
    logger.info("Received /help command")
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="ℹ️ Use /start to begin. Just type your tax question any time!")

def echo(update: Update, context: CallbackContext):
    user_msg = update.message.text
    logger.info(f"Echoing user message: {user_msg}")
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"You said: {user_msg}")

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# === Webhook route ===
@app.route(f'/{BOT_TOKEN}', methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    logger.info(f"🔔 New update from Telegram: {update}")
    dispatcher.process_update(update)
    return "OK"

# === Run only once to set webhook ===
@app.route('/set_webhook', methods=["GET"])
def set_webhook():
    res = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    )
    return f"Webhook set: {res.text}"

# Optional: root route
@app.route('/', methods=["GET"])
def home():
    return "TaxWazobia Bot is Live!"

