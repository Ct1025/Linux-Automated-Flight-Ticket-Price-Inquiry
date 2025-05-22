import requests
import argparse
import time
import sys
import random
from datetime import datetime, timedelta

def main():
    parser = argparse.ArgumentParser(description="Flight Ticket Checker CLI")
    parser.add_argument('--token', type=str, default='user-token', help='API token (user-token/vip-token)')
    args = parser.parse_args()

    print("=== 歡迎使用 ticket-checker ===\n")
    _from = input("請輸入出發地（IATA 機場代碼，例如 TPE）：")
    _to = input("請輸入目的地（IATA 機場代碼，例如 NRT）：")
    print("\n請選擇票種：\n[1] 單程\n[2] 來回")
    _type = input("輸入選項：")
    if _type == "2":
        _go_date = input(f"請輸入去程日期（格式：YYYY-MM-DD，可輸入 today / tomorrow）：{time.strftime('%Y-%m-%d')}\n")
        _return_date = input(f"請輸入回程日期（格式：YYYY-MM-DD，可輸入 today / tomorrow）：{time.strftime('%Y-%m-%d')}\n")
    else:
        _go_date = input(f"請輸入出發日期（格式：YYYY-MM-DD，可輸入 today / tomorrow）：{time.strftime('%Y-%m-%d')}\n")
        _return_date = None
    print("\n請選擇【去程】希望出發的時間區間：\n[1] 早上 (00:00 - 11:59)\n[2] 下午 (12:00 - 17:59)\n[3] 晚上 (18:00 - 23:59)\n[4] 不指定")
    _time_range = input("輸入選項：")
    _airline = input("\n若想指定航空公司，請輸入名稱（例如 EVA Air），否則直接按 Enter 跳過：\n")
    print("\n✅ 查詢條件確認：")
    print(f"- 出發地：{_from}\n- 目的地：{_to}\n- 去程日期：{_go_date}\n- 回程日期：{_return_date if _type=='2' else '無'}\n- 去程時間區間：{_time_range}\n- 票種：{'單程' if _type=='1' else '來回'}\n- 指定航空公司：{_airline if _airline else '不限'}\n- 排序方式：價格由低到高（預設固定）\n")
    confirm = input("是否開始查詢？(y/n)：")
    if confirm.strip().lower() != 'y':
        print("已取消查詢。\n")
        return

    # 檢查日期是否為未來
    try:
        def parse_date(d):
            d = d.strip().lower()
            if d == "today":
                return datetime.now().date()
            elif d == "tomorrow":
                return datetime.now().date() + timedelta(days=1)
            else:
                return datetime.strptime(d, "%Y-%m-%d").date()
        go_date = parse_date(_go_date)
        if _type == "2":
            return_date = parse_date(_return_date)
            if return_date < go_date:
                print("[錯誤] 回程日期不可早於去程日期！\n")
                return
        else:
            return_date = None
        if go_date < datetime.now().date():
            print("[錯誤] 去程日期不可為過去時間！\n")
            return
        if return_date and return_date < datetime.now().date():
            print("[錯誤] 回程日期不可為過去時間！\n")
            return
    except Exception:
        print("[錯誤] 日期格式錯誤，請輸入 YYYY-MM-DD 或 today/tomorrow\n")
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
        ("TPE", "KUL"): 5, ("TPE", "SIN"): 5, ("TPE", "BKK"): 4,
        ("TPE", "ICN"): 2.5, ("TPE", "HKG"): 2,
        ("TPE", "LAX"): 12, ("TPE", "SFO"): 12,
        ("NRT", "TPE"): 3, ("KUL", "TPE"): 5, ("SIN", "TPE"): 5,
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
                return_time = f"{(int(min_return_hour)%24):02d}:00"
            return {"flight": fid, "from": _from, "to": _to, "date": go_date.strftime("%Y-%m-%d"), "time": time_str, "price": price, "airline": airline, "return_time": return_time, "return_date": ret_date}
        else:
            return {"flight": fid, "from": _from, "to": _to, "date": go_date.strftime("%Y-%m-%d"), "time": time_str, "price": price, "airline": airline}

    def print_flights():
        sorted_flights = sorted(flights, key=lambda x: x['price'])
        print("\033c", end="")  # 清除螢幕
        print(f"查詢條件：{_from} → {_to}  票種：{'單程' if _type=='1' else '來回'}  航空公司：{_airline if _airline else '不限'}\n")
        print(f"{'編號':<8} {'航空公司':<16} {'去程時間':<24} {'回程時間':<24} {'價格':>8}")
        print("-"*88)
        for f in reversed(sorted_flights):
            if _type == "2":
                go_time = format_time(f['date'], f['time'])
                return_time_fmt = format_time(f['return_date'], f['return_time'])
            else:
                go_time = format_time(f['date'], f['time'])
                return_time_fmt = "-"
            print(f"{f['flight']:<8} {f['airline']:<16} {go_time:<24} {return_time_fmt:<24} ${f['price']:>7}")
        print(f"\n目前筆數：{len(flights)}")

    def add_flight_loop():
        try:
            while True:
                new_flight = random_flight()
                flights.append(new_flight)
                print_flights()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n已結束查詢。\n")
            sys.exit(0)

    add_flight_loop()

if __name__ == "__main__":
    main()
