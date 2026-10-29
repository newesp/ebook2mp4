"""History labels distinguish confirmed reading text from reload backups."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class ManuscriptTerminology(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        source = self.path / 'source.txt'
        source.write_bytes('原始文字。'.encode('utf-8'))
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.app.flow = ProjectWorkflow.create(self.path / 'book', '用詞測試')
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.root.update()

    def test_entry_names_and_empty_history_explain_two_document_kinds(self):
        self.assertEqual(self.app.history_action.cget('text'), '朗讀稿與重載備份')
        self.assertEqual(self.app.versions_button.cget('text'), '朗讀稿與重載備份')
        self.assertEqual(self.app.pages_button.cget('text'), 'PDF 原頁與文字對照')
        self.assertEqual(self.app.remove_pdf_button.cget('text'), '移除 PDF 批次')
        self.app.versions_button.invoke()
        self.root.update()
        self.assertIn('尚無已確認的朗讀稿或重載備份', self.app.status.history[-1])

    def test_history_keeps_readings_and_reload_backups_distinct_and_read_only(self):
        flow, batch = self.app.flow, self.app.batch_id
        reading = flow.confirm_reading(batch)
        external = self.path / 'external.txt'
        external.write_bytes('外部新校對稿。'.encode('utf-8'))
        backup = flow.reload_draft(batch, flow.inspect_txt(external),
                                   unsaved_text='重載前未存文字。', conflict='keep-copy')
        self.app.refresh()
        self.app.editor.insert('end', '目前未存編輯')
        self.root.update()
        pending = self.app.current_text
        self.app.versions_button.invoke()
        self.root.update()
        dialog = next(w for w in self.root.winfo_children()
                      if isinstance(w, tk.Toplevel) and w.title() == '朗讀稿與重載備份')
        widgets = list(descendants(dialog))
        selector = next(w for w in widgets if w.winfo_class() == 'TCombobox')
        labels = tuple(selector.cget('values'))
        self.assertTrue(labels[0].startswith('朗讀稿 ·'))
        self.assertTrue(labels[1].startswith('重載備份 ·'))
        delete = next(w for w in widgets if w.winfo_class() == 'TButton'
                      and w.cget('text') == '刪除所選朗讀稿')
        content = next(w for w in widgets if w.winfo_class() == 'Text')
        self.assertTrue(delete.instate(('disabled',)))
        self.assertEqual(content.get('1.0', 'end-1c'), '重載前未存文字。')
        self.assertEqual(str(content.cget('state')), 'disabled')
        self.assertTrue(any(w.winfo_class() == 'TLabel' and '重載前保留的未存校對文字' in w.cget('text')
                            for w in widgets))
        selector.current(0)
        selector.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertTrue(delete.instate(('!disabled',)))
        self.assertEqual(content.get('1.0', 'end-1c'), '原始文字。')
        self.assertTrue(any(w.winfo_class() == 'TLabel' and '已確認供朗讀的版本' in w.cget('text')
                            for w in widgets))
        dialog.destroy()
        self.assertEqual(self.app.current_text, pending)
        self.assertTrue(self.app.dirty)
        reopened = ProjectWorkflow.open(flow.root)
        self.assertEqual(reopened.reading_text(batch, reading['id']), '原始文字。')
        self.assertEqual(reopened.draft_copy_text(batch, backup), '重載前未存文字。')
