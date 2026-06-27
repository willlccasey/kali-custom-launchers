#!/bin/bash
# Reliable launcher for HackRF menu from .desktop / desktop icon
TITLE="HackRF Tools Menu"
SCRIPT="$HOME/bin/hackrf-menu.sh"
POST="; echo; read -p 'Menu finished - press Enter to close terminal...'"

# Detect and use best flags
if command -v qterminal >/dev/null 2>&1; then
  # qterminal: -e command
  exec qterminal -e bash -c "$SCRIPT $POST"
elif command -v xfce4-terminal >/dev/null 2>&1; then
  exec xfce4-terminal --title="$TITLE" --geometry=110x32 --command="bash -c '$SCRIPT $POST'"
elif command -v gnome-terminal >/dev/null 2>&1; then
  exec gnome-terminal --title="$TITLE" --geometry=110x32 -- bash -c "$SCRIPT $POST"
elif command -v x-terminal-emulator >/dev/null 2>&1; then
  # Try generic -e first
  exec x-terminal-emulator -e bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec x-terminal-emulator -- bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec xterm -T "$TITLE" -e bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec bash -c "$SCRIPT $POST"
elif command -v terminator >/dev/null 2>&1; then
  exec terminator -T "$TITLE" -e "bash -c '$SCRIPT $POST'"
else
  echo "Falling back to current shell..."
  exec bash -c "$SCRIPT $POST"
fi
