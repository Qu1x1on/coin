import os
import time
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

supabase_client = None

def get_supabase_client(url=None, key=None):
    """Initializes or returns the Supabase client safely."""
    global supabase_client
    u = url or SUPABASE_URL
    k = key or SUPABASE_KEY
    if not u or not k:
        return None
    try:
        from supabase import create_client, Client
        return create_client(u, k)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        return None

# Initialize default client if env vars present
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = get_supabase_client()

# Cache for coin prices to avoid rate limiting
COIN_CACHE = {
    'timestamp': 0,
    'data': []
}

FALLBACK_COINS = [
    {
        "id": "bitcoin",
        "symbol": "BTC",
        "name": "Bitcoin",
        "current_price": 96420.50,
        "price_change_percentage_24h": 2.45,
        "market_cap": 1890000000000,
        "total_volume": 42500000000,
        "high_24h": 97800.00,
        "low_24h": 94100.00,
        "sparkline": [94100, 94600, 95200, 95900, 96100, 96420]
    },
    {
        "id": "ethereum",
        "symbol": "ETH",
        "name": "Ethereum",
        "current_price": 2740.80,
        "price_change_percentage_24h": -1.15,
        "market_cap": 330000000000,
        "total_volume": 19400000000,
        "high_24h": 2820.00,
        "low_24h": 2710.00,
        "sparkline": [2810, 2790, 2760, 2730, 2720, 2740]
    },
    {
        "id": "solana",
        "symbol": "SOL",
        "name": "Solana",
        "current_price": 184.25,
        "price_change_percentage_24h": 5.82,
        "market_cap": 86000000000,
        "total_volume": 6800000000,
        "high_24h": 188.00,
        "low_24h": 172.50,
        "sparkline": [173, 176, 178, 181, 183, 184]
    },
    {
        "id": "toncoin",
        "symbol": "TON",
        "name": "Toncoin",
        "current_price": 5.85,
        "price_change_percentage_24h": 3.12,
        "market_cap": 14500000000,
        "total_volume": 410000000,
        "high_24h": 6.05,
        "low_24h": 5.60,
        "sparkline": [5.6, 5.68, 5.75, 5.82, 5.8, 5.85]
    },
    {
        "id": "binancecoin",
        "symbol": "BNB",
        "name": "BNB",
        "current_price": 645.10,
        "price_change_percentage_24h": 0.85,
        "market_cap": 94000000000,
        "total_volume": 1200000000,
        "high_24h": 652.00,
        "low_24h": 638.00,
        "sparkline": [640, 642, 641, 644, 646, 645]
    },
    {
        "id": "ripple",
        "symbol": "XRP",
        "name": "XRP",
        "current_price": 2.48,
        "price_change_percentage_24h": 8.64,
        "market_cap": 142000000000,
        "total_volume": 9800000000,
        "high_24h": 2.65,
        "low_24h": 2.25,
        "sparkline": [2.26, 2.31, 2.38, 2.45, 2.52, 2.48]
    },
    {
        "id": "cardano",
        "symbol": "ADA",
        "name": "Cardano",
        "current_price": 0.78,
        "price_change_percentage_24h": -0.45,
        "market_cap": 27500000000,
        "total_volume": 850000000,
        "high_24h": 0.82,
        "low_24h": 0.76,
        "sparkline": [0.81, 0.79, 0.77, 0.78, 0.77, 0.78]
    },
    {
        "id": "avalanche-2",
        "symbol": "AVAX",
        "name": "Avalanche",
        "current_price": 32.40,
        "price_change_percentage_24h": 4.15,
        "market_cap": 13200000000,
        "total_volume": 590000000,
        "high_24h": 33.50,
        "low_24h": 30.80,
        "sparkline": [31.0, 31.4, 31.8, 32.2, 32.8, 32.4]
    }
]

# In-memory watchlist fallback when Supabase is not connected
MEMORY_WATCHLIST = [
    {
        "id": "demo-1",
        "symbol": "BTC",
        "name": "Bitcoin",
        "target_price": 120000.0,
        "notes": "HODL! Основной актив портфеля.",
        "created_at": "2026-02-20T10:00:00Z"
    },
    {
        "id": "demo-2",
        "symbol": "ETH",
        "name": "Ethereum",
        "target_price": 4500.0,
        "notes": "Стейкинг и L2 экосистемы",
        "created_at": "2026-02-20T10:05:00Z"
    },
    {
        "id": "demo-3",
        "symbol": "TON",
        "name": "Toncoin",
        "target_price": 10.0,
        "notes": "Интеграция с Telegram Apps",
        "created_at": "2026-02-20T10:10:00Z"
    }
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    """Healthcheck endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "service": "coin-web-app",
        "timestamp": time.time(),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY)
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
                res = client.table('watchlist').select('*').limit(1).execute()
                db_connected = True
        except Exception as e:
            error_msg = str(e)
            db_connected = False

    return jsonify({
        "app_name": "Coin Platform",
        "environment": "production" if os.getenv('RENDER') else "development",
        "supabase": {
            "configured": has_env,
            "connected": db_connected,
            "url": SUPABASE_URL[:18] + "..." if SUPABASE_URL else None,
            "error": error_msg
        }
    })

@app.route('/api/coins')
def get_coins():
    """Fetch live crypto market data with local caching and fallback."""
    global COIN_CACHE
    now = time.time()

    # Return cached data if fresh (less than 45 seconds)
    if COIN_CACHE['data'] and (now - COIN_CACHE['timestamp'] < 45):
        return jsonify({"source": "cache", "data": COIN_CACHE['data']})

    try:
        # Fetch from CoinGecko API
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

    # Fallback data
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
        return jsonify({"error": "Символ монеты обязателен (напр. BTC, ETH)"}), 400

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

    # Memory fallback
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

    # Memory fallback
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
            "message": f"Ошибка подключения: {str(e)}. Проверьте URL, Ключ и создана ли таблица 'watchlist'."
        }), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
