#!/bin/bash
#
# Wifite Launcher - Desktop Launcher (GUI configurator + Crack Only mode)
#
# Features:
# - Beautiful GUI for configuring and launching wifite
# - "Crack Only" mode: no monitor mode needed. Browse previous handshakes
#   from any hs/ directory, pick wordlist, choose cracking tool (hashcat/aircrack),
#   and crack offline with live progress.
# - Full Wifite mode: pre-configure common options then launch in terminal
# - Smart wordlist discovery (rockyou, probable, fasttrack, etc.)
#
# Uses pkexec for clean graphical sudo when root is required.

LAUNCHER_DIR="/home/will/bin/wifite-launcher"
PYTHON_SCRIPT="$LAUNCHER_DIR/wifite_launcher.py"

# Pre-flight dependency checks (run as normal user)
if ! command -v python3 >/dev/null 2>&1; then
    zenity --error --title="Wifite Launcher" --text="python3 is not installed.\n\nPlease run:\n  sudo apt install python3 python3-tk" 2>/dev/null || \
    echo "ERROR: python3 not found. Install with: sudo apt install python3 python3-tk"
    exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    zenity --question --title="Wifite Launcher" --text="python3-tk is missing.\n\nInstall it now?" 2>/dev/null
    sudo apt update && sudo apt install -y python3-tk || exit 1
fi

# Check for basic aircrack (recommended but not fatal - crack-only can still work with hashcat)
if ! command -v airmon-ng >/dev/null 2>&1 && ! command -v aircrack-ng >/dev/null 2>&1; then
    zenity --info --title="Wifite Launcher" --text="aircrack-ng tools not found.\n\nFor best results (monitor mode + handshake capture):\n  sudo apt install aircrack-ng\n\nCrack-only mode will still work with hashcat." 2>/dev/null || true
fi

# Hashcat is highly recommended for fast offline cracking
if ! command -v hashcat >/dev/null 2>&1; then
    zenity --info --title="Wifite Launcher" --text="hashcat not found.\n\nHighly recommended for Crack Only mode.\n  sudo apt install hashcat\n\nYou can still use aircrack-ng for .cap files." 2>/dev/null || true
fi

# If we're not root, re-launch ourselves via pkexec (clean graphical auth dialog, no terminal)
if [ "$(id -u)" -ne 0 ]; then
    # Allow root to talk to our X11 session
    xhost +local:root >/dev/null 2>&1 || true

    # Re-execute this exact script as root via pkexec.
    # pkexec will show a nice password dialog and then run us again as root.
    exec pkexec env \
        DISPLAY="${DISPLAY}" \
        XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
        HOME="$HOME" \
        "$0" "$@"
fi

# === We are now running as root ===

# Make sure we can still talk to the display
xhost +local:root >/dev/null 2>&1 || true

cd "$LAUNCHER_DIR" || exit 1

# Launch the GUI (no terminal involved)
exec python3 "$PYTHON_SCRIPT" "$@"
