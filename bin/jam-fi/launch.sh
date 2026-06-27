#!/bin/bash
#
# Jam-Fi Desktop Launcher
# Wi-Fi Chaos Tool (Deauth, Evil Twin, MITM, CVE exploits, etc.)
#
# Puts the wireless interface into monitor mode using raw ip/iw commands
# (bypassing airmon-ng), then launches jam_fi.py.
#
# IMPORTANT: The internal / daily-driver card (wlan0) is PROTECTED.
#            Never use it for monitor mode / attacks.
#
# Usage:
#   ./launch.sh            # uses wlan1 (recommended external card)
#   ./launch.sh wlan1      # explicit
#   ./launch.sh wlan2      # if you have more cards

JAMFI_DIR="/home/will/Jam_fi"

# Load central protection list
source "/home/will/bin/protected-interfaces.sh" 2>/dev/null || true

IFACE="${1:-wlan1}"

# Note: No longer refusing any interface. User wants all cards (including internal)
# to be allowed to go down when putting the ASUS into monitor mode.


if [ ! -d "$JAMFI_DIR" ]; then
    zenity --error --title="Jam-Fi" --text="Jam_fi directory not found at:\n$JAMFI_DIR" 2>/dev/null || \
    echo "ERROR: Jam_fi directory not found at $JAMFI_DIR"
    exit 1
fi

cd "$JAMFI_DIR" || exit 1

# Check for required tools
MISSING=()
for cmd in ip iw; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        MISSING+=("$cmd")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    zenity --error --title="Jam-Fi" --text="Missing required commands: ${MISSING[*]}\n\nInstall with: sudo apt install iproute2 iw" 2>/dev/null || true
    exit 1
fi

# Launch in a terminal
if command -v terminator >/dev/null 2>&1; then
    exec terminator --working-directory="$JAMFI_DIR" --title="Jam-Fi - WiFi Chaos Tool" \
        -x bash -c "
            echo '═══════════════════════════════════════════════════════════════'
            echo '  Jam-Fi - Wi-Fi Chaos Tool'
            echo '  Interface: $IFACE'
            echo '═══════════════════════════════════════════════════════════════'
            echo
            echo '[*] Bringing $IFACE down...'
            sudo ip link set $IFACE down || { echo 'Failed to bring interface down'; read -r; exit 1; }
            echo '[*] Setting $IFACE to monitor mode...'
            sudo iw dev $IFACE set type monitor || { echo 'Failed to set monitor mode'; read -r; exit 1; }
            echo '[*] Bringing $IFACE up in monitor mode...'
            sudo ip link set $IFACE up || { echo 'Failed to bring interface up'; read -r; exit 1; }
            echo
            echo '[+] Monitor mode enabled on $IFACE'
            echo
            echo '───────────────────────────────────────────────────────────────'
            echo 'Launching Jam-Fi...'
            echo '───────────────────────────────────────────────────────────────'
            echo
            sudo python3 jam_fi.py
            echo
            echo '───────────────────────────────────────────────────────────────'
            echo 'Jam-Fi session ended. Press Enter to close this window.'
            echo '───────────────────────────────────────────────────────────────'
            read -r
            exec bash
        "
else
    # Fallback to default terminal
    exec x-terminal-emulator -e bash -c "
        cd '$JAMFI_DIR' && \
        echo 'Setting $IFACE to monitor mode...' && \
        sudo ip link set $IFACE down && \
        sudo iw dev $IFACE set type monitor && \
        sudo ip link set $IFACE up && \
        echo 'Monitor mode set. Starting Jam-Fi...' && \
        sudo python3 jam_fi.py; \
        echo; echo 'Press Enter to close...'; read -r; \
        exec bash
    "
fi
