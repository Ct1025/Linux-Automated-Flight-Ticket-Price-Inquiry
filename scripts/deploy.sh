#!/bin/bash
# deploy.sh - Flight Ticket Checker 系統部署腳本
# 作者: UNIX 專題小組

set -euo pipefail

# --- 設定區域 ---
INSTALL_DIR="/opt/flight-checker"
SERVICE_USER="flightchecker"
SERVICE_GROUP="flightchecker"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log/flight-checker"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- 輔助函式 ---
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此腳本需要 root 權限執行"
        exit 1
    fi
}

# --- 建立系統使用者 ---
create_system_user() {
    log_info "建立系統使用者和群組..."
    
    if ! getent group "$SERVICE_GROUP" > /dev/null; then
        groupadd --system "$SERVICE_GROUP"
        log_success "已建立群組: $SERVICE_GROUP"
    else
        log_warning "群組 $SERVICE_GROUP 已存在"
    fi
    
    if ! getent passwd "$SERVICE_USER" > /dev/null; then
        useradd --system --gid "$SERVICE_GROUP" \
                --home-dir "$INSTALL_DIR" \
                --shell /bin/false \
                --comment "Flight Checker Service User" \
                "$SERVICE_USER"
        log_success "已建立使用者: $SERVICE_USER"
    else
        log_warning "使用者 $SERVICE_USER 已存在"
    fi
}

# --- 建立目錄結構 ---
create_directories() {
    log_info "建立目錄結構..."
    
    mkdir -p "$INSTALL_DIR"/{cli,scripts,data,logs,systemd}
    mkdir -p "$LOG_DIR"
    
    # 設定權限
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
    
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$LOG_DIR"
    chmod 750 "$INSTALL_DIR"/{data,logs}
    
    log_success "目錄結構建立完成"
}

# --- 安裝 Python 依賴 ---
install_dependencies() {
    log_info "安裝 Python 依賴套件..."
    
    # 檢查 Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安裝，請先安裝 Python 3"
        exit 1
    fi
    
    # 檢查 pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安裝，請先安裝 pip3"
        exit 1
    fi
    
    # 安裝依賴
    pip3 install flask requests
    
    log_success "Python 依賴安裝完成"
}

# --- 複製檔案 ---
copy_files() {
    log_info "複製專案檔案..."
    
    # 複製主要程式檔案
    cp *.py "$INSTALL_DIR/"
    cp -r data "$INSTALL_DIR/"
    cp -r cli "$INSTALL_DIR/" 2>/dev/null || true
    cp -r scripts "$INSTALL_DIR/" 2>/dev/null || true
    
    # 設定執行權限
    chmod +x "$INSTALL_DIR"/scripts/*.sh 2>/dev/null || true
    chmod +x "$INSTALL_DIR"/cli/*.py 2>/dev/null || true
    
    # 設定檔案權限
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chmod 640 "$INSTALL_DIR"/data/*.json 2>/dev/null || true
    
    log_success "檔案複製完成"
}

# --- 安裝 systemd 服務 ---
install_systemd_services() {
    log_info "安裝 systemd 服務..."
    
    # 複製服務檔案
    if [[ -d "systemd" ]]; then
        cp systemd/*.service "$SYSTEMD_DIR/"
        cp systemd/*.timer "$SYSTEMD_DIR/"
        
        # 重新載入 systemd
        systemctl daemon-reload
        
        log_success "systemd 服務安裝完成"
    else
        log_warning "找不到 systemd 目錄，跳過服務安裝"
    fi
}

# --- 設定 logrotate ---
setup_logrotate() {
    log_info "設定日誌輪轉..."
    
    cat > /etc/logrotate.d/flight-checker << 'EOF'
/var/log/flight-checker/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    create 640 flightchecker flightchecker
    postrotate
        /usr/bin/systemctl reload flight-checker-* > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_success "logrotate 設定完成"
}

# --- 設定防火牆 ---
setup_firewall() {
    log_info "設定防火牆規則..."
    
    if command -v ufw &> /dev/null; then
        # 使用 ufw
        ufw allow 5000/tcp comment "Flight Checker API"
        log_success "已使用 ufw 開放 API 端口"
    elif command -v firewall-cmd &> /dev/null; then
        # 使用 firewalld
        firewall-cmd --permanent --add-port=5000/tcp
        firewall-cmd --reload
        log_success "已使用 firewalld 開放 API 端口"
    else
        log_warning "未找到防火牆管理工具，請手動設定"
    fi
}

# --- 設定 cron 任務 ---
setup_monitoring() {
    log_info "設定監控任務..."
    
    # 建立 cron 任務來執行 log_watcher.sh
    if [[ -f "$INSTALL_DIR/scripts/log_watcher.sh" ]]; then
        cat > /etc/cron.d/flight-checker-monitor << EOF
# Flight Checker 監控任務
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# 每分鐘檢查一次濫用行為
* * * * * $SERVICE_USER $INSTALL_DIR/scripts/log_watcher.sh >> $LOG_DIR/monitor.log 2>&1
EOF
        
        chmod 644 /etc/cron.d/flight-checker-monitor
        log_success "監控任務設定完成"
    else
        log_warning "找不到監控腳本，跳過監控設定"
    fi
}

# --- 啟動服務 ---
start_services() {
    log_info "啟動服務..."
    
    # 啟用並啟動 timer
    if systemctl list-unit-files | grep -q "vip-checker.timer"; then
        systemctl enable vip-checker.timer
        systemctl start vip-checker.timer
        log_success "VIP checker timer 已啟動"
    fi
    
    if systemctl list-unit-files | grep -q "normal-checker.timer"; then
        systemctl enable normal-checker.timer
        systemctl start normal-checker.timer
        log_success "Normal checker timer 已啟動"
    fi
}

# --- 驗證安裝 ---
verify_installation() {
    log_info "驗證安裝..."
    
    # 檢查使用者
    if getent passwd "$SERVICE_USER" > /dev/null; then
        log_success "✓ 系統使用者已建立"
    else
        log_error "✗ 系統使用者建立失敗"
    fi
    
    # 檢查目錄
    if [[ -d "$INSTALL_DIR" ]]; then
        log_success "✓ 安裝目錄已建立"
    else
        log_error "✗ 安裝目錄建立失敗"
    fi
    
    # 檢查權限
    if [[ -O "$INSTALL_DIR" ]] || [[ $(stat -c %U "$INSTALL_DIR") == "$SERVICE_USER" ]]; then
        log_success "✓ 目錄權限設定正確"
    else
        log_error "✗ 目錄權限設定錯誤"
    fi
    
    # 檢查服務
    if systemctl list-unit-files | grep -q "checker.timer"; then
        log_success "✓ systemd 服務已安裝"
    else
        log_warning "⚠ systemd 服務未安裝"
    fi
    
    echo
    log_success "🎉 Flight Ticket Checker 部署完成！"
    echo
    echo "後續步驟："
    echo "1. 編輯 $INSTALL_DIR/data/users.json 添加使用者"
    echo "2. 啟動 API 服務器: systemctl start flight-api"
    echo "3. 查看服務狀態: systemctl status vip-checker.timer"
    echo "4. 查看日誌: journalctl -u vip-checker -f"
    echo
}

# --- 主函式 ---
main() {
    echo "🚀 Flight Ticket Checker 系統部署腳本"
    echo "======================================"
    
    check_root
    
    create_system_user
    create_directories
    install_dependencies
    copy_files
    install_systemd_services
    setup_logrotate
    setup_firewall
    setup_monitoring
    start_services
    verify_installation
}

# --- 執行主程式 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
