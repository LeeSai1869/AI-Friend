#!/bin/bash
# Administrator-run setup only. Never called by a model or the running app.
set -euo pipefail
umask 077
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
docker_bin=$(command -v docker || true)
if [[ -z "$docker_bin" && -x /Applications/Docker.app/Contents/Resources/bin/docker ]]; then
  docker_bin=/Applications/Docker.app/Contents/Resources/bin/docker
  export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
fi
if [[ -z "$docker_bin" ]]; then
  echo 'Install Docker Desktop for your Mac, open it, then rerun this script.' >&2
  exit 1
fi
"$docker_bin" info --format '{{.ServerVersion}}' >&2
python_bin="$repo_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin=$(command -v python3); fi
base_reference=${1:-python:3.12-slim}
"$docker_bin" pull "$base_reference" >&2
test_base=$("$docker_bin" image inspect "$base_reference" --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}')
echo "Resolved Python base: $test_base" >&2
test_image=$("$python_bin" "$repo_root/scripts/build_test_image.py" --base "$test_base")
"$docker_bin" image inspect "$test_image" >/dev/null
"$docker_bin" run --rm --pull=never --network=none --cap-drop=ALL \
  --security-opt=no-new-privileges --pids-limit=64 --memory=512m \
  "$test_image" python -I -c 'import pytest; print("Python test runtime ready; pytest " + pytest.__version__)'
"$python_bin" - "$test_image" <<'PY'
import os
from pathlib import Path
import re
import sys
import tempfile
image=sys.argv[1]
if not re.fullmatch(r'sha256:[a-f0-9]{64}',image):
    raise SystemExit('Invalid image ID; runtime configuration was not changed')
root=Path.home()/'Library/Application Support/AI Friend V1/runtime'
root.mkdir(parents=True,exist_ok=True)
with tempfile.NamedTemporaryFile(mode='w',dir=root,delete=False) as handle:
    handle.write(image+'\n')
    temporary=handle.name
os.replace(temporary,root/'test-image-id')
print('Saved coding runtime: '+str(root/'test-image-id'))
PY
echo 'Keep Docker Desktop running. Both updated development and installed backends can read this image ID.'
