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
# FINAL PROGRESS BAR (ALWAYS LAST LINE)
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

# --------------------------------------------------
# ARGUMENTS
# --------------------------------------------------

section "ARGUMENTS"

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
        info "Repository:"
        cd "$APP_DIR"
        echo " Path: $APP_DIR"
        echo " Branch: $(git branch --show-current)"
        echo " Commit: $(git log -1 --oneline)"
    else
        error "Repo missing"
    fi

    echo

    if [ -d "$VENV_DIR" ]; then
        info "Venv:"
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
# STOP SERVICE (IMPORTANT)
# --------------------------------------------------

section "STOP UARV API"

if systemctl is-active --quiet uarv-api; then
    sudo systemctl stop uarv-api
    success "uarv-api stopped"
else
    info "uarv-api not running"
fi

systemctl is-active --quiet uarv-api && {
    error "Failed to stop uarv-api"
    progress_bar 100
    echo ""
    exit 1
}

success "Service fully stopped"

# --------------------------------------------------
# REPOSITORY
# --------------------------------------------------

section "REPOSITORY"

if [ -d "$APP_DIR/.git" ] && ! $FORCE; then
    info "Pull repo"
    cd "$APP_DIR"
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
# DEPLOY
# --------------------------------------------------

section "DEPLOY FRONTEND"

sudo rm -rf "$WEB_DIR"
sudo mkdir -p "$WEB_DIR"

sudo cp -a "$APP_DIR/admin_panel/." "$WEB_DIR/"

sudo chown -R www-data:www-data "$WEB_DIR"
sudo chmod -R 755 "$WEB_DIR"

success "Frontend deployed"

# --------------------------------------------------
# RESTART SERVICE
# --------------------------------------------------

section "UARV API RESTART"

if systemctl is-active --quiet uarv-api; then
    sudo systemctl restart uarv-api
    success "uarv-api restarted"
else
    sudo systemctl start uarv-api
    success "uarv-api started"
fi

systemctl is-active --quiet uarv-api && success "Service running" || error "Service failed"

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

section "DEPLOYMENT DONE"

success "Deployment completed"

if [ -d "$BACKUP_TARGET" ]; then
    info "Backup: $BACKUP_TARGET"
fi

# --------------------------------------------------
# FINAL PROGRESS BAR (ABSOLUTE LAST OUTPUT)
# --------------------------------------------------

progress_bar 100
echo ""