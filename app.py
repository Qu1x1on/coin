import os
import time
import json
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

supabase_client = None

def get_supabase_client(url=None, key=None):
    """Initializes or returns the Supabase client safely."""
    global supabase_client
    u = url or SUPABASE_URL
    k = key or SUPABASE_KEY
    if not u or not k:
        return None
    try:
        from supabase import create_client
        return create_client(u, k)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        return None

# Initialize default client if env vars present
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = get_supabase_client()

# In-memory storage fallback
MEMORY_TELEGRAM_USERS = {}
COIN_CACHE = {'timestamp': 0, 'data': []}

FALLBACK_COINS = [
    {
        "id": "bitcoin", "symbol": "BTC", "name": "Bitcoin",
        "current_price": 96420.50, "price_change_percentage_24h": 2.45,
        "market_cap": 1890000000000, "total_volume": 42500000000,
        "high_24h": 97800.00, "low_24h": 94100.00
    },
    {
        "id": "ethereum", "symbol": "ETH", "name": "Ethereum",
        "current_price": 2740.80, "price_change_percentage_24h": -1.15,
        "market_cap": 330000000000, "total_volume": 19400000000,
        "high_24h": 2820.00, "low_24h": 2710.00
    },
    {
        "id": "solana", "symbol": "SOL", "name": "Solana",
        "current_price": 184.25, "price_change_percentage_24h": 5.82,
        "market_cap": 86000000000, "total_volume": 6800000000,
        "high_24h": 188.00, "low_24h": 172.50
    },
    {
        "id": "toncoin", "symbol": "TON", "name": "Toncoin",
        "current_price": 5.85, "price_change_percentage_24h": 3.12,
        "market_cap": 14500000000, "total_volume": 410000000,
        "high_24h": 6.05, "low_24h": 5.60
    },
    {
        "id": "binancecoin", "symbol": "BNB", "name": "BNB",
        "current_price": 645.10, "price_change_percentage_24h": 0.85,
        "market_cap": 94000000000, "total_volume": 1200000000,
        "high_24h": 652.00, "low_24h": 638.00
    },
    {
        "id": "ripple", "symbol": "XRP", "name": "XRP",
        "current_price": 2.48, "price_change_percentage_24h": 8.64,
        "market_cap": 142000000000, "total_volume": 9800000000,
        "high_24h": 2.65, "low_24h": 2.25
    }
]

MEMORY_WATCHLIST = [
    {
        "id": "demo-1", "symbol": "BTC", "name": "Bitcoin",
        "target_price": 120000.0, "notes": "HODL! Основной актив портфеля.",
        "created_at": "2026-02-20T10:00:00Z"
    },
    {
        "id": "demo-2", "symbol": "ETH", "name": "Ethereum",
        "target_price": 4500.0, "notes": "Стейкинг и L2 экосистемы",
        "created_at": "2026-02-20T10:05:00Z"
    },
    {
        "id": "demo-3", "symbol": "TON", "name": "Toncoin",
        "target_price": 10.0, "notes": "Интеграция с Telegram Apps",
        "created_at": "2026-02-20T10:10:00Z"
    }
]

def verify_telegram_init_data(init_data: str, bot_token: str):
    """
    Validates Telegram WebApp initData string using HMAC-SHA256.
    Returns (is_valid, user_data_dict)
    """
    if not init_data or not bot_token:
        return False, None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return False, None

        # Build data-check-string
        items = [f"{k}={v}" for k, v in sorted(parsed.items())]
        data_check_string = "\n".join(items)

        # secret_key = HMAC_SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(b"WebAppData", bot_token.encode('utf-8'), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

        is_valid = hmac.compare_digest(received_hash, calculated_hash)
        user_dict = json.loads(parsed.get('user', '{}')) if 'user' in parsed else None
        return is_valid, user_dict
    except Exception as e:
        print(f"Telegram initData verification error: {e}")
        return False, None

@app.route('/')
def index():
    return render_template('index.html', bot_token=TELEGRAM_BOT_TOKEN)

@app.route('/health')
def health():
    """Healthcheck endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "service": "coin-telegram-mini-app",
        "timestamp": time.time(),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "bot_configured": bool(TELEGRAM_BOT_TOKEN)
    }), 200

@app.route('/api/status')
def status():
    """Returns application status and Supabase connection state."""
    has_env = bool(SUPABASE_URL and SUPABASE_KEY)
    db_connected = False
    error_msg = None

    if has_env:
        try:
            client = get_supabase_client()
            if client:
                client.table('watchlist').select('*').limit(1).execute()
                db_connected = True
        except Exception as e:
            error_msg = str(e)
            db_connected = False

    return jsonify({
        "app_name": "Coin Telegram WebApp",
        "environment": "production" if os.getenv('RENDER') else "development",
        "bot_name": "@fanat_mavro_robot",
        "supabase": {
            "configured": has_env,
            "connected": db_connected,
            "url": SUPABASE_URL[:18] + "..." if SUPABASE_URL else None,
            "error": error_msg
        }
    })

@app.route('/api/telegram/auth', methods=['POST'])
def telegram_auth():
    """
    Receives Telegram WebApp initData or user payload, verifies signature,
    and saves/updates user in Supabase database.
    """
    data = request.get_json() or {}
    init_data = data.get('initData', '')
    user_payload = data.get('user', {})

    is_verified = False
    user_info = None

    if init_data and TELEGRAM_BOT_TOKEN:
        is_verified, user_info = verify_telegram_init_data(init_data, TELEGRAM_BOT_TOKEN)

    # Fallback to direct client user payload (with verified=False flag if signature not provided)
    if not user_info and user_payload:
        user_info = user_payload
        is_verified = bool(is_verified)

    if not user_info:
        return jsonify({"error": "No valid user information provided"}), 400

    user_id = user_info.get('id')
    first_name = user_info.get('first_name', '')
    last_name = user_info.get('last_name', '')
    username = user_info.get('username', '')
    photo_url = user_info.get('photo_url', '')
    language_code = user_info.get('language_code', 'ru')
    is_premium = bool(user_info.get('is_premium', False))

    saved_to_db = False

    # Sync with Supabase if configured
    if SUPABASE_URL and SUPABASE_KEY and user_id:
        try:
            client = get_supabase_client()
            if client:
                now_str = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                payload = {
                    "id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "photo_url": photo_url,
                    "language_code": language_code,
                    "is_premium": is_premium,
                    "updated_at": now_str
                }
                client.table('telegram_users').upsert(payload).execute()
                saved_to_db = True
        except Exception as e:
            print(f"Supabase user upsert error: {e}")

    # In-memory save
    if user_id:
        MEMORY_TELEGRAM_USERS[str(user_id)] = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "photo_url": photo_url,
            "language_code": language_code,
            "is_premium": is_premium,
            "verified": is_verified,
            "last_seen": time.time()
        }

    return jsonify({
        "status": "success",
        "verified": is_verified,
        "saved_to_db": saved_to_db,
        "user": {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "photo_url": photo_url,
            "language_code": language_code,
            "is_premium": is_premium
        }
    })

@app.route('/api/telegram/set-menu', methods=['POST'])
def set_telegram_menu():
    """Configures the Telegram Bot's Menu Button to open this Mini App"""
    data = request.get_json() or {}
    web_app_url = data.get('url') or request.host_url
    if not web_app_url.startswith('https://'):
        # Telegram WebApps require https in production
        web_app_url = f"https://{request.host}" if not request.is_secure else request.host_url

    try:
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setChatMenuButton"
        payload = {
            "menu_button": {
                "type": "web_app",
                "text": "🪙 COIN HUB",
                "web_app": {
                    "url": web_app_url
                }
            }
        }
        resp = requests.post(tg_url, json=payload, timeout=5)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/coins')
def get_coins():
    """Fetch live crypto market data with local caching and fallback."""
    global COIN_CACHE
    now = time.time()

    if COIN_CACHE['data'] and (now - COIN_CACHE['timestamp'] < 45):
        return jsonify({"source": "cache", "data": COIN_CACHE['data']})

    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": "bitcoin,ethereum,solana,the-open-network,binancecoin,ripple,cardano,avalanche-2,dogecoin,polkadot",
            "order": "market_cap_desc",
            "sparkline": "false",
            "price_change_percentage": "24h"
        }
        resp = requests.get(url, params=params, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            formatted_data = []
            for item in data:
                formatted_data.append({
                    "id": item.get("id"),
                    "symbol": item.get("symbol", "").upper(),
                    "name": item.get("name"),
                    "current_price": item.get("current_price", 0),
                    "price_change_percentage_24h": item.get("price_change_percentage_24h", 0),
                    "market_cap": item.get("market_cap", 0),
                    "total_volume": item.get("total_volume", 0),
                    "high_24h": item.get("high_24h", 0),
                    "low_24h": item.get("low_24h", 0),
                    "image": item.get("image")
                })
            COIN_CACHE = {'timestamp': now, 'data': formatted_data}
            return jsonify({"source": "live", "data": formatted_data})
    except Exception as e:
        print(f"Live coin fetch failed, using fallback: {e}")

    return jsonify({"source": "fallback", "data": FALLBACK_COINS})

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """Retrieve watchlist items from Supabase or memory fallback."""
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            client = get_supabase_client()
            if client:
                res = client.table('watchlist').select('*').order('created_at', desc=True).execute()
                return jsonify({"source": "supabase", "data": res.data})
        except Exception as e:
            print(f"Supabase query error: {e}")
            return jsonify({"source": "memory", "data": MEMORY_WATCHLIST, "warning": str(e)})

    return jsonify({"source": "memory", "data": MEMORY_WATCHLIST})

@app.route('/api/watchlist', methods=['POST'])
def add_watchlist():
    """Add a new coin/note to the watchlist."""
    data = request.get_json() or {}
    symbol = data.get('symbol', '').strip().upper()
    name = data.get('name', '').strip() or symbol
    target_price = data.get('target_price')
    notes = data.get('notes', '').strip()

    if not symbol:
        return jsonify({"error": "Символ монеты обязателен"}), 400

    try:
        target_price = float(target_price) if target_price is not None and str(target_price).strip() else None
    except ValueError:
        target_price = None

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            client = get_supabase_client()
            if client:
                payload = {
                    "symbol": symbol,
                    "name": name,
                    "target_price": target_price,
                    "notes": notes
                }
                res = client.table('watchlist').insert(payload).execute()
                return jsonify({"status": "success", "source": "supabase", "item": res.data[0] if res.data else payload})
        except Exception as e:
            return jsonify({"error": f"Supabase insert failed: {str(e)}"}), 500

    import uuid
    new_item = {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "name": name,
        "target_price": target_price,
        "notes": notes,
        "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }
    MEMORY_WATCHLIST.insert(0, new_item)
    return jsonify({"status": "success", "source": "memory", "item": new_item})

@app.route('/api/watchlist/<item_id>', methods=['DELETE'])
def delete_watchlist(item_id):
    """Delete a watchlist item."""
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            client = get_supabase_client()
            if client:
                client.table('watchlist').delete().eq('id', item_id).execute()
                return jsonify({"status": "deleted", "source": "supabase", "id": item_id})
        except Exception as e:
            return jsonify({"error": f"Supabase delete failed: {str(e)}"}), 500

    global MEMORY_WATCHLIST
    MEMORY_WATCHLIST = [x for x in MEMORY_WATCHLIST if str(x.get('id')) != str(item_id)]
    return jsonify({"status": "deleted", "source": "memory", "id": item_id})

@app.route('/api/test-supabase', methods=['POST'])
def test_supabase_credentials():
    """Test custom Supabase credentials directly from the UI."""
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    key = data.get('key', '').strip()

    if not url or not key:
        return jsonify({"success": False, "message": "Укажите URL и anon/service_role ключ"}), 400

    try:
        from supabase import create_client
        client = create_client(url, key)
        res = client.table('watchlist').select('*').limit(1).execute()
        return jsonify({
            "success": True, 
            "message": "Успешное подключение к Supabase! Таблица 'watchlist' доступна.",
            "sample_count": len(res.data)
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"Ошибка подключения: {str(e)}."
        }), 400

# Background Telegram Bot Polling (Replies to /start with Mini App button)
def run_telegram_bot_poller():
    """Simple Telegram Bot polling thread to handle /start command"""
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
                        # Send greeting with WebApp button
                        reply_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        
                        # In production on Render, RENDER_EXTERNAL_URL is available
                        render_url = os.getenv('RENDER_EXTERNAL_URL', 'https://coin-app.onrender.com')
                        
                        reply_payload = {
                            "chat_id": chat_id,
                            "text": f"👋 Привет, {first_name}!\n\nДобро пожаловать в 🪙 *COIN HUB Mini App*.\n\nНажмите кнопку ниже, чтобы открыть веб-приложение:",
                            "parse_mode": "Markdown",
                            "reply_markup": {
                                "inline_keyboard": [
                                    [
                                        {
                                            "text": "🚀 Открыть COIN HUB",
                                            "web_app": {"url": render_url}
                                        }
                                    ]
                                ]
                            }
                        }
                        requests.post(reply_url, json=reply_payload, timeout=5)
        except Exception as e:
            time.sleep(5)

# Start bot poller in daemon thread
if TELEGRAM_BOT_TOKEN:
    bot_thread = threading.Thread(target=run_telegram_bot_poller, daemon=True)
    bot_thread.start()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
