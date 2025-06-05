# ticket-checker.py (Final Integrated Version)
import argparse
import time
import sys
import random
import os
import json
from datetime import datetime, timedelta

# <<< ADDED: Ensure requests library is available >>>
try:
    import requests
except ImportError:
    print("[錯誤] 'requests' 函式庫未安裝。")
    print("請在您的終端機執行: pip install requests")
    sys.exit(1)

# Define the path to the users.json file
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
# API URL
API_URL = "http://127.0.0.1:5000/api/flights"

# (此處省略與原版相同的 NonBlockingInput, get_valid_date, load_users 程式碼以節省篇幅)
# --- Start of Platform-Agnostic Non-Blocking Input ---
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
def load_users():
    if not os.path.exists(USERS_FILE_PATH): return []
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return []
def get_valid_date(prompt):
    while True:
        try:
            d = input(prompt).strip().lower()
            if d == "today": return datetime.now().date()
            elif d == "tomorrow": return datetime.now().date() + timedelta(days=1)
            else:
                parsed_date = datetime.strptime(d, "%Y-%m-%d").date()
                if parsed_date < datetime.now().date(): raise ValueError("[錯誤] 日期不可為過去的日期，請重新輸入！")
                return parsed_date
        except ValueError as e: print(e if str(e) else "[錯誤] 日期格式錯誤，請輸入YYYY-MM-DD 或 today/tomorrow\n")


def main():
    print("=== 歡迎使用 Ticket Checker (API 連線版) ===\n")
    
    # --- Token Input and Permission Level Retrieval ---
    global token_input, current_permission_level
    users = load_users()
    if not users:
        print("\n[錯誤] 找不到任何使用者資料 (data/users.json)。")
        print("請先執行 register.py 註冊至少一位使用者。")
        return

    # Let user choose which user to act as
    print("請選擇要使用的 Token:")
    for i, user in enumerate(users):
        print(f"[{i+1}] 使用者: {user['username']} (權限: {user['permission_level']})")
    
    while True:
        try:
            choice = int(input(f"請輸入選項 (1-{len(users)}): "))
            if 1 <= choice <= len(users):
                selected_user = users[choice - 1]
                token_input = selected_user['token']
                current_permission_level = selected_user.get('permission_level', 'free')
                print(f"\n✅ 已選擇使用者 '{selected_user['username']}'。開始 API 輪詢...")
                time.sleep(1)
                break
            else:
                print("無效選項，請重新輸入。")
        except ValueError:
            print("請輸入數字。")

    # --- Use query_conditions() for input validation ---
    # <<< CHANGED: We now inform the user that these conditions are for demonstration >>>
    print("\n--- 正在設定查詢條件 ---")
    print("注意：目前 API 為簡易版，僅回傳固定資料，以下條件僅為操作演練。")
    query_conditions()

    print("\n✅ 查詢條件確認：")
    print(f"- 出發地：{_from}\n- 目的地：{_to}\n- 去程日期：{go_date}\n ...等")
    confirm = input("是否開始向 API 查詢？(y/n)：")
    if confirm.strip().lower() != 'y':
        print("已取消查詢。\n")
        return

    print("\n正在連接 API 並啟動動態查詢，請稍候...\n")
    add_flight_loop()

# <<< CHANGED: The API call function now takes the token as an argument >>>
def fetch_flights_from_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("flights", []), "OK"
        elif response.status_code == 429:
            return [], "請求過於頻繁 (Too Many Requests)"
        elif response.status_code == 401:
            return [], "Token 無效或未被伺服器識別"
        else:
            return [], f"伺服器錯誤, 狀態碼: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return [], f"無法連接至 API 伺服器: {e}"

# <<< REMOVED: The old random_flight() function is no longer needed >>>

# <<< CHANGED: The print_flights function is kept, but will display adapted API data >>>
def print_flights(flights_from_api, status_msg):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"=== Ticket Checker (API 連線版) | 權限: {current_permission_level.upper()} ===")
    print(f"狀態: {status_msg} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"查詢條件：{_from} → {_to} (注意: API目前回傳固定資料)")
    print("-" * 80)
    print(f"{'航班號碼':<12} {'航空公司':<16} {'出發地':<8} {'目的地':<8} {'時間':<10} {'價格':>10}")
    print("-" * 80)

    if not flights_from_api:
        print("... 等待 API 回應 ...")
    else:
        for f in flights_from_api:
            # Adapt API data to fit the rich display format
            # We add placeholder data for fields not provided by the simple API
            f_adapted = {
                "flight": f.get("flight", "N/A"),
                "airline": "API Airline", # Placeholder
                "from": f.get("from", "N/A"),
                "to": f.get("to", "N/A"),
                "time": f.get("time", "N/A"),
                "price": f.get("price", 0)
            }
            print(f"{f_adapted['flight']:<12} {f_adapted['airline']:<16} {f_adapted['from']:<8} {f_adapted['to']:<8} {f_adapted['time']:<10} ${f_adapted['price']:>9,}")
    
    print("-" * 80)
    print(f"目前顯示筆數：{len(flights_from_api)}")
    print("按下 Ctrl+C 結束程式")


# <<< CHANGED: The main loop now calls the API instead of generating random data >>>
def add_flight_loop():
    try:
        # Permission level now determines the API call interval
        interval_map = {"pro": 1, "plus": 3, "free": 5}
        interval = interval_map.get(current_permission_level, 5) # Default to 5s

        while True:
            # 1. Fetch data from API using the selected token
            api_flights, status = fetch_flights_from_api(token_input)
            
            # 2. Display the data
            print_flights(api_flights, status)
            
            # 3. Wait for the next refresh cycle
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n已結束查詢。\n")
        sys.exit(0)

# (query_conditions is kept as part of the UI, but it's not used by the API call itself)
def query_conditions():
  global _from, _to, _type, go_date, return_date, _time_range, _airline, min_price, max_price
  valid_airports = ["TPE", "NRT", "HND", "KIX", "KUL", "SIN", "BKK", "ICN", "HKG", "LAX", "SFO"]
  _from = input("請輸入出發地（IATA 機場代碼，例如 TPE）：").strip().upper()
  _to = input("請輸入目的地（IATA 機場代碼，例如 NRT）：").strip().upper()
  _type = "1" # Simplified for demo
  go_date = datetime.now().date()
  return_date = None
  _time_range = "4"
  _airline = "" 
  min_price = 0
  max_price = 99999

if __name__ == "__main__":
    main()