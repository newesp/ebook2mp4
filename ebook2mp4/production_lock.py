"""Process-owned production lease; Windows releases it after a hard exit."""
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path

from .workflow import ProjectError

_owned: set[str] = set()


def _kernel():
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.ReleaseMutex.argtypes = [wintypes.HANDLE]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    return api


def _legacy_alive(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        pid = int(path.read_text(encoding='ascii'))
        if pid <= 0:
            return True
        api = _kernel()
        handle = api.OpenProcess(0x100000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Invalid PID is the only safe absence.
        try:
            return api.WaitForSingleObject(handle, 0) == 258
        finally:
            api.CloseHandle(handle)
    except (OSError, ValueError):
        raise ProjectError('任務鎖無法辨識。請關閉舊版程式後還原專案備份。') from None


class ProductionLease:
    def __init__(self, path: Path):
        self.path = path
        self.key = str(path.resolve()).casefold()
        self.handle = None
        if self.key in _owned:
            raise ProjectError('專案已有產生成品任務，請先等待任務停止。')
        api = _kernel()
        name = 'Local\\ebook2mp4-production-' + hashlib.sha256(self.key.encode()).hexdigest()
        handle = api.CreateMutexW(None, False, name)
        if not handle:
            raise ProjectError('無法取得製作任務鎖。請檢查本機權限。')
        outcome = api.WaitForSingleObject(handle, 0)
        if outcome not in (0, 0x80):
            api.CloseHandle(handle)
            raise ProjectError('專案已有產生成品任務，請先等待任務停止。')
        try:
            # Respect the PID-only leases written by older releases.
            if _legacy_alive(path):
                raise ProjectError('專案已有舊版產生成品任務，請先關閉舊版程式。')
            path.write_text(str(os.getpid()), encoding='ascii')
        except Exception:
            api.ReleaseMutex(handle)
            api.CloseHandle(handle)
            raise
        self.handle = handle
        _owned.add(self.key)

    def release(self):
        if self.handle is None:
            return
        # Remove the marker while still owning the OS lease. Cleanup is retryable.
        self.path.unlink(missing_ok=True)
        api = _kernel()
        api.ReleaseMutex(self.handle)
        api.CloseHandle(self.handle)
        self.handle = None
        _owned.discard(self.key)


def production_active(path: Path) -> bool:
    key = str(path.resolve()).casefold()
    if key in _owned:
        return True
    return _legacy_alive(path)
