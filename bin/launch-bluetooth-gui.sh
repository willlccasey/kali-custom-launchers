#!/bin/bash
# Launcher for the Bluetooth Tools GUI (device-first chooser)
# Click device button first (Ubertooth/Raytac/HackRF) -> it activates the device and
# filters the tool list to only relevant ones (no clutter).
# Preferred over the old text menu because it avoids shell input problems.

SCRIPT="$HOME/bin/bluetooth_tools_gui.py"
TITLE="Bluetooth Tools GUI"

# Pre-cache sudo (so actions like btscanner, kismet, etc. don't re-prompt)
sudo -v || true

# Try to run the GUI directly (it will open its own windows as needed)
if command -v python3 >/dev/null; then
    if python3 -c "import tkinter" >/dev/null 2>&1; then
        exec python3 "$SCRIPT" "$@"
    else
        echo "python3-tk not available, falling back to zenity selector..."
        if [[ -x "$HOME/bin/bluetooth-zenity.sh" ]]; then
            exec "$HOME/bin/bluetooth-zenity.sh" "$@"
        else
            echo "No GUI or zenity fallback found."
            exit 1
        fi
    fi
else
    echo "python3 not found"
    exit 1
fi
