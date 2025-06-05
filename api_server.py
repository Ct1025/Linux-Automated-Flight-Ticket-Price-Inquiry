# api_server.py (Upgraded with Permission-Based Density)
from flask import Flask, request, jsonify
from functools import wraps
import time
import os
import json
import random

app = Flask(__name__)

# --- (此處省略與前版相同的 load_user_tokens, rate_limiter 程式碼以節省篇幅) ---
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
        role = current_tokens[token]["role"]
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


# (此處省略與前版相同的 AIRLINES 字典)
AIRLINES = {
    "CI": "China Airlines",
    "BR": "EVA Air",
    "JX": "Starlux",
    "TG": "Thai Airways",
    "JL": "Japan Airlines"
}

# <<< CHANGED: The generation function now accepts a 'count' parameter >>>
def generate_random_flights(from_loc, to_loc, count):
    """Generates a specific COUNT of random flights."""
    if not from_loc or not to_loc:
        return []

    generated_flights = []
    for _ in range(count): # 使用傳入的 count 來決定生成數量
        airline_code = random.choice(list(AIRLINES.keys()))
        flight = {
            "flight": f"{airline_code}-{random.randint(100, 999)}",
            "airline": AIRLINES[airline_code],
            "from": from_loc,
            "to": to_loc,
            "time": f"{random.randint(7, 21):02d}:{random.choice(['00', '15', '30', '45'])}",
            "price": random.randint(5000, 15000) // 100 * 100
        }
        generated_flights.append(flight)
    
    return sorted(generated_flights, key=lambda x: x['price'])


@app.route("/api/flights")
@rate_limiter
def flights():
    # 從 URL 查詢參數中獲取客戶端傳來的條件
    query_from = request.args.get('from', default=None, type=str)
    query_to = request.args.get('to', default=None, type=str)
    
    # --- ADDED: Logic to determine density based on user permission ---
    # 1. 再次獲取 token 和使用者資料
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    all_users_data = load_user_tokens()
    
    # 2. 根據 token 找到使用者的權限等級
    user_permission = all_users_data.get(token, {}).get("role", "free") # 找不到則預設為 free
    
    # 3. 根據權限設定這次要生成的資料筆數 (密度)
    density_config = {
        "pro": 3,
        "plus": 2,
        "free": 1
    }
    num_to_generate = density_config.get(user_permission, 1) # 找不到權限則預設為 1
    # --- END ADDED ---
    
    # 呼叫生成函式，並傳入要生成的數量
    randomly_generated_flights = generate_random_flights(query_from, query_to, num_to_generate)

    # 回傳動態生成的結果
    return jsonify({"flights": randomly_generated_flights})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)