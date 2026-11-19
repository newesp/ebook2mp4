"""v2 chrome ownership and measured manuscript layout regression contracts."""
import unittest
import json
from unittest.mock import patch
from tkinter import ttk

import test_unified_manuscript as unified


class ManuscriptShellTests(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app
    spin = unified.ManuscriptTests.spin

    def pdf_app(self):
        from test_pdf import pdf_bytes
        path = self.folder/'source.pdf'
        path.write_bytes(pdf_bytes(3))
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(path), 1, 3)
        self.assertTrue(job.wait(10))
        self.batch = self.flow.finish_pdf_extraction(job)
        root, app = self.app()
        self.spin(root, lambda: app.source_image is not None)
        return root, app

    def settle(self, root, app, size):
        root.state('normal')
        root.geometry(size)
        root.update()
        app.layout_workspace()
        root.update()

    def test_pdf_action_gaps_match_editor_and_survive_source_transitions(self):
        root, app = self.pdf_app()
        for size in ('1536x793', '1360x820', '1280x720', '1100x760', '900x640'):
            with self.subTest(size=size):
                self.settle(root, app, size)
                if size == '900x640':
                    app.narrow_source = True
                    app.adapt_source()
                app.render_source_page()
                self.spin(root, lambda: app.source_tools.image_future is None)
                self.settle(root, app, size)
                pairs = ((app.pdf_previous, app.page_entry), (app.page_total, app.pdf_next),
                         (app.pdf_next, app.zoom_control), (app.zoom_control, app.source_control))
                gaps = [b.winfo_rootx()-a.winfo_rootx()-a.winfo_width() for a,b in pairs]
                self.assertEqual(gaps, [4,4,4,4], 'PDF actions must match the editor toolbar gap')
                heights = [w.winfo_height() for w in (app.pdf_previous, app.page_entry, app.zoom_control, app.source_control)]
                self.assertLessEqual(max(heights)-min(heights), 2)
                self.assertLessEqual(app.source_control.winfo_rootx()+app.source_control.winfo_width(),
                                     app.source_frame.winfo_rootx()+app.source_frame.winfo_width())
        # TXT must release the hidden PDF controls; returning must restore gaps.
        txt = next(b['id'] for b in app.flow.state['batches'] if b['kind']=='txt')
        app.batch_id = txt
        app.refresh()
        root.update()
        self.assertFalse(app.pdf_previous.winfo_ismapped())
        self.assertTrue(app.source_control.winfo_ismapped())

    def test_shell_survives_tools_production_and_collapsing_without_losing_editor(self):
        root, app = self.app()
        self.settle(root, app, '1360x820')
        app.confirm_reading()
        shell = app.shell
        widgets = tuple(map(str, (shell.navigation, shell.documents, shell.workspace, shell.footer, app.editor)))
        app.editor.insert('end', '\n未保存人工稿。')
        root.update()
        app.editor.mark_set('insert', '2.3')
        app.editor.tag_add('sel', '1.0', '1.3')
        before = app.current_text
        app.show_versions()
        app.close_tools()
        app.confirm_reading()
        app.show_step(4)
        root.update()
        app.show_step(1)
        app.focus_button.invoke()
        self.settle(root, app, '1360x820')
        self.assertEqual(app.center.winfo_x(), 0)
        self.assertEqual(app.center.winfo_width(), app.body.winfo_width())
        self.assertEqual(tuple(map(str, (shell.navigation, shell.documents, shell.workspace, shell.footer, app.editor))), widgets)
        self.assertEqual(app.current_text, before)
        self.assertEqual(str(app.next_button.master), str(shell.footer.footer_actions))
        self.assertIs(app.batch_list.master,shell.documents.batch_view)

    def test_wide_collapsed_editor_toolbar_stays_inside_its_pane(self):
        from ebook2mp4.desktop import make_app
        from ebook2mp4.workflow import ProjectWorkflow
        from test_pdf import pdf_bytes
        source=self.folder/'auto.pdf'
        source.write_bytes(pdf_bytes(3))
        flow=ProjectWorkflow.create(self.folder/'auto-book','恢復收合書籍')
        job=flow.start_pdf_extraction(flow.inspect_pdf(source),1,3)
        self.assertTrue(job.wait(10))
        batch=flow.finish_pdf_extraction(job)
        flow.save_reading_manuscript(batch,'\n\n'.join(f'第 {i} 段。保留長文。' for i in range(400)))
        manifest=flow.state
        manifest['manuscript_view']=dict(list_collapsed=True,source_visible=True,source_ratio=.5)
        flow._commit(manifest,[])
        home=self.folder/'app-home'
        home.mkdir()
        (home/'session.json').write_text(json.dumps(dict(last_project=str(flow.root.resolve()))),encoding='utf-8')
        with patch.dict('os.environ',EBOOK2MP4_APP_HOME=str(home.resolve())):
            root,app=make_app(restore_last_project=True)
            self.addCleanup(lambda: app.close() if root.winfo_exists() else None)
            root.after(1000,root.quit)
            root.mainloop()
        controls=(app.source_toggle, app.edit_control, app.proof_control, app.version_control, app.save_button)
        end=app.right_stack.winfo_rootx()+app.right_stack.winfo_width()
        for control in controls:
            self.assertTrue(control.winfo_ismapped())
            self.assertGreaterEqual(control.winfo_width(),control.winfo_reqwidth()-2)
            self.assertGreaterEqual(control.winfo_rootx(),app.right_stack.winfo_rootx())
            self.assertGreaterEqual(control.winfo_rooty(),app.editor_nav.winfo_rooty())
            self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),app.editor.winfo_rooty(),
                (control.grid_info(),app.editor_actions.grid_info(),app.editor_nav.winfo_height()))
            self.assertLessEqual(control.winfo_rootx()+control.winfo_width(),end,
                (str(control),control.winfo_rootx(),end,app.editor_actions.grid_info()))
            ancestor=control.master
            while ancestor is not app.editor_frame:
                self.assertGreaterEqual(control.winfo_rootx(),ancestor.winfo_rootx())
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(),ancestor.winfo_rootx()+ancestor.winfo_width(),
                    (str(ancestor),ancestor.winfo_width(),ancestor.winfo_reqwidth()))
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),ancestor.winfo_rooty()+ancestor.winfo_height())
                ancestor=ancestor.master

    def test_action_replacement_removes_old_callback_and_busy_disables_current(self):
        from ebook2mp4.desktop_shell import ActionBar, ActionSpec, PagePresentation
        root, app = self.app()
        frame = ttk.Frame(root)
        bar = ActionBar(frame)
        calls = []
        bar.present(PagePresentation(1, 'A', '第一頁', (
            ActionSpec('first', '第一動作', 'primary', lambda: calls.append('A')),)))
        first = bar.buttons['first']
        dispatcher = first.cget('command')
        for _ in range(50):
            bar.present(PagePresentation(1, 'A', '更新狀態', (
                ActionSpec('first', '第一動作', 'primary', lambda: calls.append('A')),)))
        self.assertEqual(first.cget('command'), dispatcher, 'Status refresh must reuse its Tcl dispatcher')
        bar.present(PagePresentation(1, 'B', '第二頁', (
            ActionSpec('second', '第二動作', 'primary', lambda: calls.append('B')),)))
        first.invoke()
        bar.buttons['second'].invoke()
        self.assertEqual(calls, ['B'])
        bar.present(PagePresentation(1, 'B', '處理中', (
            ActionSpec('second', '第二動作', 'primary', lambda: calls.append('busy')),), busy=True))
        bar.buttons['second'].invoke()
        self.assertEqual(calls, ['B'])
        frame.destroy()

    def test_return_stays_left_and_busy_cancel_remains_available(self):
        from ebook2mp4.desktop_shell import ActionBar, ActionSpec, PagePresentation
        root, app = self.app()
        frame = ttk.Frame(root)
        frame.place(x=0, y=100, width=800, height=160)
        frame.columnconfigure(0, weight=1)
        bar = ActionBar(frame)
        calls = []
        bar.present(PagePresentation(1, '任務', '處理中', (
            ActionSpec('return', '返回', 'back', lambda: None),
            ActionSpec('cancel', '取消', 'primary', lambda: calls.append('cancel'), available_while_busy=True)), busy=True))
        root.update()
        back, cancel = bar.buttons['return'], bar.buttons['cancel']
        self.assertLess(back.winfo_rootx(), cancel.winfo_rootx())
        cancel.invoke()
        self.assertEqual(calls, ['cancel'])
        frame.destroy()


if __name__ == '__main__':
    unittest.main()
