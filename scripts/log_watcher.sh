#!/bin/bash
# log_watcher.sh - Flight Ticket API 濫用偵測與防禦腳本
# 作者: UNIX 專題小組
# 功能: 監控 API 請求日誌，自動封鎖濫用帳號

# --- 設定區域 ---
LOG_FILE="/opt/flight-checker/logs/ticket-checker.log"
BLOCKED_LOG="/opt/flight-checker/logs/blocked.log"
TEMP_DIR="/tmp/flight-checker"
ABUSE_THRESHOLD=100        # 每分鐘請求次數閾值
TIME_WINDOW=60            # 時間窗口（秒）
BLOCK_DURATION=3600       # 封鎖時長（秒）

# 建立必要目錄
mkdir -p "$TEMP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$BLOCKED_LOG")"

# --- 日誌函式 ---
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [LOG_WATCHER] $1" | tee -a "$BLOCKED_LOG"
}

log_block_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [BLOCKED] $1" | tee -a "$BLOCKED_LOG"
    logger -t flight-defender "$1"
}

# --- 解析日誌並統計請求頻率 ---
analyze_requests() {
    local current_time=$(date +%s)
    local window_start=$((current_time - TIME_WINDOW))
    
    # 從日誌中提取最近時間窗口內的請求
    if [[ -f "$LOG_FILE" ]]; then
        # 使用 awk 解析日誌格式並統計每個 token 的請求次數
        awk -v start_time="$window_start" -v current="$current_time" '
        /API_REQUEST/ {
            # 假設日誌格式: TIMESTAMP [API_REQUEST] token=TOKEN_VALUE endpoint=ENDPOINT
            if (match($0, /token=([a-zA-Z0-9]+)/, token_match)) {
                # 提取時間戳 (假設格式為 YYYY-MM-DD HH:MM:SS)
                if (match($0, /^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})/, time_match)) {
                    cmd = "date -d \"" time_match[1] "\" +%s"
                    cmd | getline timestamp
                    close(cmd)
                    
                    if (timestamp >= start_time && timestamp <= current) {
                        token_count[token_match[1]]++
                    }
                }
            }
        }
        END {
            for (token in token_count) {
                if (token_count[token] > '$ABUSE_THRESHOLD') {
                    print token ":" token_count[token]
                }
            }
        }' "$LOG_FILE" > "$TEMP_DIR/abuse_tokens.tmp"
    fi
}

# --- 封鎖濫用 Token ---
block_abusive_tokens() {
    if [[ -s "$TEMP_DIR/abuse_tokens.tmp" ]]; then
        while IFS=':' read -r token count; do
            log_block_action "檢測到濫用 Token: $token (請求次數: $count 次/分鐘)"
            
            # 將 token 加入黑名單
            echo "$token:$(date +%s):$BLOCK_DURATION" >> "$TEMP_DIR/blocked_tokens.list"
            
            # 使用 iptables 封鎖相關 IP (如果有記錄)
            block_token_ip "$token"
            
            # 移除使用者的執行權限 (如果是系統使用者)
            revoke_user_permissions "$token"
            
            # 發送系統通知
            notify_admin "$token" "$count"
            
        done < "$TEMP_DIR/abuse_tokens.tmp"
    fi
}

# --- 封鎖 IP 地址 ---
block_token_ip() {
    local token="$1"
    
    # 從日誌中查找該 token 對應的 IP 地址
    local ip_list=$(grep "token=$token" "$LOG_FILE" | \
                   grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | \
                   sort -u)
    
    for ip in $ip_list; do
        if [[ -n "$ip" ]]; then
            # 檢查是否已經被封鎖
            if ! iptables -L INPUT | grep -q "$ip"; then
                iptables -I INPUT -s "$ip" -j DROP
                log_block_action "已封鎖 IP 地址: $ip (關聯 Token: $token)"
                
                # 設定自動解封定時器
                (sleep "$BLOCK_DURATION"; iptables -D INPUT -s "$ip" -j DROP; \
                 log_message "已解封 IP 地址: $ip") &
            fi
        fi
    done
}

# --- 撤銷使用者權限 ---
revoke_user_permissions() {
    local token="$1"
    
    # 從 users.json 中查找對應的使用者名稱
    local username=$(python3 -c "
import json
try:
    with open('/opt/flight-checker/data/users.json', 'r') as f:
        users = json.load(f)
    for user in users:
        if user.get('token') == '$token':
            print(user.get('username', ''))
            break
except:
    pass
")
    
    if [[ -n "$username" ]] && id "$username" &>/dev/null; then
        # 移除執行權限
        usermod -s /bin/false "$username"
        
        # 鎖定帳號
        usermod -L "$username"
        
        log_block_action "已鎖定使用者帳號: $username (Token: $token)"
        
        # 設定自動解鎖定時器
        (sleep "$BLOCK_DURATION"; \
         usermod -U "$username"; \
         usermod -s /bin/bash "$username"; \
         log_message "已解鎖使用者帳號: $username") &
    fi
}

# --- 通知管理員 ---
notify_admin() {
    local token="$1"
    local count="$2"
    
    # 發送系統通知
    wall "⚠️  Flight Ticket API 安全警告: 檢測到濫用行為 (Token: ${token:0:8}..., 請求: $count 次/分鐘)"
    
    # 寫入系統日誌
    logger -p daemon.warning -t flight-defender "API abuse detected: token=${token:0:8}... requests=$count/min"
    
    # 發送郵件給管理員 (如果配置了 mail 命令)
    if command -v mail &>/dev/null; then
        echo "檢測到 Flight Ticket API 濫用行為

Token: ${token:0:8}...
請求次數: $count 次/分鐘
時間: $(date)
動作: 已自動封鎖

詳細資訊請查看: $BLOCKED_LOG" | \
        mail -s "Flight Ticket API 安全警告" root
    fi
}

# --- 清理過期的封鎖記錄 ---
cleanup_expired_blocks() {
    if [[ -f "$TEMP_DIR/blocked_tokens.list" ]]; then
        local current_time=$(date +%s)
        local temp_file="$TEMP_DIR/blocked_tokens.tmp"
        
        while IFS=':' read -r token block_time duration; do
            local expire_time=$((block_time + duration))
            if [[ $current_time -lt $expire_time ]]; then
                echo "$token:$block_time:$duration" >> "$temp_file"
            else
                log_message "Token 封鎖已過期: ${token:0:8}..."
            fi
        done < "$TEMP_DIR/blocked_tokens.list"
        
        if [[ -f "$temp_file" ]]; then
            mv "$temp_file" "$TEMP_DIR/blocked_tokens.list"
        else
            rm -f "$TEMP_DIR/blocked_tokens.list"
        fi
    fi
}

# --- 主函式 ---
main() {
    log_message "開始 Flight Ticket API 濫用偵測..."
    
    # 分析請求頻率
    analyze_requests
    
    # 封鎖濫用者
    block_abusive_tokens
    
    # 清理過期封鎖
    cleanup_expired_blocks
    
    # 清理臨時文件
    rm -f "$TEMP_DIR/abuse_tokens.tmp"
    
    log_message "濫用偵測完成"
}

# --- 信號處理 ---
cleanup_and_exit() {
    log_message "收到終止信號，正在清理..."
    rm -f "$TEMP_DIR"/*.tmp
    exit 0
}

trap cleanup_and_exit SIGTERM SIGINT

# --- 執行主程式 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
