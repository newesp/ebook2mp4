"""Behavioral checks for the approved workspace and its persisted output."""
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.manuscript import merge_candidate
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class ManuscriptTests(unittest.TestCase):
    def setUp(self):
        Path('.scratch/test-runs').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='.scratch/test-runs')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder/'source.txt'
        self.source.write_bytes('第一章。\n\nHello world.'.encode('utf-8'))
        self.flow = ProjectWorkflow.create(self.folder/'book', '測試書籍')
        self.batch = self.flow.import_txt(self.flow.inspect_txt(self.source))

    def app(self):
        root, app = make_app()
        app.flow, app.batch_id = self.flow, self.batch
        app.refresh()
        root.update()
        app.report = lambda error: app.status.configure(text=str(error))
        self.addCleanup(lambda: app.close() if root.winfo_exists() else None)
        return root, app

    def spin(self, root, predicate, seconds=8):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic() < deadline:
            root.update()
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_atomic_publication_exact_text_and_deduplication(self):
        text = '畫面人工全文\n\n第二段。'
        snapshot = self.flow.save_reading_manuscript(self.batch, text)
        opened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(opened.texts(self.batch)[1], text)
        self.assertEqual(opened.reading_text(self.batch), text)
        self.assertEqual(self.flow.save_reading_manuscript(self.batch, text)['id'], snapshot['id'])
        self.assertEqual(len(self.flow._batch(self.batch)['readings']), 1)

    def test_publication_failure_rolls_back_both_and_keeps_workspace(self):
        self.flow.save_workspace(self.batch, '人工修改')
        before = (self.flow.root/'project.json').read_bytes()
        atomic = self.flow._atomic
        def fail_manifest(path, data):
            if path.name == 'project.json':
                raise OSError('controlled disk failure')
            atomic(path, data)
        with patch.object(self.flow, '_atomic', side_effect=fail_manifest):
            with self.assertRaises(ProjectError):
                self.flow.save_reading_manuscript(self.batch, '人工修改')
        self.assertEqual((self.flow.root/'project.json').read_bytes(), before)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.workspace_state(self.batch)['text'], '人工修改')
        self.assertFalse(reopened._batch(self.batch).get('current_reading'))

    def test_source_anomaly_blocks_publication_until_explicit_resolution(self):
        self.flow.record_source_issues(self.batch, ['缺頁'])
        with self.assertRaisesRegex(ProjectError, '來源異常'):
            self.flow.save_reading_manuscript(self.batch, '全文')
        self.flow.resolve_source_issue(self.batch, 0, 'skipped')
        self.flow.save_reading_manuscript(self.batch, '全文')
        self.assertEqual(self.flow.reading_text(self.batch), '全文')

    def test_legacy_project_and_reading_survive_workspace_reopen(self):
        snapshot = self.flow.confirm_reading(self.batch)
        self.flow.save_workspace(self.batch, '草稿')
        opened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(opened.reading_text(self.batch, snapshot['id']), '第一章。\n\nHello world.')
        self.assertIsNone(opened._batch(self.batch)['current_reading'])
        self.assertEqual(opened.workspace_state(self.batch)['text'], '草稿')

    def test_manual_edit_publish_same_editor_and_two_navigation_steps(self):
        root, app = self.app()
        identity = str(app.editor)
        app.editor.insert('end', '\n人工修改。')
        root.update()
        self.assertEqual(len(app.steps), 2)
        with patch('ebook2mp4.desktop.messagebox.askyesno') as confirm:
            app.next_button.invoke()
            confirm.assert_not_called()
        self.assertEqual(app.flow.reading_text(self.batch), app.current_text)
        self.assertEqual(str(app.editor), identity)
        self.assertEqual(app.step, 1)
        self.assertEqual(app.reading_status.cget('text'), '已儲存，可朗讀')
        self.assertFalse([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])
        app.editor.insert('end', '再修改')
        root.update()
        self.assertFalse(app.reading_ready())
        self.assertTrue(app.steps[1].instate(['disabled']))

    def test_failed_ui_save_preserves_buffer_and_cannot_advance(self):
        root, app = self.app()
        app.editor.insert('end', '保留')
        root.update()
        text = app.current_text
        with patch('ebook2mp4.workflow.os.replace', side_effect=OSError()), patch.object(app, 'report'):
            self.assertFalse(app.confirm_reading())
        self.assertEqual(app.current_text, text)
        self.assertFalse(app.reading_ready())
        self.assertEqual(app.step, 1)

    def test_autosaved_workspace_reopens_without_reading_confirmation(self):
        root, app = self.app()
        app.editor.insert('end', '草稿')
        root.update()
        app.save()
        app.flow = ProjectWorkflow.open(app.flow.root)
        app.refresh()
        self.assertTrue(app.current_text.endswith('草稿'))
        self.assertFalse(app.reading_ready())

    def test_tool_switch_preserves_search_selection_and_editor(self):
        root, app = self.app()
        app.editor.mark_set('insert', '1.2')
        app.find_text.set('Hello')
        for index in (0, 1, 2, 0):
            app.open_tools(index)
            root.update()
            app.close_tools()
        self.assertEqual(app.editor.index('insert'), '1.2')
        self.assertEqual(app.find_text.get(), 'Hello')
        app.focus_search()
        app.find_next()
        self.assertEqual(app.editor.get('sel.first', 'sel.last'), 'Hello')

    def test_version_restore_previews_then_backs_up_current_draft(self):
        root, app = self.app()
        app.confirm_reading()
        original = app.current_text
        app.editor.insert('end', '新的人工稿')
        root.update()
        app.show_versions()
        app.version_selector.current(0)
        app.preview_version()
        self.assertTrue(app.current_text.endswith('新的人工稿'))
        app.restore_version()
        self.assertEqual(app.current_text, original)
        copies = app.flow._batch(self.batch)['draft_copies']
        self.assertTrue(app.flow.draft_copy_text(self.batch, copies[-1]['id']).endswith('新的人工稿'))
        self.assertFalse(app.reading_ready())

    def test_txt_reload_preview_and_backup_without_window(self):
        root, app = self.app()
        app.editor.insert('end', '現稿')
        root.update()
        external = self.folder/'external.txt'
        external.write_text('外部全文', encoding='utf-8')
        with patch('ebook2mp4.manuscript_source.filedialog.askopenfilename', return_value=str(external)):
            app.import_txt(reload=True)
        self.assertTrue(app.current_text.endswith('現稿'))
        app.source_tools.apply()
        self.assertEqual(app.current_text, '外部全文')
        self.assertFalse(app.reading_ready())
        self.assertFalse([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])

    def test_new_txt_import_does_not_send_ai_or_open_window(self):
        root, app = self.app()
        with patch('ebook2mp4.manuscript_source.filedialog.askopenfilename', return_value=str(self.source)), patch('ebook2mp4.gemini.generate') as network:
            app.import_txt()
            network.assert_not_called()
        self.assertEqual(len(app.flow.state['batches']), 2)
        self.assertFalse([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])

    def test_txt_preview_updates_commands_without_a_window_resize(self):
        root, app = self.app()
        root.state('normal')
        root.geometry('900x640')
        root.update()
        app.compare_pdf_pages()
        root.update()
        tools = app.source_tools
        saved = app.current_text
        encoding = tools.encoding.get()
        tools.load_txt()
        actions = app.inner_host.actions
        self.assertEqual(actions.visible_ids, {'source.apply', 'source.discard'})
        root.update()
        self.assertEqual(tools.preview.yview(), (0.0, 1.0))
        self.assertFalse(tools.preview_scroll.winfo_ismapped())

        actions.buttons['source.discard'].invoke()
        root.update()
        self.assertFalse(actions.visible_ids)
        self.assertFalse(tools.preview.winfo_ismapped())
        self.assertTrue(tools.txt_fields.winfo_ismapped())
        self.assertEqual(tools.encoding.get(), encoding)
        self.assertEqual(app.current_text, saved)
        self.assertNotIn('先檢查差異', app.inner_host.presentation.summary)

    def test_txt_preview_button_stays_mapped_during_a_layout_refresh(self):
        root, app = self.app()
        app.compare_pdf_pages()
        app.source_tools.load_txt()
        app.update_stats()
        root.update()
        button = app.inner_host.actions.buttons['source.discard']
        self.assertTrue(button.winfo_ismapped())
        button.event_generate('<Enter>', x=8, y=8)
        button.event_generate('<ButtonPress-1>', x=8, y=8)
        self.assertTrue(button.instate(['pressed']))
        app.layout_workspace()
        self.assertTrue(button.winfo_ismapped())
        button.event_generate('<ButtonRelease-1>', x=8, y=8)
        self.assertIsNone(app.source_tools.text_candidate)

    def test_settings_model_persisted_without_credentials(self):
        root, app = self.app()
        app.model.set('gemini-custom-v7')
        app.script.set('繁體')
        app.font_size.set('18')
        app.normalize_punctuation.set(False)
        app.save_manuscript_settings()
        app.flow = ProjectWorkflow.open(app.flow.root)
        app.refresh()
        self.assertEqual(app.model.get(), 'gemini-custom-v7')
        self.assertEqual(app.font_size.get(), '18')
        self.assertFalse(app.normalize_punctuation.get())
        self.assertNotIn('protected_key', (app.flow.root/'project.json').read_text(encoding='utf-8'))

    def test_full_ai_candidate_edit_publish_and_layout_retained(self):
        root, app = self.app()
        app.source_visible = True
        app.adapt_source()
        app.editor.mark_set('insert', '1.2')
        root.update()
        panes, page = app.panes.panes(), app.page_number.get()
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=lambda k,m,parts: dict(paragraphs=[p.replace('第一章', '序章') for p in parts], notes=[])), patch('ebook2mp4.desktop.messagebox.askyesno') as confirm:
            app.gemini_review()
            self.spin(root, lambda: app.workspace_job is None)
            confirm.assert_not_called()
        self.assertEqual(app.panes.panes(), panes)
        self.assertEqual(app.page_number.get(), page)
        self.assertEqual(app.editor.index('insert'), '1.2')
        self.assertTrue(app.current_text.startswith('序章'))
        self.assertTrue(app.editor.tag_ranges('ai_change'))
        self.assertEqual(app.flow.texts(self.batch)[1], '第一章。\n\nHello world.')
        app.editor.insert('end', '\n人工候選修改')
        root.update()
        self.assertTrue(app.confirm_reading())
        self.assertEqual(app.flow.reading_text(self.batch), app.current_text)

    def test_cancelled_late_ai_output_keeps_original_and_can_resume(self):
        root, app = self.app()
        started, release = threading.Event(), threading.Event()
        def generate(*args):
            started.set()
            release.wait(4)
            return dict(paragraphs=['晚到錯誤']*len(args[2]), notes=[])
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=generate):
            before = app.current_text
            app.gemini_review()
            self.assertTrue(started.wait(2))
            app.cancel_workspace_job()
            release.set()
            self.spin(root, lambda: app.workspace_job is None)
        self.assertEqual(app.current_text, before)
        self.assertTrue(app.next_button.instate(['disabled']))
        app.keep_partial()
        self.assertTrue(app.confirm_reading())
        self.assertTrue(app.flow._batch(self.batch)['readings'][-1]['partial_ai'])

    def test_stale_ai_never_overwrites_later_manual_text(self):
        root, app = self.app()
        release = threading.Event()
        def generate(k,m,parts):
            release.wait(4)
            return dict(paragraphs=['候選']*len(parts), notes=[])
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=generate):
            app.gemini_review()
            app.set_editor('後來人工內容')
            release.set()
            self.spin(root, lambda: app.workspace_job is None)
        self.assertEqual(app.current_text, '後來人工內容')

    def test_merge_retry_preserves_human_edits(self):
        merged, conflicts = merge_candidate('A first. B second.', 'A first. B fixed.', 'A manual. B second.')
        self.assertEqual(merged, 'A manual. B fixed.')
        self.assertEqual(conflicts, 0)
        merged, conflicts = merge_candidate('abcdef', 'abXXef', 'abYYef')
        self.assertEqual(merged, 'abYYef')
        self.assertEqual(conflicts, 1)

    def test_partial_ai_reopen_resume_only_missing_and_preserve_candidate_edits(self):
        text = '\n\n'.join(c*3500+'。' for c in '甲乙丙')
        self.flow.save_draft(self.batch, text)
        root, app = self.app()
        results = [dict(paragraphs=['甲'*3500+'！'], notes=[]),
                   ProjectError('controlled failure'), dict(paragraphs=['丙'*3500+'！'], notes=[])]
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=results):
            app.gemini_review()
            self.spin(root, lambda: app.workspace_job is None, 15)
        self.assertTrue(app.next_button.instate(['disabled']))
        app.editor.insert('1.0', '人工補充。')
        root.update()
        app.save()
        app.flow = ProjectWorkflow.open(app.flow.root)
        app.refresh()
        self.assertTrue(app.current_text.startswith('人工補充。'))
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['乙'*3500+'！'], notes=[])) as request:
            app.retry_workspace()
            self.spin(root, lambda: app.workspace_job is None, 15)
            self.assertEqual(request.call_count, 1)
        self.assertTrue(app.current_text.startswith('人工補充。'))
        self.assertIn('乙'*3500+'！', app.current_text)
        self.assertTrue(app.confirm_reading())

    def test_ai_commit_failure_retries_without_new_network_request(self):
        root, app = self.app()
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=lambda k,m,p: dict(paragraphs=p,notes=[])) as network:
            app.gemini_review()
            self.assertTrue(app.workspace_job.wait(4))
            with patch.object(app.flow, '_commit', side_effect=ProjectError('controlled storage failure')):
                root.update()
                time.sleep(.12)
                root.update()
                self.assertIsNotNone(app.workspace_job)
                self.assertFalse(app.reading_ready())
            self.spin(root, lambda: app.workspace_job is None)
            self.assertEqual(network.call_count, 1)

    def test_pdf_ai_preserves_physical_page_and_column_width(self):
        from test_pdf import pdf_bytes
        path = self.folder/'compare.pdf'
        path.write_bytes(pdf_bytes(3))
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(path), 1, 3)
        job.wait(5)
        self.batch = self.flow.finish_pdf_extraction(job)
        root, app = self.app()
        root.state('normal')
        root.geometry('1400x820')
        root.update()
        if not app.source_visible:
            app.toggle_source()
        app.page_number.set('2')
        app.render_source_page()
        self.spin(root, lambda: app.source_tools.image_future is None)
        app.render_source_page()
        self.spin(root, lambda: app.source_tools.image_future is None)
        app.panes.sashpos(0, 380)
        root.update()
        before = app.panes.sashpos(0)
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=lambda k,m,p: dict(paragraphs=[s.replace('original','corrected') for s in p],notes=[])):
            app.gemini_review()
            self.spin(root, lambda: app.workspace_job is None)
        self.assertEqual(app.page_number.get(), '2')
        self.assertEqual(app.panes.sashpos(0), before)
        self.assertTrue(app.image_canvas.find_all())


if __name__ == '__main__':
    unittest.main()
