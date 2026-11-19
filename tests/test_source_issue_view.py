"""Source issue view keeps processing controls out of the issue task."""
import unittest
import test_unified_manuscript as unified


class SourceIssueViewTests(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app
    spin = unified.ManuscriptTests.spin

    def test_empty_issues_have_no_scroll_owner_after_processing(self):
        root, app = self.app()
        app.compare_pdf_pages()
        root.update()
        app.review_source_issues()
        root.update()
        self.assertTrue(app.source_tools.issue_empty.winfo_ismapped())
        self.assertFalse(app.source_tools.scroll.winfo_ismapped())

    def test_pdf_form_two_columns_fit_after_issue_transition(self):
        from test_v2_manuscript_shell import ManuscriptShellTests
        root, app = ManuscriptShellTests.pdf_app(self)
        root.state('normal')
        for size in ('1360x820', '1280x720', '900x640'):
            root.geometry(size)
            app.compare_pdf_pages()
            for _ in range(3):
                root.update()
                app.layout_workspace()
            source = app.source_tools
            self.assertEqual([int(f.grid_info()['column']) for f in source.pdf_field_groups], [0,1,0,1,0,1,0,1])
            self.assertEqual(source.scroll.canvas.yview(), (0.0,1.0))
            app.review_source_issues()
            root.update()
            self.assertTrue(source.issue_empty.winfo_ismapped())
            self.assertFalse(source.scroll.winfo_ismapped())
            app.close_tools()
            app.compare_pdf_pages()
            root.update()
            self.assertTrue(source.scroll.winfo_ismapped())
            self.assertFalse(source.issue_empty.winfo_ismapped())
            rotation = source.pdf_field_groups[6].grid_slaves(row=1)[0]
            button = source.ocr_button
            for value in ('winfo_rooty', 'winfo_width', 'winfo_height'):
                self.assertLessEqual(abs(getattr(rotation,value)()-getattr(button,value)()), 2, value)

    def test_issue_view_and_return_to_processing(self):
        self.flow.record_source_issues(self.batch, ['請檢查來源'])
        root, app = self.app()
        app.review_source_issues()
        root.update()
        source = app.source_tools
        self.assertTrue(source.issue_view)
        self.assertEqual(source.issue_selector.current(), 0)
        self.assertFalse(source.txt_fields.winfo_ismapped())
        self.assertFalse(source.run_button.winfo_ismapped())
        self.assertTrue(source.issue_frame.winfo_ismapped())
        self.assertEqual(app.inner_host.title.cget('text'), '來源異常')
        source.resolve('resolved')
        root.update()
        self.assertFalse(source.issue_frame.winfo_ismapped())
        self.assertEqual(source.detail.cget('text'), '來源異常已全部處理。')
        app.compare_pdf_pages()
        root.update()
        self.assertFalse(source.issue_view)
        self.assertTrue(source.txt_fields.winfo_ismapped())
        self.assertEqual(app.inner_host.title.cget('text'), '來源處理')
