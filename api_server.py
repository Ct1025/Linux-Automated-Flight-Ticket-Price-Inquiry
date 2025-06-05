# api_server.py (Final Corrected Version with On-Demand Generation)
from flask import Flask, request, jsonify
from functools import wraps
import time
import os
import json
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# --- 使用者載入與速率限制邏輯 (不變) ---
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
def load_user_tokens():
    if not os.path.exists(USERS_FILE_PATH): return {}
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            users = json.load(f)
            token_map = {}
            for user in users:
                permission = user.get("permission_level")
                limit = 5
                if permission == 'plus': limit = 15
                elif permission == 'pro': limit = 30
                token_map[user["token"]] = {"role": permission, "limit": limit}
            return token_map
        except (json.JSONDecodeError, KeyError): return {}
RATE_LIMIT = {}
def rate_limiter(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_tokens = load_user_tokens()
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token not in current_tokens:
            return jsonify({"error": "Invalid or unknown token"}), 401
        limit = current_tokens[token]["limit"]
        now = int(time.time())
        window = 60
        key = f"{token}:{now // window}"
        RATE_LIMIT.setdefault(key, 0)
        if RATE_LIMIT[key] >= limit:
            return jsonify({"error": "Too Many Requests"}), 429
        RATE_LIMIT[key] += 1
        return f(*args, **kwargs)
    return decorated
# --- END ---

# --- 規則定義 (不變) ---
AIRLINES = {
    "CI": "China Airlines", "BR": "EVA Air", "JX": "Starlux",
    "TG": "Thai Airways", "JL": "Japan Airlines", "SQ": "Singapore Airlines",
    "TR": "Scoot", "IT": "Tigerair Taiwan"
}
PRICE_CATEGORIES = {
    ("TPE", "NRT"): {"promo": (3500, 5500), "normal": (6000, 10000), "peak": (11000, 16000)},
    ("TPE", "KIX"): {"promo": (3500, 5500), "normal": (6000, 10000), "peak": (11000, 16000)},
    ("TPE", "SIN"): {"promo": (3500, 5500), "normal": (6000, 9000), "peak": (9000, 12000)},
    ("TPE", "BKK"): {"promo": (3000, 5000), "normal": (5500, 8500), "peak": (8500, 11000)},
}
DEFAULT_PRICE_RANGES = {"promo": (2000, 4000), "normal": (4000, 7000), "peak": (7000, 10000)}

# <<< REMOVED: 不再需要預先生成 ALL_FLIGHTS 和 populate_flights_database() >>>

# <<< NEW: 全新的即時生成函式 >>>
def generate_flights_on_demand(params):
    """根據傳入的條件，即時生成完全符合的航班列表"""
    
    # 從參數中獲取條件
    from_loc = params.get('from')
    to_loc = params.get('to')
    date_str = params.get('date')
    req_type = params.get('type')
    min_p = params.get('min_price', 0)
    max_p = params.get('max_price', 99999)
    count = params.get('count', 1) # 要生成的數量

    # 如果缺少基本條件，回傳空列表
    if not from_loc or not to_loc or not date_str:
        return []

    generated_flights = []
    for _ in range(count):
        # 如果使用者指定了票種，就用該票種；否則隨機選一個
        ticket_type = req_type if req_type else random.choice(["promo", "normal", "peak"])
        
        # 根據航線和票種，取得對應的價格範圍
        route_prices = PRICE_CATEGORIES.get((from_loc, to_loc), DEFAULT_PRICE_RANGES)
        type_min_p, type_max_p = route_prices.get(ticket_type)

        # 在票種的價格範圍和使用者指定的價格範圍之間，取交集
        final_min_price = max(min_p, type_min_p)
        final_max_price = min(max_p, type_max_p)

        # 如果價格交集無效（例如最低價>最高價），則跳過此筆生成
        if final_min_price > final_max_price:
            continue
            
        airline_code = random.choice(list(AIRLINES.keys()))
        flight = {
            "flight": f"{airline_code}-{random.randint(100, 999)}",
            "airline": AIRLINES[airline_code],
            "from": from_loc, "to": to_loc,
            "date": date_str,
            "time": f"{random.randint(7, 21):02d}:{random.choice(['00', '30'])}",
            "price": random.randint(final_min_price, final_max_price) // 100 * 100,
            "type": ticket_type
        }
        generated_flights.append(flight)
    
    return sorted(generated_flights, key=lambda x: x['price'])


@app.route("/api/flights")
@rate_limiter
def flights():
    # 1. 獲取所有查詢參數
    query_params = request.args.to_dict(flat=True)
    query_params['min_price'] = int(query_params.get('min_price', 0))
    query_params['max_price'] = int(query_params.get('max_price', 99999))
    
    # 2. 根據使用者權限決定生成密度 (要生成幾筆)
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user_permission = load_user_tokens().get(token, {}).get("role", "free")
    density_config = {"pro": 3, "plus": 2, "free": 1}
    query_params['count'] = density_config.get(user_permission, 1)

    # 3. 呼叫新的即時生成函式
    final_flights = generate_flights_on_demand(query_params)
    
    # 4. 回傳結果
    return jsonify({"flights": final_flights})

if __name__ == "__main__":
    # 不再需要啟動時生成資料庫
    app.run(host="0.0.0.0", port=5000)