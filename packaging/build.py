"""Build an isolated Windows desktop distribution without shell execution."""
import argparse
from pathlib import Path
import os
import subprocess
import sys

from build_preflight import build_lock, check_distribution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--install-tools', action='store_true')
    mode.add_argument('--check-only', action='store_true', help='Check availability without building')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.exit(1, 'Windows is required to build ebook2mp4.\n')

    root = Path(__file__).resolve().parents[1]
    dist = root / 'dist'
    with build_lock(dist):
        check_distribution(root)
        if args.check_only:
            print(f'Build preflight passed: {dist / "ebook2mp4"}')
            return
        if args.install_tools:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--target', str(root / '.scratch/build-tools'),
                            '-r', str(root / 'packaging/requirements-build.txt')], check=True)
            check_distribution(root)
        env = os.environ.copy()
        env['PYTHONPATH'] = str(root / '.scratch/build-tools')
        env['PYINSTALLER_CONFIG_DIR'] = str(root / '.scratch/pyinstaller-cache')
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(dist),
                        '--workpath', '.scratch/pyinstaller-build', 'packaging/ebook2mp4.spec'],
                       cwd=root, env=env, check=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
