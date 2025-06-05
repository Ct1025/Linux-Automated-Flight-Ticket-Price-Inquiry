# api_server.py (Upgraded with Search Functionality)
from flask import Flask, request, jsonify
from functools import wraps
import time
import os
import json

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

# <<< ADDED: A larger "database" of flights to make searching meaningful >>>
ALL_FLIGHTS = [
    {"flight": "CI-100", "airline": "China Airlines", "from": "TPE", "to": "NRT", "time": "09:30", "price": 7500},
    {"flight": "BR-198", "airline": "EVA Air", "from": "TPE", "to": "NRT", "time": "08:50", "price": 7800},
    {"flight": "JX-800", "airline": "Starlux", "from": "TPE", "to": "NRT", "time": "10:00", "price": 8200},
    {"flight": "CI-104", "airline": "China Airlines", "from": "TPE", "to": "HND", "time": "14:20", "price": 8500},
    {"flight": "BR-190", "airline": "EVA Air", "from": "TPE", "to": "HND", "time": "16:00", "price": 8300},
    {"flight": "CI-156", "airline": "China Airlines", "from": "TPE", "to": "KIX", "time": "08:30", "price": 6800},
    {"flight": "JX-820", "airline": "Starlux", "from": "TPE", "to": "KIX", "time": "09:45", "price": 7200},
    {"flight": "BR-225", "airline": "EVA Air", "from": "TPE", "to": "SIN", "time": "07:40", "price": 9500},
    {"flight": "CI-751", "airline": "China Airlines", "from": "TPE", "to": "SIN", "time": "13:50", "price": 9200},
    {"flight": "TG-635", "airline": "Thai Airways", "from": "TPE", "to": "BKK", "time": "20:05", "price": 6500},
]

# <<< CHANGED: The flights endpoint now performs filtering >>>
@app.route("/api/flights")
@rate_limiter
def flights():
    # 從 URL 查詢參數中獲取客戶端傳來的條件
    # 例如: /api/flights?from=TPE&to=NRT
    query_from = request.args.get('from', default=None, type=str)
    query_to = request.args.get('to', default=None, type=str)
    
    # 開始篩選
    filtered_flights = ALL_FLIGHTS
    
    if query_from:
        filtered_flights = [f for f in filtered_flights if f['from'].upper() == query_from.upper()]
        
    if query_to:
        filtered_flights = [f for f in filtered_flights if f['to'].upper() == query_to.upper()]
        
    # 未來可以繼續增加對日期、價格等的篩選...

    # 回傳篩選後的結果
    return jsonify({"flights": filtered_flights})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)