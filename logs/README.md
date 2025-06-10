# Logs 目錄說明

此目錄用於存放系統運行過程中產生的各種日誌文件。

## 日誌文件說明

### ticket-checker.log
- **用途**：記錄所有機票查詢 API 的請求日誌
- **格式**：`TIMESTAMP [API_REQUEST] token=TOKEN_VALUE status=STATUS ip=IP_ADDRESS endpoint=ENDPOINT params=PARAMS`
- **內容包含**：
  - 請求時間戳
  - 使用者 Token
  - 請求狀態（SUCCESS, ERROR, RATE_LIMITED 等）
  - 來源 IP 地址
  - API 端點
  - 查詢參數

### blocked.log
- **用途**：記錄系統防禦機制的執行日誌
- **格式**：`TIMESTAMP [LOG_WATCHER/BLOCKED] ACTION_DESCRIPTION`
- **內容包含**：
  - 封鎖動作時間
  - 被封鎖的 Token 或 IP
  - 封鎖原因（請求頻率過高等）
  - 防禦措施（IP 封鎖、帳號鎖定等）

## 日誌輪轉設定

建議使用 logrotate 來管理日誌文件：

```bash
# /etc/logrotate.d/flight-checker
/opt/flight-checker/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 flightchecker flightchecker
    postrotate
        systemctl reload log-watcher || true
    endscript
}
```

## 監控命令

```bash
# 即時監控 API 請求
tail -f ticket-checker.log

# 即時監控防禦動作
tail -f blocked.log

# 查看今日的封鎖記錄
grep "$(date '+%Y-%m-%d')" blocked.log

# 統計請求頻率
grep "API_REQUEST" ticket-checker.log | grep "$(date '+%Y-%m-%d')" | wc -l
```

## 權限設定

- 檔案擁有者：`flightchecker:flightchecker`
- 檔案權限：`644` (讀寫 for owner, 只讀 for group/others)
- 目錄權限：`755` (完整權限 for owner, 讀取執行 for others) 