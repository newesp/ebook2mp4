"""Compact format selection and resumable output results in the assembly page."""
import tkinter as tk
from functools import partial
from copy import deepcopy
from tkinter import ttk

from .workflow import ProjectError

NAMES = dict(ready='準備', running='執行中', completed='完成', missing='缺項',
             failed='失敗', cancelled='已取消', stale='待更新')
OVERALL = dict(completed='全部要求已完成', partial='部分完成', failed='未完成 · 有格式失敗',
               cancelled='未完成 · 已取消', incomplete='尚未完成', running='處理中')


class OutputControls:
    def __init__(self, page):
        self.page = page
        self.plan = None
        self.frame = frame = ttk.Frame(page.main)
        frame.grid(row=5, column=0, sticky='ew', pady=(2, 4))
        ttk.Label(frame, text='要求輸出').pack(side='left')
        selected = page.flow.output_formats()
        self.values = {k: tk.BooleanVar(value=k in selected) for k in ('mp3', 'mp4')}
        self.checks = []
        for k, label in (('mp3', '總 MP3／SRT'), ('mp4', '總 MP4／SRT')):
            check = ttk.Checkbutton(frame, text=label, variable=self.values[k], command=self.changed)
            check.pack(side='left', padx=8)
            self.checks.append(check)
        self.saved = ttk.Label(frame, text='選擇已儲存')
        self.saved.pack(side='right')
        self.results = results = ttk.Frame(page.main)
        results.grid(row=6, column=0, sticky='ew', pady=(0, 4))
        results.columnconfigure(2, weight=1)
        self.labels = {}
        for i, k in enumerate(('mp3', 'mp4')):
            name = ttk.Label(results, text='總 '+k.upper()+'／SRT', width=15)
            status = ttk.Label(results, text='檢查中', width=9)
            reason = ttk.Label(results, text='', width=1)
            action = ttk.Button(results, text='查看詳情 ▸', command=partial(self.open, k))
            for column, widget in enumerate((name, status, reason, action)):
                widget.grid(row=i, column=column, sticky='ew', padx=(0, 6), pady=2)
            self.labels[k] = (name, status, reason, action)
        self.summary = ttk.Label(page.main, text='正在檢查輸出…', style='Heading.TLabel')
        self.summary.grid(row=7, column=0, sticky='ew')
        # Existing status and controls retain their callbacks and accessibility.
        page.status.grid_configure(row=8)
        self.actions = page.start_button.master
        page.result_info.master.grid_remove()
        page.result_info.grid_remove()

    def changed(self):
        page = self.page
        formats = [k for k, v in self.values.items() if v.get()]
        if not formats:
            self.saved.configure(text='請至少選一種格式')
            self.refresh()
            return
        try:
            page.flow.save_output_formats(formats)
            self.saved.configure(text='選擇已儲存')
            page.recheck()
        except (ProjectError, OSError) as error:
            page.status.configure(text=str(error))
        self.refresh()

    def open(self, kind):
        page = self.page
        if kind == 'mp4' and self.plan and self.plan['rows'][kind]['status'] == 'missing':
            if not page.movie:
                page.app.total_video()
                return
            missing = self.plan['rows'][kind].get('missing', [])
            for row in page.rows:
                if any(m.startswith(row['name']+'：') for m in missing):
                    page.table.selection_set(row['batch_id'])
                    page.fix_source()
                    return
        if self.plan and self.plan['rows'][kind]['status'] != 'completed':
            row = self.plan['rows'][kind]
            if not page.info_open:
                page.toggle_info()
            page.info_text.configure(state='normal')
            page.info_text.delete('1.0', 'end')
            page.info_text.insert('1.0', '總 '+kind.upper()+'／SRT · '+NAMES[row['status']]+'\n\n'+
                (row['reason'] or '來源齊全，可開始製作。')+'\n\n成功成品與同版 SRT 保留。只重試未完成輸出。')
            page.info_text.configure(state='disabled')
            return
        versions = page.app.production.show_versions()
        route = 'audio' if kind == 'mp3' else 'batch-videos' if page.movie else 'total-audio'
        versions.requested_route = route

    def refresh(self):
        page = self.page
        busy = page.job is not None or page.check_job is not None or page.production_busy
        formats = [k for k, v in self.values.items() if v.get()]
        workspace = page.app.production
        for check in self.checks:
            check.configure(state='disabled' if busy else 'normal')
        plan = self.plan
        if plan is None:
            return
        from .outputs import OutputJob
        active = isinstance(page.job, OutputJob)
        report = page.job.state if active else None
        rows = deepcopy(report['formats'] if report and report['formats'] else plan['rows'])
        shared = page.flow.assembly_settings()
        dirty = page.selected != [s['batch_id'] for s in shared['sources']]
        pause_valid = True
        try:
            dirty |= page.pause_ms() != shared['pause_ms']
        except ProjectError:
            pause_valid = False
        resolution_dirty = page.movie and page.resolution.get() != page.flow.state.get('video_merge_resolution', '1080p')
        for k, row in rows.items():
            if row['status'] == 'completed' and (dirty or k == 'mp4' and resolution_dirty):
                row.update(status='stale', reason='設定尚未儲存，製作時更新；上一版保留。')
        for k, widgets in self.labels.items():
            visible = k in formats or k == 'mp3' and 'mp4' in formats and not page.movie and rows[k]['status'] != 'completed'
            for widget in widgets:
                if visible:
                    widget.grid()
                else:
                    widget.grid_remove()
            name, status_widget, reason, action = widgets
            row = rows[k]
            name.configure(text='前置總音訊' if k == 'mp3' and k not in formats else '總 '+k.upper()+'／SRT')
            status_widget.configure(text=NAMES.get(row['status'], row['status']))
            reason.configure(text=row.get('reason', '').replace('\n', '；') or (
                '先準備總音訊，再製片' if k == 'mp4' and plan['needs_audio'] else '來源齊全，可製作'))
            action.configure(text='成品操作 ▸' if row['status'] == 'completed' else '補齊缺項 ▸' if row['status'] == 'missing' else '查看詳情 ▸',
                             state='disabled' if busy else 'normal')
        from .outputs import overall
        n = sum(rows[k]['status'] == 'completed' for k in formats)
        status = 'running' if active and not page.job.closed else overall(formats, rows) if formats else 'incomplete'
        self.summary.configure(text=(OVERALL[status]+f' · {n}／{len(formats)} 個要求格式完成') if formats else '請至少選一種輸出格式')
        can_run = bool(formats) and any(rows[k]['status'] not in ('completed', 'missing') for k in formats)
        if (dirty or resolution_dirty) and page.selected:
            can_run = True
        can_run = can_run and pause_valid
        page.video_button.grid_remove()
        page.start_button.grid()
        pending = active and page.job.publish_pending
        page.start_button.configure(state='normal' if pending or not busy and can_run else 'disabled', text=(
            '重試保存' if pending else '製作中…' if active else '輸出均已完成' if formats and n == len(formats) else '先製作可用的 MP3 →' if 'mp3' in formats and 'mp4' in formats and rows['mp4']['status'] == 'missing' and rows['mp3']['status'] != 'completed'
            else '只重試未完成輸出 →' if n or any(rows[k]['status'] in ('failed', 'cancelled', 'stale') for k in formats)
            else '製作所選輸出 →'))
        # Material selection must also be reachable before a total MP3 exists.
        page.video_step.configure(state='normal' if not busy and not page.movie and 'mp4' in formats else 'disabled')
        page.versions_button.configure(state='disabled' if busy else 'normal')

    def poll(self):
        page = self.page
        job = page.job
        state = job.state
        if not job.wait(0):
            page.status.configure(text=(state.get('error', '')+' 請按重試保存，或取消以捨棄本次未保存結果。')
                if job.publish_pending else '取消中，正在釋放檔案…' if job.cancelled else state['phase'])
            page.progress.configure(maximum=max(1, state['total']), value=state.get('completed', 0))
            self.refresh()
            page.schedule()
            return
        page.flow.finish_outputs(job)
        page.job = None
        page.production_busy = page.app.production.busy_for(page.flow)
        page.last_status = state['status']
        page.status.configure(text=OVERALL.get(state['status'], '未完成')+'。'+state.get('error', '')+' 成功成品保留。')
        if page.closing:
            page.release()
        else:
            page.recheck()
