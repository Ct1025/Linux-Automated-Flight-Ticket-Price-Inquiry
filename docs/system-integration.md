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

## 完成狀況分析

### ✅ 已完成項目
- **systemd 服務配置文件**（`vip-checker.service`, `normal-checker.service`）
- **systemd 定時器配置**（`vip-checker.timer`, `normal-checker.timer`）
- **log 偵測腳本**（`log_watcher.sh`）- 功能完整
- **異常查詢模擬腳本**（`simulate_abuse.py`）- 功能完整

### ❌ 仍需完成的項目
1. **建立 logs 目錄結構** - 目前 `logs/` 目錄不存在
2. **部署腳本整合測試** - 需要完整的部署流程驗證
3. **各組員模組整合測試** - 需要測試所有組件的相容性
4. **實際 Linux 環境部署驗證** - 確保在真實 Linux 環境中運作正常

## Scripts 檔案說明

`/scripts` 內的檔案**不是直接 demo**，而是**實際的生產級腳本**：

- `log_watcher.sh` - 完整的濫用偵測與防禦腳本，包含：
  - 日誌分析功能
  - IP 封鎖機制（使用 iptables）
  - 使用者權限撤銷
  - 系統通知機制
  
- `monitor.sh` - 系統監控腳本
- `deploy.sh` - 部署腳本

這些都是可以在 Linux 環境中直接執行的完整腳本。

## Linux Demo 流程

### 📋 準備階段
```bash
# 1. 建立必要目錄
sudo mkdir -p /opt/flight-checker
sudo mkdir -p /opt/flight-checker/logs
sudo mkdir -p /opt/flight-checker/data

# 2. 建立系統使用者
sudo useradd -r -s /bin/bash -d /opt/flight-checker flightchecker
sudo chown -R flightchecker:flightchecker /opt/flight-checker
```

### 🚀 部署階段
```bash
# 1. 複製檔案到系統目錄
sudo cp -r . /opt/flight-checker/
sudo chmod +x /opt/flight-checker/scripts/*.sh
sudo chmod +x /opt/flight-checker/cli/simulate_abuse.py

# 2. 安裝 systemd 服務
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

### 🔧 啟動服務
```bash
# 1. 啟動定時器
sudo systemctl enable vip-checker.timer
sudo systemctl enable normal-checker.timer
sudo systemctl start vip-checker.timer
sudo systemctl start normal-checker.timer

# 2. 啟動監控腳本
sudo systemctl enable log-watcher
sudo systemctl start log-watcher
```

### 🧪 測試 Demo
```bash
# 1. 啟動 API 服務器
cd /opt/flight-checker
python3 api_server.py &

# 2. 模擬正常使用（背景運行）
python3 cli/simulate_abuse.py --scenario normal --duration 120 &

# 3. 模擬攻擊行為
python3 cli/simulate_abuse.py --scenario burst --duration 60 --rps 10

# 4. 觀察防禦效果
tail -f logs/ticket-checker.log
tail -f logs/blocked.log
```

### 📊 監控 Demo 效果
```bash
# 查看服務狀態
sudo systemctl status vip-checker.timer
sudo systemctl status normal-checker.timer

# 查看日誌
sudo journalctl -u vip-checker -f
sudo journalctl -u log-watcher -f

# 查看封鎖效果
sudo iptables -L INPUT
cat /opt/flight-checker/logs/blocked.log
```

### 🛑 清理與重置
```bash
# 停止所有服務
sudo systemctl stop vip-checker.timer normal-checker.timer
sudo killall python3

# 清理 iptables 規則
sudo iptables -F INPUT

# 重置日誌
sudo rm -f /opt/flight-checker/logs/*.log
```

## 注意事項

1. **權限設定**：確保 flightchecker 使用者有適當的權限執行監控腳本
2. **防火牆規則**：log_watcher.sh 需要 root 權限來操作 iptables
3. **日誌輪轉**：建議設定 logrotate 來管理日誌文件大小
4. **監控告警**：可以整合 systemd 的 OnFailure 機制來發送故障通知

這個流程會完整展示系統整合與防禦邏輯的運作，包括自動化排程、濫用偵測、以及防禦機制的有效性。