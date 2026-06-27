#!/bin/bash
# Interactive menu: sync custom Kali desktop launchers + scripts to GitHub via gh CLI.
# Nothing is uploaded until you choose "Sync to GitHub" and confirm.

set -euo pipefail

CONFIG="$HOME/.config/gh-launcher-sync/config"
COLLECTOR="$HOME/bin/gh-launcher-sync/collect-launchers.sh"
# shellcheck source=/dev/null
source "$CONFIG"

REPO_FULL="${GH_USER}/${REPO_NAME}"
STAGING="${STAGING_DIR:-$HOME/.local/share/gh-launcher-sync/staging}"
WORK_DIR="$HOME/.local/share/gh-launcher-sync/repo"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

pause() {
  read -r -p "Press Enter to continue..."
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ensure_gh() {
  if ! have_cmd gh; then
    echo -e "${RED}gh CLI is not installed.${NC}"
    echo "Install with: sudo apt install gh"
    exit 1
  fi
}

ensure_git_identity() {
  local login
  login="$(gh api user -q .login 2>/dev/null || echo "$GH_USER")"
  if [[ -z "$(git config --global user.name 2>/dev/null || true)" ]]; then
    git config --global user.name "$login"
    echo -e "${GREEN}Set git user.name -> $login${NC}"
  fi
  if [[ -z "$(git config --global user.email 2>/dev/null || true)" ]]; then
    git config --global user.email "${login}@users.noreply.github.com"
    echo -e "${GREEN}Set git user.email -> ${login}@users.noreply.github.com${NC}"
  fi
}

gh_status() {
  echo -e "${CYAN}=== GitHub CLI Status ===${NC}"
  if gh auth status 2>&1; then
    echo
    gh api user --jq '"Logged in as: \(.login)\nProfile: \(.html_url)"' 2>/dev/null || true
    echo
    echo -e "Target repo: ${YELLOW}${REPO_FULL}${NC} (${REPO_VISIBILITY})"
    if gh repo view "$REPO_FULL" --json name,url,pushedAt 2>/dev/null | jq -r '"Repo exists: \(.name)\nURL: \(.url)\nLast push: \(.pushedAt)"' 2>/dev/null; then
      :
    else
      echo -e "${YELLOW}Repo not created yet — will be created on first sync.${NC}"
    fi
  else
    echo -e "${RED}Not logged in. Use menu option 2 to authenticate.${NC}"
  fi
  echo
  pause
}

gh_login() {
  echo -e "${CYAN}=== GitHub Login ===${NC}"
  echo "A browser window will open for GitHub authentication."
  echo "Recommended: gh auth login -h github.com -p https -w"
  echo
  read -r -p "Press Enter to start login (Ctrl+C to cancel)..."
  gh auth login -h github.com -p https -w
  ensure_git_identity
  GH_USER="$(gh api user -q .login)"
  sed -i "s/^GH_USER=.*/GH_USER=${GH_USER}/" "$CONFIG"
  echo -e "${GREEN}Authenticated as ${GH_USER}${NC}"
  pause
}

configure_repo() {
  echo -e "${CYAN}=== Configure Target Repository ===${NC}"
  local new_name new_vis
  read -r -p "Repository name [${REPO_NAME}]: " new_name
  new_name="${new_name:-$REPO_NAME}"
  echo "Visibility: public | private"
  read -r -p "Visibility [${REPO_VISIBILITY}]: " new_vis
  new_vis="${new_vis:-$REPO_VISIBILITY}"

  REPO_NAME="$new_name"
  REPO_VISIBILITY="$new_vis"
  REPO_FULL="${GH_USER}/${REPO_NAME}"

  sed -i "s/^REPO_NAME=.*/REPO_NAME=${REPO_NAME}/" "$CONFIG"
  sed -i "s/^REPO_VISIBILITY=.*/REPO_VISIBILITY=${REPO_VISIBILITY}/" "$CONFIG"

  echo -e "${GREEN}Target set to ${REPO_FULL} (${REPO_VISIBILITY})${NC}"
  pause
}

preview_collection() {
  echo -e "${CYAN}=== Preview Custom Launchers ===${NC}"
  local count
  count="$("$COLLECTOR")"
  echo
  echo -e "${GREEN}Collected ${count} custom launcher(s) into:${NC}"
  echo "  $STAGING"
  echo
  if [[ -f "$STAGING/MANIFEST.txt" ]]; then
    cat "$STAGING/MANIFEST.txt"
  fi
  echo
  echo "Tree:"
  find "$STAGING" -type f | sort | sed 's|^|  |'
  echo
  pause
}

sync_to_github() {
  echo -e "${CYAN}=== Sync to GitHub ===${NC}"
  if ! gh auth status >/dev/null 2>&1; then
    echo -e "${RED}Not authenticated. Use option 2 first.${NC}"
    pause
    return
  fi

  ensure_git_identity
  GH_USER="$(gh api user -q .login 2>/dev/null || echo "$GH_USER")"
  REPO_FULL="${GH_USER}/${REPO_NAME}"

  echo "This will:"
  echo "  1. Collect custom launchers + scripts"
  echo "  2. Create repo ${REPO_FULL} if missing (${REPO_VISIBILITY})"
  echo "  3. Commit and push to GitHub"
  echo
  read -r -p "Type YES to continue: " confirm
  [[ "$confirm" == "YES" ]] || { echo "Cancelled."; pause; return; }

  local count
  count="$("$COLLECTOR")"
  echo -e "${GREEN}Staged ${count} launcher(s).${NC}"

  if ! gh repo view "$REPO_FULL" >/dev/null 2>&1; then
    echo "Creating repository ${REPO_FULL}..."
    if [[ "$REPO_VISIBILITY" == "public" ]]; then
      gh repo create "$REPO_FULL" --public --description "Custom Kali Linux desktop launchers and companion scripts (non-native apps)"
    else
      gh repo create "$REPO_FULL" --private --description "Custom Kali Linux desktop launchers and companion scripts (non-native apps)"
    fi
  fi

  rm -rf "$WORK_DIR"
  gh repo clone "$REPO_FULL" "$WORK_DIR"
  cd "$WORK_DIR"
  rsync -a --delete \
    --exclude='.git' \
    "$STAGING/" ./

  if [[ ! -f README.md ]]; then
    cat >README.md <<EOF
# Kali Custom Launchers

Desktop \`.desktop\` launchers and companion scripts for non-Kali-native apps on this machine.

Collected automatically by \`gh-launcher-sync\` from:

- \`~/Desktop/*.desktop\`
- \`~/.local/share/applications/*.desktop\`
- Referenced scripts under \`~/bin\` and \`~/.local/bin\`

## Layout

- \`desktop/\` — launcher files
- \`bin/\` — scripts and launcher subdirectories
- \`icons/\` — custom icons referenced by launchers
- \`meta/\` — reserved for future metadata
- \`MANIFEST.txt\` — collection log

## Sync

Run **GitHub Launcher Sync** from the desktop, or:

\`\`\`bash
$HOME/bin/gh-launcher-sync/gh-launcher-sync.sh
\`\`\`

For authorized use on your own systems.
EOF
  fi

  git add -A
  if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to push.${NC}"
  else
    git commit -m "Sync custom Kali launchers ($(date -Iseconds), ${count} launchers)"
    git push -u origin HEAD
    echo -e "${GREEN}Pushed to https://github.com/${REPO_FULL}${NC}"
  fi

  pause
}

pull_from_github() {
  echo -e "${CYAN}=== Pull from GitHub ===${NC}"
  if ! gh repo view "$REPO_FULL" >/dev/null 2>&1; then
    echo -e "${RED}Repository ${REPO_FULL} does not exist yet.${NC}"
    pause
    return
  fi

  rm -rf "$WORK_DIR"
  gh repo clone "$REPO_FULL" "$WORK_DIR"
  echo -e "${GREEN}Cloned to ${WORK_DIR}${NC}"
  echo "Restore launchers manually from there, or extend this script later."
  pause
}

main_menu() {
  while true; do
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     GitHub Launcher Sync (gh CLI)        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo
    echo "  Account: ${GH_USER}    Repo: ${REPO_NAME} (${REPO_VISIBILITY})"
    echo
    echo "  1) Check gh / GitHub status"
    echo "  2) Login / re-authenticate gh"
    echo "  3) Configure target repository"
    echo "  4) Preview launchers (collect only, no upload)"
    echo "  5) Sync to GitHub (collect + commit + push)"
    echo "  6) Pull / clone from GitHub"
    echo "  0) Exit"
    echo
    read -r -p "Choice: " choice
    case "$choice" in
      1) gh_status ;;
      2) gh_login ;;
      3) configure_repo ;;
      4) preview_collection ;;
      5) sync_to_github ;;
      6) pull_from_github ;;
      0|q|Q) exit 0 ;;
      *) echo "Invalid choice"; sleep 1 ;;
    esac
  done
}

ensure_gh
ensure_git_identity
main_menu