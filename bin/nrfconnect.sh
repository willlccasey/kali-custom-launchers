#!/bin/bash
# Final robust launcher for nRF Connect on Kali
APPIMAGE="$HOME/opt/nrfconnect.AppImage"
FLAGS="--no-sandbox --disable-gpu --disable-gpu-sandbox --disable-software-rasterizer --ignore-gpu-blocklist"

if [ ! -x "$APPIMAGE" ]; then
    zenity --error --text="nRF Connect AppImage missing at $APPIMAGE" --width=400 2>/dev/null || echo "AppImage missing"
    exit 1
fi

# Use APPIMAGE_EXTRACT_AND_RUN=1 to bypass the libfuse.so.2 requirement
# This extracts to /tmp temporarily instead of using FUSE mount
export APPIMAGE_EXTRACT_AND_RUN=1

if ! "$APPIMAGE" $FLAGS "$@"; then
    zenity --error --title="nRF Connect" --text="nRF Connect did not start cleanly.\n\nQuick fixes:\n1. Install FUSE support:\n   sudo apt update && sudo apt install -y libfuse2\n\n2. Or run manually:\n   APPIMAGE_EXTRACT_AND_RUN=1 $APPIMAGE\n\nThe 'nRF BLE Pentest Suite' on your Desktop is the main tool for the Nordic Sniffer + pentesting (Bettercap, Kismet, Wireshark, etc.)." --width=520 2>/dev/null || \
    x-terminal-emulator -e "echo 'nRF Connect failed. Install libfuse2 or use APPIMAGE_EXTRACT_AND_RUN=1'; read" 2>/dev/null || true
fi
