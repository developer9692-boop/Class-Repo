import sqlite3
import requests
import json
import time
import os
from urllib.parse import urlparse
from flask import Flask, request

# ================= CONFIG =================
BOT_TOKEN = '8669859381:AAEXATKTVgmuOHg1Jg9hQ84YBjq9L7Z6G28'
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/'

OWNER_ID = 6808803040
ADMIN_PASSWORD = 'Rimjhim'

CHANNELS = ["@ERRORARMY1", "@SELLANYTHING4"]

# ================= SERVICES =================
services = {
    "Followers": {"name": "👤 Followers", "base": 100,  "cost": 10},
    "Likes":     {"name": "❤️ Likes",     "base": 100,  "cost": 5},
    "Views":     {"name": "👁 Views",      "base": 1000, "cost": 2},
    "Shares":    {"name": "🔁 Shares",    "base": 1000, "cost": 5},
    "Comments":  {"name": "💬 Comments",  "base": 100,  "cost": 3},
}

# ================= DATABASE =================
_db_conn = None

def db():
    global _db_conn
    if not _db_conn:
        _db_conn = sqlite3.connect('bot.db', check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row

        _db_conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                credits     INTEGER DEFAULT 2,
                referral_id INTEGER,
                step        TEXT DEFAULT '',
                is_verified INTEGER DEFAULT 0
            )
        """)

        _db_conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                service_name TEXT,
                quantity     INTEGER,
                link         TEXT,
                cost         INTEGER,
                status       TEXT
            )
        """)

        _db_conn.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code         TEXT PRIMARY KEY,
                reward_value INTEGER,
                max_uses     INTEGER,
                current_uses INTEGER DEFAULT 0
            )
        """)

        _db_conn.commit()
    return _db_conn

# ================= BOT =================
def bot(method, data=None):
    if data is None:
        data = {}
    res = requests.post(API_URL + method, data=data)
    return res.json()

# ================= USER =================
def get_user(user_id):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return get_user(user_id)
    return dict(row)

def set_step(user_id, step):
    conn = db()
    conn.execute("UPDATE users SET step=? WHERE user_id=?", (step, user_id))
    conn.commit()

# ================= VERIFY =================
def is_joined(user_id):
    for ch in CHANNELS:
        res = bot('getChatMember', {'chat_id': ch, 'user_id': user_id})
        status = res.get('result', {}).get('status')
        if not status or status == 'left':
            return False
    return True

# ================= JOIN MENU =================
def join_menu(chat_id):
    bot('sendMessage', {
        'chat_id': chat_id,
        'text': "✨ Welcome to Free Astro!\n\nJoin channels first.",
        'reply_markup': json.dumps({
            'inline_keyboard': [
                [
                    {'text': "Join Channel 1 🌐", 'url': "https://t.me/ERRORARMY1"},
                    {'text': "Join Channel 2 🌐", 'url': "https://t.me/SELLANYTHING4"}
                ],
                [
                    {'text': "Verify ✅", 'callback_data': "verify"}
                ]
            ]
        })
    })

# ================= MAIN MENU =================
def main_menu(chat_id, user):
    credits = user['credits']
    text = (
        f"✨ <b>Welcome to Free Astro</b> ✨\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>User ID:</b> <code>{chat_id}</code>\n"
        f"💰 <b>Credits:</b> {credits}\n\n"
        f"🚀 <b>Your Trusted Provider</b>\n\n"
        f"🌐 <b>Website:</b>\nhttps://astrropulse.vercel.app/\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 <i>Earn • Order • Grow</i>"
    )
    bot('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': "HTML",
        'reply_markup': json.dumps({
            'keyboard': [
                ["🛒 Order Now"],
                ["🎁 Redeem"],
                ["👨‍💻 Contact Owner"]
            ],
            'resize_keyboard': True
        })
    })

# ================= FLASK APP =================
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running! ✅'

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()

    if not update:
        return 'ok'

    # ================= CALLBACK =================
    if 'callback_query' in update:
        cb      = update['callback_query']
        user_id = cb['from']['id']
        chat_id = cb['message']['chat']['id']

        if cb['data'] == "verify":
            if is_joined(user_id):
                db().execute("UPDATE users SET is_verified=1 WHERE user_id=?", (user_id,))
                db().commit()
                bot('sendMessage', {'chat_id': chat_id, 'text': "✅ Verified"})
                user = get_user(user_id)
                main_menu(chat_id, user)
            else:
                bot('answerCallbackQuery', {
                    'callback_query_id': cb['id'],
                    'text': "Join channels first",
                    'show_alert': True
                })
        return 'ok'

    # ================= USER MESSAGE HANDLER =================
    msg = update.get('message')
    if not msg:
        return 'ok'

    text    = msg.get('text', '')
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']

    user = get_user(user_id)

    if not user['is_verified']:
        join_menu(chat_id)
        return 'ok'

    # ================= START =================
    if text.startswith("/start"):
        main_menu(chat_id, user)
        return 'ok'

    # ================= BACK =================
    if text == "🔙 Back":
        set_step(user_id, "")
        main_menu(chat_id, user)
        return 'ok'

    # ================= ORDER =================
    if text == "🛒 Order Now":
        set_step(user_id, "service")
        bot('sendMessage', {
            'chat_id': chat_id,
            'text': "Select Service",
            'reply_markup': json.dumps({
                'keyboard': [
                    ["Followers", "Likes"],
                    ["Views", "Shares"],
                    ["Comments"],
                    ["🔙 Back"]
                ],
                'resize_keyboard': True
            })
        })
        return 'ok'

    # ================= SERVICE SELECT =================
    if text in services:
        s = services[text]
        set_step(user_id, f"qty:{text}")
        bot('sendMessage', {
            'chat_id': chat_id,
            'text': (
                f"✨ Service Selected\n\n"
                f"📦 {s['name']}\n"
                f"💰 {s['cost']} Credits per {s['base']}\n\n"
                f"Minimum: 100\n\n"
                f"Enter Quantity:"
            ),
            'reply_markup': json.dumps({
                'keyboard': [["🔙 Back"]],
                'resize_keyboard': True
            })
        })
        return 'ok'

    # ================= QUANTITY =================
    if user['step'].startswith("qty:"):
        service = user['step'].split(":")[1]
        qty = int(text) if text.isdigit() else 0

        if qty < 100:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Minimum is 100"})
            return 'ok'

        s     = services[service]
        units = -(-qty // s['base'])  # ceil division
        cost  = units * s['cost']

        set_step(user_id, f"confirm:{service}:{qty}:{cost}")
        bot('sendMessage', {
            'chat_id': chat_id,
            'text': (
                f"📊 Order Summary\n\n"
                f"Service: {s['name']}\n"
                f"Qty: {qty}\n"
                f"Cost: {cost} Credits\n\n"
                f"Confirm?"
            ),
            'reply_markup': json.dumps({
                'keyboard': [
                    ["✅ Confirm Order"],
                    ["🔙 Back"]
                ],
                'resize_keyboard': True
            })
        })
        return 'ok'

    # ================= CONFIRM =================
    if text == "✅ Confirm Order" and user['step'].startswith("confirm:"):
        _, service, qty, cost = user['step'].split(":")
        qty  = int(qty)
        cost = int(cost)

        if user['credits'] < cost:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Not enough credits"})
            return 'ok'

        db().execute("UPDATE users SET credits=credits-? WHERE user_id=?", (cost, user_id))
        db().commit()
        set_step(user_id, f"link:{service}:{qty}:{cost}")
        bot('sendMessage', {'chat_id': chat_id, 'text': "Send Link"})
        return 'ok'

    # ================= PLACE ORDER =================
    if user['step'].startswith("link:"):
        _, service, qty, cost = user['step'].split(":")

        try:
            result = urlparse(text)
            valid  = all([result.scheme, result.netloc])
        except Exception:
            valid = False

        if not valid:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Send valid link"})
            return 'ok'

        link = text

        conn = db()
        conn.execute(
            "INSERT INTO orders (user_id, service_name, quantity, link, cost, status) VALUES (?,?,?,?,?,?)",
            (user_id, service, qty, link, cost, 'Pending')
        )
        conn.commit()
        oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        owner_text = (
            f"🚀 <b>New Order Received</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>Order ID:</b> <code>{oid}</code>\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n\n"
            f"📦 <b>Service:</b> {service}\n"
            f"🔢 <b>Quantity:</b> {qty}\n"
            f"🔗 <b>Link:</b>\n<code>{link}</code>\n\n"
            f"💰 <b>Cost:</b> {cost}\n"
            f"📊 <b>Status:</b> Pending\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Use: <code>/done {oid}</code>"
        )
        bot('sendMessage', {'chat_id': OWNER_ID, 'text': owner_text, 'parse_mode': "HTML"})

        user_text = (
            f"✅ <b>Order Placed Successfully</b>\n\n"
            f"🆔 Order ID: <code>{oid}</code>\n"
            f"📦 Service: {service}\n"
            f"🔢 Quantity: {qty}\n"
            f"💰 Cost: {cost}\n\n"
            f"⏳ Status: Pending"
        )
        bot('sendMessage', {'chat_id': chat_id, 'text': user_text, 'parse_mode': "HTML"})
        set_step(user_id, "")
        return 'ok'

    # ================= REDEEM =================
    if text == "🎁 Redeem":
        set_step(user_id, "redeem")
        bot('sendMessage', {
            'chat_id': chat_id,
            'text': "🎟 <b>Redeem Code</b>\n\nEnter your code below:",
            'parse_mode': "HTML",
            'reply_markup': json.dumps({
                'keyboard': [["🔙 Back"]],
                'resize_keyboard': True
            })
        })
        return 'ok'

    if user['step'] == "redeem":
        code = text.strip()
        c    = db().execute("SELECT * FROM redeem_codes WHERE code=?", (code,)).fetchone()

        if c:
            c = dict(c)
            if c['current_uses'] >= c['max_uses']:
                bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Code Expired"})
            else:
                db().execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (c['reward_value'], user_id))
                db().execute("UPDATE redeem_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
                db().commit()
                bot('sendMessage', {
                    'chat_id': chat_id,
                    'text': (
                        f"✅ <b>Redeemed Successfully!</b>\n\n"
                        f"💰 Credits Added: {c['reward_value']}\n\n"
                        f"Use /start to refresh balance"
                    ),
                    'parse_mode': "HTML"
                })
        else:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Invalid Code"})

        set_step(user_id, "")
        return 'ok'

    # ================= CONTACT =================
    if text == "👨‍💻 Contact Owner":
        set_step(user_id, "contact")
        bot('sendMessage', {'chat_id': chat_id, 'text': "Send Message"})
        return 'ok'

    if user['step'] == "contact":
        set_step(user_id, "")
        bot('forwardMessage', {
            'chat_id': OWNER_ID,
            'from_chat_id': chat_id,
            'message_id': msg['message_id']
        })
        bot('sendMessage', {'chat_id': chat_id, 'text': "✅ Sent"})
        return 'ok'

    # ================= ADMIN LOGIN =================
    if text == "/admin" and user_id == OWNER_ID:
        set_step(user_id, "admin_pass")
        bot('sendMessage', {'chat_id': chat_id, 'text': "🔐 Enter Admin Password:"})
        return 'ok'

    if user['step'] == "admin_pass":
        if text == ADMIN_PASSWORD:
            set_step(user_id, "admin")
            bot('sendMessage', {
                'chat_id': chat_id,
                'text': "👑 Admin Panel",
                'reply_markup': json.dumps({
                    'keyboard': [
                        ["📊 Stats", "👥 Users"],
                        ["📦 Orders", "🎟 Create Code"],
                        ["📢 Broadcast"]
                    ],
                    'resize_keyboard': True
                })
            })
        else:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Wrong Password"})
        return 'ok'

    # ================= ADMIN FEATURES =================

    # 📊 Stats
    if text == "📊 Stats" and user['step'] == "admin":
        u = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
        o = db().execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        bot('sendMessage', {
            'chat_id': chat_id,
            'text': f"📊 Bot Stats\n\n👥 Total Users: {u}\n📦 Total Orders: {o}"
        })
        return 'ok'

    # 👥 Users
    if text == "👥 Users" and user['step'] == "admin":
        rows = db().execute("SELECT user_id, credits FROM users ORDER BY user_id DESC LIMIT 30").fetchall()
        msg_text = "👥 Users List:\n\n"
        for r in rows:
            msg_text += f"🆔 {r['user_id']} | 💰 {r['credits']}\n"
        bot('sendMessage', {'chat_id': chat_id, 'text': msg_text})
        return 'ok'

    # 📦 Orders
    if text == "📦 Orders" and user['step'] == "admin":
        rows = db().execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10").fetchall()
        msg_text = "📦 Recent Orders:\n\n"
        for o in rows:
            msg_text += (
                f"🆔 #{o['id']}\n"
                f"👤 {o['user_id']}\n"
                f"📦 {o['service_name']}\n"
                f"🔢 {o['quantity']}\n"
                f"📊 {o['status']}\n\n"
            )
        bot('sendMessage', {'chat_id': chat_id, 'text': msg_text})
        return 'ok'

    # 🎟 CREATE CODE (Step 1)
    if text == "🎟 Create Code" and user['step'] == "admin":
        set_step(user_id, "code_name")
        bot('sendMessage', {'chat_id': chat_id, 'text': "🎟 Send Code Name:"})
        return 'ok'

    # Step 2
    if user['step'] == "code_name":
        set_step(user_id, f"code_value:{text}")
        bot('sendMessage', {'chat_id': chat_id, 'text': "💰 Enter Credit Value:"})
        return 'ok'

    # Step 3
    if user['step'].startswith("code_value:"):
        code = user['step'].split(":")[1]
        if not text.isdigit():
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Enter valid number"})
            return 'ok'
        set_step(user_id, f"code_limit:{code}:{text}")
        bot('sendMessage', {'chat_id': chat_id, 'text': "🔢 Enter Max Uses:"})
        return 'ok'

    # Step 4 FINAL
    if user['step'].startswith("code_limit:"):
        parts = user['step'].split(":")
        code  = parts[1]
        value = parts[2]
        if not text.isdigit():
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Enter valid number"})
            return 'ok'
        db().execute(
            "INSERT INTO redeem_codes (code, reward_value, max_uses) VALUES (?,?,?)",
            (code, int(value), int(text))
        )
        db().commit()
        bot('sendMessage', {'chat_id': chat_id, 'text': "✅ Code Created Successfully!"})
        set_step(user_id, "admin")
        return 'ok'

    # 📢 BROADCAST
    if text == "📢 Broadcast" and user['step'] == "admin":
        set_step(user_id, "broadcast")
        bot('sendMessage', {'chat_id': chat_id, 'text': "📢 Send Message to Broadcast:"})
        return 'ok'

    if user['step'] == "broadcast":
        set_step(user_id, "admin")
        rows = db().execute("SELECT user_id FROM users").fetchall()
        for u in rows:
            bot('sendMessage', {'chat_id': u['user_id'], 'text': text})
            time.sleep(0.05)  # anti flood
        bot('sendMessage', {'chat_id': chat_id, 'text': "✅ Broadcast Sent to All Users"})
        return 'ok'

    # ================= DONE COMMAND =================
    if text.startswith("/done") and user_id == OWNER_ID:
        parts = text.split(" ")
        oid   = parts[1] if len(parts) > 1 else None

        if not oid:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Use: /done order_id"})
            return 'ok'

        o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()

        if o:
            o = dict(o)
            db().execute("UPDATE orders SET status='Completed' WHERE id=?", (oid,))
            db().commit()

            user_msg = (
                f"🎉 <b>Your Order Completed!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 <b>Order ID:</b> <code>{oid}</code>\n"
                f"📦 <b>Service:</b> {o['service_name']}\n"
                f"🔢 <b>Quantity:</b> {o['quantity']}\n"
                f"🔗 <b>Link:</b>\n<code>{o['link']}</code>\n\n"
                f"✅ <b>Status:</b> Completed\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💎 Thank you for using our service!"
            )
            bot('sendMessage', {'chat_id': o['user_id'], 'text': user_msg, 'parse_mode': "HTML"})
            bot('sendMessage', {'chat_id': chat_id, 'text': f"✅ Order #{oid} marked as Completed"})
        else:
            bot('sendMessage', {'chat_id': chat_id, 'text': "❌ Order not found"})

        return 'ok'

    return 'ok'

# ================= RUN =================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
