#!/bin/bash
# Push the prepared local repo once willlccasey/kali-custom-launchers exists on GitHub.

set -euo pipefail

source "$HOME/.config/gh-launcher-sync/config"
REPO_FULL="${GH_USER}/${REPO_NAME}"
WORK_DIR="$HOME/.local/share/gh-launcher-sync/repo"

if ! gh auth status >/dev/null 2>&1; then
  echo "gh is not authenticated. Run: gh auth login -h github.com -p https -s repo,workflow -w"
  exit 1
fi

if [[ ! -d "$WORK_DIR/.git" ]]; then
  echo "Local repo missing. Run preview/sync from GitHub Launcher Sync first."
  exit 1
fi

if ! gh repo view "$REPO_FULL" >/dev/null 2>&1; then
  echo "Repository $REPO_FULL does not exist yet."
  echo "Create it at: https://github.com/new?name=${REPO_NAME}&visibility=public"
  echo "Or re-authenticate gh with repo scope, then run sync option 5."
  exit 1
fi

cd "$WORK_DIR"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${REPO_FULL}.git"
git push -u origin main
gh repo view "$REPO_FULL" --json url,visibility,pushedAt -q '"Pushed to \(.url) (\(.visibility)) at \(.pushedAt)"'