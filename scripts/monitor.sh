#!/bin/bash
# monitor.sh - Flight Ticket Checker 系統監控腳本
# 作者: UNIX 專題小組

# --- 設定區域 ---
INSTALL_DIR="/opt/flight-checker"
LOG_DIR="/var/log/flight-checker"
API_URL="http://localhost:5000/api/flights"
ALERT_EMAIL="admin@example.com"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- 輔助函式 ---
log_info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
log_error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }

# --- 檢查服務狀態 ---
check_services() {
    log_info "🔍 檢查系統服務狀態..."
    
    local services=("vip-checker.timer" "normal-checker.timer")
    local all_ok=true
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log_success "✓ $service 運行正常"
        else
            log_error "✗ $service 未運行"
            all_ok=false
            
            # 嘗試重啟服務
            systemctl start "$service" && \
                log_info "🔄 已嘗試重啟 $service" || \
                log_error "❌ 重啟 $service 失敗"
        fi
    done
    
    return $all_ok
}

# --- 檢查 API 健康狀態 ---
check_api_health() {
    log_info "🌐 檢查 API 服務健康狀態..."
    
    # 使用測試 token 進行健康檢查
    local test_token="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    local test_params="from=TPE&to=NRT&date=$(date -d '+1 day' '+%Y-%m-%d')"
    
    local response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $test_token" \
        "$API_URL?$test_params" \
        -o /tmp/api_health_check.json 2>/dev/null)
    
    if [[ "$response" == "200" ]]; then
        log_success "✓ API 服務健康"
        return 0
    elif [[ "$response" == "429" ]]; then
        log_warning "⚠ API 達到速率限制 (正常現象)"
        return 0
    elif [[ "$response" == "401" ]]; then
        log_error "✗ API 認證失敗"
        return 1
    else
        log_error "✗ API 服務異常 (HTTP $response)"
        return 1
    fi
}

# --- 檢查系統資源 ---
check_system_resources() {
    log_info "📊 檢查系統資源使用狀況..."
    
    # CPU 使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_warning "⚠ CPU 使用率偏高: ${cpu_usage}%"
    else
        log_success "✓ CPU 使用率正常: ${cpu_usage}%"
    fi
    
    # 記憶體使用率
    local mem_info=$(free | grep Mem)
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_usage=$(echo "scale=2; $mem_used * 100 / $mem_total" | bc)
    
    if (( $(echo "$mem_usage > 85" | bc -l) )); then
        log_warning "⚠ 記憶體使用率偏高: ${mem_usage}%"
    else
        log_success "✓ 記憶體使用率正常: ${mem_usage}%"
    fi
    
    # 磁碟使用率
    local disk_usage=$(df "$INSTALL_DIR" | tail -1 | awk '{print $5}' | cut -d'%' -f1)
    if (( disk_usage > 90 )); then
        log_warning "⚠ 磁碟使用率偏高: ${disk_usage}%"
    else
        log_success "✓ 磁碟使用率正常: ${disk_usage}%"
    fi
}

# --- 檢查日誌檔案 ---
check_log_files() {
    log_info "📋 檢查日誌檔案狀態..."
    
    local log_files=(
        "$LOG_DIR/ticket-checker.log"
        "$LOG_DIR/blocked.log"
        "$LOG_DIR/monitor.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            local size=$(du -h "$log_file" | cut -f1)
            log_success "✓ $(basename "$log_file"): $size"
            
            # 檢查檔案是否過大
            local size_mb=$(du -m "$log_file" | cut -f1)
            if (( size_mb > 100 )); then
                log_warning "⚠ 日誌檔案過大，建議進行輪轉"
            fi
        else
            log_warning "⚠ 日誌檔案不存在: $log_file"
        fi
    done
}

# --- 檢查近期錯誤 ---
check_recent_errors() {
    log_info "🔍 檢查近期錯誤和異常..."
    
    # 檢查 systemd 日誌中的錯誤
    local recent_errors=$(journalctl -u "vip-checker*" -u "normal-checker*" \
                         --since "1 hour ago" --priority=err --no-pager -q)
    
    if [[ -n "$recent_errors" ]]; then
        log_error "發現近期錯誤:"
        echo "$recent_errors"
    else
        log_success "✓ 未發現近期嚴重錯誤"
    fi
    
    # 檢查封鎖日誌
    if [[ -f "$LOG_DIR/blocked.log" ]]; then
        local recent_blocks=$(tail -20 "$LOG_DIR/blocked.log" | grep "$(date '+%Y-%m-%d')")
        if [[ -n "$recent_blocks" ]]; then
            log_warning "⚠ 今日有以下封鎖記錄:"
            echo "$recent_blocks"
        fi
    fi
}

# --- 生成報告 ---
generate_report() {
    local report_file="/tmp/flight-checker-report-$(date '+%Y%m%d-%H%M%S').txt"
    
    {
        echo "Flight Ticket Checker 系統監控報告"
        echo "生成時間: $(date)"
        echo "========================================"
        echo
        
        echo "=== 服務狀態 ==="
        systemctl status vip-checker.timer normal-checker.timer --no-pager -l
        echo
        
        echo "=== 系統資源 ==="
        echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')"
        echo "記憶體: $(free -h | grep Mem)"
        echo "磁碟: $(df -h "$INSTALL_DIR")"
        echo
        
        echo "=== 近期日誌 ==="
        journalctl -u "vip-checker*" -u "normal-checker*" \
                   --since "1 hour ago" --no-pager | tail -50
        echo
        
        echo "=== 封鎖記錄 ==="
        if [[ -f "$LOG_DIR/blocked.log" ]]; then
            tail -20 "$LOG_DIR/blocked.log"
        else
            echo "無封鎖記錄"
        fi
        
    } > "$report_file"
    
    log_success "📄 監控報告已生成: $report_file"
    echo "$report_file"
}

# --- 發送告警 ---
send_alert() {
    local message="$1"
    local severity="$2"
    
    # 發送系統通知
    wall "🚨 Flight Checker Alert [$severity]: $message"
    
    # 寫入系統日誌
    logger -p daemon.warning -t flight-checker-monitor "$message"
    
    # 發送郵件 (如果配置了)
    if command -v mail &>/dev/null && [[ -n "$ALERT_EMAIL" ]]; then
        echo "$message

詳細資訊請查看監控報告:
$(generate_report)" | mail -s "Flight Checker Alert [$severity]" "$ALERT_EMAIL"
    fi
}

# --- 自動修復 ---
auto_repair() {
    log_info "🔧 嘗試自動修復..."
    
    # 重啟失敗的服務
    local failed_services=$(systemctl list-units --failed --no-legend | \
                            grep "checker" | awk '{print $1}')
    
    for service in $failed_services; do
        log_info "🔄 重啟失敗的服務: $service"
        systemctl restart "$service" && \
            log_success "✓ $service 重啟成功" || \
            log_error "✗ $service 重啟失敗"
    done
    
    # 清理臨時文件
    find /tmp -name "flight-checker-*" -mtime +1 -delete 2>/dev/null || true
    
    # 清理過期日誌
    find "$LOG_DIR" -name "*.log.*" -mtime +30 -delete 2>/dev/null || true
}

# --- 主函式 ---
main() {
    local mode="${1:-check}"
    
    echo "🔍 Flight Ticker Checker 系統監控"
    echo "=================================="
    echo "模式: $mode"
    echo "時間: $(date)"
    echo
    
    case "$mode" in
        check)
            check_services
            check_api_health
            check_system_resources
            check_log_files
            check_recent_errors
            ;;
        report)
            generate_report
            ;;
        repair)
            auto_repair
            ;;
        alert)
            local message="${2:-系統異常}"
            local severity="${3:-WARNING}"
            send_alert "$message" "$severity"
            ;;
        *)
            echo "用法: $0 [check|report|repair|alert]"
            echo "  check  - 執行健康檢查 (預設)"
            echo "  report - 生成監控報告"
            echo "  repair - 嘗試自動修復"
            echo "  alert  - 發送告警訊息"
            exit 1
            ;;
    esac
}

# --- 執行主程式 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
