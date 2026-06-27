#!/bin/bash
# bluetooth-zenity.sh
# Desktop-friendly GUI selector for Bluetooth Tools.
# FIRST: select device (Ubertooth One / Raytac-nRF / HackRF). This activates ("brings up")
# the device via the USB manager and then shows a FILTERED list of only the tools
# that make sense for the chosen device (much less clutter).
# Uses zenity lists (no typing). Desktop icon points to the python GUI now, but this
# is kept for compatibility / direct use.
#
# When you select an item, it runs the corresponding command (usually in a new terminal
# so interactive tools like btscanner, kismet, etc. work properly).

set -euo pipefail

# Paths (match the other launchers)
HOME_DIR="$HOME"
SNIFFER_LAUNCH="$HOME_DIR/bin/sniffer-usb-manager/launch.sh"
HACKRF_LAUNCH="$HOME_DIR/bin/launch-hackrf-menu.sh"
INTERCEPT_LAUNCH="$HOME_DIR/intercept/launch.sh"
BTSCANNER_WRAPPER="$HOME_DIR/bin/btscanner-wrapper.sh"
SETUP_NRF_WIRESHARK="$HOME_DIR/bin/setup-nrf-wireshark-sniffer.sh"
BLUETOOTH_TEXT_MENU="$HOME_DIR/bin/bluetooth-menu.sh"

# Function to launch something in a terminal (reuses similar logic to your other launchers)
launch_in_terminal() {
    local cmd="$1"
    local title="${2:-Bluetooth Tool}"
    local term_cmd=""

    if command -v qterminal >/dev/null 2>&1; then
        term_cmd="qterminal -e bash -c '$cmd; echo; read -p \"Press Enter to close terminal...\"'"
    elif command -v xfce4-terminal >/dev/null 2>&1; then
        term_cmd="xfce4-terminal --title=\"$title\" --geometry=110x36 --command=\"bash -c '$cmd; echo; read -p \\\"Press Enter to close terminal...\\\"'\""
    elif command -v gnome-terminal >/dev/null 2>&1; then
        term_cmd="gnome-terminal --title=\"$title\" --geometry=110x36 -- bash -c \"$cmd; echo; read -p 'Press Enter to close terminal...'\""
    elif command -v terminator >/dev/null 2>&1; then
        term_cmd="terminator -T \"$title\" -e \"bash -c '$cmd; echo; read -p \\\"Press Enter to close terminal...\\\"'\""
    elif command -v x-terminal-emulator >/dev/null 2>&1; then
        term_cmd="x-terminal-emulator -e bash -c '$cmd; echo; read -p \"Press Enter to close terminal...\"'"
    else
        echo "No suitable terminal found. Running directly:"
        bash -c "$cmd"
        return
    fi

    eval "$term_cmd" &
}

# The list of options (matching the numbered menu for familiarity)
# Format: "NUMBER) Description"
OPTIONS=(
    "1) Check all RF devices status (Ubertooth + Raytac/nRF + HackRF)"
    "2) Activate nRF Sniffer mode (Raytac MDBT50Q-CX)"
    "3) Activate Ubertooth One mode"
    "4) Prepare for HackRF (unbinds BT sniffers for clean SDR use)"
    "5) Launch Sniffer USB Manager GUI (covers Ubertooth + Raytac + HackRF)"
    "6) Run Full Optimized Setup (udev + passwordless sudo for manager)"
    "7) btscanner (classic scanner — wrapper will guide you)"
    "8) blue-hydra (Bluetooth device tracker/logger)"
    "9) Kismet + nRF sniffer (MODERN BLE scanner for Raytac — recommended)"
    "10) ubertooth-btle (BLE advertiser sniffer / follow)"
    "11) crackle (decrypt BLE from pcap)"
    "12) Launch INTERCEPT (advanced BT + Ubertooth + TSCM)"
    "13) Launch HackRF Tools menu"
    "14) List all detected BT / nRF / HackRF tools"
    "15) nRF Sniffer + Wireshark extcap notes"
    "16) nrfutil notes (for flashing Raytac/nRF)"
    "17) Setup nRF Sniffer for Wireshark (modern live capture for Raytac)"
    "18) Open original text menu (fallback)"
    "19) Bettercap BLE Launcher (choose device + dropdown of commands for your Raytac/Ubertooth/hci0)"
)

# Device-specific subsets (by original number). Keeps the list short per device.
get_device_nums() {
    local dev="$1"
    case "$dev" in
        *"Ubertooth One"*)
            echo "1 5 6 7 8 10 11 12 14 18 19"
            ;;
        *"Raytac"*|*"nRF Sniffer"*)
            echo "1 5 6 7 8 9 11 12 14 15 16 17 18 19"
            ;;
        *"HackRF One"*)
            echo "1 5 6 13 14 18"
            ;;
        *"full list"*|*"Show full"*)
            echo "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19"
            ;;
        *)
            echo "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19"
            ;;
    esac
}

build_filtered_list() {
    local nums_str="$1"
    local -a nums
    read -ra nums <<< "$nums_str"
    local -a filtered=()
    for opt in "${OPTIONS[@]}"; do
        local n
        n=$(echo "$opt" | cut -d')' -f1 | tr -d ' ')
        for want in "${nums[@]}"; do
            if [[ "$n" == "$want" ]]; then
                filtered+=("$opt")
                break
            fi
        done
    done
    printf '%s\n' "${filtered[@]}"
}

# Map number to the actual command/action
run_action() {
    local num="$1"
    case "$num" in
        1)
            launch_in_terminal "python3 -c '
import sys
sys.path.insert(0, \"$HOME_DIR/bin/sniffer-usb-manager\")
from sniffer_usb_manager import get_detected_devices
for d in get_detected_devices():
    print(f\"  {d.name}  vid={d.vid}:{d.pid}  mode={d.mode}\")
' ; echo \"Also lsusb:\" ; lsusb | grep -iE \"1d50|1915|nrf|hackrf|raytac\" || echo \"No RF dongles visible right now.\"" "RF Devices Status"
            ;;
        2)
            launch_in_terminal "\"$SNIFFER_LAUNCH\" --nrf" "Activate nRF Mode"
            ;;
        3)
            launch_in_terminal "\"$SNIFFER_LAUNCH\" --ubertooth" "Activate Ubertooth Mode"
            ;;
        4)
            launch_in_terminal "\"$SNIFFER_LAUNCH\" --hackrf" "Prepare for HackRF"
            ;;
        5)
            # GUI, run directly
            "\"$SNIFFER_LAUNCH\" --gui" &
            ;;
        6)
            launch_in_terminal "\"$SNIFFER_LAUNCH\" --full-setup" "Full Optimized Setup"
            ;;
        7)
            launch_in_terminal "\"$BTSCANNER_WRAPPER\"" "btscanner"
            ;;
        8)
            launch_in_terminal "sudo blue-hydra" "blue-hydra"
            ;;
        9)
            launch_in_terminal "sudo kismet -c nrf-52840-0 || sudo kismet" "Kismet nRF Sniffer"
            ;;
        10)
            launch_in_terminal "sudo ubertooth-btle -n" "ubertooth-btle"
            ;;
        11)
            launch_in_terminal "crackle --help || true; echo 'Example: sudo crackle -i your-capture.pcap -o decrypted.pcap'" "crackle"
            ;;
        12)
            if [[ -x "$INTERCEPT_LAUNCH" ]]; then
                "$INTERCEPT_LAUNCH" &
            else
                launch_in_terminal "echo 'INTERCEPT launch script not found at $INTERCEPT_LAUNCH'" "INTERCEPT"
            fi
            ;;
        13)
            if [[ -x "$HACKRF_LAUNCH" ]]; then
                "$HACKRF_LAUNCH" &
            else
                launch_in_terminal "echo 'HackRF launcher not found'" "HackRF Tools"
            fi
            ;;
        14)
            launch_in_terminal "
echo '=== Installed tools ==='
for t in btscanner blue-hydra bluelog blueranger bluesnarfer crackle redfang spooftooph ubertooth-btle ubertooth-util kismet kismet_cap_nrf_52840 hackrf_info bluetoothctl; do
    which \$t 2>/dev/null && echo \"  \$t: \$(which \$t)\" || echo \"  \$t: not found\"
done
echo ''
echo 'Python bits:'
python3 -c '
import importlib.util as u
for m in [\"bleak\", \"bluepy\", \"scapy\"]:
    print(\"  \", m, \"->\", \"present\" if u.find_spec(m) else \"MISSING\")
' 2>/dev/null || true
echo 'See ~/kali-bluetooth-warfare-setup.txt for original suite.'
read -p 'Press Enter to close...' _
" "List Tools"
            ;;
        15)
            launch_in_terminal "
echo 'Wireshark + nRF Sniffer (official Nordic extcap)'
echo 'You do NOT currently have the Nordic nRF Sniffer for Bluetooth LE extcap installed (or not in the right place).'
echo ''
echo 'To add it:'
echo '  1. Download from Nordic: nRF Sniffer for Bluetooth LE (software)'
echo '  2. Run: ~/bin/setup-nrf-wireshark-sniffer.sh  (it will ask for the zip)'
echo '  3. Restart Wireshark. Look for \"nRF Sniffer for Bluetooth LE\" interface.'
echo ''
echo 'Alternative right now: Use Kismet nRF (option 9) or capture with other tools + open the pcap.'
echo 'Scapy also has contrib/nrf_sniffer.py for dissecting Nordic BLE pcaps.'
read -p 'Press Enter to close...' _
" "Wireshark nRF Notes"
            ;;
        16)
            launch_in_terminal "
echo 'nrfutil (for flashing / managing firmware on Raytac MDBT50Q-CX / nRF52840)'
echo 'Not present in PATH on your system (or not in a standard location).'
echo ''
echo 'This is the main tool from Nordic to:'
echo '  - Flash or update the sniffer firmware on the dongle'
echo '  - Generate DFU packages'
echo '  - Switch the module between different firmwares'
echo ''
echo 'Install options:'
echo '  - pip install --break-system-packages nrfutil'
echo '  - Download the official nRF Command Line Tools / nrfutil from Nordic'
echo ''
echo 'If you have a J-Link or CMSIS-DAP + bare module, you may also want nrfjprog / JLink.'
read -p 'Press Enter to close...' _
" "nrfutil Notes"
            ;;
        17)
            if [[ -x "$SETUP_NRF_WIRESHARK" ]]; then
                launch_in_terminal "\"$SETUP_NRF_WIRESHARK\"" "Setup nRF Wireshark"
            else
                echo "Setup script not found: $SETUP_NRF_WIRESHARK"
            fi
            ;;
        18)
            if [[ -x "$BLUETOOTH_TEXT_MENU" ]]; then
                launch_in_terminal "\"$BLUETOOTH_TEXT_MENU\"" "Bluetooth Text Menu"
            else
                echo "Text menu not found"
            fi
            ;;
        19)
            if [[ -x "$HOME_DIR/bin/launch-bettercap-ble.sh" ]]; then
                "$HOME_DIR/bin/launch-bettercap-ble.sh" &
            elif [[ -x "$HOME_DIR/bin/bettercap-ble-launcher.sh" ]]; then
                launch_in_terminal "\"$HOME_DIR/bin/bettercap-ble-launcher.sh\"" "Bettercap BLE"
            else
                launch_in_terminal "echo 'Bettercap BLE launcher not found in ~/bin'; ls ~/bin/*bettercap* 2>/dev/null || true" "Bettercap BLE"
            fi
            ;;
        *)
            echo "Unknown selection"
            ;;
    esac
}

# =============================================================================
# Device-first flow (new): pick device -> activate it -> show only its tools
# Only run when script is executed directly (not sourced for tests/inspection)
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then

DEVICE=$(zenity --list \
    --title="Bluetooth Tools - Choose Device" \
    --text="FIRST: Select the device to use.\nThis will bring the device up (activate mode) and show ONLY the tools that work with it.\n\nPick one:" \
    --column="Device" \
    --width=520 \
    --height=280 \
    "Ubertooth One" \
    "Raytac / nRF Sniffer (MDBT50Q-CX)" \
    "HackRF One" \
    "Sniffer USB Manager (all devices + switch)" \
    "Show full list of all tools (no filter)" \
    2>/dev/null || true)

if [[ -z "$DEVICE" ]]; then
    echo "No device selected. Exiting."
    exit 0
fi

# Special cases: direct launch manager or full list
if [[ "$DEVICE" == *"Sniffer USB Manager"* ]]; then
    echo "Launching Sniffer USB Manager for all devices..."
    "$SNIFFER_LAUNCH" --gui &
    exit 0
fi

# Activate / bring up the device (sync, quick after full-setup)
ACT_MSG=""
case "$DEVICE" in
    *"Ubertooth One"*)
        echo "Activating Ubertooth One..."
        ACT_MSG=$("$SNIFFER_LAUNCH" --ubertooth 2>&1 | tail -6 || true)
        zenity --info --title="Ubertooth One" --text="Device brought up:\n\n${ACT_MSG}\n\nNow pick a tool for Ubertooth." --timeout=4 --width=480 2>/dev/null || true
        ;;
    *"Raytac"*|*"nRF Sniffer"*)
        echo "Activating nRF Sniffer (Raytac)..."
        ACT_MSG=$("$SNIFFER_LAUNCH" --nrf 2>&1 | tail -6 || true)
        zenity --info --title="Raytac / nRF" --text="Device brought up:\n\n${ACT_MSG}\n\nNow pick a tool for your Raytac nRF sniffer." --timeout=4 --width=480 2>/dev/null || true
        ;;
    *"HackRF One"*)
        echo "Preparing for HackRF (unbinding sniffers)..."
        ACT_MSG=$("$SNIFFER_LAUNCH" --hackrf 2>&1 | tail -6 || true)
        zenity --info --title="HackRF" --text="Device prep done:\n\n${ACT_MSG}\n\nNow pick a tool (or launch the HackRF menu)." --timeout=4 --width=480 2>/dev/null || true
        ;;
    *)
        # full list - no specific activate
        ;;
esac

# Build filtered list for the chosen device
NUMS=$(get_device_nums "$DEVICE")
mapfile -t FILTERED_OPTS < <(build_filtered_list "$NUMS")

if [[ ${#FILTERED_OPTS[@]} -eq 0 ]]; then
    FILTERED_OPTS=("${OPTIONS[@]}")  # fallback
fi

LIST_ITEMS=()
for opt in "${FILTERED_OPTS[@]}"; do
    LIST_ITEMS+=("$opt")
done

# Show the (filtered) zenity list dialog
SELECTED=$(zenity --list \
    --title="Bluetooth Tools — $DEVICE" \
    --text="Device is active. Select a relevant tool (list filtered for this device):" \
    --column="Selection" \
    --width=720 \
    --height=420 \
    "${LIST_ITEMS[@]}" 2>/dev/null || true)

if [[ -z "$SELECTED" ]]; then
    echo "No tool selected. Exiting."
    exit 0
fi

# Extract the number (first field before ")")
NUM=$(echo "$SELECTED" | cut -d')' -f1 | tr -d ' ')

echo "Selected: $SELECTED (number $NUM) for device $DEVICE"

# Run the action for that number (same actions as before)
run_action "$NUM"

fi  # end of direct-execution guard
