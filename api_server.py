# api_server.py (Modified Version)
from flask import Flask, request, jsonify
from functools import wraps
import time
import os
import json

app = Flask(__name__)

# --- ADDED: Logic to load users from users.json ---
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')

def load_user_tokens():
    if not os.path.exists(USERS_FILE_PATH):
        return {}
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            users = json.load(f)
            token_map = {}
            for user in users:
                permission = user.get("permission_level")
                limit = 5  # Default for 'free'
                if permission == 'plus':
                    limit = 15
                elif permission == 'pro':
                    limit = 30
                token_map[user["token"]] = {"role": permission, "limit": limit}
            return token_map
        except (json.JSONDecodeError, KeyError):
            return {}
# --- END ADDED ---

RATE_LIMIT = {}

def rate_limiter(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # --- CHANGED: Load tokens dynamically ---
        current_tokens = load_user_tokens()
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if token not in current_tokens:
            return jsonify({"error": "Invalid or unknown token"}), 401
        
        role = current_tokens[token]["role"]
        limit = current_tokens[token]["limit"]
        # --- END CHANGED ---

        now = int(time.time())
        window = 60
        key = f"{token}:{now // window}"
        RATE_LIMIT.setdefault(key, 0)

        if RATE_LIMIT[key] >= limit:
            return jsonify({"error": "Too Many Requests"}), 429
        
        RATE_LIMIT[key] += 1
        return f(*args, **kwargs)
    return decorated

@app.route("/api/flights")
@rate_limiter
def flights():
    # 回傳假資料
    return jsonify({
        "flights": [
            {"flight": "API-111", "from": "TPE", "to": "NRT", "time": "10:00", "price": 5000},
            {"flight": "API-222", "from": "TPE", "to": "HND", "time": "12:00", "price": 5200}
        ]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)