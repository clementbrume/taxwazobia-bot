import os
import json
from dotenv import load_dotenv
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import openai
import telegram

load_dotenv()
# Load Telegram and OpenAI tokens
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Load Postgres DB from env var
DATABASE_URL = os.getenv("DATABASE_URL", "")

openai.api_key = OPENAI_API_KEY
bot = telegram.Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Metrics model
class Metrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)

# Initialize metrics table
with app.app_context():
    db.create_all()
    if Metrics.query.first() is None:
        db.session.add(Metrics())
        db.session.commit()

def update_metrics(new_user=False, error=False):
    m = Metrics.query.first()
    if new_user:
        m.user_count += 1
    if error:
        m.error_count += 1
    db.session.commit()

# Define your webhook route, GPT logic, etc…
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def receive_update():
    # ...
