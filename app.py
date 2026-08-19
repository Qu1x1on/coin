import os
import time
import json
import uuid
import hmac
import hashlib
import urllib.parse
import threading
import requests
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

# Load environment variables safely
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-secret-key-12345')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
SUPABASE_KEY = (os.getenv('SUPABASE_KEY', '') or os.getenv('SUPABASE_PUBLISHABLE_KEY', '') or os.getenv('SUPABASE_SECRET_KEY', '')).strip()

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8514899291:AAE7F-rk6_X99izW-9LEKOkdlknNIHd2jgs').strip()

STARTING_BALANCE = 100.0

# Memory fallback storage
MEMORY_STATE = {
    "coin": {"name": "Дискойн", "symbol": "🪙", "value": 12.5},
    "accounts": [],
    "transactions": []
}

def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase init error: {e}")
        return None

def verify_telegram_init_data(init_data: str, bot_token: str):
    """Validates Telegram WebApp initData string using HMAC-SHA256."""
    if not init_data or not bot_token:
        return False, None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return False, None

        items = [f"{k}={v}" for k, v in sorted(parsed.items())]
        data_check_string = "\n".join(items)

        secret_key = hmac.new(b"WebAppData", bot_token.encode('utf-8'), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

        is_valid = hmac.compare_digest(received_hash, calculated_hash)
        user_dict = json.loads(parsed.get('user', '{}')) if 'user' in parsed else None
        return is_valid, user_dict
    except Exception as e:
        print(f"Telegram verification error: {e}")
        return False, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "coin-tracker",
        "timestamp": time.time()
    }), 200

@app.route('/api/data', methods=['GET'])
def get_all_data():
    """Returns coin config, all accounts, and recent transactions."""
    client = get_supabase_client()
    coin = MEMORY_STATE["coin"]
    accounts = MEMORY_STATE["accounts"]
    transactions = MEMORY_STATE["transactions"]

    if client:
        try:
            # Coin config
            c_res = client.table('coin_config').select('*').limit(1).execute()
            if c_res.data and len(c_res.data) > 0:
                coin = {
                    "name": c_res.data[0].get("name", "Дискойн"),
                    "symbol": c_res.data[0].get("symbol", "🪙"),
                    "value": float(c_res.data[0].get("value", 12.5))
                }
                MEMORY_STATE["coin"] = coin

            # Accounts
            a_res = client.table('accounts').select('*').order('balance', desc=True).execute()
            if a_res.data is not None:
                accounts = [
                    {
                        "id": str(a["id"]),
                        "name": a["name"],
                        "balance": float(a.get("balance", 0)),
                        "telegram_id": a.get("telegram_id"),
                        "username": a.get("username")
                    }
                    for a in a_res.data
                ]
                MEMORY_STATE["accounts"] = accounts

            # Transactions
            t_res = client.table('transactions').select('*').order('timestamp', desc=True).limit(50).execute()
            if t_res.data is not None:
                transactions = [
                    {
                        "id": str(t["id"]),
                        "from": t["from_id"],
                        "fromName": t["from_name"],
                        "to": t["to_id"],
                        "toName": t["to_name"],
                        "amount": float(t["amount"]),
                        "timestamp": int(t["timestamp"])
                    }
                    for t in t_res.data
                ]
                MEMORY_STATE["transactions"] = transactions

        except Exception as e:
            print(f"Supabase fetch error: {e}")

    return jsonify({
        "coin": coin,
        "accounts": accounts,
        "transactions": transactions
    })

@app.route('/api/profile', methods=['POST'])
def handle_profile():
    """Logs in or creates an account by name or Telegram info."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    tg_user = data.get('tg_user')
    init_data = data.get('initData')

    client = get_supabase_client()

    # If Telegram user provided
    if tg_user and isinstance(tg_user, dict):
        tg_id = tg_user.get('id')
        first_name = tg_user.get('first_name', '').strip()
        last_name = tg_user.get('last_name', '').strip()
        username = tg_user.get('username', '').strip()
        tg_name = f"{first_name} {last_name}".strip() or username or f"TG_{tg_id}"

        # 1. Search in Supabase
        if client:
            try:
                res = client.table('accounts').select('*').eq('telegram_id', tg_id).execute()
                if res.data and len(res.data) > 0:
                    acc = res.data[0]
                    return jsonify({"account": {
                        "id": str(acc["id"]),
                        "name": acc["name"],
                        "balance": float(acc["balance"]),
                        "telegram_id": acc.get("telegram_id"),
                        "username": acc.get("username")
                    }})
            except Exception as e:
                print(f"Supabase TG search error: {e}")

        # 2. Check in memory
        for a in MEMORY_STATE["accounts"]:
            if a.get("telegram_id") == tg_id:
                return jsonify({"account": a})

        # 3. Create new TG account
        acc_id = f"acc_{uuid.uuid4().hex[:8]}"
        new_acc = {
            "id": acc_id,
            "name": tg_name,
            "telegram_id": tg_id,
            "username": username,
            "balance": STARTING_BALANCE
        }

        if client:
            try:
                client.table('accounts').insert(new_acc).execute()
            except Exception as e:
                print(f"Supabase insert TG acc error: {e}")

        MEMORY_STATE["accounts"].append(new_acc)
        return jsonify({"account": new_acc})

    # Manual Name login / creation
    if not name:
        return jsonify({"error": "Введите имя участника"}), 400

    # Search existing
    if client:
        try:
            res = client.table('accounts').select('*').ilike('name', name).execute()
            if res.data and len(res.data) > 0:
                acc = res.data[0]
                return jsonify({"account": {
                    "id": str(acc["id"]),
                    "name": acc["name"],
                    "balance": float(acc["balance"])
                }})
        except Exception as e:
            print(f"Supabase search error: {e}")

    for a in MEMORY_STATE["accounts"]:
        if a["name"].lower() == name.lower():
            return jsonify({"account": a})

    # Create new
    acc_id = f"acc_{uuid.uuid4().hex[:8]}"
    new_acc = {
        "id": acc_id,
        "name": name,
        "balance": STARTING_BALANCE
    }

    if client:
        try:
            client.table('accounts').insert(new_acc).execute()
        except Exception as e:
            print(f"Supabase insert error: {e}")

    MEMORY_STATE["accounts"].append(new_acc)
    return jsonify({"account": new_acc})

@app.route('/api/coin', methods=['POST'])
def update_coin():
    """Updates the exchange rate of the coin."""
    data = request.get_json() or {}
    val = data.get('value')
    name = data.get('name')
    symbol = data.get('symbol')

    try:
        val = float(val)
        if val <= 0:
            return jsonify({"error": "Курс должен быть больше 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректное значение курса"}), 400

    coin_data = MEMORY_STATE["coin"]
    coin_data["value"] = val
    if name: coin_data["name"] = name
    if symbol: coin_data["symbol"] = symbol

    client = get_supabase_client()
    if client:
        try:
            client.table('coin_config').upsert({
                "id": "main",
                "name": coin_data["name"],
                "symbol": coin_data["symbol"],
                "value": val,
                "updated_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }).execute()
        except Exception as e:
            print(f"Supabase coin update error: {e}")

    return jsonify({"status": "success", "coin": coin_data})

@app.route('/api/transfer', methods=['POST'])
def make_transfer():
    """Transfers coins from one account to another and saves transaction."""
    data = request.get_json() or {}
    from_id = data.get('from_id')
    to_id = data.get('to_id')
    amount_str = data.get('amount')

    if not from_id or not to_id:
        return jsonify({"error": "Выберите получателя."}), 400

    if from_id == to_id:
        return jsonify({"error": "Нельзя перевести самому себе."}), 400

    try:
        amt = float(amount_str)
        if amt <= 0:
            return jsonify({"error": "Введите корректную сумму."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Введите корректную сумму."}), 400

    client = get_supabase_client()

    # Find accounts
    sender = None
    recipient = None

    if client:
        try:
            s_res = client.table('accounts').select('*').eq('id', from_id).execute()
            r_res = client.table('accounts').select('*').eq('id', to_id).execute()
            if s_res.data: sender = s_res.data[0]
            if r_res.data: recipient = r_res.data[0]
        except Exception as e:
            print(f"Supabase fetch accounts error: {e}")

    if not sender:
        sender = next((a for a in MEMORY_STATE["accounts"] if a["id"] == from_id), None)
    if not recipient:
        recipient = next((a for a in MEMORY_STATE["accounts"] if a["id"] == to_id), None)

    if not sender or not recipient:
        return jsonify({"error": "Участник не найден."}), 404

    sender_balance = float(sender.get("balance", 0))
    recipient_balance = float(recipient.get("balance", 0))

    if amt > sender_balance:
        return jsonify({"error": "Недостаточно монет на балансе."}), 400

    new_sender_balance = sender_balance - amt
    new_recipient_balance = recipient_balance + amt

    tx_id = f"tx_{uuid.uuid4().hex[:8]}"
    now_ts = int(time.time() * 1000)

    tx_record = {
        "id": tx_id,
        "from_id": from_id,
        "from_name": sender.get("name", "?"),
        "to_id": to_id,
        "to_name": recipient.get("name", "?"),
        "amount": amt,
        "timestamp": now_ts
    }

    # Save to Supabase
    if client:
        try:
            client.table('accounts').update({"balance": new_sender_balance}).eq('id', from_id).execute()
            client.table('accounts').update({"balance": new_recipient_balance}).eq('id', to_id).execute()
            client.table('transactions').insert(tx_record).execute()
        except Exception as e:
            print(f"Supabase transfer transaction error: {e}")

    # Update in memory
    for a in MEMORY_STATE["accounts"]:
        if a["id"] == from_id: a["balance"] = new_sender_balance
        if a["id"] == to_id: a["balance"] = new_recipient_balance

    MEMORY_STATE["transactions"].insert(0, {
        "id": tx_id,
        "from": from_id,
        "fromName": sender.get("name", "?"),
        "to": to_id,
        "toName": recipient.get("name", "?"),
        "amount": amt,
        "timestamp": now_ts
    })

    return jsonify({
        "status": "success",
        "tx": tx_record,
        "sender_balance": new_sender_balance,
        "recipient_balance": new_recipient_balance
    })

# Background Telegram Bot Polling
def run_telegram_bot_poller():
    if not TELEGRAM_BOT_TOKEN:
        return
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 20}
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                updates = resp.json().get('result', [])
                for update in updates:
                    offset = update['update_id'] + 1
                    msg = update.get('message')
                    if not msg:
                        continue
                    text = msg.get('text', '')
                    chat_id = msg['chat']['id']
                    first_name = msg.get('from', {}).get('first_name', 'пользователь')

                    if text.startswith('/start'):
                        reply_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        render_url = os.getenv('RENDER_EXTERNAL_URL', 'https://coin-app.onrender.com')
                        
                        reply_payload = {
                            "chat_id": chat_id,
                            "text": f"👋 Привет, {first_name}!\n\nДобро пожаловать в 🪙 *Coin Tracker*.\n\nНажмите кнопку ниже, чтобы открыть приложение и управлять балансом:",
                            "parse_mode": "Markdown",
                            "reply_markup": {
                                "inline_keyboard": [
                                    [
                                        {
                                            "text": "🪙 Открыть Coin Tracker",
                                            "web_app": {"url": render_url}
                                        }
                                    ]
                                ]
                            }
                        }
                        requests.post(reply_url, json=reply_payload, timeout=5)
        except Exception as e:
            time.sleep(5)

if TELEGRAM_BOT_TOKEN:
    bot_thread = threading.Thread(target=run_telegram_bot_poller, daemon=True)
    bot_thread.start()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
