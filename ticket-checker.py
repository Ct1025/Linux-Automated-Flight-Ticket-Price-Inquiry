# ticket-checker.py (Final Version with Real Search)
# ... (此處省略與前版相同的 NonBlockingInput, load_users, get_valid_date 程式碼以節省篇幅) ...
# --- Start of Platform-Agnostic Non-Blocking Input ---
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
    
    global token_input, current_permission_level
    users = load_users()
    if not users:
        print("\n[錯誤] 找不到任何使用者資料 (data/users.json)。")
        return

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
                print(f"\n✅ 已選擇使用者 '{selected_user['username']}'。")
                break
            else: print("無效選項，請重新輸入。")
        except ValueError: print("請輸入數字。")

    print("\n--- 正在設定查詢條件 ---")
    query_conditions() # 呼叫查詢條件函式

    print("\n✅ 查詢條件確認完成。")
    confirm = input("是否開始向 API 查詢？(y/n)：")
    if confirm.strip().lower() != 'y':
        print("已取消查詢。\n")
        return

    print("\n正在連接 API 並啟動動態查詢，請稍候...\n")
    add_flight_loop()

# <<< CHANGED: API call now accepts query parameters >>>
def fetch_flights_from_api(token, params):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # 將 params 字典傳給 requests，它會自動轉換成 URL 查詢字串
        response = requests.get(API_URL, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            return response.json().get("flights", []), "OK"
        # ... (其他錯誤處理與前版相同) ...
        elif response.status_code == 429: return [], "請求過於頻繁 (Too Many Requests)"
        elif response.status_code == 401: return [], "Token 無效或未被伺服器識別"
        else: return [], f"伺服器錯誤, 狀態碼: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return [], f"無法連接至 API 伺服器: {e}"


def print_flights(flights_from_api, status_msg):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"=== Ticket Checker (API 連線版) | 權限: {current_permission_level.upper()} ===")
    print(f"狀態: {status_msg} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"查詢條件：{_from} → {_to}")
    print("-" * 80)
    print(f"{'航班號碼':<12} {'航空公司':<18} {'出發地':<8} {'目的地':<8} {'時間':<10} {'價格':>10}")
    print("-" * 80)

    if not flights_from_api:
        print("... API 未回傳符合條件的航班 ...")
    else:
        # API現在回傳的資料更豐富了
        for f in flights_from_api:
            print(f"{f.get('flight', 'N/A'):<12} {f.get('airline', 'N/A'):<18} {f.get('from', 'N/A'):<8} {f.get('to', 'N/A'):<8} {f.get('time', 'N/A'):<10} ${f.get('price', 0):>9,}")
    
    print("-" * 80)
    print(f"找到 {len(flights_from_api)} 筆符合條件的航班")
    print("按下 Ctrl+C 結束程式")


def add_flight_loop():
    try:
        interval_map = {"pro": 2, "plus": 4, "free": 6} # 微調更新頻率
        interval = interval_map.get(current_permission_level, 6)

        while True:
            # <<< CHANGED: Prepare parameters and pass them to the API call >>>
            # 建立要傳送給 API 的查詢參數字典
            query_params = {
                'from': _from,
                'to': _to,
                # 'date': go_date.strftime("%Y-%m-%d") # 未來可擴充
            }
            
            # 呼叫 API，並傳入 token 和查詢參數
            api_flights, status = fetch_flights_from_api(token_input, query_params)
            
            print_flights(api_flights, status)
            
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n已結束查詢。\n")
        sys.exit(0)

# <<< CHANGED: Simplified query_conditions, as we only use from/to for now >>>
def query_conditions():
    global _from, _to
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

if __name__ == "__main__":
    main()