import telebot
from telebot import types
from dotenv import load_dotenv
import os
import sqlite3
import google.genai as genai
from flask import Flask, request

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= FLASK =================
app = Flask(__name__)

# ================= BOT =================
bot = telebot.TeleBot(BOT_TOKEN)

# ================= GEMINI (NEW SDK FIXED) =================
client = genai.Client(api_key=GEMINI_API_KEY)

def ask_ai(text):
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text
        )
        return res.text
    except Exception as e:
        return f"❌ AI xatolik: {e}"

# ================= ADMIN =================
ADMIN_ID = 5550228074  # o‘zingni ID

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

# ================= HELPERS =================
def ensure_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, premium, xp) VALUES (?,0,0)",
            (user_id,)
        )
        conn.commit()

def is_admin(user_id):
    return user_id == ADMIN_ID

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

    bot.send_message(
        message.chat.id,
        "👋 Xush kelibsiz!",
        reply_markup=markup
    )

# ================= MY ID =================
@bot.message_handler(commands=['myid'])
def myid(message):
    bot.send_message(message.chat.id, f"🆔 ID: {message.from_user.id}")

# ================= PREMIUM =================
@bot.message_handler(func=lambda m: m.text == "💎 Premium")
def premium(message):
    bot.send_message(
        message.chat.id,
        "💎 PREMIUM:\n\n"
        "✔ Ads yo‘q\n"
        "✔ Bonus XP\n"
        "✔ Sovg‘alar\n\n"
        "📸 To‘lov screenshot yuboring"
    )

# ================= PAYMENT PHOTO =================
@bot.message_handler(content_types=['photo'])
def payment_photo(message):
    user_id = message.from_user.id
    ensure_user(user_id)

    bot.send_message(message.chat.id, "📸 Qabul qilindi!")

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"💰 To‘lov\nUser ID: {user_id}"
    )

# ================= PREMIUM GIVE =================
def give_gift(user_id):
    cursor.execute(
        "UPDATE users SET xp = xp + 100 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()

    bot.send_message(user_id, "🎁 +100 XP bonus!")

@bot.message_handler(commands=['give_premium'])
def give_premium(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Admin emassiz")
        return

    try:
        user_id = int(message.text.split()[1])

        cursor.execute(
            "UPDATE users SET premium=1 WHERE user_id=?",
            (user_id,)
        )
        conn.commit()

        give_gift(user_id)

        bot.send_message(user_id, "🎉 Siz PREMIUM bo‘ldingiz!")
        bot.send_message(message.chat.id, "✅ Berildi!")

    except:
        bot.send_message(message.chat.id, "❌ /give_premium USER_ID")

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
        "SELECT id, task_text, done FROM tasks WHERE user_id=?",
        (message.from_user.id,)
    )

    tasks = cursor.fetchall()

    if not tasks:
        bot.send_message(message.chat.id, "📭 Yo‘q")
        return

    text = ""
    for i, t in enumerate(tasks, 1):
        status = "✔" if t[2] else "❌"
        text += f"{i}. {t[1]} {status}\n"

    if is_premium(message.from_user.id):
        text += "\n💎 Premium user"

    bot.send_message(message.chat.id, text)

# ================= AI HANDLER =================
@bot.message_handler(func=lambda m: True)
def ai_handler(message):
    if message.text in ["➕ Vazifa qo'shish", "📋 Vazifalar", "💎 Premium"]:
        return

    bot.send_message(message.chat.id, ask_ai(message.text))

# ================= WEBHOOK =================
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'ok', 200

# ================= START SERVER =================
if __name__ == '__main__':
    bot.remove_webhook()

    bot.set_webhook(
        url='https://to-do-bot-96w0.onrender.com/webhook'
    )

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))