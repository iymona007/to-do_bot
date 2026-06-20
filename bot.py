import os
import re
import sqlite3
import telebot
from telebot import types
from flask import Flask, request
from dotenv import load_dotenv
from groq import Groq

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN yo‘q!")
if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY yo‘q!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

client = Groq(api_key=GROQ_API_KEY)

ADMIN_ID = 5550228074

# ================= DATABASE =================
conn = sqlite3.connect("todo.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    premium INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    task_text TEXT,
    done INTEGER DEFAULT 0
)
""")

conn.commit()

# ================= AI =================
def ask_ai(text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI xatolik: {e}"

# ================= HELPERS =================
def ensure_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, premium, xp) VALUES (?,0,0)",
            (user_id,)
        )
        conn.commit()

def is_premium(user_id):
    cursor.execute("SELECT premium FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    return data and data[0] == 1

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    ensure_user(message.from_user.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("➕ Vazifa qo'shish"),
        types.KeyboardButton("📋 Vazifalar"),
        types.KeyboardButton("💎 Premium")
    )

    bot.send_message(message.chat.id, "👋 Xush kelibsiz!", reply_markup=markup)

# ================= PREMIUM =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):
    bot.send_message(message.chat.id, "💎 Premium tizim")

# ================= ADD TASK =================
@bot.message_handler(func=lambda m: m.text == "➕ Vazifa qo'shish")
def add_task(message):
    msg = bot.send_message(message.chat.id, "📝 Vazifa yozing:")
    bot.register_next_step_handler(msg, save_task)

def save_task(message):
    cursor.execute(
        "INSERT INTO tasks (user_id, task_text) VALUES (?,?)",
        (message.from_user.id, message.text)
    )
    conn.commit()
    bot.send_message(message.chat.id, "✅ Qo‘shildi")

# ================= SHOW TASKS =================
@bot.message_handler(func=lambda m: m.text == "📋 Vazifalar")
def show_tasks(message):
    cursor.execute(
        "SELECT task_text, done FROM tasks WHERE user_id=?",
        (message.from_user.id,)
    )
    tasks = cursor.fetchall()

    if not tasks:
        bot.send_message(message.chat.id, "📭 Bo‘sh")
        return

    text = ""
    for i, t in enumerate(tasks, 1):
        status = "✔" if t[1] else "❌"
        text += f"{i}. {t[0]} {status}\n"

    bot.send_message(message.chat.id, text)

# ================= FILTER =================
bad_words = ['jinni','ahmoq','idiot','stupid','loser']

def has_link(text):
    return bool(re.search(r'(https?://|t\.me/)', text))

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    text = message.text or ""

    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        is_admin = member.status in ["administrator", "creator"]
    except:
        is_admin = False

    if has_link(text) and not is_admin:
        bot.delete_message(message.chat.id, message.message_id)
        return

    for w in bad_words:
        if w in text.lower():
            bot.delete_message(message.chat.id, message.message_id)
            return

    # AI fallback
    bot.send_message(message.chat.id, ask_ai(text))

# ================= WEBHOOK =================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/")
def home():
    return "Bot ishlayapti", 200

# ================= RUN =================
if __name__ == "__main__":
    WEBHOOK_URL = "https://YOUR-APP.onrender.com/webhook"

    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))