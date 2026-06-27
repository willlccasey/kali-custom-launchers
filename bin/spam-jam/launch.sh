#!/bin/bash
#
# Spam Jam Desktop Launcher
# BLE & Bluetooth Attack Toolkit (Spam, Jam, L2Ping, RFCOMM Flood, Mesh Botnet)
#
# Opens a terminal, cds to the Spam-Jam directory, and runs with sudo
# (root is required for raw Bluetooth access).

SPAMJAM_DIR="/home/will/Spam-Jam"

if [ ! -d "$SPAMJAM_DIR" ]; then
    zenity --error --title="Spam Jam" --text="Spam-Jam directory not found at:\n$SPAMJAM_DIR" 2>/dev/null || \
    echo "ERROR: Spam-Jam directory not found at $SPAMJAM_DIR"
    exit 1
fi

cd "$SPAMJAM_DIR" || exit 1

# Launch in a terminal with sudo. Keep the shell open after exit so user can see output.
if command -v terminator >/dev/null 2>&1; then
    exec terminator --working-directory="$SPAMJAM_DIR" --title="Spam Jam - BLE/Bluetooth Toolkit" \
        -x bash -c "
            echo '═══════════════════════════════════════════════════════════════'
            echo '  Spam Jam - BLE & Bluetooth Attack Toolkit'
            echo '  Running with sudo (required for Bluetooth hardware access)'
            echo '═══════════════════════════════════════════════════════════════'
            echo
            sudo python3 spam_jam.py
            echo
            echo '───────────────────────────────────────────────────────────────'
            echo 'Spam Jam session ended. Press Enter to close this window.'
            echo '───────────────────────────────────────────────────────────────'
            read -r
            exec bash
        "
else
    # Fallback to whatever x-terminal-emulator is configured
    exec x-terminal-emulator -e bash -c "
        cd '$SPAMJAM_DIR' && \
        echo 'Starting Spam Jam...' && \
        sudo python3 spam_jam.py; \
        echo; echo 'Press Enter to close...'; read -r; \
        exec bash
    "
fi
