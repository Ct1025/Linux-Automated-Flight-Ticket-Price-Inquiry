
import argparse
import time
import sys
import random
import os
import json # Import the json module
from datetime import datetime, timedelta

# Define the path to the users.json file
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
# Ensure the 'data' directory exists
os.makedirs(os.path.dirname(USERS_FILE_PATH), exist_ok=True)

# --- Start of Platform-Agnostic Non-Blocking Input ---
class NonBlockingInput:
    def __init__(self):
        self.is_windows = os.name == 'nt'
        if self.is_windows:
            import msvcrt
            self.msvcrt = msvcrt
        else:
            import termios
            import tty
            self.termios = termios
            self.tty = tty
            self.fd = sys.stdin.fileno()
            self.old_settings = None

    def kbhit(self):
        if self.is_windows:
            return self.msvcrt.kbhit()
        else:
            # Check if there's input available on stdin without blocking
            import select
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            return dr != []

    def getch(self):
        if self.is_windows:
            return self.msvcrt.getwch() # Use getwch for wide char (Unicode) input
        else:
            # Save original terminal settings
            self.old_settings = self.termios.tcgetattr(self.fd)
            try:
                # Set terminal to raw mode (no echoing, no buffering)
                self.tty.setraw(self.fd)
                ch = sys.stdin.read(1) # Read one character
            finally:
                # Restore original terminal settings
                self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old_settings)
            return ch

# Create an instance of our non-blocking input handler
nb_input = NonBlockingInput()
# --- End of Platform-Agnostic Non-Blocking Input ---

# --- User Data Loading Function ---
def load_users():
    """Loads user data from users.json."""
    if not os.path.exists(USERS_FILE_PATH):
        return []
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return [] # Return empty list if JSON is malformed
# --- End of User Data Loading Function ---


def get_valid_date(prompt):
    while True:
        try:
            d = input(prompt).strip().lower()
            if d == "today":
                return datetime.now().date()
            elif d == "tomorrow":
                return datetime.now().date() + timedelta(days=1)
            else:
                parsed_date = datetime.strptime(d, "%Y-%m-%d").date()
                # Check for invalid February 29th
                if parsed_date.month == 2 and parsed_date.day == 29:
                    if not (parsed_date.year % 4 == 0 and (parsed_date.year % 100 != 0 or parsed_date.year % 400 == 0)):
                        raise ValueError("[錯誤] 該年份的2月沒有29日！")
                # Check if the date is in the past
                if parsed_date < datetime.now().date():
                    raise ValueError("[錯誤] 日期不可為過去的日期，請重新輸入！")
                # Check if the date is within 365 days from today
                max_date = datetime.now().date() + timedelta(days=365)
                if parsed_date > max_date:
                    raise ValueError(f"[錯誤] 日期超出可查詢範圍（最多 365 天內）。請重新輸入！")
                return parsed_date
        except ValueError as e:
            print(e if str(e) else "[錯誤] 日期格式錯誤，請輸入YYYY-MM-DD 或 today/tomorrow\n")

def main():
    # Removed argparse as token will now be input interactively
    # parser = argparse.ArgumentParser(description="Flight Ticket Checker CLI")
    # parser.add_argument('--token', type=str, default='user-token', help='API token (user-token/vip-token)')
    # args = parser.parse_args()

    print("=== 歡迎使用 ticket-checker ===\n")

    # --- Token Input and Permission Level Retrieval ---
    global current_permission_level # Make it global to be accessible in add_flight_loop
    users = load_users()
    while True:
        token_input = input("請輸入您的 API Token：").strip()
        found_user = None
        for user in users:
            if user.get("token") == token_input:
                found_user = user
                break
        
        if found_user:
            current_permission_level = found_user["permission_level"]
            print(f"✅ Token 驗證成功！您的權限等級為：{current_permission_level.upper()}\n")
            break
        else:
            print("❌ 無效的 API Token，請重新輸入！\n")
            # Optionally, you could exit here after a few failed attempts
            # sys.exit(1)
    # --- End Token Input and Permission Level Retrieval ---


    # Use query_conditions() for input validation
    query_conditions()

    print("\n✅ 查詢條件確認：")
    print(f"- 出發地：{_from}\n- 目的地：{_to}\n- 去程日期：{go_date}\n- 回程日期：{return_date if _type=='2' else '無'}\n- 去程時間區間：{_time_range}\n- 票種：{'單程' if _type=='1' else '來回'}\n- 指定航空公司：{_airline if _airline else '不限'}\n- 排序方式：價格由低到高（預設固定）\n")
    confirm = input("是否開始查詢？(y/n)：")
    if confirm.strip().lower() != 'y':
        print("已取消查詢。\n")
        return

    print("\n正在查詢與啟動動態機制，請稍候...\n")

    flights = []
    flight_ids = set()
    airlines = ["EVA Air", "China Airlines", "ANA", "JAL", "Tigerair", "Peach"]

    def format_time(date_str, tstr):
        hour = int(tstr.split(":")[0])
        suffix = "am" if hour < 12 else "pm"
        return f"{date_str} {tstr}{suffix}"

    # 飛行時間表（小時）
    flight_duration = {
        ("TPE", "NRT"): 3, ("TPE", "HND"): 3, ("TPE", "KIX"): 3,
        ("TPE", "KUL"): 6, ("TPE", "SIN"): 6, ("TPE", "BKK"): 4,
        ("TPE", "ICN"): 2.5, ("TPE", "HKG"): 2,
        ("TPE", "LAX"): 12, ("TPE", "SFO"): 12,
        ("NRT", "TPE"): 3, ("KUL", "TPE"): 6, ("SIN", "TPE"): 6,
        ("BKK", "TPE"): 4, ("ICN", "TPE"): 2.5, ("HKG", "TPE"): 2,
        ("LAX", "TPE"): 12, ("SFO", "TPE"): 12
    }

    def random_flight():
        while True:
            fid = f"{random.choice(['AB','CD','EF','GH','IJ'])}{random.randint(100,999)}"
            if fid not in flight_ids:
                flight_ids.add(fid)
                break
        airline = _airline if _airline else random.choice(airlines)
        price = random.randint(4000, 8000)
        time_str = random.choice(["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"])
        if _type == "2":
            go_hour = int(time_str.split(":")[0])
            duration = flight_duration.get((_from.upper(), _to.upper()), 3)
            min_return_hour = int(go_hour + duration + 2)
            # 回程日期與時間
            ret_date = return_date.strftime("%Y-%m-%d")
            possible_return_times = []
            for rt in ["10:00", "13:00", "15:00", "19:00", "21:00", "22:00", "23:00"]:
                return_hour = int(rt.split(":")[0])
                if (return_date > go_date) or (return_date == go_date and return_hour >= min_return_hour):
                    possible_return_times.append(rt)
            if possible_return_times:
                return_time = random.choice(possible_return_times)
            else:
                # Fallback if no suitable return time in the list
                return_time = f"{(int(min_return_hour)%24):02d}:00"
            return {"flight": fid, "from": _from, "to": _to, "date": go_date.strftime("%Y-%m-%d"), "time": time_str, "price": price, "airline": airline, "return_time": return_time, "return_date": ret_date, "website": f"https://{airline.replace(' ', '').lower()}.com"}
        else:
            return {"flight": fid, "from": _from, "to": _to, "date": go_date.strftime("%Y-%m-%d"), "time": time_str, "price": price, "airline": airline, "website": f"https://{airline.replace(' ', '').lower()}.com"}

    def print_flights():
        sorted_flights = sorted(flights, key=lambda x: x['price'])
        filtered_flights = [f for f in sorted_flights if min_price <= f['price'] <= max_price]
        print("\033c", end="")  # 清除螢幕
        print(f"查詢條件：{_from} → {_to}  票種：{'單程' if _type=='1' else '來回'}  航空公司：{_airline if _airline else '不限'}\n")
        print(f"{'編號':<8} {'航空公司':<16} {'去程時間':<24} {'回程時間':<24} {'飛行時間':<12} {'價格':>8} {'網站':<30}")
        print("-"*140)
        for f in filtered_flights[:len(flights)]:
            if _type == "2":
                go_time = format_time(f['date'], f['time'])
                return_time_fmt = format_time(f['return_date'], f['return_time'])
            else:
                go_time = format_time(f['date'], f['time'])
                return_time_fmt = "-"

            # Calculate flight duration
            duration = flight_duration.get((_from.upper(), _to.upper()), 3)
            duration_str = f"{int(duration)} 小時 {int((duration - int(duration)) * 60)} 分鐘"

            print(f"{f['flight']:<8} {f['airline']:<16} {go_time:<24} {return_time_fmt:<24} {duration_str:<12} ${f['price']:>7} {f['website']:<30}")
        print(f"\n目前筆數：{len(filtered_flights)}")

    # 新增功能：查詢結果導出
    def export_to_csv():
        import csv
        with open("flight_results.csv", "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["編號", "航空公司", "去程時間", "回程時間", "價格", "網站"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for f in flights:
                writer.writerow({
                    "編號": f['flight'],
                    "航空公司": f['airline'],
                    "去程時間": format_time(f['date'], f['time']),
                    "回程時間": format_time(f['return_date'], f['return_time']) if _type == "2" else "-",
                    "價格": f['price'],
                    "網站": f['website']
                })
        print("\n✅ 查詢結果已導出為 flight_results.csv 文件！")

    def add_flight_loop():
        try:
            # --- MODIFIED: Determine user privilege level from global variable ---
            # user_privilege is now set based on the token loaded from users.json
            if current_permission_level == "free":
                interval = 5  # Free: 1 flight every 5 seconds
                batch_size = 1
            elif current_permission_level == "plus":
                interval = 3  # Plus: 2 flights every 3 seconds
                batch_size = 2
            elif current_permission_level == "pro":
                interval = 1  # Pro: 3 flights every second
                batch_size = 3
            else:
                # Fallback for unknown permission levels
                interval = 5
                batch_size = 1
                print("\n[警告] 未知權限等級，將使用預設 'free' 查詢速率。\n")
            # --- END MODIFIED ---

            while True:
                # Generate enough flight data dynamically
                for _ in range(batch_size):
                    new_flight = random_flight()
                    flights.append(new_flight)

                # Display the current batch of flights
                print_flights()
                print(f"\n目前顯示筆數：{len(flights)}")

                # 提示：輸入 'r' 可以返回條件輸入界面。
                print("\n提示：輸入 'r' 可以返回條件輸入界面。")

                # Check if the user wants to return to input conditions
                start_time = time.time()
                while time.time() - start_time < interval:
                    # Use the platform-agnostic kbhit
                    if nb_input.kbhit():
                        user_input = nb_input.getch().strip().lower() # Use platform-agnostic getch
                        if user_input == 'r':
                            flights.clear()
                            query_conditions()  # Return to condition input interface
                            return
                    time.sleep(0.01) # Small sleep to prevent busy-waiting

        except KeyboardInterrupt:
            print("\n已結束查詢。\n")
            sys.exit(0)

    add_flight_loop()
    # 在查詢完成後導出結果
    export_to_csv()

def query_conditions():
    global _from, _to, _type, go_date, return_date, _time_range, _airline, min_price, max_price

    valid_airports = ["TPE", "NRT", "HND", "KIX", "KUL", "SIN", "BKK", "ICN", "HKG", "LAX", "SFO"]

    while True:
        _from = input("請輸入出發地（IATA 機場代碼，例如 TPE）：").strip().upper()
        if _from in valid_airports:
            print(f"[確認] 出發地 '{_from}' 有效。\n")
            break
        else:
            print(f"[錯誤] 出發地 '{_from}' 不存在，請重新輸入！\n")

    while True:
        _to = input("請輸入目的地（IATA 機場代碼，例如 NRT）：").strip().upper()
        if _to in valid_airports:
            print(f"[確認] 目的地 '{_to}' 有效。\n")
            break
        else:
            print(f"[錯誤] 目的地 '{_to}' 不存在，請重新輸入！\n")

    if _from == _to:
        print("[錯誤] 出發地和目的地不能相同，請重新輸入！\n")
        return query_conditions() # Re-call to get new inputs

    while True:
        print("\n請選擇票種：\n[1] 單程\n[2] 來回")
        _type = input("輸入選項：")
        if _type in ["1", "2"]:
            break
        else:
            print("[錯誤] 無效的選項，請重新輸入！\n")

    go_date = get_valid_date(f"請輸入去程日期（格式：YYYY-MM-DD，可輸入 today / tomorrow）：\n")

    if _type == "2":
        while True:
            return_date = get_valid_date(f"請輸入回程日期（格式：YYYY-MM-DD，可輸入 today / tomorrow）：\n")
            if return_date < go_date:
                print("[錯誤] 回程日期不可早於去程日期！\n")
            else:
                break
    else:
        return_date = None

    while True:
        print("\n請選擇【去程】希望出發的時間區間：\n[1] 早上 (00:00 - 11:59)\n[2] 下午 (12:00 - 17:59)\n[3] 晚上 (18:00 - 23:59)\n[4] 不指定")
        _time_range = input("輸入選項：")
        if _time_range in ["1", "2", "3", "4"]:
            break
        else:
            print("[錯誤] 無效的選項，請重新輸入！\n")

    valid_airlines = ["EVA Air", "China Airlines", "ANA", "JAL", "Tigerair", "Peach"]
    while True:
        _airline = input("\n若想指定航空公司，請輸入名稱（例如 EVA Air），否則直接按 Enter 跳過：\n")
        if not _airline or _airline in valid_airlines:
            break
        else:
            print(f"[錯誤] 航空公司 '{_airline}' 不存在，請重新輸入！\n")

    while True:
        try:
            min_price = int(input("\n請輸入最低價格範圍（例如 4000）："))
            break
        except ValueError:
            print("[錯誤] 價格必須是數字！")
    while True:
        try:
            max_price = int(input("請輸入最高價格範圍（例如 8000）："))
            if max_price < min_price:
                print("[錯誤] 最高價格不能低於最低價格！")
            else:
                break
        except ValueError:
            print("[錯誤] 價格必須是數字！")


if __name__ == "__main__":
    main()
