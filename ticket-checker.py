# ticket-checker.py (Final Version with Token Login)
# --- 省略不變的程式碼 (Imports, NonBlockingInput, load_users, etc.) ---
import os
import sys
import json
import time
from datetime import datetime, timedelta
import requests
class NonBlockingInput:
    def __init__(self):
        self.is_windows = os.name == 'nt'
        if self.is_windows:
            import msvcrt
            self.msvcrt = msvcrt
        else:
            import termios, tty
            self.termios, self.tty = termios, tty
            self.fd = sys.stdin.fileno()
            self.old_settings = None
    def kbhit(self):
        if self.is_windows: return self.msvcrt.kbhit()
        else:
            import select
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            return dr != []
    def getch(self):
        if self.is_windows: return self.msvcrt.getwch()
        else:
            self.old_settings = self.termios.tcgetattr(self.fd)
            try:
                self.tty.setraw(self.fd)
                ch = sys.stdin.read(1)
            finally:
                self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old_settings)
            return ch
nb_input = NonBlockingInput()
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
API_URL = "http://127.0.0.1:5000/api/flights"
def load_users():
    if not os.path.exists(USERS_FILE_PATH): return []
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return []
def fetch_flights_from_api(token, params):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get("flights", []), "OK"
        elif response.status_code == 429: return [], "請求過於頻繁 (Too Many Requests)"
        elif response.status_code == 401: return [], "Token 無效或未被伺服器識別"
        else: return [], f"伺服器錯誤, 狀態碼: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return [], f"無法連接至 API 伺服器: {e}"
def print_flights(all_flights, status_msg):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"=== Ticket Checker (API 連線版) | 權限: {current_permission_level.upper()} ===")
    print(f"狀態: {status_msg} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    price_filter_str = f"價格: ${min_price if min_price > 0 else '不限'} - ${max_price if max_price < 99999 else '不限'}"
    print(f"查詢條件：{_from} → {_to} | {price_filter_str}")
    print("-" * 80)
    print(f"{'航班號碼':<12} {'航空公司':<18} {'出發地':<8} {'目的地':<8} {'時間':<10} {'價格':>10}")
    print("-" * 80)
    sorted_flights = sorted(all_flights, key=lambda x: x['price'])
    if not sorted_flights:
        print("... 正在搜尋或無符合條件的航班 ...")
    else:
        for f in sorted_flights:
            print(f"{f.get('flight', 'N/A'):<12} {f.get('airline', 'N/A'):<18} {f.get('from', 'N/A'):<8} {f.get('to', 'N/A'):<8} {f.get('time', 'N/A'):<10} ${f.get('price', 0):>9,}")
    print("-" * 80)
    print(f"找到 {len(sorted_flights)} 筆航班")
    print("按下 Ctrl+C 結束程式")
def add_flight_loop():
    all_found_flights = []
    found_flight_ids = set()
    try:
        interval_map = {"pro": 1, "plus": 3, "free": 5}
        interval = interval_map.get(current_permission_level, 5)
        while True:
            query_params = {'from': _from, 'to': _to, 'min_price': min_price, 'max_price': max_price}
            newly_fetched_flights, status = fetch_flights_from_api(token_input, query_params)
            if newly_fetched_flights:
                for new_flight in newly_fetched_flights:
                    if new_flight['flight'] not in found_flight_ids:
                        all_found_flights.append(new_flight)
                        found_flight_ids.add(new_flight['flight'])
            print_flights(all_found_flights, status)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n已結束查詢。\n")
        sys.exit(0)
def query_conditions():
    global _from, _to, min_price, max_price
    valid_airports = ["TPE", "NRT", "HND", "KIX", "SIN", "BKK"]
    while True:
        _from = input(f"請輸入出發地 ({'/'.join(valid_airports)}): ").strip().upper()
        if _from in valid_airports: break
        else: print("[錯誤] 無效的出發地！")
    while True:
        _to = input(f"請輸入目的地 ({'/'.join(valid_airports)}): ").strip().upper()
        if _to in valid_airports and _to != _from: break
        elif _to == _from: print("[錯誤] 出發地與目的地不可相同！")
        else: print("[錯誤] 無效的目的地！")
    while True:
        try:
            min_price_str = input("請輸入最低價格 (例如 5000，留空則不限): ").strip()
            min_price = int(min_price_str) if min_price_str else 0
            break
        except ValueError: print("[錯誤] 請輸入數字！")
    while True:
        try:
            max_price_str = input("請輸入最高價格 (例如 12000，留空則不限): ").strip()
            max_price = int(max_price_str) if max_price_str else 99999
            if max_price < min_price: print("[錯誤] 最高價格不可低於最低價格！")
            else: break
        except ValueError: print("[錯誤] 請輸入數字！")
# --- END of Unchanged Code ---


def main():
    print("=== 歡迎使用 Ticket Checker (API 連線版) ===\n")
    
    global token_input, current_permission_level
    users = load_users()
    if not users:
        print("\n[錯誤] 找不到任何使用者資料 (data/users.json)。")
        print("請先執行 register.py 註冊至少一位使用者。")
        return

    # <<< --- REMOVED: The old user selection block is removed. --- >>>

    # <<< --- ADDED: New login flow based on entering a token. --- >>>
    while True:
        # 1. 要求使用者輸入他們的 Token
        token_to_check = input("請輸入您的 API Token 進行登入: ").strip()
        
        # 2. 在已載入的使用者列表中尋找匹配的 Token
        found_user = None
        for user in users:
            if user.get("token") == token_to_check:
                found_user = user
                break # 找到就跳出迴圈
        
        # 3. 判斷是否找到
        if found_user:
            # 如果找到了，設定全域變數並歡迎使用者
            token_input = found_user['token']
            current_permission_level = found_user.get('permission_level', 'free')
            print(f"\n✅ Token 驗證成功！歡迎，{found_user['username']} ({current_permission_level})！")
            time.sleep(1)
            break # 登入成功，跳出登入迴圈
        else:
            # 如果沒找到，提示錯誤並讓使用者重試
            print("❌ 無效的 API Token，請重新輸入或檢查您的 Token 是否正確。\n")
    # <<< --- END of ADDED block --- >>>

    print("\n--- 正在設定查詢條件 ---")
    query_conditions()
    
    print("\n✅ 查詢條件確認完成。")
    confirm = input("是否開始向 API 查詢？(y/n)：")
    if confirm.strip().lower() != 'y':
        print("已取消查詢。\n")
        return

    print("\n正在連接 API 並啟動動態查詢，請稍候...\n")
    add_flight_loop()


if __name__ == "__main__":
    main()