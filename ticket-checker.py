#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Ticket Checker - UNIX 自動化航班查詢工具
==============================================

一個現代化的航班價格查詢工具，整合 UNIX 系統特性
支援互動模式和自動模式，提供優雅的用戶體驗
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import requests

# 嘗試導入 UNIX 特定模組
try:
    import termios
    import tty
    import select
    HAS_UNIX_FEATURES = True
except ImportError:
    HAS_UNIX_FEATURES = False

try:
    import msvcrt
    HAS_WINDOWS_FEATURES = True
except ImportError:
    HAS_WINDOWS_FEATURES = False

# 顏色代碼常量
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 圖示常量
class Icons:
    PLANE = "✈️"
    SEARCH = "🔍"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    MONEY = "💰"
    TIME = "⏰"
    STOP = "🛑"
    ROCKET = "🚀"
    STAR = "⭐"

@dataclass
class Flight:
    """航班資料類別"""
    flight: str
    price: int
    departure_time: str
    arrival_time: str
    airline: str = "Unknown"
    aircraft: str = "Unknown"
    
    def __str__(self) -> str:
        return f"{self.flight} | ${self.price} | {self.departure_time}-{self.arrival_time}"

@dataclass
class QueryConditions:
    """查詢條件類別"""
    from_airport: str
    to_airport: str
    departure_date: datetime
    min_price: int = 0
    max_price: int = 99999
    ticket_type: Optional[str] = None

class FlightChecker:
    """航班查詢器主類別"""
    
    def __init__(self, quiet_mode=False):
        self.quiet_mode = quiet_mode
        self.logger = self._setup_logging()
        self.users_file = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
        self.api_url = "http://127.0.0.1:5000/api/flights"
        self.running = True
        self.token = None
        self.permission_level = "free"
        self.query_conditions = None
        self.found_flights = []
        self.found_flight_ids = set()
        
        # 註冊信號處理
        self._setup_signal_handlers()
        
        # 初始化輸入處理器
        self.input_handler = self._create_input_handler()
        
    def _setup_logging(self, level="INFO", log_file=None) -> logging.Logger:
        """設定日誌系統"""
        logger = logging.getLogger('flight_checker')
        logger.setLevel(getattr(logging, level.upper()))
        logger.handlers.clear()
        
        # 建立格式化器
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 檔案處理器
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _setup_signal_handlers(self):
        """設定 UNIX 信號處理器"""
        def signal_handler(signum, frame):
            signal_names = {
                signal.SIGTERM: "SIGTERM",
                signal.SIGINT: "SIGINT", 
                signal.SIGHUP: "SIGHUP"
            }
            signal_name = signal_names.get(signum, f"Signal {signum}")
            self.logger.info(f"收到 {signal_name} 信號")
            self._graceful_shutdown(signal_name)
        
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _graceful_shutdown(self, signal_name: str):
        """優雅關閉"""
        print(f"\n{Icons.STOP} 收到 {signal_name} 信號，正在安全退出...")
        self.logger.info(f"開始優雅關閉流程")
        self.running = False
        
        # 保存結果
        if self.found_flights:
            self._save_results()
        
        print(f"{Icons.SUCCESS} 程式已安全退出")
        sys.exit(0)
    
    def _create_input_handler(self):
        """建立輸入處理器"""
        if HAS_WINDOWS_FEATURES:
            return WindowsInputHandler()
        elif HAS_UNIX_FEATURES:
            return UnixInputHandler()
        else:
            return BasicInputHandler()
    
    def print_banner(self):
        """顯示程式橫幅"""
        banner = f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    {Icons.PLANE} 航班價格查詢工具 {Icons.PLANE}                      ║
║                    Flight Ticket Checker                    ║
║                                                              ║
║  {Colors.OKCYAN}一個現代化的 UNIX 航班查詢系統{Colors.HEADER}                        ║
║  {Colors.OKGREEN}支援實時查詢、智能監控、優雅退出{Colors.HEADER}                      ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
        print(banner)
        
        # 顯示系統資訊
        print(f"{Colors.OKBLUE}系統資訊:{Colors.ENDC}")
        print(f"  {Icons.INFO} 作業系統: {os.name}")
        print(f"  {Icons.INFO} 程序 ID: {os.getpid()}")
        print(f"  {Icons.INFO} UNIX 特性: {'可用' if HAS_UNIX_FEATURES else '不可用'}")
        print(f"  {Icons.INFO} 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def authenticate_user(self, token: str = None) -> bool:
        """用戶認證"""
        if token:
            # 自動模式使用提供的 token
            return self._validate_token(token)
        
        # 互動模式登入
        print(f"{Colors.BOLD}用戶認證{Colors.ENDC}")
        print("請輸入您的 API Token:")
        
        while True:
            try:
                token = input(f"{Icons.ROCKET} Token: ").strip()
                if not token:
                    print(f"{Icons.WARNING} Token 不能為空，請重新輸入")
                    continue
                
                if self._validate_token(token):
                    return True
                else:
                    print(f"{Icons.ERROR} Token 無效，請檢查後重新輸入")
                    retry = input("是否重試？(y/n): ").lower()
                    if retry != 'y':
                        return False
                        
            except KeyboardInterrupt:
                print(f"\n{Icons.STOP} 取消認證")
                return False
    
    def _validate_token(self, token: str) -> bool:
        """驗證 token"""
        try:
            users = self._load_users()
            user = next((u for u in users if u.get("token") == token), None)
            
            if user:
                self.token = token
                self.permission_level = user.get('permission_level', 'free')
                if not self.quiet_mode:
                    print(f"{Icons.SUCCESS} 認證成功！歡迎 {user['username']} ({self.permission_level})")
                self.logger.info(f"用戶認證成功: {user['username']} ({self.permission_level})")
                return True
            else:
                self.logger.warning(f"Token 驗證失敗: {token[:8]}...")
                return False
                
        except Exception as e:
            self.logger.error(f"認證過程發生錯誤: {e}")
            return False
    
    def _load_users(self) -> List[Dict]:
        """載入用戶資料"""
        if not os.path.exists(self.users_file):
            return []
        
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"載入用戶資料失敗: {e}")
            return []
    
    def get_query_conditions(self) -> QueryConditions:
        """取得查詢條件"""
        print(f"\n{Colors.BOLD}設定查詢條件{Colors.ENDC}")
        print("=" * 50)
        
        # 出發地
        from_airport = self._get_airport_input("出發地", "TPE", "台北桃園機場")
        
        # 目的地
        to_airport = self._get_airport_input("目的地", "NRT", "東京成田機場")
        
        # 出發日期
        departure_date = self._get_date_input()
        
        # 價格範圍
        min_price, max_price = self._get_price_range()
        
        # 票種
        ticket_type = self._get_ticket_type()
        
        conditions = QueryConditions(
            from_airport=from_airport,
            to_airport=to_airport,
            departure_date=departure_date,
            min_price=min_price,
            max_price=max_price,
            ticket_type=ticket_type
        )
        
        self._display_conditions_summary(conditions)
        self.query_conditions = conditions
        return conditions
    
    def _get_airport_input(self, prompt: str, default: str, default_name: str) -> str:
        """取得機場輸入"""
        while True:
            try:
                value = input(f"{Icons.PLANE} {prompt} (預設: {default} - {default_name}): ").strip().upper()
                if not value:
                    print(f"  {Icons.INFO} 使用預設: {default}")
                    return default
                
                if len(value) == 3 and value.isalpha():
                    return value
                else:
                    print(f"  {Icons.WARNING} 請輸入有效的 3 字母機場代碼")
                    
            except KeyboardInterrupt:
                print(f"\n{Icons.STOP} 取消輸入")
                raise
    
    def _get_date_input(self) -> datetime:
        """取得日期輸入"""
        print(f"\n{Icons.TIME} 出發日期:")
        print("  1. today (今天)")
        print("  2. tomorrow (明天)")
        print("  3. 自訂日期 (YYYY-MM-DD)")
        
        while True:
            try:
                choice = input("請選擇 (1-3) 或直接輸入日期: ").strip().lower()
                
                if choice == "1" or choice == "today":
                    return datetime.now()
                elif choice == "2" or choice == "tomorrow":
                    return datetime.now() + timedelta(days=1)
                elif choice == "3":
                    date_str = input("請輸入日期 (YYYY-MM-DD): ")

                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    # 嘗試直接解析為日期
                    date_obj = datetime.strptime(choice, "%Y-%m-%d")
                
                if date_obj.date() < datetime.now().date():
                    print(f"  {Icons.WARNING} 日期不能是過去的日期")
                    continue
                
                return date_obj
                
            except ValueError:
                print(f"  {Icons.ERROR} 日期格式錯誤，請重新輸入")
            except KeyboardInterrupt:
                print(f"\n{Icons.STOP} 取消輸入")
                raise
    
    def _get_price_range(self) -> Tuple[int, int]:
        """取得價格範圍"""
        print(f"\n{Icons.MONEY} 價格範圍:")
        
        try:
            min_input = input("最低價格 (留空為 0): ").strip()
            min_price = int(min_input) if min_input else 0
            
            max_input = input("最高價格 (留空為不限): ").strip()
            max_price = int(max_input) if max_input else 99999
            
            if min_price > max_price:
                print(f"  {Icons.WARNING} 最低價格不能大於最高價格，已自動調整")
                min_price, max_price = max_price, min_price
            
            return min_price, max_price
            
        except ValueError:
            print(f"  {Icons.WARNING} 價格格式錯誤，使用預設範圍")
            return 0, 99999
    
    def _get_ticket_type(self) -> Optional[str]:
        """取得票種"""
        print(f"\n{Icons.STAR} 票種選擇:")
        ticket_types = {
            "1": "經濟艙",
            "2": "商務艙", 
            "3": "頭等艙"
        }
        
        for key, value in ticket_types.items():
            print(f"  {key}. {value}")
        print("  0. 不限制")
        
        try:
            choice = input("請選擇 (0-3): ").strip()
            return ticket_types.get(choice)
        except KeyboardInterrupt:
            print(f"\n{Icons.STOP} 取消輸入")
            raise
    
    def _display_conditions_summary(self, conditions: QueryConditions):
        """顯示查詢條件摘要"""
        print(f"\n{Colors.BOLD}查詢條件確認{Colors.ENDC}")
        print("=" * 50)
        print(f"{Icons.PLANE} 航線: {conditions.from_airport} → {conditions.to_airport}")
        print(f"{Icons.TIME} 日期: {conditions.departure_date.strftime('%Y-%m-%d')}")
        print(f"{Icons.MONEY} 價格: ${conditions.min_price} - ${conditions.max_price}")
        print(f"{Icons.STAR} 票種: {conditions.ticket_type or '不限制'}")
        print("=" * 50)
        
        confirm = input(f"\n確認開始查詢嗎？(y/n): ").lower()
        if confirm != 'y':
            print(f"{Icons.INFO} 已取消查詢")
            sys.exit(0)
    
    def start_monitoring(self, auto_mode: bool = False, duration: int = None):
        """開始監控查詢"""
        if not self.query_conditions:
            self.logger.error("查詢條件未設定")
            return
        
        # 根據權限設定查詢間隔
        interval_map = {"pro": 1, "plus": 3, "free": 5}
        interval = interval_map.get(self.permission_level, 5)
        
        print(f"\n{Colors.BOLD}開始航班監控{Colors.ENDC}")
        print(f"{Icons.INFO} 權限等級: {self.permission_level}")
        print(f"{Icons.TIME} 查詢間隔: {interval} 秒")
        
        if not auto_mode:
            print(f"{Icons.INFO} 按 'q' 鍵隨時停止查詢")
        
        if duration:
            print(f"{Icons.TIME} 執行時間: {duration} 秒")
        
        print("-" * 60)
        
        start_time = time.time()
        query_count = 0
        
        try:
            while self.running:
                # 檢查執行時間
                if duration and (time.time() - start_time) >= duration:
                    print(f"\n{Icons.TIME} 達到預設執行時間，停止查詢")
                    break
                
                # 檢查用戶輸入 (僅互動模式)
                if not auto_mode and self.input_handler.has_input():
                    key = self.input_handler.get_char()
                    if key and key.lower() == 'q':
                        print(f"\n{Icons.STOP} 用戶按下 'q' 鍵，停止查詢")
                        break
                
                # 執行查詢
                query_count += 1
                self._perform_query(query_count)
                
                # 等待下次查詢
                if self.running:
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            print(f"\n{Icons.STOP} 收到中斷信號，正在停止...")
        except Exception as e:
            self.logger.error(f"監控過程發生錯誤: {e}")
            print(f"{Icons.ERROR} 查詢過程中發生錯誤: {e}")
        
        # 顯示最終結果
        self._display_final_results(query_count)
    
    def _perform_query(self, query_count: int):
        """執行單次查詢"""
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"{Icons.SEARCH} 第 {query_count} 次查詢 ({current_time})")
        
        # 建構查詢參數
        params = {
            'from': self.query_conditions.from_airport,
            'to': self.query_conditions.to_airport,
            'date': self.query_conditions.departure_date.strftime('%Y-%m-%d'),
            'min_price': self.query_conditions.min_price,
            'max_price': self.query_conditions.max_price
        }
        
        if self.query_conditions.ticket_type:
            params['type'] = self.query_conditions.ticket_type
        
        # 查詢 API
        flights, status = self._fetch_flights(params)
        
        if status == "OK":
            new_flights = self._process_new_flights(flights)
            if new_flights:
                print(f"{Icons.SUCCESS} 發現 {len(new_flights)} 個新航班")
                for flight in new_flights:
                    print(f"  {Icons.PLANE} {flight}")
            else:
                print(f"{Icons.INFO} 本次查詢無新航班")
            
            print(f"{Icons.INFO} 累計找到 {len(self.found_flights)} 個航班")
        else:
            print(f"{Icons.WARNING} API 狀態: {status}")
        
        print("-" * 40)
    
    def _fetch_flights(self, params: Dict) -> Tuple[List[Dict], str]:
        """從 API 獲取航班資料"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(self.api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("flights", []), "OK"
            elif response.status_code == 429:
                return [], "請求過於頻繁"
            elif response.status_code == 401:
                return [], "Token 無效"
            else:
                return [], f"伺服器錯誤 ({response.status_code})"
                
        except requests.exceptions.Timeout:
            return [], "請求超時"
        except requests.exceptions.ConnectionError:
            return [], "無法連接到伺服器"
        except Exception as e:
            self.logger.error(f"API 請求錯誤: {e}")
            return [], f"請求錯誤: {e}"
    
    def _process_new_flights(self, flights_data: List[Dict]) -> List[Flight]:
        """處理新航班資料"""
        new_flights = []
        
        for flight_data in flights_data:
            flight_id = flight_data.get('flight', '')
            
            if flight_id not in self.found_flight_ids:
                flight = Flight(
                    flight=flight_id,
                    price=flight_data.get('price', 0),
                    departure_time=flight_data.get('departure_time', ''),
                    arrival_time=flight_data.get('arrival_time', ''),
                    airline=flight_data.get('airline', 'Unknown'),
                    aircraft=flight_data.get('aircraft', 'Unknown')
                )
                
                self.found_flights.append(flight)
                self.found_flight_ids.add(flight_id)
                new_flights.append(flight)
        
        return new_flights
    
    def _display_final_results(self, query_count: int):
        """顯示最終結果"""
        print(f"\n{Colors.BOLD}查詢結果總覽{Colors.ENDC}")
        print("=" * 60)
        
        if self.found_flights:
            print(f"{Icons.SUCCESS} 共找到 {len(self.found_flights)} 個符合條件的航班:")
            print()
            
            # 按價格排序
            sorted_flights = sorted(self.found_flights, key=lambda f: f.price)
            
            for i, flight in enumerate(sorted_flights, 1):
                print(f"{i:2d}. {flight}")
            
            # 顯示統計資訊
            prices = [f.price for f in self.found_flights]
            print(f"\n{Colors.OKGREEN}價格統計:{Colors.ENDC}")
            print(f"  最低價格: ${min(prices)}")
            print(f"  最高價格: ${max(prices)}")
            print(f"  平均價格: ${sum(prices) // len(prices)}")
            
        else:
            print(f"{Icons.WARNING} 很抱歉，未找到符合條件的航班")
        
        print(f"\n{Icons.INFO} 執行統計: 總計 {query_count} 次查詢")
        print("=" * 60)
    
    def _save_results(self):
        """保存查詢結果"""
        if not self.found_flights:
            return
        
        # 建立結果資料夾
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # 生成檔案名稱
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"flight_results_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # 準備資料
        results_data = {
            'query_time': datetime.now().isoformat(),
            'conditions': {
                'from': self.query_conditions.from_airport,
                'to': self.query_conditions.to_airport,
                'date': self.query_conditions.departure_date.strftime('%Y-%m-%d'),
                'price_range': [self.query_conditions.min_price, self.query_conditions.max_price],
                'ticket_type': self.query_conditions.ticket_type
            },
            'flights': [
                {
                    'flight': f.flight,
                    'price': f.price,
                    'departure_time': f.departure_time,
                    'arrival_time': f.arrival_time,
                    'airline': f.airline,
                    'aircraft': f.aircraft
                }
                for f in self.found_flights
            ],
            'statistics': {
                'total_flights': len(self.found_flights),
                'min_price': min(f.price for f in self.found_flights),
                'max_price': max(f.price for f in self.found_flights),
                'avg_price': sum(f.price for f in self.found_flights) // len(self.found_flights)
            }
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            print(f"{Icons.SUCCESS} 結果已保存至: {filepath}")
            self.logger.info(f"查詢結果已保存至: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存結果失敗: {e}")


class InputHandler:
    """輸入處理器基類"""
    
    def has_input(self) -> bool:
        """檢查是否有輸入"""
        return False
    
    def get_char(self) -> str:
        """取得字元"""
        return ""


class WindowsInputHandler(InputHandler):
    """Windows 輸入處理器"""
    
    def has_input(self) -> bool:
        return msvcrt.kbhit()
    
    def get_char(self) -> str:
        return msvcrt.getwch()


class UnixInputHandler(InputHandler):
    """UNIX 輸入處理器"""
    
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
    
    def has_input(self) -> bool:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        return dr != []
    
    def get_char(self) -> str:
        try:
            tty.setraw(self.fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)


class BasicInputHandler(InputHandler):
    """基本輸入處理器 (不支援非阻塞輸入)"""
    pass


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description='Flight Ticket Checker - 現代化航班查詢工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  互動模式:       python ticket-checker.py
  自動模式:       python ticket-checker.py -a -t YOUR_TOKEN
  設定日誌:       python ticket-checker.py -l /var/log/flight-checker.log
  限制時間:       python ticket-checker.py -a -t TOKEN -d 3600
  詳細模式:       python ticket-checker.py -v -L DEBUG
  快速查詢:       python ticket-checker.py -a -t TOKEN -d 30 -q
  
UNIX 風格短選項:
  -h, --help      顯示幫助信息
  -v, --version   顯示版本信息
  -t, --token     指定 API Token
  -a, --auto      自動模式
  -d, --duration  執行時間限制
  -l, --log-file  日誌檔案路徑
  -L, --log-level 日誌等級
  -q, --quiet     安靜模式 (減少輸出)
  -V, --verbose   詳細模式 (增加輸出)
        """
    )
    
    # UNIX 風格的短選項和長選項
    parser.add_argument('-t', '--token', 
                       help='API Token (自動模式必需)')
    parser.add_argument('-a', '--auto', '--auto-mode', 
                       action='store_true', dest='auto_mode',
                       help='自動模式 (供 systemd 或排程使用)')
    parser.add_argument('-L', '--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='日誌等級')
    parser.add_argument('-l', '--log-file', 
                       help='日誌檔案路徑')
    parser.add_argument('-d', '--duration', type=int, 
                       help='執行時間 (秒，0 表示無限制)')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='安靜模式 (減少輸出)')
    parser.add_argument('-V', '--verbose', action='store_true',
                       help='詳細模式 (增加輸出)')
    parser.add_argument('-v', '--version', action='version', 
                       version='%(prog)s 2.0')
    
    args = parser.parse_args()
    
    # 建立查詢器實例
    checker = FlightChecker(quiet_mode=args.quiet)
    
    # 處理安靜模式和詳細模式
    if args.quiet and args.verbose:
        if not args.quiet:  # 只在非安靜模式顯示警告
            print(f"{Icons.WARNING} 警告: 同時指定 --quiet 和 --verbose，將使用詳細模式")
        args.quiet = False
    
    # 根據模式調整日誌等級
    if args.quiet:
        args.log_level = 'ERROR'
    elif args.verbose:
        args.log_level = 'DEBUG'
    
    # 重新配置日誌
    if args.log_file or args.log_level != 'INFO':
        checker.logger = checker._setup_logging(args.log_level, args.log_file)
    
    checker.logger.info("=== Flight Ticket Checker 啟動 ===")
    checker.logger.info(f"運行模式: {'自動' if args.auto_mode else '互動'}")
    checker.logger.info(f"程序資訊: PID={os.getpid()}, OS={os.name}")
    
    try:        # 顯示橫幅 (僅互動模式且非安靜模式)
        if not args.auto_mode and not args.quiet:
            checker.print_banner()
        
        # 用戶認證
        if not checker.authenticate_user(args.token):
            print(f"{Icons.ERROR} 認證失敗，程式退出")
            return 1
        
        # 設定查詢條件
        if args.auto_mode:
            # 自動模式使用預設條件 (或從環境變數讀取)
            checker.query_conditions = QueryConditions(
                from_airport=os.getenv('FLIGHT_FROM', 'TPE'),
                to_airport=os.getenv('FLIGHT_TO', 'NRT'),
                departure_date=datetime.now() + timedelta(days=1),
                min_price=int(os.getenv('FLIGHT_MIN_PRICE', '0')),
                max_price=int(os.getenv('FLIGHT_MAX_PRICE', '99999')),
                ticket_type=os.getenv('FLIGHT_TYPE')
            )
            checker.logger.info(f"使用自動模式查詢條件: "
                              f"{checker.query_conditions.from_airport} → "
                              f"{checker.query_conditions.to_airport}")
        else:
            # 互動模式獲取用戶輸入
            checker.get_query_conditions()
        
        # 開始監控
        checker.start_monitoring(args.auto_mode, args.duration)
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n{Icons.STOP} 程式被用戶中斷")
        return 0
    except Exception as e:
        checker.logger.error(f"程式執行錯誤: {e}")
        print(f"{Icons.ERROR} 程式執行錯誤: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())