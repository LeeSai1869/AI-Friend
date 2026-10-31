#!/bin/bash
# Consistent development entry point; never kills an existing app/backend.
set -euo pipefail
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ ! -f "$repo_root/section_0_app/package.json" || ! -f "$repo_root/section_0_app/src/window-chat.html" || ! -f "$repo_root/section_1_central_mind/main.py" ]]; then
  echo 'The source checkout is incomplete. Development launch stopped.' >&2
  exit 1
fi
if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'A backend already owns port 8765. Quit its AI Friend app before launching.' >&2
  lsof -nP -iTCP:8765 -sTCP:LISTEN >&2
  exit 1
fi
echo "Development source: $repo_root"
cd "$repo_root/section_0_app"
exec npm run dev
