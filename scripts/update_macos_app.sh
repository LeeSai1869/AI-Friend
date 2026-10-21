#!/bin/bash
# Build the installed .app from this checkout, preserving existing runtime data.
set -euo pipefail
umask 077
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Run this script on your Mac." >&2; exit 1
fi
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
if lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Quit AI Friend before updating. A backend is still listening:" >&2
  lsof -nP -iTCP:8765 -sTCP:LISTEN >&2
  echo "If it remains after quitting, inspect that PID before stopping it; this updater never kills processes." >&2
  exit 1
fi
install_dir="${1:-/Applications}"
app_support="$HOME/Library/Application Support/AI Friend V1"
python3 -m venv "$app_support/runtime/venv"
"$app_support/runtime/venv/bin/python" -m pip install -r requirements-runtime.txt
npm ci --prefix section_0_app
npm run build --prefix section_0_app -- --bundles app
built_app="$repo_root/section_0_app/src-tauri/target/release/bundle/macos/AI Friend.app"
[[ -d "$built_app" ]] || { echo "Built .app not found: $built_app" >&2; exit 1; }
mkdir -p "$install_dir" "$app_support/backups" "$app_support/state"
target_app="$install_dir/AI Friend.app"
# Preserve a complete previous installation and migrate DATA only, never old code.
if [[ -d "$target_app" ]]; then
  backup="$app_support/backups/AI Friend-$(date +%Y%m%d-%H%M%S).app"
  ditto "$target_app" "$backup"
  old_root="$target_app/Contents/Resources/_up_/_up_"
  if [[ -d "$old_root/.central_mind" && ! -e "$app_support/state/.central_mind" ]]; then
    ditto "$old_root/.central_mind" "$app_support/state/.central_mind"
  fi
  if [[ -d "$old_root/section_3_memory/entries" && ! -e "$app_support/state/memory/entries" ]]; then
    mkdir -p "$app_support/state/memory"
    ditto "$old_root/section_3_memory/entries" "$app_support/state/memory/entries"
    for journal in knowledge_proposals.json deletion_proposals.json; do
      if [[ -f "$old_root/section_3_memory/$journal" && ! -e "$app_support/state/memory/$journal" ]]; then
        cp "$old_root/section_3_memory/$journal" "$app_support/state/memory/$journal"
      fi
    done
  fi
  echo "Previous installation saved to: $backup"
fi
stage=$(mktemp -d "$install_dir/.ai-friend-update.XXXXXX")
cleanup() {
  if [[ -d "$stage/previous.app" && ! -e "$target_app" ]]; then
    mv "$stage/previous.app" "$target_app"
  fi
  rm -rf "$stage"
}
trap cleanup EXIT
ditto "$built_app" "$stage/AI Friend.app"
if [[ -d "$target_app" ]]; then mv "$target_app" "$stage/previous.app"; fi
mv "$stage/AI Friend.app" "$target_app"
echo "Installed: $target_app"
echo "Look for Build 2026.10.21.3 · UI / Mind connected in the app."
open "$target_app"
