#!/usr/bin/env bash
# Viking GPS - install if needed, ensure gpsd, launch live map viewer
set -euo pipefail

APP_NAME="Viking GPS"
GPS_DEVICE="/dev/ttyACM0"
DESKTOP_FILE="$HOME/Desktop/Viking-GPS.desktop"
LOG_FILE="/tmp/viking-gps-launch.log"

exec >>"$LOG_FILE" 2>&1
echo "=== $(date) Viking GPS launch ==="

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "$APP_NAME" "$1" --icon=gps 2>/dev/null || \
        notify-send "$APP_NAME" "$1" 2>/dev/null || true
    fi
}

find_viking_icon() {
    local candidates=(
        "/usr/share/pixmaps/viking.png"
        "/usr/share/icons/hicolor/scalable/apps/viking.svg"
        "/usr/share/icons/hicolor/48x48/apps/viking.png"
        "/usr/share/icons/hicolor/32x32/apps/viking.png"
    )
    local path
    for path in "${candidates[@]}"; do
        if [[ -f "$path" ]]; then
            echo "$path"
            return 0
        fi
    done
    find /usr/share/icons /usr/share/pixmaps -iname 'viking.*' 2>/dev/null | head -1
}

update_desktop_icon() {
    local icon
    icon="$(find_viking_icon || true)"
    if [[ -n "${icon:-}" && -f "$DESKTOP_FILE" ]]; then
        sed -i "s|^Icon=.*|Icon=$icon|" "$DESKTOP_FILE"
    fi
}

install_viking() {
    if command -v viking >/dev/null 2>&1; then
        return 0
    fi

    if ! command -v pkexec >/dev/null 2>&1; then
        zenity --error --title="$APP_NAME" \
            --text="Viking is not installed and pkexec is unavailable.\n\nRun in a terminal:\n  sudo apt install -y viking" \
            --width=360 2>/dev/null || true
        exit 1
    fi

    zenity --question --title="$APP_NAME" \
        --text="Viking map viewer is not installed yet.\n\nInstall now? You will be prompted for your admin password." \
        --width=360 2>/dev/null || exit 0

    notify "Installing Viking (admin password required)..."
    if ! pkexec apt-get update -qq && pkexec apt-get install -y viking; then
        zenity --error --title="$APP_NAME" \
            --text="Installation failed.\n\nTry manually:\n  sudo apt install -y viking" \
            --width=360 2>/dev/null || true
        exit 1
    fi

    update_desktop_icon
    notify "Viking installed successfully"
}

ensure_gpsd() {
    if systemctl is-active --quiet gpsd 2>/dev/null; then
        return 0
    fi

    if [[ ! -e "$GPS_DEVICE" ]]; then
        zenity --warning --title="$APP_NAME" \
            --text="GPS receiver not found at $GPS_DEVICE.\n\nPlug in your u-blox USB GPS and try again." \
            --width=360 2>/dev/null || true
        return 0
    fi

    notify "Starting GPS service..."
    if command -v pkexec >/dev/null 2>&1; then
        pkexec systemctl start gpsd.socket gpsd.service 2>/dev/null || true
    fi

    sleep 1
    if ! systemctl is-active --quiet gpsd 2>/dev/null; then
        zenity --warning --title="$APP_NAME" \
            --text="gpsd is not running.\n\nTry in a terminal:\n  sudo systemctl start gpsd.socket" \
            --width=360 2>/dev/null || true
    fi
}

show_first_run_tip() {
    local stamp="$HOME/.cache/viking-gps-first-run-done"
    if [[ -f "$stamp" ]]; then
        return 0
    fi
    mkdir -p "$(dirname "$stamp")"
    touch "$stamp"

    zenity --info --title="$APP_NAME" \
        --text="Viking is opening.\n\nTo see your live position on the map:\n  1. Go outside (or near a window) for a GPS fix\n  2. In Viking: Layers → GPS → Real-time GPS Tracking\n  3. Map will follow your location when fix is acquired\n\nYour u-blox GPS connects via gpsd automatically." \
        --width=420 2>/dev/null || true
}

launch_viking() {
    if ! command -v viking >/dev/null 2>&1; then
        exit 1
    fi

    show_first_run_tip
    notify "Launching Viking map viewer"
    nohup viking >/dev/null 2>&1 &
}

install_viking
ensure_gpsd
launch_viking