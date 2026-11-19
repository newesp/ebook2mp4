"""Runtime contracts for the accepted v6 mock and its relocated capabilities."""
from pathlib import Path
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

import test_unified_manuscript as unified


class ManuscriptV6(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app
    spin = unified.ManuscriptTests.spin

    def settle(self, root, app):
        root.update()
        app.layout_workspace()
        root.update()

    def wide(self):
        root, app = self.app()
        root.state('normal')
        root.geometry('1500x850')
        self.settle(root, app)
        return root, app

    def test_collapsed_list_releases_track_and_ratio_survives_navigation(self):
        root, app = self.wide()
        self.assertEqual(len(app.panes.panes()), 2)
        self.assertLessEqual(abs(app.source_frame.winfo_width()-app.right_stack.winfo_width()), 2)
        selection = app.batch_list.selection()
        app.focus_button.invoke()
        self.settle(root, app)
        self.assertEqual(app.center.winfo_x(), 0)
        self.assertEqual(app.center.winfo_width(), app.body.winfo_width())
        self.assertLessEqual(abs(app.source_frame.winfo_width()-app.right_stack.winfo_width()), 2)
        app.panes.sashpos(0, 520)
        app.remember_source_sash()
        ratio = app.source_sash
        app.open_tools(1)
        app.tool_reopen.invoke()
        app.close_tools()
        self.settle(root, app)
        self.assertEqual(app.batch_list.selection(), selection)
        self.assertAlmostEqual(app.source_sash, ratio)
        self.assertLessEqual(abs(app.panes.sashpos(0)/(app.panes.winfo_width()-5)-ratio), .01)

    def test_reopen_list_with_hidden_source_and_narrow_window(self):
        root, app = self.wide()
        app.source_toggle.invoke()
        app.focus_button.invoke()
        root.geometry('900x640')
        self.settle(root, app)
        self.assertTrue(app.editor_reopen.winfo_ismapped())
        app.editor_reopen.invoke()
        self.settle(root, app)
        self.assertTrue(app.left_panel.winfo_ismapped())
        self.assertTrue(app.next_button.winfo_ismapped())
        self.assertTrue(app.editor.winfo_ismapped())

    def test_three_content_edges_align_and_controls_match_height(self):
        root, app = self.wide()
        ys = [w.winfo_rooty() for w in (app.source, app.editor, app.batch_list)]
        self.assertLessEqual(max(ys)-min(ys), 2)
        app.focus_search()
        self.settle(root, app)
        heights = [w.winfo_height() for w in (app.find_entry, app.find_button)]
        self.assertLessEqual(max(heights)-min(heights), 2, heights)

    def test_restored_comparison_reflows_groups_without_clipping(self):
        root, app = self.wide()
        root.geometry('1100x760')
        self.settle(root, app)
        self.assertEqual(len(app.panes.panes()), 2)
        for control in (app.source_toggle, app.edit_control, app.proof_control, app.version_control, app.save_button):
            self.assertTrue(control.winfo_ismapped())
            self.assertLessEqual(control.winfo_rootx()+control.winfo_width(), app.editor_frame.winfo_rootx()+app.editor_frame.winfo_width())
        ys = [w.winfo_rooty() for w in (app.source, app.editor, app.batch_list)]
        self.assertLessEqual(max(ys)-min(ys), 2)

    def test_long_version_diff_owns_scroll_and_editor_state_returns(self):
        root, app = self.wide()
        text = '\n'.join(f'第 {i} 行。原稿與文稿比較。' for i in range(500))
        app.set_editor(text)
        app.confirm_reading()
        app.set_editor(text.replace('原稿', '人工稿'))
        root.update()
        app.editor.mark_set('insert', '250.3')
        app.editor.tag_add('sel', '250.0', '250.5')
        app.editor.yview_moveto(.4)
        root.update()
        before = (app.current_text, app.editor.index('insert'), app.editor.yview()[0], app.editor.get('sel.first', 'sel.last'))
        app.show_versions()
        root.update()
        bounds = [(w.winfo_rooty(), w.winfo_height()) for w in (app.inner_host.back, app.inner_host.actions.buttons['versions.restore'], app.inner_host.title)]
        app.version_diff.yview_moveto(1)
        root.update()
        self.assertEqual(app.version_diff.yview()[1], 1)
        self.assertEqual(bounds, [(w.winfo_rooty(), w.winfo_height()) for w in (app.inner_host.back, app.inner_host.actions.buttons['versions.restore'], app.inner_host.title)])
        app.version_diff.yview_moveto(0)
        self.assertEqual(app.version_diff.yview()[0], 0)
        app.inner_host.back.invoke()
        root.update()
        self.assertEqual((app.current_text, app.editor.index('insert'), app.editor.get('sel.first', 'sel.last')), (before[0], before[1], before[3]))
        self.assertAlmostEqual(app.editor.yview()[0], before[2], places=2)

    def test_search_replace_export_reload_cleanup_new_edit_menu(self):
        root, app = self.wide()
        app.edit_menu.invoke(0)
        app.find_text.set('Hello')
        app.replace_text.set('Goodbye')
        app.replace_all_button.invoke()
        root.update()
        self.assertIn('Goodbye', app.current_text)
        app.undo_button.invoke()
        root.update()
        self.assertIn('Hello', app.current_text)
        output = self.folder/'output.txt'
        with patch('ebook2mp4.desktop.filedialog.asksaveasfilename', return_value=str(output)):
            app.export_button.invoke()
        self.assertEqual(output.read_text(encoding='utf-8'), app.current_text)
        app.cleanup_button.invoke()
        self.assertEqual(app.active_tool, 3)
        self.assertTrue(app.cleanup_preview.empty.winfo_manager())
        self.assertFalse(app.cleanup_preview.apply())
        app.close_tools()
        external = self.folder/'big5.txt'
        external.write_bytes('外部繁體文稿。'.encode('cp950'))
        with patch('ebook2mp4.manuscript_source.filedialog.askopenfilename', return_value=str(external)):
            app.reload_button.invoke()
        app.source_tools.encoding.set('CP950')
        app.source_tools.load_txt()
        root.update()
        self.assertEqual(app.source_tools.text_candidate, '外部繁體文稿。')
        app.source_tools.apply_button.invoke()
        self.assertEqual(app.current_text, '外部繁體文稿。')
        self.assertTrue(app.flow._batch(app.batch_id)['draft_copies'])

    def test_proof_menu_real_candidate_diff_restore_and_discard(self):
        root, app = self.wide()
        before = app.current_text
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=lambda k,m,p: dict(paragraphs=[s.replace('Hello', 'Fixed') for s in p],notes=[])):
            app.proof_menu.invoke(0)
            self.spin(root, lambda: app.workspace_job is None)
        self.assertIn('Fixed', app.current_text)
        app.diff_action.invoke()
        self.assertFalse(app.editor.tag_ranges('ai_change'))
        app.diff_action.invoke()
        self.assertTrue(app.editor.tag_ranges('ai_change'))
        app.editor.mark_set('insert', app.editor.search('Fixed', '1.0'))
        app.restore_change_action.invoke()
        self.assertEqual(app.current_text, before)
        app.editor.insert('end', '候選人工修改')
        root.update()
        app.discard_action.invoke()
        self.assertEqual(app.current_text, before)
        copies = app.flow._batch(app.batch_id)['draft_copies']
        self.assertTrue(app.flow.draft_copy_text(app.batch_id, copies[-1]['id']).endswith('候選人工修改'))
        app.version_menu.invoke(1)
        self.assertTrue(any('AI 候選' in x for x in app.version_labels))

    def test_pdf_source_open_missing_zoom_rotate_and_region_coordinates(self):
        from test_pdf import pdf_bytes
        source = self.folder/'source.pdf'
        source.write_bytes(pdf_bytes(3))
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(source), 1, 3)
        self.assertTrue(job.wait(8))
        self.batch = self.flow.finish_pdf_extraction(job)
        root, app = self.wide()
        self.spin(root, lambda: app.source_tools.image_future is None)
        with patch('os.startfile') as open_file:
            app.open_pdf_action.invoke()
            open_file.assert_called_once()
            self.assertTrue(Path(open_file.call_args.args[0]).is_file())
        with patch.object(app.flow, 'pdf_source_preview', side_effect=ProjectError('來源檔不存在')):
            app.open_pdf_action.invoke()
        self.assertIn('目前文稿保留', app.status.cget('text'))
        app.source_zoom.set('150%')
        app.draw_source_image()
        root.update()
        self.assertGreater(app.display_image.width(), app.image_canvas.winfo_width())
        app.source_process_action.invoke()
        root.update()
        app.source_tools.rotation.set('90')
        app.source_tools.render_page()
        self.spin(root, lambda: app.source_tools.image_future is None)
        app.source_tools.scope.set('框選區域')
        app.source_tools.scope_changed()
        self.spin(root, lambda: app.source_tools.image_future is None)
        root.update()
        app.draw_source_image()
        canvas = app.source_tools.page_canvas
        self.assertTrue(canvas.winfo_ismapped())
        self.assertTrue(app.source_tools.region_text.winfo_ismapped())
        app.begin_source_region(SimpleNamespace(widget=canvas,x=20,y=20))
        app.end_source_region(SimpleNamespace(widget=canvas,x=100,y=100))
        self.assertEqual(len(app.source_selection), 4)
        self.assertTrue(all(0 <= n <= 1 for n in app.source_selection))

    def test_pdf_reextract_preview_and_region_retry_keep_original_manuscript(self):
        from test_pdf import pdf_bytes
        source = self.folder/'retry.pdf'
        source.write_bytes(pdf_bytes(2))
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(source), 1, 2)
        self.assertTrue(job.wait(8))
        self.batch = self.flow.finish_pdf_extraction(job)
        self.flow.save_draft(self.batch, '人工稿必須保留。')
        root, app = self.wide()
        original_batch = app.batch_id
        app.source_process_action.invoke()
        tools = app.source_tools
        tools.run_button.invoke()
        self.spin(root, lambda: app.source_pending is not None)
        self.assertEqual(app.current_text, '人工稿必須保留。')
        root.update()
        self.assertTrue(tools.preview.winfo_ismapped())
        self.assertFalse(tools.scroll.winfo_ismapped())
        tools.apply_button.invoke()
        self.assertNotEqual(app.batch_id, original_batch)
        self.assertEqual(app.flow.texts(original_batch)[1], '人工稿必須保留。')
        app.compare_pdf_pages()
        self.spin(root, lambda: tools.image_future is None)
        tools.scope.set('框選區域')
        tools.scope_changed()
        app.source_selection = (0., 0., .5, .5)
        tools.region_text.tag_add('sel', '1.0', '1.7')
        tools.rotation.set('90')
        with patch('ebook2mp4.ocr.model_info', return_value=dict(ready=True,codes='eng',engine_error='')), patch('ebook2mp4.ocr.recognize_page', return_value=dict(text='Corrected',confidence=95)):
            tools.run_button.invoke()
            self.spin(root, lambda: app.source_pending is not None)
        self.assertIn('Corrected', tools.text_candidate)
        self.assertEqual(app.source_pending.rotation, 90)
        tools.show_region()
        root.update()
        self.assertTrue(tools.region_text.winfo_ismapped())
        tools.show_form()
        root.update()
        self.assertTrue(tools.scroll.winfo_ismapped())
        tools.discard()
        self.assertIsNone(app.source_pending)


from ebook2mp4.workflow import ProjectError
