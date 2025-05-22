from flask import Flask, request, jsonify
from functools import wraps
import time

app = Flask(__name__)

# 模擬用戶資料與權限
TOKENS = {
    "user-token": {"role": "user", "limit": 5},
    "vip-token": {"role": "vip", "limit": 30}
}
# 記錄每個 token 的請求時間戳
RATE_LIMIT = {}

# 速率限制裝飾器
def rate_limiter(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token not in TOKENS:
            return jsonify({"error": "Invalid token"}), 401
        role = TOKENS[token]["role"]
        limit = TOKENS[token]["limit"]
        now = int(time.time())
        window = 60  # 1 分鐘
        key = f"{token}:{now // window}"
        RATE_LIMIT.setdefault(key, 0)
        if RATE_LIMIT[key] >= limit:
            # 超速，回傳 429
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
            {"flight": "AB123", "from": "TPE", "to": "NRT", "time": "10:00", "price": 5000},
            {"flight": "CD456", "from": "TPE", "to": "HND", "time": "12:00", "price": 5200}
        ]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
