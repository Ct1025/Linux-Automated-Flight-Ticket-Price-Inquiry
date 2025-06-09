# Linux-Automated-Flight-Ticket-Price-Inquiry

> 基於 UNIX 系統程式設計理念的自動化航班票價查詢系統

## 🎯 專案概述

本專案是一個完整的 UNIX/Linux 系統解決方案，展現了現代 UNIX 系統程式設計的核心概念：

- **模組化設計** - 遵循 UNIX 哲學 "Do One Thing Well"
- **系統整合** - 深度整合 Linux 系統服務和工具
- **自動化運維** - 使用 systemd、cron、shell scripting 實現自動化
- **安全防護** - 實現多層次的系統安全機制
- **跨平台兼容** - 支援 Windows/Linux 跨平台運行

## 🏗️ 系統架構

```
Linux Flight Ticket Checker
├── API 服務層
│   ├── Flask RESTful API
│   ├── Token 認證系統
│   └── 速率限制機制
├── CLI 工具層  
│   ├── 非阻塞式輸入處理
│   ├── 跨平台系統調用
│   └── 動態查詢引擎
├── 系統整合層
│   ├── systemd 服務管理
│   ├── cron 定時任務
│   └── 自動化部署腳本
└── 安全防護層
    ├── 日誌監控系統
    ├── 入侵偵測機制
    └── 自動封鎖邏輯
```

## 🔧 UNIX 技術棧

### 核心 UNIX 概念應用

1. **進程管理與 IPC**
   - HTTP API 作為進程間通信機制
   - systemd 服務生命週期管理
   - 信號處理 (SIGTERM, SIGINT)

2. **檔案系統與權限**
   - UNIX 檔案權限模型
   - 專用系統使用者和群組
   - 安全的檔案存取控制

3. **系統調用與底層 API**
   - `termios` - 終端控制
   - `select` - I/O 多工
   - `signal` - 信號處理

4. **Shell 程式設計**
   - Bash 腳本自動化
   - 管道和重導向
   - 文本處理工具鏈

### 系統工具整合

```bash
# systemd 服務管理
systemctl status vip-checker.timer
journalctl -u normal-checker -f

# 日誌分析與監控
tail -f /var/log/flight-checker/ticket-checker.log
grep "BLOCKED" /var/log/flight-checker/blocked.log

# 網路安全管理
iptables -L INPUT | grep DROP
ss -tlnp | grep :5000

# 系統資源監控
ps aux | grep flight-checker
netstat -an | grep 5000
```

## 📦 安裝與部署

### 自動化部署 (推薦)

```bash
# 下載專案
git clone <repository-url>
cd Linux-Automated-Flight-Ticket-Price-Inquiry

# 執行自動部署腳本 (需要 root 權限)
sudo chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh

# 驗證安裝
sudo systemctl status vip-checker.timer
sudo systemctl status normal-checker.timer
```

### 手動部署

<details>
<summary>展開手動部署步驟</summary>

1. **建立系統使用者**
```bash
sudo groupadd --system flightchecker
sudo useradd --system --gid flightchecker \
             --home-dir /opt/flight-checker \
             --shell /bin/false flightchecker
```

2. **建立目錄結構**
```bash
sudo mkdir -p /opt/flight-checker/{cli,scripts,data,logs}
sudo mkdir -p /var/log/flight-checker
sudo chown -R flightchecker:flightchecker /opt/flight-checker
```

3. **複製檔案**
```bash
sudo cp *.py /opt/flight-checker/
sudo cp -r cli scripts systemd /opt/flight-checker/
sudo cp data/users.json /opt/flight-checker/data/
```

4. **安裝 systemd 服務**
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

5. **啟動服務**
```bash
sudo systemctl enable --now vip-checker.timer
sudo systemctl enable --now normal-checker.timer
```

</details>

## 🚀 使用方式

### 1. API 服務器

```bash
# 手動啟動
python3 api_server.py

# 使用 systemd 管理
sudo systemctl start flight-api
sudo systemctl enable flight-api
```

### 2. 使用者註冊

```bash
# 互動式註冊
python3 register.py

# 範例輸出
# Enter username: alice
# Enter password: ********
# Enter permission level (free/plus/pro): pro
# Your API Token: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 3. CLI 查詢工具

```bash
# 互動式查詢
python3 ticket-checker.py

# 自動化查詢 (systemd 管理)
systemctl status vip-checker.timer
```

### 4. 濫用行為模擬

```bash
# 模擬正常使用
python3 cli/simulate_abuse.py --scenario normal --duration 60

# 模擬突發攻擊
python3 cli/simulate_abuse.py --scenario burst --rps 10

# 模擬分散式攻擊
python3 cli/simulate_abuse.py --scenario distributed --rps 20
```

## 🛡️ 安全機制

### 多層次防護體系

1. **API 層防護**
   - Token 認證機制
   - 速率限制 (Rate Limiting)：
     - Free 用戶: 15 次/分鐘
     - Plus 用戶: 25 次/分鐘
     - Pro 用戶: 100 次/分鐘
   - 權限分級控制

2. **系統層防護**
   - 日誌實時監控
   - 自動 IP 封鎖
   - 使用者權限撤銷

3. **網路層防護**
   - iptables 規則管理
   - 入侵偵測系統
   - 異常流量分析

### 監控與告警

```bash
# 系統健康檢查
./scripts/monitor.sh check

# 生成監控報告
./scripts/monitor.sh report

# 自動修復
./scripts/monitor.sh repair

# 發送告警
./scripts/monitor.sh alert "API 服務異常" "CRITICAL"
```

## 📊 系統監控

### 即時監控

```bash
# 查看服務狀態
sudo systemctl status vip-checker.timer normal-checker.timer

# 監控系統日誌
sudo journalctl -f -u vip-checker -u normal-checker

# 監控應用日誌
sudo tail -f /var/log/flight-checker/ticket-checker.log

# 查看封鎖記錄
sudo tail -f /var/log/flight-checker/blocked.log
```

### 性能分析

```bash
# 系統資源使用
htop
iotop
nethogs

# 網路連接狀態
ss -tlnp
netstat -an | grep 5000

# 檔案描述符使用
lsof -p $(pgrep -f flight-checker)
```

## 🔧 故障排除

### 常見問題

1. **服務無法啟動**
```bash
sudo systemctl status vip-checker.service
sudo journalctl -u vip-checker.service
```

2. **API 無法連接**
```bash
curl -I http://localhost:5000/api/flights
netstat -tlnp | grep 5000
```

3. **權限問題**
```bash
sudo chown -R flightchecker:flightchecker /opt/flight-checker
sudo chmod 755 /opt/flight-checker
```

4. **日誌檔案過大**
```bash
sudo logrotate -f /etc/logrotate.d/flight-checker
```

### 除錯模式

```bash
# 啟用除錯模式
export FLASK_ENV=development
export FLASK_DEBUG=1

# 詳細日誌輸出
python3 api_server.py --verbose
```

## 📁 專案結構

```
Linux-Automated-Flight-Ticket-Price-Inquiry/
├── api_server.py              # Flask API 服務器
├── register.py                # 使用者註冊工具
├── ticket-checker.py          # CLI 查詢工具
├── data/
│   └── users.json            # 使用者資料庫
├── cli/
│   └── simulate_abuse.py     # 濫用行為模擬器
├── scripts/
│   ├── deploy.sh             # 自動部署腳本
│   ├── monitor.sh            # 系統監控腳本
│   └── log_watcher.sh        # 日誌監控腳本
├── systemd/
│   ├── vip-checker.service   # VIP 使用者服務
│   ├── vip-checker.timer     # VIP 使用者定時器
│   ├── normal-checker.service # 一般使用者服務
│   └── normal-checker.timer  # 一般使用者定時器
├── logs/                     # 日誌目錄
└── docs/                     # 文件目錄
    ├── api-auth.md
    ├── cli-checker.md
    └── system-integration.md
```

## 🎓 UNIX 學習重點

本專案展現的 UNIX 核心概念：

1. **程序設計哲學**
   - 模組化設計
   - 單一職責原則
   - 工具組合使用

2. **系統程式設計**
   - 系統調用使用
   - 信號處理機制
   - 檔案與權限管理

3. **Shell 程式設計**
   - Bash 腳本編寫
   - 文本處理工具鏈
   - 自動化任務管理

4. **系統管理**
   - 服務管理 (systemd)
   - 日誌管理與分析
   - 安全與監控

5. **網路程式設計**
   - Socket 程式設計概念
   - HTTP 協議應用
   - 網路安全機制

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request！

### 開發環境設定

```bash
# 複製專案
git clone <repository-url>
cd Linux-Automated-Flight-Ticket-Price-Inquiry

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install flask requests

# 執行測試
python3 -m pytest tests/
```

## 📄 授權條款

MIT License - 詳見 [LICENSE](LICENSE) 檔案

## 👥 作者

UNIX 專題小組

---

**本專案是 UNIX 系統程式設計的實踐示範，展現了 Linux 系統管理、自動化運維、和安全防護的完整解決方案。**
