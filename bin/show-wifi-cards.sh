#!/usr/bin/env bash
#
# show-wifi-cards.sh
# Shows all wireless interfaces, clearly marks which are PROTECTED (internal/daily driver)
# vs recommended for monitor mode / attacks, and suggests the best card to use.
#
# Usage:
#   ./show-wifi-cards.sh
#   ./show-wifi-cards.sh --best          # prints only the recommended attack interface name
#   ./show-wifi-cards.sh --recommend     # same as --best
#
# This script is safe to run anytime. It never changes interface state.
#

set -euo pipefail

# --- Load protection data ---
PROTECTED_FILE="/home/will/bin/PROTECTED_WIFI_INTERFACES"
source "/home/will/bin/protected-interfaces.sh" 2>/dev/null || true

# --- Colors (only if stdout is a terminal) ---
if [ -t 1 ]; then
    RED=$(tput setaf 1 2>/dev/null || echo -e '\033[31m')
    GREEN=$(tput setaf 2 2>/dev/null || echo -e '\033[32m')
    YELLOW=$(tput setaf 3 2>/dev/null || echo -e '\033[33m')
    CYAN=$(tput setaf 6 2>/dev/null || echo -e '\033[36m')
    BOLD=$(tput bold 2>/dev/null || echo -e '\033[1m')
    RESET=$(tput sgr0 2>/dev/null || echo -e '\033[0m')
else
    RED="" GREEN="" YELLOW="" CYAN="" BOLD="" RESET=""
fi

# --- Flags ---
BEST_ONLY=false
if [[ "${1:-}" == "--best" || "${1:-}" == "--recommend" ]]; then
    BEST_ONLY=true
fi

# --- Collect wireless interfaces ---
declare -a IFACES=()
declare -a PHYS=()
declare -a TYPES=()
declare -a STATES=()
declare -a DRIVERS=()
declare -a IS_USB=()
declare -a CONNS=()

mapfile -t IW_LINES < <(iw dev 2>/dev/null | cat)

current_iface=""
current_phy=""

while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^phy#([0-9]+) ]]; then
        current_phy="phy${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]*Interface[[:space:]]+([^[:space:]]+) ]]; then
        iface="${BASH_REMATCH[1]}"
        IFACES+=("$iface")
        PHYS+=("$current_phy")

        # Get type (managed / monitor / ...)
        type=$(iw dev "$iface" info 2>/dev/null | awk '/type/ {print $2; exit}' || echo "unknown")
        TYPES+=("$type")

        # Clean state
        state_raw=$(ip -o link show "$iface" 2>/dev/null | awk -F': ' '{print $3}' || echo "")
        if echo "$state_raw" | grep -q "LOWER_UP"; then
            state="UP"
        elif echo "$state_raw" | grep -q "UP"; then
            state="UP (no carrier)"
        else
            state="DOWN"
        fi
        STATES+=("$state")

        # Driver
        drv="unknown"
        if [[ -e "/sys/class/net/$iface/device/driver" ]]; then
            drv=$(readlink "/sys/class/net/$iface/device/driver" 2>/dev/null | xargs basename 2>/dev/null || echo "unknown")
        fi
        DRIVERS+=("$drv")

        # USB vs PCI hint (multiple methods)
        is_usb="no"
        # Method 1: device path contains usb
        if [[ -e "/sys/class/net/$iface/device" ]]; then
            if readlink "/sys/class/net/$iface/device" 2>/dev/null | grep -qi usb; then
                is_usb="yes"
            fi
        fi

        # Method 2: known attack-card USB vendor IDs (ASUS 0x0b05, common Realtek dongles, etc.)
        # This catches your ASUS card reliably even if the exact driver name varies slightly.
        if [[ -e "/sys/class/net/$iface/device" ]]; then
            # Walk up the device tree to find the USB device
            devpath=$(readlink -f "/sys/class/net/$iface/device" 2>/dev/null || true)
            for i in 1 2 3 4; do
                if [[ -f "$devpath/idVendor" ]]; then
                    vid=$(cat "$devpath/idVendor" 2>/dev/null | tr '[:upper:]' '[:lower:]')
                    if [[ "$vid" =~ ^(0b05|0bda|2357|0e8d|148f) ]]; then
                        # 0b05 = ASUS, 0bda = Realtek, 2357 = TP-Link, 0e8d = MediaTek, 148f = Ralink
                        is_usb="yes"
                    fi
                    break
                fi
                devpath=$(dirname "$devpath")
            done
        fi

        # Method 3: known USB WiFi driver names (very reliable for common attack cards)
        if [[ "$drv" =~ (88xxau|8812au|8821au|8822bu|88x2bu|rtl88|mt76|ath9k_htc|carl9170|rt2800usb|rt2x00usb) ]]; then
            is_usb="yes"
        fi
        # Method 4: PCI drivers that are known internal (rtw89, iwlwifi, etc.)
        if [[ "$drv" =~ ^(rtw89|iwlwifi|brcmfmac) ]]; then
            is_usb="no"
        fi
        IS_USB+=("$is_usb")

        # Connection status (nmcli)
        conn=$(nmcli -g GENERAL.CONNECTION device show "$iface" 2>/dev/null || true)
        [[ -z "$conn" || "$conn" == "--" ]] && conn="-"
        CONNS+=("$conn")

        current_iface="$iface"
    fi
done < <(printf '%s\n' "${IW_LINES[@]}")

if [[ ${#IFACES[@]} -eq 0 ]]; then
    if $BEST_ONLY; then
        echo "none"
        exit 1
    fi
    echo "No wireless interfaces detected."
    exit 0
fi

# --- Find recommended attack card ---
# Preference: non-protected + USB (best for injection) > non-protected + anything > first non-protected
RECOMMENDED=""
for i in "${!IFACES[@]}"; do
    iface="${IFACES[$i]}"
    if ! is_protected "$iface" 2>/dev/null; then
        if [[ "${IS_USB[$i]}" == "yes" ]]; then
            RECOMMENDED="$iface"
            break
        fi
    fi
done

if [[ -z "$RECOMMENDED" ]]; then
    for i in "${!IFACES[@]}"; do
        iface="${IFACES[$i]}"
        if ! is_protected "$iface" 2>/dev/null; then
            RECOMMENDED="$iface"
            break
        fi
    done
fi

# Fallback: first interface that is not protected
if [[ -z "$RECOMMENDED" ]]; then
    for iface in "${IFACES[@]}"; do
        if ! is_protected "$iface" 2>/dev/null; then
            RECOMMENDED="$iface"
            break
        fi
    done
fi

# --- Best-only mode (for scripting / other tools) ---
if $BEST_ONLY; then
    if [[ -n "$RECOMMENDED" ]]; then
        echo "$RECOMMENDED"
        exit 0
    else
        echo "none"
        exit 1
    fi
fi

# --- Pretty output ---
echo
echo "${BOLD}${CYAN}=== WiFi Cards ===${RESET}"
echo

printf "%-8s  %-6s  %-10s  %-14s  %-22s  %-6s  %s\n" \
    "IFACE" "PHY" "MODE" "STATE" "DRIVER" "USB?" "NOTES"
printf "%-8s  %-6s  %-10s  %-14s  %-22s  %-6s  %s\n" \
    "-------" "-----" "----------" "--------------" "----------------------" "-----" "------------------------------"

for i in "${!IFACES[@]}"; do
    iface="${IFACES[$i]}"
    phy="${PHYS[$i]}"
    type="${TYPES[$i]}"
    state="${STATES[$i]}"
    drv="${DRIVERS[$i]}"
    usb="${IS_USB[$i]}"
    conn="${CONNS[$i]}"

    note=""
    color="$GREEN"
    if [[ "$iface" == "$RECOMMENDED" ]]; then
        note="${BOLD}RECOMMENDED FOR MONITOR / ATTACKS${RESET}"
    else
        note="available for monitor mode"
    fi
    if [[ "$usb" == "yes" ]]; then
        note="$note  [USB - good injection support]"
    fi
    color="$GREEN"

    if [[ "$conn" != "-" && "$conn" != "" ]]; then
        note="$note  (connected: $conn)"
    fi

    printf "%-8s  %-6s  %-10s  %-14s  %-22s  %-6s  %b%s%b\n" \
        "$iface" "$phy" "$type" "$state" "$drv" "$usb" "$color" "$note" "$RESET"
done

echo
if [[ -n "$RECOMMENDED" ]]; then
    echo "${GREEN}${BOLD}→ Best card for monitor mode / attacks right now: ${RECOMMENDED}${RESET}"
    echo "   Example:  sudo airmon-ng start $RECOMMENDED"
    echo "             /home/will/bin/jam-fi/launch.sh $RECOMMENDED"
else
    echo "${YELLOW}No wireless card found.${RESET}"
fi

echo
echo "Run with --best to get just the recommended name (for scripts)."
echo
