#!/bin/bash

set -euo pipefail

# --------------------------------------------------
# COLORS
# --------------------------------------------------

YELLOW="\033[1;93m"
GREEN="\033[0;32m"
RED="\033[0;31m"
BLUE="\033[0;34m"
RESET="\033[0m"

# --------------------------------------------------
# UI HELPERS
# --------------------------------------------------

section() {
    echo -e "\n${YELLOW}==================================================${RESET}"
    echo -e "${YELLOW} $1 ${RESET}"
    echo -e "${YELLOW}==================================================${RESET}\n"
}

info() {
    echo -e "${BLUE}[INFO]${RESET} $1"
}

success() {
    echo -e "${GREEN}[OK]${RESET} $1"
}

error() {
    echo -e "${RED}[ERROR]${RESET} $1"
}

# --------------------------------------------------
# PROGRESS BAR (MUST BE LAST OUTPUT)
# --------------------------------------------------

progress_bar() {
    local percent=$1
    local width=30

    local filled=$((percent * width / 100))
    local empty=$((width - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="#"; done
    for ((i=0; i<empty; i++)); do bar+="-"; done

    echo -ne "\r\033[K[${bar}] ${percent}%"
}

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

REPO_URL="https://github.com/jonaw2005/UARV.git"

APP_DIR="$HOME/UARV_repo"
WEB_DIR="/var/www/UARV"
BACKUP_DIR="/var/www/UARV_backups"

UARV_OPT_DIR="/opt/uarv"
VENV_DIR="$UARV_OPT_DIR/venv"
REQ_HASH_FILE="$UARV_OPT_DIR/requirements.hash"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_TARGET="$BACKUP_DIR/UARV_$TIMESTAMP"

FORCE=false
ROLLBACK=false
STATUS=false
NO_RESTART=false

# --------------------------------------------------
# ARGUMENTS
# --------------------------------------------------

section "ARGUMENT PARSING"

for arg in "$@"; do
    case "$arg" in
        --force)
            FORCE=true
            info "Force enabled"
            ;;
        --rollback)
            ROLLBACK=true
            info "Rollback enabled"
            ;;
        --status)
            STATUS=true
            info "Status mode"
            ;;
        --no-restart)
            NO_RESTART=true
            info "No restart mode"
            ;;
        *)
            error "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# --------------------------------------------------
# STATUS MODE
# --------------------------------------------------

if $STATUS; then
    section "STATUS"

    if [ -d "$APP_DIR/.git" ]; then
        cd "$APP_DIR"
        info "Repository"
        echo " Path: $APP_DIR"
        echo " Branch: $(git branch --show-current)"
        echo " Commit: $(git log -1 --oneline)"
    else
        error "Repo missing"
    fi

    echo

    if [ -d "$VENV_DIR" ]; then
        info "Venv"
        "$VENV_DIR/bin/python" --version
    else
        error "Venv missing"
    fi

    echo

    systemctl is-active --quiet nginx && success "Nginx active" || error "Nginx inactive"

    echo
    info "Backups:"
    ls -1 "$BACKUP_DIR" 2>/dev/null || echo "None"

    progress_bar 100
    echo ""
    exit 0
fi

# --------------------------------------------------
# ROLLBACK
# --------------------------------------------------

if $ROLLBACK; then
    section "ROLLBACK"

    LAST_BACKUP=$(ls -1t "$BACKUP_DIR" 2>/dev/null | head -n1)

    if [ -z "${LAST_BACKUP:-}" ]; then
        error "No backup found"
        progress_bar 100
        echo ""
        exit 1
    fi

    info "Restoring $LAST_BACKUP"

    sudo rm -rf "$WEB_DIR"
    sudo cp -a "$BACKUP_DIR/$LAST_BACKUP" "$WEB_DIR"

    sudo chown -R www-data:www-data "$WEB_DIR"
    sudo chmod -R 755 "$WEB_DIR"

    sudo nginx -t
    sudo systemctl reload nginx

    success "Rollback complete"

    progress_bar 100
    echo ""
    exit 0
fi

# --------------------------------------------------
# DEPLOY START
# --------------------------------------------------

section "DEPLOYMENT START"
info "Starting deployment..."

# --------------------------------------------------
# STOP UARV API (WS SAFE)
# --------------------------------------------------

section "STOP UARV API (WEBSOCKET SAFE)"

if ! $NO_RESTART; then
    info "Stopping service gracefully..."

    sudo systemctl stop uarv-api

    TIMEOUT=15
    COUNTER=0

    while systemctl is-active --quiet uarv-api; do
        sleep 1
        COUNTER=$((COUNTER+1))

        if [ $COUNTER -ge $TIMEOUT ]; then
            error "Graceful stop timeout"
            break
        fi
    done

    if systemctl is-active --quiet uarv-api; then
        error "Forcing SIGTERM..."
        sudo systemctl kill -s SIGTERM uarv-api
        sleep 5
    fi

    if systemctl is-active --quiet uarv-api; then
        error "Forcing SIGKILL..."
        sudo systemctl kill -s SIGKILL uarv-api
        sleep 2
    fi

    if systemctl is-active --quiet uarv-api; then
        error "Cannot stop service"
        progress_bar 100
        echo ""
        exit 1
    fi

    success "uarv-api fully stopped"
else
    info "Skipping uarv-api stop due to --no-restart flag."
fi

# --------------------------------------------------
# REPOSITORY
# --------------------------------------------------

section "REPOSITORY"

if [ -d "$APP_DIR/.git" ] && ! $FORCE; then
    cd "$APP_DIR"
    info "Git pull"
    git pull origin main
else
    info "Clone repo"
    rm -rf "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
success "Repo ready"

# --------------------------------------------------
# SYSTEM SETUP
# --------------------------------------------------

section "SYSTEM SETUP"

sudo mkdir -p "$UARV_OPT_DIR"
sudo chown -R "$USER:$USER" "$UARV_OPT_DIR"

success "System ready"

# --------------------------------------------------
# VENV
# --------------------------------------------------

section "PYTHON VENV"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    success "Venv created"
else
    info "Venv exists"
fi

# --------------------------------------------------
# DEPENDENCIES
# --------------------------------------------------

section "DEPENDENCIES"

if [ -f "requirements.txt" ]; then

    NEW_HASH=$(sha256sum requirements.txt | awk '{print $1}')
    OLD_HASH=""

    [ -f "$REQ_HASH_FILE" ] && OLD_HASH=$(cat "$REQ_HASH_FILE")

    if [ "$NEW_HASH" != "$OLD_HASH" ] || $FORCE; then
        "$VENV_DIR/bin/pip" install -r requirements.txt
        echo "$NEW_HASH" > "$REQ_HASH_FILE"
        success "Dependencies installed"
    else
        success "No changes"
    fi
else
    error "requirements.txt missing"
fi

# --------------------------------------------------
# BACKUP
# --------------------------------------------------

section "BACKUP"

sudo mkdir -p "$BACKUP_DIR"

if [ -d "$WEB_DIR" ]; then
    sudo cp -a "$WEB_DIR" "$BACKUP_TARGET"
    success "Backup created"
else
    info "No existing web dir"
fi

# --------------------------------------------------
# DEPLOY FRONTEND
# --------------------------------------------------

section "DEPLOY FRONTEND"

sudo rm -rf "$WEB_DIR"
sudo mkdir -p "$WEB_DIR"

sudo cp -a "$APP_DIR/admin_panel/." "$WEB_DIR/"

sudo chown -R www-data:www-data "$WEB_DIR"
sudo chmod -R 755 "$WEB_DIR"

success "Frontend deployed"

# --------------------------------------------------
# RESTART UARV API
# --------------------------------------------------

section "UARV API START"

if ! $NO_RESTART; then
    if systemctl is-active --quiet uarv-api; then
        sudo systemctl restart uarv-api
        success "uarv-api restarted"
    else
        sudo systemctl start uarv-api
        success "uarv-api started"
    fi
else
    info "Skipping uarv-api restart due to --no-restart flag."
fi

if ! $NO_RESTART; then
    systemctl is-active --quiet uarv-api && success "Service running" || error "Service failed"
fi

# --------------------------------------------------
# NGINX
# --------------------------------------------------

section "NGINX"

sudo nginx -t
sudo systemctl reload nginx

success "Nginx reloaded"

# --------------------------------------------------
# DONE
# --------------------------------------------------

section "DEPLOYMENT COMPLETE"

success "Deployment finished"

if [ -d "$BACKUP_TARGET" ]; then
    info "Backup: $BACKUP_TARGET"
fi

if $NO_RESTART; then
    info "Skipping service restart. To activate the virtual environment, run: source /opt/uarv/venv/bin/activate"
    source /opt/uarv/venv/bin/activate
fi

# --------------------------------------------------
# FINAL OUTPUT (ABSOLUTE LAST LINE)
# --------------------------------------------------

progress_bar 100
echo ""