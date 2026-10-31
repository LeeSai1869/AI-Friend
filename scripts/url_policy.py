#!/usr/bin/env python3
"""Local administrator CLI; not exposed as a model tool."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'section_8_tools'))
from web.url_policy import policy_path, canonical

parser = argparse.ArgumentParser(description='Block sites or URL paths for AI Friend web tools')
parser.add_argument('operation', choices=['block', 'unblock', 'list'])
parser.add_argument('url', nargs='?')
args = parser.parse_args()
path = policy_path()
data = json.loads(path.read_text()) if path.exists() else {'version': 1, 'blocked': []}
if data.get('version') != 1 or not isinstance(data.get('blocked'), list):
    parser.error('Existing policy is invalid; refusing to overwrite it')
if args.operation != 'list':
    if not args.url:
        parser.error('A URL or domain is required')
    canonical(args.url)
    if args.operation == 'block' and args.url not in data['blocked']:
        data['blocked'].append(args.url)
    if args.operation == 'unblock':
        data['blocked'] = [rule for rule in data['blocked'] if rule != args.url]
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
        temporary = handle.name
        json.dump(data, handle, indent=2)
        handle.write('\n')
    os.replace(temporary, path)
print(f'Policy: {path}')
for rule in data['blocked']:
    print(rule)
