"""Build the trusted Python test image without network access inside Docker.

Only verified package downloads, their hashes, and this Dockerfile enter the
build context. No checkout, credentials, or user projects are sent to Docker.
Prints the resulting immutable image ID to stdout; build logs go to stderr.
"""
import argparse
from email.parser import BytesParser
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

PINS = ['pytest==9.1.1', 'iniconfig==2.3.1', 'packaging==26.3', 'pluggy==1.7.0', 'Pygments==2.21.0']
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, help='reviewed Python base image by immutable digest or image ID')
    parser.add_argument('--tag', default='ai-friend-coding-tests')
    args = parser.parse_args()
    if not re.fullmatch(r'(?:[A-Za-z0-9_./:-]+@)?sha256:[a-f0-9]{64}', args.base):
        parser.error('--base must be an immutable image reference')
    with tempfile.TemporaryDirectory(prefix='ai-friend-test-build-') as temporary:
        stage = Path(temporary)
        wheels = stage / 'wheels'
        wheels.mkdir()
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--no-cache-dir', '--only-binary=:all:',
                        '--no-deps', '--dest', str(wheels), *PINS], check=True, stdout=sys.stderr)
        requirements = []
        for wheel in sorted(wheels.glob('*.whl')):
            with zipfile.ZipFile(wheel) as package:
                metadata_name = next(name for name in package.namelist() if name.endswith('.dist-info/METADATA'))
                metadata = BytesParser().parsebytes(package.read(metadata_name))
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            requirements.append(f"{metadata['Name']}=={metadata['Version']} --hash=sha256:{digest}")
        if len(requirements) != len(PINS):
            raise RuntimeError('the downloaded wheel set is incomplete')
        (stage / 'requirements-tests.lock').write_text('\n'.join(requirements) + '\n')
        shutil.copyfile(ROOT / 'docker/Dockerfile.coding-tests', stage / 'Dockerfile')
        subprocess.run(['docker', 'build', '--network=none', '--build-arg', 'PYTHON_BASE=' + args.base,
                        '--tag', args.tag, str(stage)], check=True, stdout=sys.stderr)
    result = subprocess.run(['docker', 'image', 'inspect', args.tag, '--format', '{{.Id}}'],
                            check=True, capture_output=True, text=True)
    print(result.stdout.strip())


if __name__ == '__main__':
    main()
