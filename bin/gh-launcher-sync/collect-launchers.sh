#!/bin/bash
# Collect custom desktop launchers and their referenced scripts into a staging tree.

set -euo pipefail

CONFIG="${HOME}/.config/gh-launcher-sync/config"
# shellcheck source=/dev/null
source "$CONFIG"

STAGING="${STAGING_DIR:-$HOME/.local/share/gh-launcher-sync/staging}"
MANIFEST="$STAGING/MANIFEST.txt"

rm -rf "$STAGING"
mkdir -p "$STAGING/desktop" "$STAGING/bin" "$STAGING/icons" "$STAGING/meta"

is_custom_launcher() {
  local desktop="$1"
  local exec_line try_line target

  exec_line="$(grep -E '^Exec=' "$desktop" 2>/dev/null | head -1 || true)"
  try_line="$(grep -E '^TryExec=' "$desktop" 2>/dev/null | head -1 || true)"

  for line in "$exec_line" "$try_line"; do
    [[ -z "$line" ]] && continue
    target="${line#*=}"
    target="${target%% *}"
    target="${target//%[uU]/\$USER}"
    target="${target//\$HOME/$HOME}"
    target="${target//\$USER/$USER}"

    case "$target" in
      /home/"$USER"/*|"$HOME"/*)
        return 0
        ;;
    esac
  done

  return 1
}

copy_referenced_paths() {
  local desktop="$1"
  local line key value path dir subdir

  while IFS= read -r line; do
    case "$line" in
      Exec=*|TryExec=*|Icon=*)
        key="${line%%=*}"
        value="${line#*=}"
        value="${value%% *}"

        if [[ "$key" == "Icon" ]]; then
          path="$value"
          path="${path//%[uU]/\$USER}"
          path="${path//\$HOME/$HOME}"
          if [[ -f "$path" ]]; then
            cp -a "$path" "$STAGING/icons/" 2>/dev/null || true
          fi
          continue
        fi

        path="$value"
        path="${path//%[uU]/\$USER}"
        path="${path//\$HOME/$HOME}"
        path="${path//\$USER/$USER}"

        if [[ -f "$path" ]]; then
          if [[ "$path" == "$HOME/bin/"* ]]; then
            cp -a "$path" "$STAGING/bin/" 2>/dev/null || true
            dir="$(dirname "$path")"
            if [[ "$dir" != "$HOME/bin" && -d "$dir" ]]; then
              subdir="$(basename "$dir")"
              mkdir -p "$STAGING/bin/$subdir"
              rsync -a --exclude='.git' "$dir/" "$STAGING/bin/$subdir/" 2>/dev/null || true
            fi
          elif [[ "$path" == "$HOME/.local/bin/"* ]]; then
            cp -a "$path" "$STAGING/bin/" 2>/dev/null || true
          fi
        fi
        ;;
    esac
  done < "$desktop"
}

{
  echo "# Collected $(date -Iseconds) from $(hostname)"
  echo "# Custom launchers (Exec/TryExec under $HOME)"
  echo
} >"$MANIFEST"

count=0
for scan_dir in $SCAN_DESKTOP_DIRS; do
  [[ -d "$scan_dir" ]] || continue
  while IFS= read -r -d '' desktop; do
    if is_custom_launcher "$desktop"; then
      base="$(basename "$desktop")"
      cp -a "$desktop" "$STAGING/desktop/$base"
      copy_referenced_paths "$desktop"
      echo "desktop/$base  <-  $desktop" >>"$MANIFEST"
      count=$((count + 1))
    fi
  done < <(find "$scan_dir" -maxdepth 1 -name '*.desktop' -type f -print0 2>/dev/null)
done

echo >>"$MANIFEST"
echo "Total launchers: $count" >>"$MANIFEST"
echo "$count"