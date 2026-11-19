"""Audio assembly layout and presentation; media/persistence stay in AssemblyPage.

The shared video controller supplies selection, join and product commands. This
module owns the audio-only parent grid, aligned rows and fixed footer. No output
format or video-method preference participates in its presentation.
"""
import tkinter as tk
from tkinter import ttk, font

from .ui_controls import AutoHideScrollbar, CellTooltip, MessageLine
from .workspace_layout import TOOLBAR_GAP
from .workflow import ProjectError


class AudioAssemblyWorkspace:
    def __init__(self, page):
        self.page, self.app = page, page.app
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        self.header = ttk.Frame(page)
        self.header.grid(row=0, column=0, sticky='new', pady=(0, 8))
        self.files_button=self.button(self.header,'顯示文件列表',self.app.toggle_focus)
        self.files_button.configure(width=0)
        ttk.Label(self.header, text='全書合併', style='Heading.TLabel').pack(side='left')
        self.header_hint=ttk.Label(self.header, text='選取批次、調整順序，再製作合併音訊')
        self.header_hint.pack(side='left', padx=20)
        page.main = main = ttk.Frame(page, padding=12, style='Tool.TFrame', borderwidth=1, relief='solid')
        main.grid(row=1, column=0, sticky='nsew')
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        self.toolbar = toolbar = ttk.Frame(main, style='Tool.TFrame')
        toolbar.grid(row=1, column=0, sticky='ew', pady=(0, 2*TOOLBAR_GAP))
        toolbar.columnconfigure(0, minsize=112)
        ttk.Label(toolbar, text='合併來源', style='Tool.TLabel').grid(row=0, column=0, sticky='w')
        page.select_button = self.button(toolbar, '選取有效批次', page.select_valid)
        page.up_button = self.button(toolbar, '上移', lambda: page.move(-1))
        page.down_button = self.button(toolbar, '下移', lambda: page.move(1))
        page.info_button = self.button(toolbar, '來源詳情 →', page.toggle_info)
        self.source_buttons = (page.select_button, page.up_button, page.down_button, page.info_button)
        for i, button in enumerate(self.source_buttons):
            toolbar.columnconfigure(1+i*2, minsize=144, uniform='source')
            button.grid(row=0, column=1+i*2, sticky='nsew')
            if i<3: toolbar.columnconfigure(2+i*2, minsize=TOOLBAR_GAP)
        toolbar.columnconfigure(8, weight=1)
        page.table_frame = ttk.Frame(main, style='Tool.TFrame')
        page.table_frame.grid(row=2, column=0, sticky='nsew')
        page.table_frame.columnconfigure(0, weight=1)
        page.table_frame.rowconfigure(0, weight=1)
        page.table = ttk.Treeview(page.table_frame, columns=('pick','order','name','duration','status'),
                                 show='headings', selectmode='browse', height=5,style='Workspace.Treeview')
        for key,label,width,stretch in (('pick','選取',48,False),('order','順序',48,False),
            ('name','批次',220,True),('duration','時長',80,False),('status','來源狀態',240,True)):
            page.table.heading(key,text=label)
            page.table.column(key,width=width,minwidth=40,stretch=stretch)
        page.table.grid(row=0,column=0,sticky='nsew')
        self.empty_label=ttk.Label(page.table_frame,text='尚無批次。請先匯入文稿並製作批次音訊。',style='Tool.TLabel')
        self.table_scroll=AutoHideScrollbar(page.table_frame,command=page.table.yview)
        self.table_scroll.grid(row=0,column=1,sticky='ns')
        page.table.configure(yscrollcommand=self.table_scroll.set)
        page.table.bind('<ButtonRelease-1>',page.toggle_selected)
        page.table.bind('<space>',page.toggle_selected)
        page.table.bind('<<TreeviewSelect>>',lambda e:page.update_controls())
        page.table.bind('<Return>',lambda e:page.toggle_info())
        page.tooltip=CellTooltip(page.table,page.cell_help)
        self.build_details(main)
        self.rows = rows = ttk.Frame(main, style='Tool.TFrame')
        rows.grid(row=3,column=0,sticky='ew',pady=(8,0))
        for col,size in ((0,112),(1,144),(2,4),(3,144),(4,4),(5,144),(6,4),(7,144)):
            rows.columnconfigure(col,minsize=size)
        rows.columnconfigure(8,weight=1)
        ttk.Label(rows,text='交接停頓',style='Tool.TLabel').grid(row=0,column=0,sticky='w')
        self.pause_display=tk.StringVar(value=page.pause.get()+' 秒')
        self._syncing_pause=False
        self.pause_display.trace_add('write',self.edit_pause)
        page.pause.trace_add('write',self.sync_pause)
        page.pause_control=ttk.Combobox(rows,textvariable=self.pause_display,values=('0 秒','0.5 秒','1 秒','2 秒','5 秒'),
                                      width=1,style='Workspace.TCombobox')
        page.pause_control.grid(row=0,column=1,sticky='nsew')
        page.pause_control.bind('<FocusOut>',self.sync_pause,add='+')
        page.join_summary=ttk.Label(rows,text='0 個接點',width=1,style='Tool.TLabel')
        page.join_summary.grid(row=0,column=3,sticky='ew')
        page.join_button=self.button(rows,'檢查接點 →',page.open_joins)
        page.join_button.grid(row=0,column=5,sticky='nsew')
        rows.rowconfigure(1,minsize=8)
        ttk.Label(rows,text='合併音訊',style='Tool.TLabel').grid(row=2,column=0,sticky='w')
        self.result_state=ttk.Label(rows,text='檢查中',width=1,padding=(10,7),relief='solid',borderwidth=1)
        self.result_state.grid(row=2,column=1,sticky='nsew')
        self.result_format=ttk.Label(rows,text='MP3／SRT',style='Tool.TLabel')
        self.result_format.grid(row=2,column=3,sticky='w')
        self.detail_button=self.button(rows,'查看詳情 →',self.show_output_details)
        self.detail_button.grid(row=2,column=5,sticky='nsew')
        page.outputs_menu=tk.Menu(page,tearoff=False,postcommand=page.output_menu)
        page.outputs_button=ttk.Menubutton(rows,text='成品操作',menu=page.outputs_menu,style='Workspace.TMenubutton',width=0)
        page.versions_button=self.button(rows,'成品版本 →',self.show_versions)
        page.versions_button.grid(row=2,column=7,sticky='nsew')
        self.pause_help=CellTooltip(page.pause_control,lambda x,y:('pause','秒 · 全書共用 · 0～5 秒，最多三位小數。'))
        self.pause_help.widget.bind('<FocusIn>',lambda e:self.pause_help.motion(type('Focus',(),{'x':0,'y':0})()),add='+')
        self.pause_help.widget.bind('<FocusOut>',self.pause_help.hide,add='+')
        # Legacy media commands remain controller handles behind the product menu.
        for name,label,command in (('play_button','播放總音訊',page.play),('stop_button','停止播放',page.stop),
            ('export_button','另存 MP3／SRT',page.export),('folder_button','開啟資料夾',page.open_folder)):
            setattr(page,name,self.button(page,label,command))
        page.result_info=ttk.Label(page,width=1)
        page.saved_label=ttk.Label(page,text='合併設定已儲存' if page.selected else '尚未選取批次')
        page.summary=ttk.Label(page,width=1)
        self.build_footer()
        page.bind('<Configure>',self.resized,add='+')
        self.active=False
        self._geometry=None
        self._root_width=None

    @staticmethod
    def button(parent,text,command):
        return ttk.Button(parent,text=text,command=command,style='Workspace.TButton',width=1)

    def edit_pause(self,*args):
        if self._syncing_pause:return
        self._syncing_pause=True
        try:self.page.pause.set(self.pause_display.get().removesuffix('秒').strip())
        finally:self._syncing_pause=False

    def sync_pause(self,*args):
        if self._syncing_pause:return
        self._syncing_pause=True
        try:self.pause_display.set(self.page.pause.get()+' 秒')
        finally:self._syncing_pause=False

    def build_details(self,main):
        p=self.page
        p.info_frame=ttk.Frame(main,style='Tool.TFrame')
        p.info_frame.columnconfigure(0,weight=1);p.info_frame.rowconfigure(0,weight=1)
        p.info_text=tk.Text(p.info_frame,wrap='word',width=1,height=4,font=('Microsoft JhengHei',10),
                            relief='flat',padx=12,pady=10,state='disabled')
        p.info_text.grid(row=0,column=0,sticky='nsew')
        self.info_scroll=AutoHideScrollbar(p.info_frame,command=p.info_text.yview)
        self.info_scroll.grid(row=0,column=1,sticky='ns')
        p.info_text.configure(yscrollcommand=self.info_scroll.set)
        actions=ttk.Frame(p.info_frame)
        actions.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(8,0))
        p.fix_button=self.button(actions,'前往此批次製作 →',p.fix_source)
        p.fix_button.pack(side='left')
        self.button(actions,'← 返回來源清單',p.toggle_info).pack(side='left',padx=(4,0))

    def build_footer(self):
        p=self.page
        self.actions=actions=self.app.shell.create_footer(p)
        actions.columnconfigure(0,minsize=168)
        actions.columnconfigure(1,weight=1)
        p.status=MessageLine(actions,text='正在檢查來源…')
        p.status.grid(row=0,column=0,columnspan=6,sticky='ew',pady=(0,8))
        p.back_button=actions.button('← 返回音訊製做',self.app.narration,role='back',width=1)
        p.back_button.grid(row=1,column=0,sticky='ew')
        p.save_button=actions.button('儲存合併設定',p.save,width=1)
        p.start_button=actions.button('製作合併音訊',p.start,role='primary',width=1)
        p.cancel_button=actions.button('取消任務',p.cancel,width=1)
        actions.columnconfigure(2,minsize=196,uniform='commit');actions.columnconfigure(3,minsize=4)
        actions.columnconfigure(4,minsize=196,uniform='commit')
        p.save_button.grid(row=1,column=2,sticky='ew')
        p.start_button.grid(row=1,column=4,sticky='ew')
        p.progress=ttk.Progressbar(self.rows,mode='determinate')

    def set_active(self,active):
        if not self.actions.winfo_exists():return
        self.active=active

    def resized(self,event=None):
        p=self.page
        if not p.winfo_exists() or not self.header_hint.winfo_exists():return
        if event and event.widget is not p:return
        root_width=self.app.winfo_toplevel().winfo_width()
        if self.app.focus_mode:
            if not self.files_button.winfo_manager():self.files_button.pack(side='left',before=self.header.winfo_children()[1],padx=(0,8))
        else:self.files_button.pack_forget()
        if root_width<1050:self.header_hint.pack_forget()
        elif not self.header_hint.winfo_manager():self.header_hint.pack(side='left',padx=20)
        controls=(*self.source_buttons,p.pause_control,self.result_state,self.detail_button,p.outputs_button,p.versions_button,p.join_button)
        geometry=(p.winfo_width(),p.winfo_height(),tuple((w.winfo_reqwidth(),w.winfo_reqheight()) for w in controls))
        if geometry==self._geometry:return
        self._geometry=geometry
        height=max(w.winfo_reqheight() for w in controls)
        self.rows.rowconfigure(0,minsize=height);self.rows.rowconfigure(2,minsize=height)
        self.toolbar.rowconfigure(0,minsize=height)
        # Configure reaches the page before its child frame receives the new
        # size. Use the page's current width, not the previous child geometry.
        available=p.winfo_width()-26
        label_width=80 if available<700 else 112
        target_width=min(144,max(1,(available-label_width-12)//4))
        text_font=font.Font(font=ttk.Style(p).lookup('Workspace.TButton','font'))
        width=max(target_width,*(text_font.measure(b.cget('text'))+28 for b in self.source_buttons),
                  text_font.measure('查看詳情 →')+28,text_font.measure('成品操作')+44,
                  text_font.measure('成品版本 →')+28,text_font.measure('檢查接點 →')+28)
        self.toolbar.columnconfigure(0,minsize=label_width)
        self.rows.columnconfigure(0,minsize=label_width)
        for c in (1,3,5,7):self.toolbar.columnconfigure(c,minsize=width)
        for c in (1,3,5,7):self.rows.columnconfigure(c,minsize=width)

    def show_versions(self):
        result=self.app.production.show_versions()
        result.requested_route='audio'
        return result

    def show_output_details(self):
        p=self.page
        missing=next((r for r in p.rows if r['batch_id'] in p.selected and not r['valid']),None)
        if missing:
            p.table.selection_set(missing['batch_id'])
            p.fix_source()
            return
        if not p.info_open:p.toggle_info()
        content=p.status.full_text+'\n\n'+p.result_info.cget('text')+'\n\n'+p.saved_label.cget('text')
        p.info_text.configure(state='normal');p.info_text.delete('1.0','end');p.info_text.insert('1.0',content);p.info_text.configure(state='disabled')

    def refresh(self):
        p=self.page
        self.empty_label.configure(text='正在檢查批次音訊與字幕…' if p.check_job is not None else '尚無批次。請先匯入文稿並製作批次音訊。')
        if p.rows:self.empty_label.grid_remove()
        elif not self.empty_label.winfo_manager():self.empty_label.grid(row=0,column=0)
        stopped=p.job is not None and p.job.wait(0)
        pending=bool(stopped and p.job and p.job.state['status']=='completed')
        busy=p.job is not None or p.check_job is not None or p.production_busy
        valid=bool(p.selected) and all(any(r['batch_id']==i and r['valid'] for r in p.rows) for i in p.selected)
        try:pause=p.pause_ms()
        except ProjectError:pause=None;valid=False
        from .assembly_joins import metadata
        try:joins=metadata(p.flow,p.selected)
        except ProjectError:joins=[];valid=False
        warnings=sum(bool(j['warning']) and j['key'] not in p.accepted_joins for j in joins)
        current=bool(p.product and not p.product['stale'] and pause==p.product.get('pause_ms')
                     and p.selected==[s['batch_id'] for s in p.product.get('sources',[])])
        can_run=valid and not warnings and not busy and (not current or p.rebuild_requested)
        p.start_button.configure(text='重試保存' if pending else '製作合併音訊',state='normal' if pending or can_run else 'disabled')
        p.save_button.configure(state='normal' if valid and not busy else 'disabled')
        p.pause_control.configure(state='disabled' if busy else 'normal')
        p.select_button.configure(text='選取有效批次' if p.rows else '重新檢查來源',state='disabled' if busy else 'normal')
        focus=p.table.selection();index=p.selected.index(focus[0]) if focus and focus[0] in p.selected else -1
        p.up_button.configure(state='normal' if not busy and index>0 else 'disabled')
        p.down_button.configure(state='normal' if not busy and 0<=index<len(p.selected)-1 else 'disabled')
        p.info_button.configure(state='disabled' if busy else 'normal')
        p.join_button.configure(state='normal' if not busy and len(p.selected)>=2 and joins else 'disabled')
        p.join_summary.configure(text=f'{len(joins)} 個接點'+(f' · {warnings} 待確認' if warnings else ''))
        p.play_button.configure(state='normal' if p.product and not busy else 'disabled')
        p.stop_button.configure(state='normal' if p.player.alias is not None or p.check_job is not None and p.check_action=='play' else 'disabled')
        for button in (p.export_button,p.folder_button):button.configure(state='normal' if p.product and not busy else 'disabled')
        p.versions_button.configure(state='disabled' if busy else 'normal')
        text='保存失敗' if pending else '檢查中' if p.check_job is not None else '製作中' if p.job else '等待任務' if p.production_busy else '已完成' if current else '待更新' if p.product else '缺項' if p.selected and not valid or warnings else '準備'
        if not busy and p.last_status in ('failed','cancelled','interrupted') and not current:text={'failed':'失敗','cancelled':'已取消','interrupted':'已中斷'}[p.last_status]
        self.result_state.configure(text=text)
        if p.product and not busy:
            self.detail_button.grid_remove()
            if not p.outputs_button.winfo_manager():p.outputs_button.grid(row=2,column=5,sticky='nsew')
        else:
            p.outputs_button.grid_remove()
            if not self.detail_button.winfo_manager():self.detail_button.grid(row=2,column=5,sticky='nsew')
        self.detail_button.configure(state='disabled' if busy else 'normal',text='補齊缺項 →' if p.selected and not valid else '查看詳情 →')
        running=p.check_job is not None or p.job is not None and not stopped
        p.cancel_button.grid_remove();p.progress.grid_remove();self.result_format.grid()
        if running:
            p.start_button.grid_remove();p.save_button.grid_remove()
            p.cancel_button.grid(row=1,column=4,sticky='ew')
            if p.job is not None:
                self.result_format.grid_remove();p.progress.grid(row=2,column=3,sticky='ew')
        else:p.start_button.grid();p.save_button.grid()
        if p.join_page is not None and p.join_page.winfo_exists():p.join_page.update_controls()
        self.resized()
