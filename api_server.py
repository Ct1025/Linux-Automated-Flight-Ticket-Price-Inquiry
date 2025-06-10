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
                # 調整速率限制以匹配查詢間隔
                # free: 6秒間隔 = 每分鐘最多10次，設定為15次提供緩衝
                # plus: 4秒間隔 = 每分鐘最多15次，設定為25次提供緩衝  
                # pro: 2秒間隔 = 每分鐘最多30次，維持100次的高限制
                limit = 15  # free 用戶預設限制
                if permission == 'plus':
                    limit = 25
                elif permission == 'pro':
                    limit = 100
                token_map[user["token"]] = {"role": permission, "limit": limit}
            return token_map
        except (json.JSONDecodeError, KeyError):
            return {}


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

# NEW: Mapping for user-friendly cabin types to internal price categories
CABIN_TYPE_MAP = {
    "經濟艙": "normal",  # Default to 'normal' for 經濟艙 if not specified further
    "經濟艙促銷": "promo",  # Example: If you want to specify a promo economy
    "商務艙": "peak",
    "頭等艙": "peak"
}


# <<< REMOVED: 不再需要預先生成 ALL_FLIGHTS 和 populate_flights_database() >>>

# <<< NEW: 全新的即時生成函式 >>>
def generate_flights_on_demand(params):
    """根據傳入的條件，即時生成完全符合的航班列表"""

    # 從參數中獲取條件
    from_loc = params.get('from')
    to_loc = params.get('to')
    date_str = params.get('date')
    req_type = params.get('type')  # This is the raw type from query params
    min_p = params.get('min_price', 0)
    max_p = params.get('max_price', 99999)
    count = params.get('count', 1)  # 要生成的數量

    # 如果缺少基本條件，回傳空列表
    if not from_loc or not to_loc or not date_str:
        return []

    generated_flights = []
    for _ in range(count):
        # Determine the internal ticket_type based on req_type or random choice
        # If req_type is provided and in CABIN_TYPE_MAP, use that mapping.
        # Otherwise, if req_type is one of the direct price categories, use it.
        # Fallback to random if neither applies.

        # Priority 1: Use mapping if available
        if req_type and req_type in CABIN_TYPE_MAP:
            ticket_type = CABIN_TYPE_MAP[req_type]
        # Priority 2: Use req_type directly if it's one of the known internal categories
        elif req_type in ["promo", "normal", "peak"]:
            ticket_type = req_type
        # Priority 3: Fallback to random if no specific type is requested or recognized
        else:
            ticket_type = random.choice(["promo", "normal", "peak"])

        # 根據航線和票種，取得對應的價格範圍
        route_prices = PRICE_CATEGORIES.get((from_loc, to_loc), DEFAULT_PRICE_RANGES)

        # Safely get the price range tuple, providing a default if ticket_type not found
        # This is where the TypeError was likely occurring if ticket_type was unrecognized
        type_price_range = route_prices.get(ticket_type, (0, 99999))  # Default to wide range

        type_min_p, type_max_p = type_price_range

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
            "type": ticket_type  # Use the internal ticket_type here
        }
        generated_flights.append(flight)

    return sorted(generated_flights, key=lambda x: x['price'])


@app.route("/api/flights")
@rate_limiter
def flights():
    # 1. 獲取所有查詢參數
    query_params = request.args.to_dict(flat=True)

    # Robustly convert min_price and max_price to int
    try:
        query_params['min_price'] = int(query_params.get('min_price', 0))
    except ValueError:
        return jsonify({"error": "Invalid 'min_price' format. Must be an integer."}), 400

    try:
        query_params['max_price'] = int(query_params.get('max_price', 99999))
    except ValueError:
        return jsonify({"error": "Invalid 'max_price' format. Must be an integer."}), 400

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
    app.run(host="0.0.0.0", port=5000, debug=True)  # Added debug=True for development