"""Single-window production pages, independent from background task lifetime."""
from tkinter import ttk
import tkinter as tk
from typing import Any


class ScrollPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, background='#f5f6f2', width=1, height=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        from .ui_controls import AutoHideScrollbar
        scrollbar = self.scrollbar = AutoHideScrollbar(self, command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.content = ttk.Frame(self.canvas)
        item = self.canvas.create_window(0, 0, anchor='nw', window=self.content)
        def reflow(event=None):
            height=max(self.canvas.winfo_height(),self.content.winfo_reqheight())
            self.canvas.itemconfigure(item,width=self.canvas.winfo_width())
            self.canvas.configure(scrollregion=(0,0,self.canvas.winfo_width(),height))
            if height<=self.canvas.winfo_height():self.canvas.yview_moveto(0)
        self.content.bind('<Configure>',reflow)
        self.canvas.bind('<Configure>',reflow)
        # Tk does not Configure an off-screen canvas window when its requested
        # height shrinks. Reconcile that request while this viewport is mapped.
        self._extent=None
        self._extent_timer=None
        def reconcile():
            self._extent_timer=None
            extent=(self.content.winfo_reqheight(),self.canvas.winfo_width(),self.canvas.winfo_height())
            if self.winfo_ismapped() and extent!=self._extent:
                self._extent=extent;reflow()
            self._extent_timer=self.after(80,reconcile)
        def destroy(event):
            if event.widget is self and self._extent_timer:
                self.after_cancel(self._extent_timer);self._extent_timer=None
        self.bind('<Destroy>',destroy,add='+')
        self._extent_timer=self.after(80,reconcile)
        self.canvas.configure(takefocus=True)
        for key,amount,unit in (('<Prior>',-1,'pages'),('<Next>',1,'pages'),('<Up>',-1,'units'),('<Down>',1,'units')):
            self.canvas.bind(key,lambda event,n=amount,u=unit:self.canvas.yview_scroll(n,u))
        self.canvas.bind('<Control-Home>',lambda event:self.canvas.yview_moveto(0))
        self.canvas.bind('<Control-End>',lambda event:self.canvas.yview_moveto(1))

    def reveal(self, widget):
        """Bring an expanded confirmation/focused field into its own viewport."""
        self.update_idletasks()
        canvas=self.canvas
        height=max(1,self.content.winfo_height())
        top=widget.winfo_rooty()-self.content.winfo_rooty()
        bottom=top+widget.winfo_height()
        visible=canvas.canvasy(0)
        if bottom>visible+canvas.winfo_height():
            canvas.yview_moveto(max(0,bottom-canvas.winfo_height())/height)
        elif top<visible:canvas.yview_moveto(top/height)

    def bind_scroll(self):
        from .desktop import bind_canvas_wheel
        bind_canvas_wheel(self.canvas, self.content)


class ProductionWorkspace(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.shell.workspace)
        app.shell.register_content_root(self)
        self.app = app
        self.pages: dict[tuple, Any] = {}
        self.current = None
        self.assembly_drafts = {}
        self.service_page = None
        self.package_page = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.method = tk.StringVar(value='總音訊製片')
        self.tabs, buttons, self.header_separator, self.method_control = app.shell.navigation.create_production(
            dict(voice=app.voice_settings,narration=app.narration,assembly=app.total_audio,video=self.open_video),self.method)
        self.voice_tab,self.narration_tab,self.assembly_tab,self.video_tab=(buttons[k] for k in ('voice','narration','assembly','video'))
        self.method_control.bind('<<ComboboxSelected>>', self.change_method)
        self.video_toolbar = app.shell.create_header(self,1)
        self.video_toolbar.columnconfigure(5, weight=1)
        self.files_button = ttk.Button(self.video_toolbar, text='>', width=2, style='Workspace.TButton', command=self.toggle_files)
        self.files_button.grid(row=0, column=0, padx=(0, 8))
        from .ui_controls import CellTooltip
        self.files_hint = CellTooltip(self.files_button, lambda x, y: (self.files_button.help_text, self.files_button.help_text))
        self.files_button.bind('<FocusIn>', lambda event: self.files_hint.motion(type('Focus', (), {'x': 0, 'y': 0})()))
        self.files_button.bind('<FocusOut>', self.files_hint.hide)
        ttk.Label(self.video_toolbar, text='製作範圍').grid(row=0, column=1, padx=(0, 6))
        self.scope = tk.StringVar(value='本批')
        self.scope_control = ttk.Combobox(self.video_toolbar, textvariable=self.scope,
            values=('本批', '全書'), state='readonly', width=6, style='Workspace.TCombobox')
        self.scope_control.grid(row=0, column=2)
        self.scope_control.bind('<<ComboboxSelected>>', self.change_scope)
        self.video_method = tk.StringVar(value='統一素材')
        self.video_method_control = ttk.Combobox(self.video_toolbar, textvariable=self.video_method,
            values=('統一素材', '沿用各批影片'), state='readonly', width=14, style='Workspace.TCombobox')
        self.video_method_control.bind('<<ComboboxSelected>>', self.change_video_method)
        self.scope_info = ttk.Label(self.video_toolbar, width=1)
        self.scope_info.grid(row=0, column=5, sticky='ew', padx=8)
        self.host = ttk.Frame(self)
        self.host.grid(row=2, column=0, sticky='nsew')
        self.host.columnconfigure(0, weight=1)
        self.host.rowconfigure(0, weight=1)
        self.task_bar,self.task_summary,self.task_button=app.shell.create_task_banner(self.show_active)
        app.status.on_change = self.sync_summary
        self.timer: str | None = self.after(200, self.poll)
        self.bind('<Destroy>', self.destroyed, add='+')

    def destroyed(self, event):
        if event.widget is self and self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None

    def activate(self, page):
        if self.current is not None and self.current.winfo_exists():
            if hasattr(self.current, 'stop'):
                self.current.stop()
        self.current = page
        if getattr(page, 'kind', None) == 'assembly':
            self.assembly_drafts[id(page.flow)] = page
        self.app.shell.show_production_page(self.host,page)
        self.refresh_task_controls()
        video = getattr(page, 'kind', None) == 'video' or getattr(page, 'movie', False)
        if video:
            self.scope.set('本批' if getattr(page, 'batch_id', None) else '全書')
            self.video_method.set('沿用各批影片' if getattr(page, 'movie', False) else '統一素材')
        self.sync_video_toolbar()
        self.app.sync_next_action_visibility()

    def is_video(self):
        return getattr(self.current, 'kind', None) == 'video' or bool(getattr(self.current, 'movie', False))

    def sync_video_toolbar(self):
        if not self.is_video():
            return
        expanded = not self.app.focus_mode
        self.files_button.configure(text='<' if expanded else '>')
        self.files_button.help_text = ('隱藏' if expanded else '顯示') + '文件列表'
        self.files_button.expanded = expanded
        self.files_button.grid_remove() if expanded else self.files_button.grid()
        batch = getattr(self.current, 'batch_id', None)
        self.scope_info.configure(text=self.app.flow._batch(batch)['name'] if batch else '全書')
        if batch:
            self.video_method_control.grid_remove()
        else:
            self.video_method_control.grid(row=0, column=4, padx=(8, 0))

    def toggle_files(self):
        self.app.toggle_focus()
        self.sync_video_toolbar()

    def video_switch_allowed(self):
        page = self.current
        return not (getattr(page, 'job', None) is not None or getattr(page, 'check_job', None) is not None
                    or self.busy_for(self.app.flow))

    def open_video(self):
        if not self.app.flow:
            return
        self.app.step = 4
        self.app.render_step()
        self.show('merge' if self.app.flow.state.get('total_video_method') == 'batch-videos' else 'video')

    def change_scope(self, event=None):
        if not self.video_switch_allowed():
            self.sync_video_selection()
            return
        if self.scope.get() == '本批' and self.app.batch_id:
            self.app.batch_video()
        else:
            self.open_video()

    def sync_video_selection(self):
        self.scope.set('本批' if getattr(self.current, 'batch_id', None) else '全書')
        self.video_method.set('沿用各批影片' if getattr(self.current, 'movie', False) else '統一素材')

    def change_video_method(self, event=None):
        if not self.video_switch_allowed():
            self.sync_video_selection()
            return
        from .workflow import ProjectError
        try:
            movie = self.video_method.get() == '沿用各批影片'
            self.app.flow.save_total_video_method('batch-videos' if movie else 'total-audio')
            self.show('merge' if movie else 'video')
        except ProjectError as error:
            self.sync_video_selection()
            self.app.notify(str(error), kind='error')

    def sync_chrome(self):
        app=self.app
        if app._closing or app.step!=4 or self.current is None:return
        from .desktop_shell import HeaderBand, ShellPresentation
        page=self.current
        join=getattr(page,'join_page',None)
        joining=join is not None and join.winfo_exists() and bool(join.winfo_manager())
        owner=join if joining else page
        audio=page is getattr(app,'narration_dialog',None)
        voice=hasattr(page,'workspace_layout')
        layout=getattr(owner,'workspace',None) if joining else getattr(page,'assembly_workspace',None)
        video=self.is_video()
        footer=getattr(owner,'shell_footer',None)
        bands=()
        if layout is not None and not getattr(owner,'movie',False):
            bands=(HeaderBand(owner,0,(layout.header,)),)
            footer=getattr(layout,'footer',getattr(layout,'actions',None))
        elif voice:
            bands=(HeaderBand(page,0,(page.sources_panel,)),)
            footer=page.voice_footer
        elif audio:
            bands=(HeaderBand(page,0,(page.toolbar,)),)
            footer=page.actions
        elif video:
            bands=(HeaderBand(self,1,(self.video_toolbar,)),)
        elif getattr(owner,'shell_header',None) is not None:
            bands=(HeaderBand(owner,0,(owner.shell_header,)),)
        routine=not app.status.full_text or app.status.full_text.startswith(
            ('已載入專案','已自動載入上次專案','草稿已暫存','所有書稿資料保存在本機。'))
        selected='video' if video else 'assembly' if layout is not None or getattr(page,'kind',None) in ('assembly','versions') else 'voice' if voice or page is self.service_page or getattr(page,'kind',None) in ('local-package','defaults') else 'narration'
        self.sync_video_toolbar()
        app.shell.present(ShellPresentation(
            page_id=getattr(owner,'page_id',type(owner).__name__)+('.batch' if getattr(page,'batch_id',None) else '.book'),
            owner=owner,root_content=self,bands=bands,footer=footer,production=True,navigation=selected,
            show_summary=voice or audio or not (layout is not None or video),
            show_message=not (layout is not None or voice or video) and (not audio or not routine),
            document_commands_enabled=not bool(joining and (getattr(owner,'job',None) or getattr(owner,'info_job',None))),
            collapse_documents_below=1050 if layout is not None else 0))
        for item in self.pages.values():
            if not item.winfo_exists():continue
            if hasattr(item,'assembly_workspace'):
                item.assembly_workspace.set_active(owner is item)
                child=getattr(item,'join_page',None)
                if child is not None and child.winfo_exists() and hasattr(child,'workspace'):
                    child.workspace.set_active(owner is child)
            if hasattr(item,'workspace_layout'):item.workspace_layout.set_active(owner is item)
        if audio:
            page.layout_actions();page.layout_status()
        self.refresh_task_banner()


    def sync_summary(self):
        if self.app.step==4:self.sync_chrome()


    def change_method(self, event=None):
        from .workflow import ProjectError
        page=self.current
        source=page if getattr(page,'kind',None)=='assembly' else self.assembly_drafts.get(id(self.app.flow))
        movie=self.method.get()=='合併既有批次影片'
        try:
            if page is not None and (getattr(page,'job',None) is not None or getattr(page,'check_job',None) is not None):
                raise ProjectError('請等待目前操作停止，再切換影片方式。')
            self.app.flow.save_total_video_method('batch-videos' if movie else 'total-audio')
            destination=self.show('merge' if movie else 'assembly')
            if source is not None and source.winfo_exists():
                destination.selected=list(source.selected)
                destination.pause.set(source.pause.get())
                destination.accepted_joins=set(source.accepted_joins)
                destination.render_rows()
        except ProjectError as error:
            self.app.notify(str(error),kind='error')
            if page is not None:self.method.set('合併既有批次影片' if getattr(page,'movie',False) else '總音訊製片')

    def show(self, kind):
        app = self.app
        audio_only = kind == 'audio_assembly'
        if audio_only:
            kind = 'assembly'
        key = (id(app.flow), None if kind in ('assembly', 'video', 'merge', 'versions') else app.batch_id, kind)
        page: Any = self.pages.get(key)
        if page is None or not page.winfo_exists():
            if kind == 'versions':
                from .output_versions_desktop import OutputVersionsPage
                page = OutputVersionsPage(app)
            elif kind in ('assembly', 'merge'):
                from .assembly_desktop import AssemblyPage
                page = AssemblyPage(app, movie=kind == 'merge')
            elif kind == 'video':
                from .total_video_desktop import TotalVideoPage
                page = TotalVideoPage(app)
            elif kind == 'batch_video':
                from .total_video_desktop import TotalVideoPage
                page = TotalVideoPage(app, app.batch_id)
            elif kind == 'voice':
                from .voice_desktop import VoiceDialog
                page = VoiceDialog(app)
            else:
                from .narration_desktop import NarrationDialog
                page = NarrationDialog(app)
            self.pages[key] = page
        app.voice_dialog = self.pages.get((id(app.flow), app.batch_id, 'voice'))
        app.narration_dialog = self.pages.get((id(app.flow), app.batch_id, 'narration'))
        origin = self.current
        can_return = getattr(origin, 'kind', None) in ('assembly', 'versions') or origin is app.narration_dialog and origin is not None
        if (getattr(page, 'kind', None) == 'video' or getattr(page, 'movie', False)) and can_return and not self.is_video():
            page.return_origin = self.current
        self.activate(page)
        if kind == 'voice':
            page.refresh_setting_sources()
        if kind == 'narration' and page.job is None:
            page.load_runs()
            page.load_result()
        if kind in ('assembly', 'merge'):
            page.recheck()
        if kind in ('video', 'batch_video'):
            page.recheck()
        if kind == 'versions':
            page.recheck()
        return page

    def return_from_video(self, page, fallback):
        origin = getattr(page, 'return_origin', None)
        if origin is not None and origin.winfo_exists() and getattr(origin, 'flow', None) is page.flow:
            self.activate(origin)
            if hasattr(origin, 'recheck'):
                origin.recheck()
        else:
            fallback()

    def show_versions(self):
        origin = self.current
        page = self.show('versions')
        if origin is not page:
            page.return_page = origin
        return page

    def manage_services(self, owner, *, profile_id=None):
        from .service_desktop import ServiceDialog
        if self.service_page is not None and self.service_page.winfo_exists():
            self.service_page.owner = owner
            self.service_page.flow = owner.flow
            self.service_page.on_return = self.app.voice_settings
            self.activate(self.service_page)
            self.service_page.request_profile(profile_id)
            return
        self.service_page = ServiceDialog(owner, parent=self.host, on_return=self.app.voice_settings, profile_id=profile_id)
        self.activate(self.service_page)

    def service_changes_busy(self):
        # Credentials are shared by all batches. Do not mutate them during a task.
        pages=[p for p in self.pages.values() if p.winfo_exists()]
        return any(getattr(p,'job',None) is not None for p in pages) or any(
            self.busy_for(p.flow) for p in pages if hasattr(p,'flow'))

    def refresh_services(self, identity=None, *, deleted=None):
        owner=self.service_page.owner if self.service_page is not None else None
        for key,page in self.pages.items():
            if key[2]!='voice' or not page.winfo_exists(): continue
            previous=page.service_ids.get(page.service.get())
            page.reload_services()
            if previous==deleted or (page is owner and identity!=previous):
                page.service.set(page.service_labels.get(identity or 'edge-tts','Edge-TTS'))
                page.change_service()
            elif previous in page.service_labels:
                page.service.set(page.service_labels[previous])
            if previous not in (identity,deleted) and page is not owner:
                continue
            page.stop()
            page.play_button.configure(state='disabled')
            page.result_info.configure(text='服務設定已變更；請重新試聽。')

    def manage_local_packages(self,owner):
        from .kokoro_desktop import PackagePage
        if self.package_page is None or not self.package_page.winfo_exists():
            self.package_page=PackagePage(owner)
        else:
            self.package_page.owner=owner;self.package_page.flow=owner.flow;self.package_page.refresh()
        self.activate(self.package_page)

    def hide(self):
        if self.current is not None and self.current.winfo_exists() and hasattr(self.current,'stop'):
            self.current.stop()


    def active_page(self):
        return next((p for k, p in self.pages.items() if k[2] in ('narration', 'assembly', 'merge', 'video', 'batch_video') and p.winfo_exists() and p.job is not None), None)

    def show_active(self):
        page = self.active_page()
        if page is None:
            page = next((p for p in self.pages.values() if getattr(p, 'edit_return', False)
                         and p.flow is self.app.flow and p.winfo_exists()), None)
        if page is None:
            return
        app = self.app
        if getattr(page, 'kind', None) in ('assembly', 'video') and not getattr(page, 'batch_id', None):
            if app.flow is not page.flow:
                if not app.may_leave():
                    return
                app.flow, app.batch_id = page.flow, next((b['id'] for b in page.flow.state['batches']), None)
                app.refresh()
            if getattr(page, 'movie', False):
                app.step = 4
                app.render_step()
                self.show('merge')
            else:
                (app.total_video if page.kind == 'video' else app.total_audio)()
            return
        if app.flow is not page.flow or app.batch_id != page.batch_id:
            if not app.may_leave():
                return
            app.flow, app.batch_id = page.flow, page.batch_id
            app.refresh()
        (app.batch_video if getattr(page, 'kind', None) == 'video' else app.narration)()

    def poll(self):
        self.timer = None
        self.refresh_task_banner()
        self.refresh_task_controls()
        self.timer = self.after(200, self.poll)

    def refresh_task_banner(self):
        page = self.active_page()
        visible = (page is not None and self.app.step == 4 and self.current is page
                   and page.flow is self.app.flow and page.winfo_ismapped())
        if page is not None and not visible:
            state = page.job.state
            batch = '全書製片' if getattr(page, 'kind', None) == 'video' and not getattr(page, 'batch_id', None) else '全書合併' if getattr(page, 'kind', None) == 'assembly' else next((b['name'] for b in page.flow.state['batches'] if b['id'] == page.batch_id), '原批次')
            outcome = {'failed':'失敗', 'cancelled':'已取消', 'completed':'正在保存結果', 'cancelling':'取消中'}.get(state.get('status'))
            self.task_summary.configure(text=f'背景任務 · {batch} · {outcome or state.get("phase", "製作中")} · 完成 {state.get("completed", 0)}/{state.get("total", 0)}')
            self.app.shell.show_task_banner(True)
        else:
            returning = next((p for p in self.pages.values() if getattr(p, 'edit_return', False)
                              and p.winfo_exists() and p.flow is self.app.flow), None)
            if page is None and returning is not None and self.app.step != 4:
                self.task_summary.configure(text='全書合併 · 接點檢查尚未完成')
                self.app.shell.show_task_banner(True)
            else:
                self.app.shell.show_task_banner(False)

    @staticmethod
    def busy_for(flow):
        from .production_lock import production_active
        from .workflow import ProjectError
        try:
            return production_active(flow.root / '.production.lock')
        except ProjectError:
            return True

    def refresh_task_controls(self):
        page = self.current
        if self.is_video():
            state = 'readonly' if self.video_switch_allowed() else 'disabled'
            self.scope_control.configure(state=state)
            self.video_method_control.configure(state=state)
        self.method_control.configure(state='disabled' if page is not None and (getattr(page,'job',None) is not None or getattr(page,'check_job',None) is not None or self.busy_for(page.flow)) else 'readonly')
        if page is not None and page.winfo_exists() and hasattr(page, 'set_production_busy'):
            page.set_production_busy(self.busy_for(page.flow))

    def shutdown(self):
        pages = list(self.pages.values())
        if self.package_page is not None:pages.insert(0,self.package_page)
        if self.service_page is not None:
            self.service_page.on_return = None
            pages.insert(0, self.service_page)
        for page in pages:
            if page.winfo_exists():
                # Repeated requests must not postpone a page's cleanup timer.
                if not getattr(page, 'closing', False) and page.close() is False:
                    return 'cancelled'
        if any(p.winfo_exists() for p in pages):
            return 'pending'
        return 'complete'
