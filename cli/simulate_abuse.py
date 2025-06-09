#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulate_abuse.py - Flight Ticket API 濫用行為模擬器
作者: UNIX 專題小組
功能: 模擬異常查詢行為，用於測試系統防禦機制
"""

import os
import sys
import json
import time
import random
import signal
import argparse
import requests
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

class AbuseSimulator:
    def __init__(self, api_url="http://127.0.0.1:5000/api/flights", 
                 users_file="data/users.json"):
        self.api_url = api_url
        self.users_file = users_file
        self.running = True
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.blocked_requests = 0
        
        # 載入使用者資料
        self.users = self.load_users()
        
        # 設定信號處理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_users(self):
        """載入使用者資料"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ 無法載入使用者資料: {e}")
            return []
    
    def signal_handler(self, signum, frame):
        """處理終止信號"""
        print(f"\n🛑 收到信號 {signum}，正在停止模擬...")
        self.running = False
    
    def generate_random_query(self):
        """產生隨機查詢參數"""
        airports = ["TPE", "NRT", "KIX", "SIN", "BKK"]
        ticket_types = ["promo", "normal", "peak", None]
        
        from_airport = random.choice(airports)
        to_airport = random.choice([a for a in airports if a != from_airport])
        
        # 隨機日期 (今天到未來30天)
        base_date = datetime.now().date()
        random_days = random.randint(0, 30)
        query_date = base_date + timedelta(days=random_days)
        
        params = {
            'from': from_airport,
            'to': to_airport,
            'date': query_date.strftime('%Y-%m-%d'),
            'min_price': random.randint(1000, 5000),
            'max_price': random.randint(8000, 15000)
        }
        
        # 隨機添加票種過濾
        ticket_type = random.choice(ticket_types)
        if ticket_type:
            params['type'] = ticket_type
            
        return params
    
    def make_request(self, token, params):
        """發送 API 請求"""
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.get(self.api_url, headers=headers, 
                                  params=params, timeout=5)
            
            self.total_requests += 1
            
            if response.status_code == 200:
                self.successful_requests += 1
                return "SUCCESS", response.json()
            elif response.status_code == 429:
                self.blocked_requests += 1
                return "RATE_LIMITED", None
            elif response.status_code == 401:
                self.failed_requests += 1
                return "AUTH_FAILED", None
            else:
                self.failed_requests += 1
                return f"ERROR_{response.status_code}", None
                
        except requests.exceptions.RequestException as e:
            self.failed_requests += 1
            return "CONNECTION_ERROR", str(e)
    
    def write_log(self, token, status, params, response_data=None):
        """寫入日誌 (模擬真實的 API 請求日誌)"""
        log_entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "type": "API_REQUEST",
            "token": token[:8] + "..." if len(token) > 8 else token,
            "status": status,
            "params": params,
            "ip": f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"  # 模擬 IP
        }
        
        # 確保日誌目錄存在
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 寫入日誌文件
        log_file = os.path.join(log_dir, "ticket-checker.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{log_entry['timestamp']} [API_REQUEST] "
                   f"token={token} status={status} "
                   f"ip={log_entry['ip']} endpoint={self.api_url} "
                   f"params={json.dumps(params)}\n")
    
    def simulate_normal_usage(self, duration=60, requests_per_minute=10):
        """模擬正常使用行為"""
        print(f"🟢 開始模擬正常使用 (持續 {duration} 秒，每分鐘 {requests_per_minute} 次請求)")
        
        end_time = time.time() + duration
        interval = 60.0 / requests_per_minute
        
        while self.running and time.time() < end_time:
            user = random.choice(self.users)
            token = user['token']
            params = self.generate_random_query()
            
            status, response = self.make_request(token, params)
            self.write_log(token, status, params, response)
            
            print(f"📊 正常請求 - Token: {token[:8]}... Status: {status}")
            
            if self.running:
                time.sleep(interval)
    
    def simulate_burst_attack(self, duration=30, requests_per_second=5):
        """模擬突發攻擊行為"""
        print(f"🔴 開始模擬突發攻擊 (持續 {duration} 秒，每秒 {requests_per_second} 次請求)")
        
        # 選擇一個 token 進行攻擊
        attack_user = random.choice(self.users)
        attack_token = attack_user['token']
        
        end_time = time.time() + duration
        interval = 1.0 / requests_per_second
        
        while self.running and time.time() < end_time:
            params = self.generate_random_query()
            status, response = self.make_request(attack_token, params)
            self.write_log(attack_token, status, params, response)
            
            print(f"💥 攻擊請求 - Token: {attack_token[:8]}... Status: {status}")
            
            if self.running:
                time.sleep(interval)
    
    def simulate_distributed_attack(self, duration=60, total_rps=20):
        """模擬分散式攻擊行為"""
        print(f"🟡 開始模擬分散式攻擊 (持續 {duration} 秒，總計每秒 {total_rps} 次請求)")
        
        def worker_thread(token, rps):
            interval = 1.0 / rps if rps > 0 else 1.0
            end_time = time.time() + duration
            
            while self.running and time.time() < end_time:
                params = self.generate_random_query()
                status, response = self.make_request(token, params)
                self.write_log(token, status, params, response)
                
                print(f"🌐 分散攻擊 - Token: {token[:8]}... Status: {status}")
                
                if self.running:
                    time.sleep(interval)
        
        # 將請求分散到多個 token
        tokens_to_use = min(len(self.users), 5)  # 最多使用 5 個 token
        rps_per_token = total_rps / tokens_to_use
        
        with ThreadPoolExecutor(max_workers=tokens_to_use) as executor:
            futures = []
            for i in range(tokens_to_use):
                user = self.users[i]
                future = executor.submit(worker_thread, user['token'], rps_per_token)
                futures.append(future)
            
            # 等待所有線程完成
            for future in futures:
                future.result()
    
    def print_statistics(self):
        """打印統計資訊"""
        print("\n" + "="*50)
        print("📈 模擬統計報告")
        print("="*50)
        print(f"總請求數: {self.total_requests}")
        print(f"成功請求: {self.successful_requests}")
        print(f"失敗請求: {self.failed_requests}")
        print(f"被限流請求: {self.blocked_requests}")
        
        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100
            block_rate = (self.blocked_requests / self.total_requests) * 100
            print(f"成功率: {success_rate:.1f}%")
            print(f"限流率: {block_rate:.1f}%")
        
        print("="*50)
    
    def run_scenario(self, scenario, **kwargs):
        """執行指定情境"""
        start_time = time.time()
        
        if scenario == "normal":
            self.simulate_normal_usage(**kwargs)
        elif scenario == "burst":
            self.simulate_burst_attack(**kwargs)
        elif scenario == "distributed":
            self.simulate_distributed_attack(**kwargs)
        elif scenario == "mixed":
            # 混合模式：先正常使用，然後突發攻擊
            self.simulate_normal_usage(duration=30, requests_per_minute=5)
            if self.running:
                time.sleep(5)
                self.simulate_burst_attack(duration=60, requests_per_second=10)
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  模擬完成，耗時: {elapsed_time:.1f} 秒")
        self.print_statistics()

def main():
    parser = argparse.ArgumentParser(description="Flight Ticket API 濫用行為模擬器")
    parser.add_argument("--scenario", choices=["normal", "burst", "distributed", "mixed"],
                       default="burst", help="模擬情境")
    parser.add_argument("--duration", type=int, default=60, help="模擬持續時間（秒）")
    parser.add_argument("--rps", type=int, default=5, help="每秒請求數")
    parser.add_argument("--api-url", default="http://127.0.0.1:5000/api/flights",
                       help="API 服務器 URL")
    parser.add_argument("--users-file", default="data/users.json",
                       help="使用者資料文件路徑")
    
    args = parser.parse_args()
    
    print("🚀 Flight Ticket API 濫用模擬器啟動")
    print(f"🎯 模擬情境: {args.scenario}")
    print(f"⏰ 持續時間: {args.duration} 秒")
    print(f"🔥 請求頻率: {args.rps} RPS")
    print("-" * 50)
    
    simulator = AbuseSimulator(api_url=args.api_url, users_file=args.users_file)
    
    if not simulator.users:
        print("❌ 無法載入使用者資料，請確認 users.json 文件存在")
        sys.exit(1)
    
    try:
        if args.scenario == "normal":
            simulator.run_scenario("normal", duration=args.duration, 
                                 requests_per_minute=args.rps * 60)
        elif args.scenario == "burst":
            simulator.run_scenario("burst", duration=args.duration, 
                                 requests_per_second=args.rps)
        elif args.scenario == "distributed":
            simulator.run_scenario("distributed", duration=args.duration, 
                                 total_rps=args.rps)
        elif args.scenario == "mixed":
            simulator.run_scenario("mixed")
            
    except KeyboardInterrupt:
        print("\n🛑 使用者中斷模擬")
    except Exception as e:
        print(f"❌ 模擬過程中發生錯誤: {e}")
    finally:
        simulator.print_statistics()

if __name__ == "__main__":
    main()
