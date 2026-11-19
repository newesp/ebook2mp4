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

    def test_version_entry_and_empty_state_stay_in_workspace(self):
        self.assertEqual(self.app.history_action.cget('text'), '版本記錄')
        self.app.show_versions()
        self.assertEqual(self.app.version_selector.get(), '尚無版本')
        self.assertTrue(self.app.restore_version_button.instate(['disabled']))
        self.assertEqual(str(self.app.version_diff.cget('state')), 'disabled')

    def test_reading_and_backup_preview_preserves_current_editor(self):
        flow, batch = self.app.flow, self.app.batch_id
        flow.confirm_reading(batch)
        external = self.path/'external.txt'
        external.write_bytes('外部新校對稿。'.encode('utf-8'))
        flow.reload_draft(batch, flow.inspect_txt(external), unsaved_text='重載前未存文字。', conflict='keep-copy')
        self.app.refresh()
        self.app.editor.insert('end', '目前未存編輯')
        self.root.update()
        pending = self.app.current_text
        self.app.show_versions()
        self.assertTrue(self.app.version_labels[0].startswith('朗讀稿'))
        self.assertIn('重載備份', self.app.version_labels[1])
        self.assertEqual(str(self.app.version_diff.cget('state')), 'disabled')
        self.assertTrue(self.app.delete_version_button.instate(['disabled']))
        self.app.version_selector.current(0)
        self.app.preview_version()
        self.assertFalse(self.app.delete_version_button.instate(['disabled']))
        self.assertEqual(self.app.current_text, pending)
