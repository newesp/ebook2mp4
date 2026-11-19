"""Stable native chrome. Content pages supply commands and presentation data."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Literal
import tkinter as tk
from tkinter import ttk, font
import math

from .ui_controls import AutoHideScrollbar, CellTooltip, MenuAction, MessageLine, command_menu


@dataclass(frozen=True)
class ActionSpec:
    id: str
    label: str
    role: Literal['back', 'secondary', 'destructive', 'primary']
    command: Callable[[], object]
    enabled: bool = True
    available_while_busy: bool = False


@dataclass(frozen=True)
class PagePresentation:
    step: int
    title: str
    summary: str
    actions: tuple[ActionSpec, ...]
    busy: bool = False
    message_kind: Literal['normal', 'error'] = 'normal'


@dataclass(frozen=True)
class HeaderBand:
    """A page declares its local header boundary; only the shell aligns it."""
    parent: object
    row: int
    controls: tuple


@dataclass(frozen=True)
class ShellPresentation:
    page_id: str
    owner: object
    root_content: object
    bands: tuple[HeaderBand, ...] = ()
    footer: object | None = None
    production: bool = False
    navigation: str = 'voice'
    show_summary: bool = True
    show_message: bool = True
    document_commands_enabled: bool = True
    collapse_documents_below: int = 0


class PageActionButton(ttk.Button):
    """Stable Tcl dispatcher; hidden/old-project pages cannot run an action.

    Controllers may change a button's label, availability or domain command.
    They cannot replace the active-page guard by configuring a new command.
    """
    def __init__(self, parent, *, shell, owner, command=None, **kwargs):
        self.shell, self.owner, self.page_command = shell, owner, command
        super().__init__(parent, command=self.dispatch, **kwargs)

    def dispatch(self):
        if self.shell.is_active(self.owner) and not self.instate(['disabled']) and self.page_command:
            return self.page_command()
        return None

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = dict(cnf, **kwargs)
            cnf = None
        if 'command' in kwargs:
            self.page_command = kwargs.pop('command')
        return super().configure(cnf, **kwargs)

    config = configure


class FooterPort(ttk.Frame):
    """Fixed native action content inside the one shell ActionBar.

    The adapter retains its incumbent control groups in this bounded port.
    Its visibility/parent/placement and command lease belong to the shell.
    """
    def __init__(self, bar, shell, owner, *, workspace_aligned=False, **kwargs):
        super().__init__(bar, **kwargs)
        self.shell, self.owner = shell, owner
        self.workspace_aligned = workspace_aligned
        self.actions: list[tuple[ActionSpec, PageActionButton]] = []
        owner.bind('<Destroy>', self.owner_destroyed, add='+')

    def owner_destroyed(self, event):
        if event.widget is self.owner and self.winfo_exists():
            self.shell.unregister(self.owner)
            self.destroy()

    def button(self, label, command, *, parent=None, role='secondary', identity=None, **kwargs):
        style = {'primary':'Primary.TButton', 'destructive':'Destructive.TButton'}.get(role, 'Workspace.TButton')
        button = PageActionButton(parent or self, shell=self.shell, owner=self.owner,
            text=label, command=command, style=style, **kwargs)
        action = ActionSpec(identity or f'{getattr(self.owner,"page_id",type(self.owner).__name__)}.{len(self.actions)}',label,role,command)
        self.actions.append((action,button))
        return button

    def describe(self):
        return tuple(ActionSpec(a.id, b.cget('text'), a.role, b.dispatch,
            enabled=not b.instate(['disabled'])) for a,b in self.actions if b.winfo_manager())


class NavigationBar(ttk.Frame):
    def __init__(self, parent, commands):
        super().__init__(parent)
        self.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        self.columnconfigure(2, weight=1)
        nav = ttk.Frame(self)
        nav.grid(row=0, column=0, sticky='w')
        self.steps = []
        for i, (label, command) in enumerate((('1 文稿', 'manuscript'), ('2 試聽與製作', 'production'))):
            button = ttk.Button(nav, text=label, command=commands[command], style='Workspace.TButton')
            button.grid(row=0, column=i, padx=(0, 8))
            self.steps.append(button)
        self.book = ttk.Label(self, width=1, anchor='e')
        self.book.grid(row=0, column=2, sticky='ew', padx=12)
        self.project_control, self.project_menu = command_menu(self, '專案')
        self.project_control.grid(row=0, column=3)
        self.message_button = ttk.Button(self, text='訊息記錄', command=commands['messages'], style='Workspace.TButton')
        self.message_button.grid(row=0, column=4, padx=(8, 0))
        MenuAction(self.project_menu, '建立書籍專案', commands['create'])
        MenuAction(self.project_menu, '開啟專案', commands['open'])
        self.folder_button = MenuAction(self.project_menu, '開啟專案資料夾', commands['folder'])
        MenuAction(self.project_menu, '專案位置與來源資訊', commands['source_info'])

    def select(self, step):
        for button, active in zip(self.steps, (step != 4, step == 4)):
            button.configure(style='WorkspaceActive.TButton' if active else 'Workspace.TButton')

    def create_production(self, commands, method):
        self.production = tabs = ttk.Frame(self)
        self.header_separator = ttk.Separator(tabs, orient='vertical')
        self.flow_buttons = {}
        for key,label in (('voice','語音設定與試聽'),('narration','音訊製做'),
                          ('assembly','全書合併'),('video','影片製作')):
            if key in ('narration','assembly'):
                ttk.Label(tabs,text=' → ').pack(side='left')
            if key=='video':ttk.Separator(tabs,orient='vertical').pack(side='left',fill='y',padx=8)
            button=ttk.Button(tabs,text=label,command=commands[key],style='Workspace.TButton')
            button.pack(side='left')
            self.flow_buttons[key]=button
        self.method_control=ttk.Combobox(tabs,textvariable=method,state='readonly',
            values=('總音訊製片','合併既有批次影片'),width=20)
        return tabs,self.flow_buttons,self.header_separator,self.method_control

    def present_production(self, visible, selected):
        if not hasattr(self,'production'):return
        tabs=self.production
        if not visible:
            tabs.grid_remove()
            return
        f=font.Font(font=ttk.Style(self).lookup('Workspace.TButton','font'))
        width=math.ceil(max(f.measure(b.cget('text')) for b in self.flow_buttons.values())/max(1,f.measure('0')))
        for key,button in self.flow_buttons.items():
            button.configure(width=width,style='Primary.TButton' if key==selected else 'Workspace.TButton')
        if not self.header_separator.winfo_manager():
            self.header_separator.pack(side='left',before=self.flow_buttons['voice'],fill='y',padx=(4,16))
        required=sum(w.winfo_reqwidth() for w in self.grid_slaves(row=0) if w is not tabs)
        wide=self.winfo_toplevel().winfo_width()>=required+tabs.winfo_reqwidth()+64
        tabs.grid(row=0 if wide else 1,column=1 if wide else 0,columnspan=1 if wide else 5,
                  sticky='w',pady=0 if wide else (8,0))


class DocumentList(ttk.Frame):
    def __init__(self, parent, commands):
        super().__init__(parent, padding=(0, 0, 12, 0))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.list_header = ttk.Frame(self)
        self.list_header.grid(row=0, column=0, sticky='ew')
        self.focus_button = ttk.Button(self.list_header, text='‹', width=2, command=commands['toggle_files'], style='Workspace.TButton')
        self.focus_button.pack(side='left')
        self.import_control, self.import_menu = command_menu(self.list_header, '匯入')
        self.import_control.configure(width=4)
        self.import_control.pack(side='left', padx=4)
        self.import_button = MenuAction(self.import_menu, '匯入 TXT', commands['import_txt'])
        self.pdf_button = MenuAction(self.import_menu, '匯入 PDF', commands['import_pdf'])
        self.management, self.management_menu = command_menu(self.list_header, '管理')
        self.management.configure(width=4)
        self.management.pack(side='left')
        self.rename_button = MenuAction(self.management_menu, '重新命名', commands['rename'])
        self.up_button = MenuAction(self.management_menu, '上移', commands['move_up'])
        self.down_button = MenuAction(self.management_menu, '下移', commands['move_down'])
        self.management_menu.add_separator()
        self.remove_pdf_button = MenuAction(self.management_menu, '移除 PDF 批次…', commands['remove_pdf'])
        self.batch_summary = ttk.Label(self)
        self.batch_view=ttk.Frame(self,width=206,height=1)
        self.batch_view.grid(row=1,column=0,sticky='nsew')
        self.batch_view.grid_propagate(False)
        self.batch_view.columnconfigure(0,weight=1);self.batch_view.rowconfigure(0,weight=1)
        self.batch_list = ttk.Treeview(self.batch_view, columns=('status',), displaycolumns=(), show='tree', selectmode='browse', height=6, style='Manuscript.Treeview')
        self.batch_list.column('#0', width=204, minwidth=60)
        self.batch_list.column('status', width=60, stretch=False)
        self.batch_list.grid(row=0,column=0,sticky='nsew')
        self.batch_scroll=AutoHideScrollbar(self.batch_view,command=self.batch_list.yview)
        self.batch_scroll.grid(row=0,column=1,sticky='ns')
        self.batch_list.configure(yscrollcommand=self.batch_scroll.set)
        self.batch_list.bind('<<TreeviewSelect>>', commands['select_batch'])
        self.batch_tooltip = CellTooltip(self.batch_list, commands['batch_help'])


class WorkspaceFrame(ttk.Frame):
    """The content port; the shell owns its position, the page owns its children."""
    def __init__(self, parent):
        super().__init__(parent)
        self.grid(row=0, column=1, sticky='nsew')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    def create_inner_host(self, toggle_documents):
        self.inner = InnerPageHost(self, toggle_documents)
        return self.inner


class ActionBar(ttk.Frame):
    def __init__(self, parent, *, regional=False):
        super().__init__(parent, padding=(20, 10) if regional else (0, 6),
                         style='Tool.TFrame' if regional else 'TFrame')
        self.regional = regional
        self.active = True
        self.presentation: PagePresentation | None = None
        self.visible_ids: set[str] = set()
        self.grid(row=5, column=0, sticky='ew')
        self.columnconfigure(0, weight=1)
        self.reading_status = ttk.Label(self, text='', width=1)
        self.footer_actions = ttk.Frame(self, style='Tool.TFrame' if regional else 'TFrame')
        self.footer_actions.grid(row=0, column=1, rowspan=2, sticky='e', padx=(12, 0))
        self.stats = ttk.Label(self, width=1, style='Tool.TLabel' if regional else 'TLabel')
        self.stats.grid(row=0, column=0, sticky='ew')
        self.status = MessageLine(self, text='', foreground='#58695f')
        self.status.grid(row=1, column=0, sticky='ew')
        self.buttons: dict[str, ttk.Button] = {}
        self.callbacks: dict[str, Callable[[], object]] = {}
        self.back_actions = ttk.Frame(self)
        self.ports: list[FooterPort] = []
        if regional:
            self.status.grid_remove()
            self.bind('<Configure>', self.reflow)

    def reflow(self, _event=None):
        if not self.regional:
            return
        actions_width = self.footer_actions.winfo_reqwidth() if self.visible_ids else 0
        available = max(1, self.winfo_width()-40-actions_width-12)
        stacked = bool(self.visible_ids and available < 160)
        self.stats.configure(wraplength=max(1, self.winfo_width()-40 if stacked else available))
        self.footer_actions.grid_configure(row=1 if stacked else 0, rowspan=1,
                                          pady=(8, 0) if stacked else 0)

    def invoke_action(self, identity: str) -> object:
        command = self.callbacks.get(identity)
        if command is not None:
            return command()
        return None

    def set_active(self, active):
        self.active = active
        if self.presentation is not None:
            self.present(self.presentation)

    def present(self, presentation: PagePresentation):
        ids = [action.id for action in presentation.actions]
        if len(ids) != len(set(ids)):
            raise ValueError('Action identifiers must be unique within a page.')
        self.visible_ids = set(ids)
        self.presentation = presentation
        self.callbacks = {a.id: a.command for a in presentation.actions
                          if self.active and a.enabled and (not presentation.busy or a.available_while_busy)}
        self.stats.configure(text=presentation.summary, foreground='#963b32' if presentation.message_kind == 'error' else '#263d34')
        if not self.active and not self.regional:
            self.callbacks = {}
            return
        for identity, button in self.buttons.items():
            if identity not in self.visible_ids:
                button.grid_remove()
                button.configure(state='disabled')
        left = [a for a in presentation.actions if a.role == 'back']
        right = [a for a in presentation.actions if a.role != 'back']
        if left:
            self.back_actions.grid(row=2, column=0, sticky='w', pady=(8, 0))
            self.footer_actions.grid_configure(row=2, rowspan=1)
        else:
            self.back_actions.grid_remove()
            if not self.regional:
                self.footer_actions.grid_configure(row=0, rowspan=2)
        for column, action in enumerate(left+right):
            action_button = self.buttons.get(action.id)
            parent = self.back_actions if action.role == 'back' else self.footer_actions
            if action_button is not None and action_button.master is not parent:
                action_button.destroy()
                action_button = None
            if action_button is None:
                action_button = self.buttons[action.id] = ttk.Button(parent,
                    command=partial(self.invoke_action, action.id))
            style = {'primary': 'Primary.TButton', 'destructive': 'Destructive.TButton'}.get(action.role, 'Workspace.TButton')
            state = 'normal' if action.id in self.callbacks else 'disabled'
            for option, value in (('text', action.label), ('style', style), ('state', state)):
                if str(action_button.cget(option)) != value:
                    action_button.configure(**{option: value})
            action_button.grid(row=0, column=column+1, padx=(4 if column else 0, 0))
        if self.regional:
            self.reflow()

    def create_port(self, shell, owner, **kwargs):
        port=FooterPort(self,shell,owner,**kwargs)
        self.ports.append(port)
        return port

    def show_port(self, port, *, summary=True, message=True, default_actions=True):
        aligned = port is not None and port.workspace_aligned
        for item in tuple(self.ports):
            if not item.winfo_exists():self.ports.remove(item)
            elif item is port:
                inset=max(0,item.shell.workspace.winfo_rootx()-self.winfo_rootx()) if aligned else 0
                item.grid(row=0 if aligned else 2,column=0,columnspan=2,sticky='ew',padx=(inset,0),pady=(8,0))
            else:item.grid_remove()
        self.active = port is None and default_actions
        self.columnconfigure(0,weight=1)
        self.columnconfigure(1,weight=0)
        if self.active:
            if self.presentation:self.present(self.presentation)
        else:
            self.callbacks={}
            for button in self.buttons.values():button.grid_remove()
            self.footer_actions.grid_remove()
            self.back_actions.grid_remove()
        self.stats.grid_configure(row=1 if aligned else 0,column=0,columnspan=1 if self.active else 2)
        self.status.grid_configure(row=2 if aligned else 1,column=0,columnspan=1 if self.active else 2,padx=0)
        self.stats.grid() if summary else self.stats.grid_remove()
        self.status.grid() if message else self.status.grid_remove()


class InnerPageHost(ttk.Frame):
    """Own inner-page chrome; content modules supply presentation and commands."""
    def __init__(self, parent, toggle_documents):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.active_id: str | None = None
        self.active = True
        self.presentation: PagePresentation | None = None
        self.back_action: ActionSpec | None = None
        self.header = ttk.Frame(self)
        self.header.grid(row=0, column=0, sticky='new')
        self.toggle_documents = toggle_documents
        self.reopen = ttk.Button(self.header, text='›', width=2, command=self.invoke_reopen,
                                 style='Workspace.TButton')
        self.reopen_tip = CellTooltip(self.reopen, lambda x, y: ('files', '顯示文件列表'))
        self.reopen.bind('<FocusIn>', lambda e: self.reopen.event_generate('<Motion>', x=0, y=0), add='+')
        self.reopen.bind('<FocusOut>', self.reopen_tip.hide, add='+')
        self.back = ttk.Button(self.header, command=self.invoke_back, style='Workspace.TButton')
        self.back.pack(side='left')
        self.title = ttk.Label(self.header, style='Heading.TLabel')
        self.title.pack(side='left', padx=12)
        self.panel = ttk.Frame(self, style='Tool.TFrame', borderwidth=1, relief='solid')
        self.panel.grid(row=1, column=0, sticky='nsew')
        self.panel.columnconfigure(0, weight=1)
        self.panel.rowconfigure(2, weight=1)
        self.context = ttk.Label(self.panel, width=1, padding=(20, 10), style='Tool.TLabel')
        self.context.grid(row=0, column=0, sticky='ew')
        self.context_separator = ttk.Separator(self.panel)
        self.context_separator.grid(row=1, column=0, sticky='ew')
        self.content = ttk.Frame(self.panel, style='Tool.TFrame')
        self.content.grid(row=2, column=0, sticky='nsew')
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        ttk.Separator(self.panel).grid(row=3, column=0, sticky='ew')
        self.actions = ActionBar(self.panel, regional=True)
        self.actions.grid(row=4, column=0, sticky='ew')
        self.context.bind('<Configure>', lambda e: self.context.configure(wraplength=max(1, e.width-40)))

    def invoke_back(self):
        action = self.back_action
        if self.active and action and self.presentation and action.enabled and (
                not self.presentation.busy or action.available_while_busy):
            return action.command()
        return None

    def invoke_reopen(self):
        if self.active and self.active_id is not None:
            return self.toggle_documents()
        return None

    def set_active(self, active):
        self.active = active
        self.reopen.configure(state='normal' if active and self.active_id is not None else 'disabled')
        self.actions.set_active(active)
        if not active:
            self.reopen_tip.hide()
        if self.active_id and self.presentation:
            self.present(self.active_id, self.presentation, self.context.cget('text'))

    def show(self, page_id, content):
        if content.master is not self.content:
            raise ValueError('Inner-page content must have the fixed content port as parent.')
        self.active_id = page_id
        self.set_active(True)
        self.page = content
        if getattr(content, 'show_context', True):
            self.context.grid()
            self.context_separator.grid()
        else:
            self.context.grid_remove()
            self.context_separator.grid_remove()
        for child in self.content.grid_slaves():
            child.grid_remove()
        content.grid(row=0, column=0, sticky='nsew')
        self.refresh(page_id)

    def refresh(self, page_id):
        if self.active_id != page_id:
            return False
        presentation, context = self.page.describe()
        return self.present(page_id, presentation, context)

    def present(self, page_id, presentation, context):
        if page_id != self.active_id:
            return False
        backs = [a for a in presentation.actions if a.role == 'back']
        if len(backs) != 1:
            raise ValueError('An inner page needs exactly one return action.')
        self.presentation = presentation
        self.back_action = backs[0]
        self.title.configure(text=presentation.title)
        self.context.configure(text=context)
        self.back.configure(text=self.back_action.label, state='normal' if self.active and self.back_action.enabled and (
            not presentation.busy or self.back_action.available_while_busy) else 'disabled')
        self.actions.present(PagePresentation(presentation.step, presentation.title,
            presentation.summary, tuple(a for a in presentation.actions if a.role != 'back'),
            presentation.busy, presentation.message_kind))
        return True

    def show_document_toggle(self, visible):
        self.reopen.pack_forget()
        if visible:
            self.reopen.pack(side='left', before=self.back, padx=(0, 4))

    def hide(self):
        self.active_id = None
        self.back_action = None
        self.presentation = None
        self.set_active(False)
        self.reopen_tip.hide()
        self.actions.present(PagePresentation(1, '', '', ()))


class DesktopShell:
    def __init__(self, host, commands: Mapping[str, Callable]):
        self.navigation = NavigationBar(host, commands)
        self.body = ttk.Frame(host)
        self.body.grid(row=2, column=0, sticky='nsew')
        self.body.rowconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=1)
        self.documents = DocumentList(self.body, commands)
        self.workspace = WorkspaceFrame(self.body)
        self.manuscript = self.workspace
        self.current: ShellPresentation | None = None
        self.generation=0
        self._rendering=False
        self._collapse_width=None
        self._roots: list[tk.Widget]=[]
        self._registered: dict[int,ShellPresentation]={}
        self.footer = ActionBar(host)
        self.footer.present(PagePresentation(1, '文稿', '', (
            ActionSpec('manuscript.next', '儲存為朗讀稿', 'primary', commands['next']),)))

    def is_active(self, owner):
        current=self.current
        if current is None or current.owner is not owner:return False
        flow=getattr(owner,'flow',getattr(self.app,'flow',None))
        return flow is getattr(self.app,'flow',None) and not getattr(self.app,'_closing',False)

    def create_footer(self, owner, **kwargs):
        return self.footer.create_port(self,owner,**kwargs)

    def unregister(self, owner):
        self._registered.pop(id(owner),None)
        if self.current is not None and self.current.owner is owner:
            self.current=None

    def create_header(self, parent, row):
        header=ttk.Frame(parent)
        header.grid(row=row,column=0,sticky='ew')
        header.grid_remove()
        return header

    def create_task_banner(self, command):
        banner=ttk.Frame(self.app,padding=(0,6))
        banner.columnconfigure(0,weight=1)
        summary=MessageLine(banner,text='')
        summary.grid(row=0,column=0,sticky='ew',padx=(0,12))
        button=ttk.Button(banner,text='返回任務 →',command=command)
        button.grid(row=0,column=1)
        self.task_banner=banner
        return banner,summary,button

    def show_task_banner(self, visible):
        if visible:self.task_banner.grid(row=4,column=0,sticky='ew')
        else:self.task_banner.grid_remove()

    def register_content_root(self, content):
        if content.master is not self.workspace:
            raise ValueError('Main content must be created in the fixed shell workspace.')
        self._roots.append(content)

    def show_content(self, content):
        for item in self._roots:
            if item.winfo_exists():
                item.grid(row=2,column=0,sticky='nsew') if item is content else item.grid_remove()

    def show_production_page(self, parent, page):
        if page.master is not parent:raise ValueError('Production page must use the fixed content port.')
        for child in parent.grid_slaves():
            if child is not page:child.grid_remove()
        page.grid(row=0,column=0,sticky='nsew')

    def present(self, presentation):
        if self._rendering:return False
        self._rendering=True
        try:
            previous=self.current
            if previous is None or previous.owner is not presentation.owner or previous.page_id!=presentation.page_id:
                self.generation+=1
            self.current=presentation
            self._registered[id(presentation.owner)]=presentation
            self.show_content(presentation.root_content)
            self.navigation.select(4 if presentation.production else 1)
            self.navigation.present_production(presentation.production,presentation.navigation)
            root_width=self.app.root.winfo_width()
            if presentation.collapse_documents_below and root_width!=self._collapse_width:
                self._collapse_width=root_width
                if 1<root_width<presentation.collapse_documents_below and not self.app.focus_mode:
                    self.app.focus_mode=True
                    self.app.save_source_view()
            self.show_documents(not self.app.focus_mode)
            current_headers={c for band in presentation.bands for c in band.controls}
            current_tracks={(band.parent,band.row) for band in presentation.bands}
            if previous:
                for band in previous.bands:
                    if (band.parent,band.row) not in current_tracks and band.parent.winfo_exists():
                        band.parent.rowconfigure(band.row,minsize=0)
                    for control in band.controls:
                        if control not in current_headers and control.winfo_exists():control.grid_remove()
            self.align_headers(presentation.bands)
            self.footer.show_port(presentation.footer,summary=presentation.show_summary,message=presentation.show_message,
                                  default_actions=not presentation.production)
            if presentation.footer is not None or not presentation.production or presentation.show_summary or presentation.show_message:
                self.footer.grid()
            else:self.footer.grid_remove()
            self.refresh_document_commands()
            return True
        finally:self._rendering=False

    def align_headers(self, bands):
        from .workspace_layout import TOOLBAR_GAP
        controls=tuple(c for band in bands for c in band.controls if c.winfo_exists())
        height=max((self.documents.list_header.winfo_reqheight(),*(c.winfo_reqheight() for c in controls)))+2*TOOLBAR_GAP
        self.documents.rowconfigure(0,minsize=height if bands else 0)
        self.documents.list_header.grid_configure(sticky='nsew',pady=(0,2*TOOLBAR_GAP) if bands else 0)
        for band in bands:
            band.parent.rowconfigure(band.row,minsize=height)
            for control in band.controls:
                control.grid_configure(sticky='nsew',pady=(0,2*TOOLBAR_GAP))

    def set_document_commands(self, owner, enabled):
        if not self.is_active(owner):return
        from dataclasses import replace
        self.current=replace(self.current,document_commands_enabled=enabled)
        self.refresh_document_commands()

    def refresh_document_commands(self):
        enabled=bool(self.app.flow) and not (self.app.workspace_busy or self.app.source_pending)
        if self.current:enabled=enabled and self.current.document_commands_enabled
        for control in (self.documents.import_control,self.documents.management):
            control.configure(state='normal' if enabled else 'disabled')

    def show_documents(self, visible):
        if visible:
            self.documents.grid(row=0, column=0, sticky='nsew')
            self.body.columnconfigure(0, minsize=self.documents.winfo_reqwidth())
        else:
            self.documents.grid_remove()
            self.body.columnconfigure(0, minsize=0, weight=0, pad=0)

    def install_legacy_handles(self, app):
        """Temporary bridge for existing controllers, not a new page API.

        Production pages will migrate separately. Keep old entry points working
        without duplicating widgets or moving them to new parents.
        """
        for owner, names in ((self.navigation, ('steps', 'book', 'project_menu', 'message_button', 'folder_button')),
            (self.documents, ('list_header', 'focus_button', 'import_control', 'import_menu', 'import_button', 'pdf_button',
             'management_menu', 'rename_button', 'up_button', 'down_button', 'remove_pdf_button', 'batch_summary', 'batch_list', 'batch_tooltip')),
            (self.footer, ('reading_status', 'footer_actions', 'stats', 'status'))):
            for name in names:
                setattr(app, name, getattr(owner, name))
        self.app=app
        app.workspace_header = self.navigation
        app.body, app.left_panel, app.center, app.actions = self.body, self.documents, self.manuscript, self.footer
        app.next_button = self.footer.buttons['manuscript.next']
