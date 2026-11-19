"""Protect the Windows distribution before PyInstaller replaces it."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import stat
import subprocess


def _kernel():
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    api.CreateFileW.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    return api


@contextmanager
def build_lock(dist: Path):
    api = _kernel()
    key = hashlib.sha256(str(dist).casefold().encode()).hexdigest()
    ctypes.set_last_error(0)
    handle = api.CreateMutexW(None, False, 'Local\\ebook2mp4-build-' + key)
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    try:
        if error == 183:  # ERROR_ALREADY_EXISTS
            raise RuntimeError('已有封裝程序正在使用正式成品路徑。')
        yield
    finally:
        api.CloseHandle(handle)


def _check_running(executable):
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
         "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
         "Get-Process | Where-Object ProcessName -eq 'ebook2mp4' "
         "| ForEach-Object { [Console]::WriteLine(([string]$_.Id + '|' + $_.Path)) }"],
        check=True, capture_output=True, encoding='utf-8', errors='strict',
    )
    for process in result.stdout.splitlines():
        pid, _, image = process.partition('|')
        if not image or Path(image).resolve() == executable:
            raise RuntimeError(f'請先正常關閉 ebook2mp4（PID {pid}）再封裝。')


def _attributes(path):
    attributes = path.lstat().st_file_attributes
    if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise RuntimeError(f'成品路徑包含重新解析點：{path}')
    return attributes


def _check_available(api, path, attributes):
    # Request read/delete access with no sharing. For directories use backup semantics.
    flags = 0x02000000 if attributes & stat.FILE_ATTRIBUTE_DIRECTORY else 0
    handle = api.CreateFileW(str(path), 0x80010000, 0, None, 3, flags, None)
    if handle == wintypes.HANDLE(-1).value:
        error = ctypes.get_last_error()
        raise RuntimeError(f'成品無法獨占開啟：{path}（Windows 錯誤 {error}）')
    api.CloseHandle(handle)


def check_distribution(root):
    dist = root / 'dist'
    product = dist / 'ebook2mp4'
    for directory in (dist, product):
        try:
            attributes = _attributes(directory)
        except FileNotFoundError:
            break
        if not attributes & stat.FILE_ATTRIBUTE_DIRECTORY:
            raise RuntimeError(f'成品目錄路徑不是資料夾：{directory}')

    _check_running(product / 'ebook2mp4.exe')
    api = _kernel()
    pending = [product] if product.exists() else []
    while pending:
        path = pending.pop()
        attributes = _attributes(path)
        _check_available(api, path, attributes)
        if attributes & stat.FILE_ATTRIBUTE_DIRECTORY:
            pending.extend(path.iterdir())
