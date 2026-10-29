"""Initial placement for normal application dialogs; popovers keep their anchors."""
import tkinter as tk
from weakref import WeakSet


def install_dialog_placement(root):
    placed: WeakSet[tk.Tk | tk.Toplevel] = WeakSet()
    def mapped(event):
        window = event.widget
        if (not isinstance(window, (tk.Tk, tk.Toplevel)) or window.overrideredirect()
                or window in placed):
            return
        placed.add(window)

        def center():
            if not window.winfo_exists() or window.state() != 'normal':
                return
            width, height = window.winfo_width(), window.winfo_height()
            x = max(0, (window.winfo_screenwidth() - width) // 2)
            y = max(0, (window.winfo_screenheight() - height) // 2)
            window.geometry(f'+{x}+{y}')

        root.after_idle(center)

    root.bind_all('<Map>', mapped, add='+')
