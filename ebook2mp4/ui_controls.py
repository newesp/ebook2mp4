"""Small native controls shared by the manuscript workbench."""
import tkinter as tk
import time
from tkinter import ttk
from collections.abc import Callable


class CellTooltip:
    """Delayed cell help without changing selection or taking keyboard focus."""
    def __init__(self, widget: ttk.Treeview,
                 resolve: Callable[[int, int], tuple[str, str] | None], delay: int = 400):
        self.widget, self.resolve, self.delay = widget, resolve, delay
        self.window: tk.Toplevel | None = None
        self.timer: str | None = None
        self.target: tuple[str, str] | None = None
        self.position = (0, 0)
        widget.bind('<Motion>', self.motion, add='+')
        for event in ('<Leave>', '<ButtonPress>', '<MouseWheel>', '<KeyPress>', '<Unmap>', '<<TreeviewSelect>>'):
            widget.bind(event, self.hide, add='+')
        widget.bind('<Destroy>', self.destroyed, add='+')
        self.owner = widget.winfo_toplevel()
        self.owner_bindings = [
            ('<Configure>', self.owner.bind('<Configure>', self.moved, add='+')),
            ('<FocusOut>', self.owner.bind('<FocusOut>', self.hide, add='+')),
        ]

    def motion(self, event):
        self.position = (event.x, event.y)
        target = self.resolve(event.x, event.y)
        if target == self.target:
            return
        self.hide()
        if target is not None:
            self.target = target
            self.timer = self.widget.after(self.delay, self.show)

    def show(self):
        self.timer = None
        if self.target is None or self.resolve(*self.position) != self.target:
            self.hide()
            return
        window = self.window = tk.Toplevel(self.widget, takefocus=False)
        window.withdraw()
        window.overrideredirect(True)
        window.attributes('-topmost', True)
        tk.Label(window, text=self.target[1], justify='left', wraplength=320,
                 font=('Microsoft JhengHei', 10), foreground='#263d34', background='#fffef9',
                 borderwidth=1, relief='solid', padx=10, pady=7).pack()
        window.update_idletasks()
        x = self.widget.winfo_rootx() + self.position[0] + 12
        y = self.widget.winfo_rooty() + self.position[1] + 22
        left, top = self.widget.winfo_vrootx(), self.widget.winfo_vrooty()
        x = max(left, min(x, left + self.widget.winfo_vrootwidth() - window.winfo_reqwidth() - 8))
        y = max(top, min(y, top + self.widget.winfo_vrootheight() - window.winfo_reqheight() - 8))
        window.geometry(f'{x:+d}{y:+d}')
        window.deiconify()

    def hide(self, _event=None):
        self.target = None
        if self.timer is not None:
            timer = self.timer
            self.timer = None
            try:
                self.widget.after_cancel(timer)
            except tk.TclError:
                pass
        if self.window is not None:
            window = self.window
            self.window = None
            try:
                window.destroy()
            except tk.TclError:
                pass

    def moved(self, event):
        if event.widget is self.owner:
            self.hide()

    def destroyed(self, event):
        if event.widget is self.widget:
            self.hide()
            for sequence, binding in self.owner_bindings:
                try:
                    self.owner.unbind(sequence, binding)
                except tk.TclError:
                    pass


class MenuAction:
    """One native menu command with the same enabled/invoke contract as a button."""
    def __init__(self, menu, text, command):
        self.menu = menu
        menu.add_command(label=text, command=command)
        self.index = menu.index('end')

    def configure(self, **options):
        if 'text' in options:
            options['label'] = options.pop('text')
        self.menu.entryconfigure(self.index, **options)

    def cget(self, name):
        return self.menu.entrycget(self.index, 'label' if name == 'text' else name)

    def instate(self, states):
        disabled = str(self.cget('state')) == 'disabled'
        return all(disabled if state == 'disabled' else not disabled if state == '!disabled' else True
                   for state in states)

    def invoke(self):
        return self.menu.invoke(self.index)


def command_menu(parent, title):
    control = ttk.Menubutton(parent, text=title)
    menu = tk.Menu(control, tearoff=False)
    control.configure(menu=menu)
    return control, menu


class MessageLine(ttk.Label):
    """Fixed-height result summary; longer, selectable messages remain in history."""
    def __init__(self, parent, **options):
        self.history: list[str] = []
        self.full_text = ''
        super().__init__(parent, anchor='w', width=1, **options)

    def remember(self, value):
        if value and (not self.history or self.history[-1] != value):
            self.history.append(value)
            del self.history[:-100]

    def configure(self, cnf=None, **options):
        if cnf is not None:
            return super().configure(cnf, **options)
        if 'text' in options:
            value = str(options['text'])
            self.full_text = value
            self.remember(value)
            options['text'] = value.replace('\n', '  ')
            if 'foreground' not in options:
                options['foreground'] = '#58695f'
        return super().configure(**options)


class NotificationLayer:
    """One non-modal, owner-bound toast; all Tk work stays on the UI thread."""
    def __init__(self, owner):
        self.owner = owner.winfo_toplevel()
        self.window: tk.Toplevel | None = None
        self.timer: str | None = None
        self.position_timer: str | None = None
        self.focus_timer: str | None = None
        self.duration = 3000
        self.paused = False
        self.bindings = [(sequence, self.owner.bind(sequence, handler, add='+')) for sequence, handler in (
            ('<Configure>', self.moved), ('<Unmap>', self.unmapped), ('<Destroy>', self.destroyed),
            ('<FocusIn>', self.activated), ('<FocusOut>', self.deactivated))]

    def show(self, text, kind='success', duration=None):
        self.dismiss()
        if not self.owner.winfo_viewable():
            return
        self.duration = (0 if kind in ('error', 'warning') else 3000) if duration is None else duration
        self.paused = False
        self.window = window = tk.Toplevel(self.owner, takefocus=False)
        window.withdraw()
        window.title('操作提示')
        window.overrideredirect(True)
        window.transient(self.owner)
        try:
            window.attributes('-alpha', 1.0)
        except tk.TclError:
            pass  # Timed dismissal remains available without compositing.
        color = {'success': '#315d43', 'info': '#304d65', 'warning': '#775311', 'error': '#963b32'}[kind]
        background = '#fffef9'
        body = tk.Frame(window, bg=background, highlightbackground=color, highlightthickness=1, padx=12, pady=10)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        label = {'success': '完成', 'info': '提示', 'warning': '注意', 'error': '未完成'}[kind]
        self.message = tk.Label(body, text=f'{label}：{text}', bg=background, fg=color,
                                font=('Microsoft JhengHei', 10), justify='left', anchor='w')
        self.message.grid(row=0, column=0, sticky='ew')
        self.close_button = tk.Button(body, text='×', command=self.dismiss, takefocus=True,
                                      font=('Microsoft JhengHei', 12), bg=background, fg=color,
                                      relief='flat', borderwidth=0, padx=6, activebackground='#e9f0e5')
        self.close_button.grid(row=0, column=1, sticky='ne', padx=(10, 0))
        self.close_button.bind('<Escape>', lambda e: (self.dismiss(), 'break')[-1])
        # A separate native window can fade without changing the manuscript's opacity.
        for widget in (window, body, self.message, self.close_button):
            widget.bind('<Enter>', self.pause, add='+')
            widget.bind('<Leave>', self.resume, add='+')
        self.close_button.bind('<FocusIn>', self.pause, add='+')
        self.close_button.bind('<FocusOut>', self.resume, add='+')
        self.position()
        window.deiconify()
        self.activated()
        self.arm()

    def activated(self, _event=None):
        if self.window is not None:
            focused = self.owner.focus_displayof()
            if focused is not None and focused.winfo_toplevel() in (self.owner, self.window):
                self.window.lift()

    def deactivated(self, _event=None):
        if self.window is not None and self.focus_timer is None:
            self.focus_timer = self.owner.after_idle(self.check_active)

    def check_active(self):
        self.focus_timer = None
        focused = self.owner.focus_displayof()
        if self.window is not None and (focused is None or focused.winfo_toplevel() not in (self.owner, self.window)):
            self.dismiss()

    def arm(self):
        if self.window is not None and self.duration > 0 and not self.paused:
            self.timer = self.owner.after(self.duration, self.start_fade)

    def cancel_timer(self):
        if self.timer is not None:
            try:
                self.owner.after_cancel(self.timer)
            except tk.TclError:
                pass
            self.timer = None

    def pause(self, _event=None):
        self.cancel_timer()
        self.paused = True
        if self.window is not None:
            try:
                self.window.attributes('-alpha', 1.0)
            except tk.TclError:
                pass

    def resume(self, _event=None):
        self.cancel_timer()
        if self.window is None:
            return
        hovered = self.window.winfo_containing(*self.window.winfo_pointerxy())
        focused = self.window.focus_displayof()
        if (hovered is not None and hovered.winfo_toplevel() is self.window
                or focused is not None and focused.winfo_toplevel() is self.window):
            return
        self.paused = False
        self.arm()

    def start_fade(self):
        self.timer = None
        self.fade_started = time.monotonic()
        self.fade()

    def fade(self):
        self.timer = None
        if self.window is None:
            return
        progress = min(1.0, (time.monotonic() - self.fade_started) / .25)
        if progress >= 1:
            self.dismiss()
            return
        try:
            self.window.attributes('-alpha', (1 - progress) ** 3)
        except tk.TclError:
            self.dismiss()
            return
        self.timer = self.owner.after(16, self.fade)

    def position(self):
        self.position_timer = None
        if self.window is None:
            return
        width = max(120, min(400, self.owner.winfo_width() - 32))
        self.message.configure(wraplength=max(60, width - 80))
        self.window.update_idletasks()
        height = self.window.winfo_reqheight()
        x = self.owner.winfo_rootx() + (self.owner.winfo_width() - width) // 2
        y = self.owner.winfo_rooty() + 16
        self.window.geometry(f'{width}x{height}{x:+d}{y:+d}')

    def moved(self, event):
        if event.widget is self.owner and self.window is not None and self.position_timer is None:
            self.position_timer = self.owner.after_idle(self.position)

    def unmapped(self, event):
        if event.widget is self.owner:
            self.dismiss()

    def dismiss(self):
        self.cancel_timer()
        if self.focus_timer is not None:
            try:
                self.owner.after_cancel(self.focus_timer)
            except tk.TclError:
                pass
            self.focus_timer = None
        if self.position_timer is not None:
            try:
                self.owner.after_cancel(self.position_timer)
            except tk.TclError:
                pass
            self.position_timer = None
        window, self.window = self.window, None
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    def destroyed(self, event):
        if event.widget is self.owner:
            self.dismiss()


def notify(owner, text, kind='success', duration=None):
    owner = owner.winfo_toplevel()
    layer = getattr(owner, '_notification_layer', None)
    if layer is None:
        layer = owner._notification_layer = NotificationLayer(owner)
    layer.show(text, kind, duration)
    return layer
