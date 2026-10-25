"""Build an isolated Windows desktop distribution without shell execution."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if '--install-tools' in sys.argv:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--target', str(root / '.scratch/build-tools'),
                    '-r', str(root / 'packaging/requirements-build.txt')], check=True)
env = os.environ.copy()
env['PYTHONPATH'] = str(root / '.scratch/build-tools')
env['PYINSTALLER_CONFIG_DIR'] = str(root / '.scratch/pyinstaller-cache')
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', 'dist',
                '--workpath', '.scratch/pyinstaller-build', 'packaging/ebook2mp4.spec'],
               cwd=root, env=env, check=True)
