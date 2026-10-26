#!/bin/bash
# Start the live-source dev app cleanly: stop every other AI Friend process first,
# then show which code and state folder the backend is really using.
set -u
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

pkill -f "tauri dev" 2>/dev/null
pkill -f "central-mind-app" 2>/dev/null
pkill -f "AI Friend.app" 2>/dev/null
pkill -f "section_1_central_mind/main.py" 2>/dev/null
sleep 3
pkill -9 -f "central-mind-app" 2>/dev/null
pkill -9 -f "section_1_central_mind/main.py" 2>/dev/null
sleep 1

if pgrep -fl "central-mind|AI Friend|section_1_central_mind" >/dev/null; then
  echo "[dev] could not stop every AI Friend process:"
  pgrep -fl "central-mind|AI Friend|section_1_central_mind"
  exit 1
fi
if lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[dev] port 8765 is still in use:"
  lsof -nP -iTCP:8765 -sTCP:LISTEN
  exit 1
fi

(
  for _ in $(seq 1 90); do
    pid=$(pgrep -f "section_1_central_mind/main.py" | head -1)
    if [ -n "$pid" ]; then
      sleep 2
      entry=$(ps -o command= -p "$pid" | sed 's/ --serve.*//')
      state=$(ps eww -p "$pid" | grep -oE "AI_FRIEND_STATE_DIR=.{0,90}" | sed -E 's#(/state).*#\1#')
      echo "[dev] backend pid $pid"
      echo "[dev] entry: $entry"
      echo "[dev] $state"
      case "$entry" in
        */Applications/*) echo "[dev] WARNING: this backend runs from the installed app, not from the project" ;;
      esac
      exit 0
    fi
    sleep 1
  done
  echo "[dev] no backend appeared within 90 seconds"
) &
watcher=$!
trap 'kill $watcher 2>/dev/null' EXIT

cd "$repo_root/section_0_app" && npm run dev 2>&1 | tee /tmp/aifriend_dev.log
