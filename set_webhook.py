import requests

# Your actual bot token
BOT_TOKEN = "7852709951:AAFzUb7y80SrAiSr0WoFqmNNhHvYV8eHR1w"

# ✅ Your current Ngrok URL
NGROK_URL = "https://e282-105-120-135-89.ngrok-free.app"

# Combine the webhook URL properly
WEBHOOK_URL = f"{NGROK_URL}/{BOT_TOKEN}"

# Set webhook by sending a GET request to Telegram
response = requests.get(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
)

# Show Telegram's response
print("Webhook response:", response.text)
