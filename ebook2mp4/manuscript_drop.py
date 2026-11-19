"""Native Windows file drops; no auxiliary window or drag-and-drop runtime."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


class FileDrop:
    def __init__(self, app):
        self.app = app
        self.previous = None
        self.handle = None
        if os.name != 'nt':
            return
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        pointer = ctypes.c_ssize_t
        self.callback_type = ctypes.WINFUNCTYPE(pointer, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self.set_proc = self.user.SetWindowLongPtrW
        self.set_proc.argtypes = (wintypes.HWND, ctypes.c_int, pointer)
        self.set_proc.restype = pointer
        self.user.CallWindowProcW.argtypes = (pointer, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self.user.CallWindowProcW.restype = pointer
        self.shell.DragAcceptFiles.argtypes = (wintypes.HWND, wintypes.BOOL)
        self.shell.DragQueryFileW.argtypes = (wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT)
        self.shell.DragFinish.argtypes = (wintypes.HANDLE,)
        app.root.update_idletasks()
        self.user.GetParent.argtypes = (wintypes.HWND,)
        self.user.GetParent.restype = wintypes.HWND
        self.handle = self.user.GetParent(app.root.winfo_id()) or app.root.winfo_id()
        self.callback = self.callback_type(self.receive)
        self.previous = self.set_proc(self.handle, -4, ctypes.cast(self.callback, ctypes.c_void_p).value)
        self.shell.DragAcceptFiles(self.handle, True)

    def receive(self, window, message, wparam, lparam):
        if message == 0x0233:  # WM_DROPFILES
            try:
                count = self.shell.DragQueryFileW(wparam, 0xffffffff, None, 0)
                if count == 1:
                    size = self.shell.DragQueryFileW(wparam, 0, None, 0)
                    buffer = ctypes.create_unicode_buffer(size+1)
                    self.shell.DragQueryFileW(wparam, 0, buffer, size+1)
                    path = buffer.value
                    self.app.after_idle(lambda: self.import_path(path))
                else:
                    self.app.status.configure(text='每次請拖入一份 PDF 或 TXT。')
            finally:
                self.shell.DragFinish(wparam)
            return 0
        return self.user.CallWindowProcW(self.previous, window, message, wparam, lparam)

    def import_path(self, path):
        suffix = Path(path).suffix.lower()
        if suffix not in ('.pdf', '.txt'):
            self.app.status.configure(text='請拖入 PDF 或 TXT。')
        elif not self.app.flow:
            self.app.status.configure(text='請先建立或開啟專案。')
        else:
            self.app.source_tools.import_file(suffix[1:], path=path)

    def close(self):
        if self.previous and self.handle:
            self.shell.DragAcceptFiles(self.handle, False)
            self.set_proc(self.handle, -4, self.previous)
            self.previous = None
