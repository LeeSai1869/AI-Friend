#!/bin/bash
# Build and install the single canonical macOS app, preserving runtime data.
set -euo pipefail
umask 077
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Run this script on your Mac." >&2; exit 1
fi
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
if [[ $# -gt 0 && "$1" != "/Applications" ]]; then
  echo "AI Friend has one supported install location: /Applications/AI Friend.app" >&2
  exit 1
fi
if lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Quit AI Friend before updating. A backend is still listening:" >&2
  lsof -nP -iTCP:8765 -sTCP:LISTEN >&2
  echo "If it remains after quitting, inspect that PID before stopping it; this updater never kills processes." >&2
  exit 1
fi
install_dir="/Applications"
app_support="$HOME/Library/Application Support/AI Friend V1"
mkdir -p "$app_support"
build_root=$(mktemp -d "${TMPDIR:-/tmp}/ai-friend-build.XXXXXX")
stage=""
cleanup() {
  if [[ -n "$stage" ]]; then
    if [[ -d "$stage/previous.app" && ! -e "$install_dir/AI Friend.app" ]]; then
      mv "$stage/previous.app" "$install_dir/AI Friend.app"
    fi
    if [[ -d "$stage" ]]; then rm -rf "$stage"; fi
  fi
  if [[ -d "$build_root" ]]; then rm -rf "$build_root"; fi
}
trap cleanup EXIT
python3 -m venv "$app_support/runtime/venv"
"$app_support/runtime/venv/bin/python" -m pip install -r requirements-runtime.txt
"$app_support/runtime/venv/bin/python" -m playwright install chromium
npm ci --prefix section_0_app
CARGO_TARGET_DIR="$build_root/target" npm run build --prefix section_0_app -- --bundles app
built_app="$build_root/target/release/bundle/macos/AI Friend.app"
[[ -d "$built_app" ]] || { echo "Built .app not found: $built_app" >&2; exit 1; }
speech_bundle="$built_app/Contents/Helpers/AI Friend Speech.app"
mkdir -p "$speech_bundle/Contents/MacOS"
swiftc -O \
  -framework AVFoundation \
  -framework Speech \
  "$repo_root/section_0_app/src-tauri/speech_recognition.swift" \
  -o "$speech_bundle/Contents/MacOS/AI Friend Speech"
cp "$repo_root/section_0_app/src-tauri/speech-helper-Info.plist" \
  "$speech_bundle/Contents/Info.plist"
plutil -lint "$speech_bundle/Contents/Info.plist"
# Bundles must remain launchable when an administrator later owns the code.
chmod -R a+rX,go-w "$built_app"
mkdir -p "$install_dir" "$app_support/backups" "$app_support/state"
target_app="$install_dir/AI Friend.app"
# Preserve a complete previous installation and migrate DATA only, never old code.
if [[ -d "$target_app" ]]; then
  backup="$app_support/backups/AI Friend-$(date +%Y%m%d-%H%M%S).backup"
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
ditto "$built_app" "$stage/AI Friend.app"
if [[ -d "$target_app" ]]; then mv "$target_app" "$stage/previous.app"; fi
mv "$stage/AI Friend.app" "$target_app"
# Remove the duplicate left by earlier in-repository builds.
legacy_build_app="$repo_root/section_0_app/src-tauri/target/release/bundle/macos/AI Friend.app"
if [[ -d "$legacy_build_app" ]]; then rm -rf "$legacy_build_app"; fi
echo "Installed: $target_app"
echo "Look for Build 2026.10.31.2 · UI / Mind connected in the app."
open "$target_app"
