#!/bin/bash
# Push local launcher sync repo once gh has write access.
set -euo pipefail
REPO_DIR="$HOME/.local/share/gh-launcher-sync/repo"
cd "$REPO_DIR"
gh auth setup-git
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "https://github.com/willlccasey/kali-custom-launchers.git"
fi
git push -u origin main
gh repo view willlccasey/kali-custom-launchers --json url,visibility -q '"Pushed to \(.url) (\(.visibility))"'