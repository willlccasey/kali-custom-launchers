#!/bin/bash
# Desktop entry wrapper — opens GitHub Launcher Sync in a terminal.

TITLE="GitHub Launcher Sync"
SCRIPT="$HOME/bin/gh-launcher-sync/gh-launcher-sync.sh"
POST="; echo; read -p 'Finished - press Enter to close...'"

if command -v qterminal >/dev/null 2>&1; then
  exec qterminal -e bash -c "$SCRIPT $POST"
elif command -v xfce4-terminal >/dev/null 2>&1; then
  exec xfce4-terminal --title="$TITLE" --geometry=100x30 --command="bash -c '$SCRIPT $POST'"
elif command -v gnome-terminal >/dev/null 2>&1; then
  exec gnome-terminal --title="$TITLE" --geometry=100x30 -- bash -c "$SCRIPT $POST"
elif command -v x-terminal-emulator >/dev/null 2>&1; then
  exec x-terminal-emulator -e bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec x-terminal-emulator -- bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec xterm -T "$TITLE" -e bash -c "$SCRIPT $POST" 2>/dev/null || \
  exec bash -c "$SCRIPT $POST"
elif command -v terminator >/dev/null 2>&1; then
  exec terminator -T "$TITLE" -e "bash -c '$SCRIPT $POST'"
else
  exec bash -c "$SCRIPT $POST"
fi