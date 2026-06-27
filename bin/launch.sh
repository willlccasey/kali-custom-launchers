#!/usr/bin/env bash
# Launcher for USB Manager
# This brings up a GUI/CLI to switch between Ubertooth One, nRF Sniffer (Raytac MDBT50Q-CX etc.),
# HackRF, and onboard Bluetooth. It handles unbinding so specialized tools get clean access.

# Resolve the real directory even if this script is called via a symlink
SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
cd "$SCRIPT_DIR" || exit 1

exec python3 sniffer_usb_manager.py "$@"
