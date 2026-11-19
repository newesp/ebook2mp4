"""Source tasks supply presentation; the shared host owns navigation/actions."""
from tkinter import ttk
from .desktop_shell import ActionSpec, PagePresentation


class SourcePage(ttk.Frame):
    page_id = 'manuscript.source'

    def __init__(self, app, host):
        super().__init__(host.content, padding=(20, 10))
        self.app, self.host = app, host

    def describe(self):
        t, app = self.tools, self.app
        actions = [ActionSpec('source.back', '← 返回文稿', 'back', app.close_tools)]
        if app.root.winfo_width() < 1100 and t.has_pdf_page():
            actions.append(ActionSpec('source.view', '顯示資訊' if t.page_focus else '顯示原頁', 'secondary', t.toggle_page_view))
        if t.issue_view:
            title = '來源異常'
            if t.issues:
                actions.extend((ActionSpec('source.resolve', '已處理', 'primary', lambda: t.resolve('resolved')),
                                ActionSpec('source.skip', '明確略過', 'secondary', lambda: t.resolve('skipped'))))
        else:
            title = '來源處理'
            if t.preview_actions.winfo_manager():
                actions.extend((ActionSpec('source.discard', '放棄預覽', 'secondary', t.discard),
                                ActionSpec('source.apply', '套用預覽', 'primary', t.apply,
                                           enabled=not t.apply_button.instate(['disabled']))))
                if app.source_pending:
                    actions.append(ActionSpec('source.refine', '保留選擇，繼續修正', 'secondary', t.continue_refining))
            elif t.run_button.winfo_manager():
                actions.append(ActionSpec('source.extract', t.run_button.cget('text'), 'primary', t.extract,
                                          enabled=not bool(app.source_pending)))
                if t.scope.get() == '框選區域':
                    actions.extend((ActionSpec('source.form', '處理設定', 'secondary', t.show_form),
                                    ActionSpec('source.region', '框選文字', 'secondary', t.show_region)))
        t.footer.grid_remove()
        t.detail.grid_remove()
        # Keep preview visibility as state, but let the host own its commands.
        for child in t.preview_actions.winfo_children():
            child.pack_forget()
        for child in t.issue_frame.grid_slaves(row=1):
            child.grid_remove()
        batch = app.flow._batch(app.batch_id) if app.flow and app.batch_id else None
        context = '目前文件 · ' + batch['name'] if batch else '來源匯入'
        return PagePresentation(1, title, t.detail.cget('text'), tuple(actions),
                                busy=bool(app.workspace_busy)), context
