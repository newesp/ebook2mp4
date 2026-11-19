"""Shared toolbar spacing and native content header layout; no domain state."""

TOOLBAR_GAP = 4


class ToolbarLayout:
    @staticmethod
    def equal_button_pair(parent, first, second, *, row=0, column=0, group='actions'):
        """Equal natural button widths with a dedicated, exact spacing track."""
        parent.columnconfigure(column, weight=0, uniform=group)
        parent.columnconfigure(column+1, weight=0, minsize=TOOLBAR_GAP)
        parent.columnconfigure(column+2, weight=0, uniform=group)
        first.grid(row=row, column=column, sticky='ew')
        second.grid(row=row, column=column+2, sticky='ew')

    @staticmethod
    def pack_groups(groups):
        """Keep a page number and its total together, with gaps between actions."""
        for group in groups:
            for i, control in enumerate(group):
                control.pack(side='left', padx=(TOOLBAR_GAP//2 if i == 0 else 0,
                                              TOOLBAR_GAP//2 if i == len(group)-1 else 0))

    @staticmethod
    def wrap(controls, available):
        for control in controls:
            control.pack_forget()
        row = column = used = 0
        for control in controls:
            width = control.winfo_reqwidth()+TOOLBAR_GAP
            if used and used+width > available:
                row, column, used = row+1, 0, 0
            control.grid(row=row, column=column, padx=TOOLBAR_GAP//2, pady=2)
            used += width
            column += 1


class ManuscriptLayout:
    def __init__(self, source_title, source_tools, editor_title, editor_tools, editor_actions, pdf_groups, source_menu):
        self.source_title, self.source_tools = source_title, source_tools
        self.editor_title, self.editor_tools = editor_title, editor_tools
        self.editor_actions, self.pdf_groups = editor_actions, pdf_groups
        self.source_menu = source_menu

    def show_pdf_controls(self, visible):
        for group in self.pdf_groups:
            for control in group:
                control.pack_forget()
        groups = self.pdf_groups if visible else ()
        # The source menu also applies to TXT; keep its fixed parent/order.
        menu = self.source_menu
        menu.pack_forget()
        ToolbarLayout.pack_groups((*groups, (menu,)))

    def reflow(self, source_width, editor_width):
        natural = sum(w.winfo_reqwidth()+TOOLBAR_GAP for w in self.editor_actions)
        editor_wrap = self.editor_title.winfo_reqwidth()+natural+16 > editor_width
        source_wrap = self.source_title.winfo_reqwidth()+self.source_tools.winfo_reqwidth()+16 > source_width
        self.editor_tools.grid_configure(row=1 if editor_wrap else 0, column=0 if editor_wrap else 1, sticky='e')
        available = editor_width if editor_wrap else max(1, editor_width-self.editor_title.winfo_reqwidth()-16)
        ToolbarLayout.wrap(self.editor_actions, available)
        self.source_tools.grid_configure(row=1 if source_wrap else 0, column=0 if source_wrap else 1, sticky='e')
class ProductionPageLayout:
    """Fixed production toolbar/footer ports with active-page command routing."""
    def __init__(self, page, app, toolbar, footer, commands):
        from .desktop_shell import ActionSpec
        self.page, self.app, self.toolbar, self.footer = page, app, toolbar, footer
        self.active = False
        self.commands = tuple((ActionSpec('voice.'+key, control.cget('text'),
            'back' if key == 'back' else 'primary' if key == 'produce' else 'secondary', command), control)
            for key, control, command in commands)
        for action, control in self.commands:
            control.configure(command=lambda a=action,c=control:self.invoke(a,c))
        page.bind('<Destroy>', self.destroyed, add='+')

    def destroyed(self, event):
        if event.widget is self.page:
            self.active = False
            if self.footer.winfo_exists():
                self.footer.destroy()

    def invoke(self, action, control):
        if self.active and not control.instate(['disabled']):
            return action.command()
        return None

    def describe(self):
        from .desktop_shell import PagePresentation
        return PagePresentation(4, '語音設定與試聽', self.page.status.cget('text'),
            tuple(action for action, control in self.commands if control.winfo_manager()),
            busy=self.page.job is not None)

    def set_active(self, active):
        self.active = active
