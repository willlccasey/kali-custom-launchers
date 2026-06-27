#!/bin/bash
# Reliable launcher for IMSI-Catcher menu from .desktop (same style as HackRF/GR-GSM)
TITLE="IMSI-Catcher Tools Menu"
SCRIPT="$HOME/bin/imsi-catcher-menu.sh"
POST="; echo; read -p 'Menu finished - press Enter to close terminal...'"

# Automatically authenticate sudo with the provided password (2482)
# This allows sniff mode (-s), installs, wireshark capture etc. without repeated prompts
# in the launched terminal session. (Only for this personal authorized-use setup.)
SUDO_PASS="2482"
echo "$SUDO_PASS" | sudo -S -v 2>/dev/null || true

if command -v qterminal >/dev/null 2>&1; then
  exec qterminal -e bash -c "$SCRIPT $POST"
elif command -v xfce4-terminal >/dev/null 2>&1; then
  exec xfce4-terminal --title="$TITLE" --geometry=110x34 --command="bash -c '$SCRIPT $POST'"
elif command -v gnome-terminal >/dev/null 2>&1; then
  exec gnome-terminal --title="$TITLE" --geometry=110x34 -- bash -c "$SCRIPT $POST"
elif command -v x-terminal-emulator >/dev/null 2>&1; then
  exec x-terminal-emulator -e bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec x-terminal-emulator -- bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec xterm -T "$TITLE" -e bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec bash -c "$SCRIPT $POST"
elif command -v terminator >/dev/null 2>&1; then
  exec terminator -T "$TITLE" -e "bash -c '$SCRIPT $POST'"
else
  echo "Falling back..."
  exec bash -c "$SCRIPT $POST"
fi
