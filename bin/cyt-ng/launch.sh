#!/bin/bash
#
# Chasing Your Tail NG (CYT-NG) Desktop Launcher
#
# Clean desktop integration for the enhanced Tkinter GUI from:
# https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG
#
# Features exposed via the nice dark-themed GUI:
#   🚀 START CHASING YOUR TAIL - real-time Wi-Fi probe monitoring (Kismet db polling)
#   📝 Create / Delete Ignore Lists - from current Kismet device/probe data (secure JSON)
#   📈 Analyze Logs - historical probe analysis (local by default, optional WiGLE)
#   🗺️ Surveillance Analysis - GPS correlation (auto from Kismet Bluetooth GPS), 
#       persistence scoring for following/stalking detection, spectacular professional
#       KML output for Google Earth with color-coded paths, heatmaps, balloons, etc.
#   📊 System status checks (Kismet running, monitor mode, db device counts, creds)
#
# The GUI uses:
# - Dark theme (#1a1a1a) with matrix-green (#00ff41) logs and accents
# - Chunky "Fisher Price" style buttons optimized for small/touch screens (800x480)
# - Security-hardened backend (no SQLi, encrypted creds, safe ignore loading)
# - Organized outputs: surveillance_reports/, kml_files/, logs/, reports/, ignore_lists/
#
# This wrapper:
# - Performs pre-flight dependency checks with zenity dialogs (user friendly)
# - Uses pkexec for graphical sudo (no terminal window, clean auth dialog)
# - Passes X11 / session env so the Tkinter GUI renders properly as root
# - Runs the full cyt_gui.py (and its subprocesses) as root so it can access
#   Kismet databases, monitor interfaces, write privileged outputs if needed.
# - Matches the launcher pattern used by Wifite, WiFi-Pentest-Kit, Jam-Fi etc. in this env.
#
# Requirements (installed by this launcher where possible):
#   python3 + python3-tk
#   Kismet (for live capture + .kismet dbs; analyzer works on existing dbs too)
#   Wi-Fi adapter capable of monitor mode (for full real-time chasing)
#
# For authorized security research, personal safety, and network admin use only.
# Comply with all local laws.
#

CYT_DIR="/home/will/bin/cyt-ng"
PYTHON_SCRIPT="$CYT_DIR/cyt_gui.py"

# --- Pre-flight checks (run as the invoking normal user) ---

if ! command -v python3 >/dev/null 2>&1; then
    zenity --error --title="Chasing Your Tail NG" --text="python3 is not installed.\n\nPlease run:\n  sudo apt install python3 python3-tk" 2>/dev/null || \
        echo "ERROR: python3 not found."
    exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    zenity --question --title="Chasing Your Tail NG" --text="python3-tk is missing.\n\nInstall it now with:\n  sudo apt install python3-tk ?" 2>/dev/null
    sudo apt update && sudo apt install -y python3-tk || exit 1
fi

# Core Python packages (requests + cryptography for secure mode / API)
if ! python3 -c "import requests, cryptography" 2>/dev/null; then
    echo "[*] Installing missing Python packages (requests, cryptography)..."
    pip3 install --break-system-packages requests cryptography 2>/dev/null || \
    sudo pip3 install --break-system-packages requests cryptography || true
fi

# Kismet is highly recommended (for live monitoring + GPS). Not fatal for analysis on existing dbs.
if ! command -v kismet >/dev/null 2>&1; then
    zenity --info --title="Chasing Your Tail NG" --text="Kismet not found in PATH.\n\nFor full real-time monitoring and automatic GPS:\n  sudo apt install kismet\n\nYou can still run historical analysis and surveillance detection against existing .kismet database files." 2>/dev/null || true
fi

# Optional but nice: pandoc for HTML report generation from the surveillance analyzer
if ! command -v pandoc >/dev/null 2>&1; then
    echo "[*] Optional: pandoc not found (used for nice HTML reports). Install with: sudo apt install pandoc"
fi

# If not root, re-launch via pkexec (graphical password prompt, no terminal appears)
if [ "$(id -u)" -ne 0 ]; then
    xhost +local:root >/dev/null 2>&1 || true

    # Preserve important session vars for the GUI under root
    if [ -z "${SUDO_USER:-}" ]; then
        if [ -n "${PKEXEC_UID:-}" ]; then
            SUDO_USER=$(getent passwd "$PKEXEC_UID" 2>/dev/null | cut -d: -f1 || true)
        fi
        if [ -z "${SUDO_USER:-}" ]; then
            SUDO_USER=$(logname 2>/dev/null || whoami 2>/dev/null || echo "will")
        fi
    fi

    exec pkexec env \
        DISPLAY="${DISPLAY}" \
        XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
        HOME="$HOME" \
        DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS}" \
        XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR}" \
        XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP}" \
        XDG_SESSION_TYPE="${XDG_SESSION_TYPE}" \
        SUDO_USER="${SUDO_USER}" \
        "$0" "$@"
fi

# === Now running as root ===

xhost +local:root >/dev/null 2>&1 || true

# Normalize SUDO_USER if we came via pkexec
if [ -z "${SUDO_USER:-}" ] && [ -n "${PKEXEC_UID:-}" ]; then
    export SUDO_USER=$(getent passwd "$PKEXEC_UID" 2>/dev/null | cut -d: -f1 || true)
fi

cd "$CYT_DIR" || { zenity --error --title="Chasing Your Tail NG" --text="Failed to cd to $CYT_DIR"; exit 1; }

# Make sure Python security/runtime deps are available for root as well
python3 -c "import requests, cryptography, tkinter" 2>/dev/null || \
    pip3 install --break-system-packages requests cryptography 2>/dev/null || true

# One-time security note (non-fatal, migrate is idempotent)
if [ -f migrate_credentials.py ]; then
    python3 migrate_credentials.py >/dev/null 2>&1 || true
fi

# Ensure output directories exist (scripts create them but nice to pre-create with correct perms)
mkdir -p logs analysis_logs reports surveillance_reports kml_files ignore_lists secure_credentials

# Launch the nice enhanced GUI (no terminal window)
# The GUI itself forces CYT_TEST_MODE and provides the full interface
exec python3 "$PYTHON_SCRIPT" "$@"
