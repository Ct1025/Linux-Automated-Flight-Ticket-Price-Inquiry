### A. 系統整合與防禦邏輯設計

使用技術：
- systemd.service / timer（帳號排程）
- shell script（log 偵測、封鎖帳號）
- journalctl、logger、usermod、iptables（系統管控）
- Python 模擬腳本（異常查詢觸發）

負責內容：
- 設定 VIP / Free 用戶的 systemd 查詢排程（如每 30 秒 / 5 分鐘）
- 撰寫 log 偵測腳本，封鎖過度請求帳號或移除查詢工具執行權限
- 撰寫異常查詢模擬腳本 `simulate_abuse.py`，用於觸發防禦邏輯
- 整合 Linux 排程、log 與帳號權限機制，形成自動化防禦流程
- 測試各組員模組的整合相容性與防線有效性

對應檔案結構：
systemd/
├── vip-checker.service
├── vip-checker.timer
├── normal-checker.service
├── normal-checker.timer
scripts/
├── log_watcher.sh
cli/
├── simulate_abuse.py
logs/
├── ticket-checker.log
├── blocked.log