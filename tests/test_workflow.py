import errno
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class ProjectJourney(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='書籍 T01 ', dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '原稿（第一章）.txt'
        self.text = '第一章：風與樹\r\n\r\nHello, world! 繁體／简体。\r\n3.14 與 U.S.A.\r\n'
        self.source.write_bytes(self.text.encode('utf-8'))

    def imported(self, folder='書籍 專案'):
        flow = ProjectWorkflow.create(self.root / folder, '風與樹')
        preview = flow.inspect_txt(self.source)
        batch = flow.import_txt(preview)
        return flow, batch

    def test_utf8_and_bom_create_import_edit_save_reopen_move(self):
        for bom in (b'', b'\xef\xbb\xbf'):
            with self.subTest(bom=bom):
                data = bom + self.text.encode('utf-8')
                self.source.write_bytes(data)
                flow = ProjectWorkflow.create(self.root / f'專案{len(bom)}', '測試書籍')
                preview = flow.inspect_txt(self.source)
                self.assertEqual(preview.text, self.text)
                self.assertEqual(preview.sha256, hashlib.sha256(data).hexdigest())
                info = flow.import_requirements(preview)
                self.assertEqual(info['source_copy_bytes'], len(data))
                self.assertEqual(info['project_location'], str(flow.root))
                self.assertGreater(info['required_bytes'], len(data))
                batch = flow.import_txt(preview)
                edited = self.text + '\n校對後的結尾。'
                flow.save_draft(batch, edited)
                reopened = ProjectWorkflow.open(flow.root / 'project.json')
                self.assertEqual(reopened.texts(batch), (self.text, edited))
                self.assertEqual(reopened.state['batches'][0]['revision'], 2)
                self.assertEqual(self.source.read_bytes(), data)
                state = reopened.state
                self.assertEqual(state['format_version'], 1)
                for key in ('source', 'draft'):
                    ref = state['batches'][0][key]
                    self.assertFalse(Path(ref['path']).is_absolute())
                    self.assertEqual(hashlib.sha256((flow.root / ref['path']).read_bytes()).hexdigest(), ref['sha256'])
                self.assertNotIn('page', json.dumps(state))
                relocated = self.root / f'搬移 書籍 {len(bom)}'
                shutil.move(flow.root, relocated)
                self.assertEqual(ProjectWorkflow.open(relocated).texts(batch), (self.text, edited))

    def test_preview_is_exact_import_snapshot(self):
        flow = ProjectWorkflow.create(self.root / 'project', '書籍')
        preview = flow.inspect_txt(self.source)
        self.source.write_text('外部變更', encoding='utf-8')
        batch = flow.import_txt(preview)
        self.assertEqual(flow.texts(batch), (self.text, self.text))

    def test_two_txt_batches_keep_independent_drafts_names_and_order(self):
        flow, first = self.imported()
        self.source.write_bytes('第二章，另一份中文原稿。'.encode('utf-8'))
        second = flow.import_txt(flow.inspect_txt(self.source))
        flow.save_draft(first, '第一批已校對。')
        flow.rename_batch(second, '第二章 校對中')
        flow.reorder_batches([second, first])
        reopened = ProjectWorkflow.open(flow.root)
        self.assertEqual([b['id'] for b in reopened.state['batches']], [second, first])
        self.assertEqual(reopened.state['batches'][0]['name'], '第二章 校對中')
        self.assertEqual(reopened.texts(first), (self.text, '第一批已校對。'))
        self.assertEqual(reopened.texts(second), ('第二章，另一份中文原稿。', '第二章，另一份中文原稿。'))
        self.assertEqual(reopened.state['batches'][0]['revision'], 1)

    def test_failed_publication_preserves_last_save_and_allows_retry(self):
        flow, batch = self.imported()
        previous = (flow.root / 'project.json').read_bytes()
        import os
        replace = os.replace

        def fail_manifest(src, dst):
            if Path(dst).name == 'project.json':
                raise OSError(errno.ENOSPC, 'test storage fault')
            return replace(src, dst)

        with patch('ebook2mp4.workflow.os.replace', side_effect=fail_manifest):
            with self.assertRaisesRegex(ProjectError, '前次成功資料仍保留'):
                flow.save_draft(batch, '新稿件')
        self.assertEqual((flow.root / 'project.json').read_bytes(), previous)
        self.assertEqual(ProjectWorkflow.open(flow.root).texts(batch)[1], self.text)
        self.assertEqual(flow.state['batches'][0]['revision'], 1)
        self.assertFalse((flow.root / '.write.lock').exists())
        flow.save_draft(batch, '新稿件')
        self.assertEqual(ProjectWorkflow.open(flow.root).texts(batch)[1], '新稿件')

    def test_permission_failure_and_space_failure_are_recoverable(self):
        flow, batch = self.imported()
        for patcher, error in (
            (patch('ebook2mp4.workflow.tempfile.NamedTemporaryFile', side_effect=PermissionError()), '寫入權限'),
            (patch('ebook2mp4.workflow.shutil.disk_usage', return_value=shutil._ntuple_diskusage(100, 100, 0)), '空間不足'),
        ):
            with patcher, self.assertRaisesRegex(ProjectError, error):
                flow.save_draft(batch, '新稿')
            self.assertEqual(ProjectWorkflow.open(flow.root).texts(batch)[1], self.text)

    def test_failed_import_remains_empty_and_retry_works(self):
        flow = ProjectWorkflow.create(self.root / 'project', '書籍')
        preview = flow.inspect_txt(self.source)
        with patch('ebook2mp4.workflow.os.replace', side_effect=PermissionError()):
            with self.assertRaises(ProjectError):
                flow.import_txt(preview)
        self.assertEqual(ProjectWorkflow.open(flow.root).state['batches'], [])
        batch = flow.import_txt(preview)
        self.assertEqual(ProjectWorkflow.open(flow.root).texts(batch)[0], self.text)

    def test_other_window_update_is_not_overwritten(self):
        flow, batch = self.imported()
        other = ProjectWorkflow.open(flow.root)
        flow.save_draft(batch, '視窗 A 已儲存')
        with self.assertRaisesRegex(ProjectError, '另一個視窗'):
            other.save_draft(batch, '視窗 B 不可覆寫')
        self.assertEqual(ProjectWorkflow.open(flow.root).texts(batch)[1], '視窗 A 已儲存')

    def test_write_lock_is_actionable_and_not_removed_by_other_window(self):
        flow, batch = self.imported()
        lock = flow.root / '.write.lock'
        lock.touch()
        with self.assertRaisesRegex(ProjectError, '正被寫入'):
            flow.save_draft(batch, '新稿')
        self.assertTrue(lock.exists())

    def test_missing_and_modified_project_content_are_reported(self):
        flow, batch = self.imported()
        ref = flow.state['batches'][0]['source']['path']
        path = flow.root / ref
        path.unlink()
        with self.assertRaisesRegex(ProjectError, ref):
            ProjectWorkflow.open(flow.root)
        path.write_bytes(b'altered')
        with self.assertRaisesRegex(ProjectError, '內容已變更'):
            ProjectWorkflow.open(flow.root)

    def test_bad_encoding_is_rejected_without_replacement_characters(self):
        self.source.write_bytes('繁體中文'.encode('cp950'))
        with self.assertRaisesRegex(ProjectError, 'UTF-8'):
            ProjectWorkflow.inspect_txt(self.source)

    def test_supported_encodings_preview_and_reopen_exact_originals(self):
        flow = ProjectWorkflow.create(self.root / '編碼書籍', '不同編碼')
        examples = [
            ('UTF-8', 'utf-8', '繁體、简体 and English。', 'auto'),
            ('UTF-8 BOM', 'utf-8-sig', '繁體中文。', 'auto'),
            ('UTF-16 BOM', 'utf-16', '繁體、简体 and English。', 'auto'),
            ('Big5', 'big5', '第一章，繁體中文。', 'Big5'),
            ('CP950', 'cp950', '第二章，碁。', 'CP950'),
        ]
        for label, codec, text, selection in examples:
            with self.subTest(encoding=label):
                data = text.encode(codec)
                self.source.write_bytes(data)
                preview = flow.inspect_txt(self.source, encoding=selection)
                self.assertEqual(preview.text, text)
                self.assertEqual(preview.encoding, label)
                batch = flow.import_txt(preview)
                reopened = ProjectWorkflow.open(flow.root)
                self.assertEqual(reopened.texts(batch), (text, text))
                self.assertEqual(self.source.read_bytes(), data)
        # Wrong selection never returns a successful preview or changes the project.
        before = flow.state
        with self.assertRaises(ProjectError):
            flow.inspect_txt(self.source, encoding='UTF-8')
        self.assertEqual(flow.state, before)
        self.assertEqual(flow.inspect_txt(self.source, encoding='CP950').text, '第二章，碁。')

    def test_suspected_garbled_text_needs_explicit_acknowledgment(self):
        flow, first = self.imported()
        self.source.write_bytes('來源真的含有 � 字元。'.encode('utf-8'))
        preview = flow.inspect_txt(self.source)
        self.assertTrue(preview.warnings)
        with self.assertRaisesRegex(ProjectError, '確認'):
            flow.import_txt(preview)
        self.assertEqual(len(ProjectWorkflow.open(flow.root).state['batches']), 1)
        second = flow.import_txt(preview, accept_warnings=True)
        self.assertEqual(flow.texts(second), ('來源真的含有 � 字元。', '來源真的含有 � 字元。'))
        self.assertEqual(flow.texts(first), (self.text, self.text))

    def test_empty_file_and_100k_manuscript_round_trip(self):
        for text in ('', '長篇 English, 段落。\n\n' * 7000):
            self.source.write_bytes(text.encode('utf-8'))
            flow, batch = self.imported(f'project-{len(text)}')
            self.assertEqual(ProjectWorkflow.open(flow.root).texts(batch), (text, text))

    def test_existing_folder_never_overwritten(self):
        flow, _ = self.imported()
        before = (flow.root / 'project.json').read_bytes()
        with self.assertRaisesRegex(ProjectError, '空資料夾'):
            ProjectWorkflow.create(flow.root, 'another')
        self.assertEqual((flow.root / 'project.json').read_bytes(), before)

    def test_future_version_and_unsafe_reference_rejected(self):
        flow, _ = self.imported()
        state = flow.state
        state['format_version'] = 99
        manifest = flow.root / 'project.json'
        manifest.write_text(json.dumps(state), encoding='utf-8')
        with self.assertRaisesRegex(ProjectError, '版本'):
            ProjectWorkflow.open(flow.root)
        state['format_version'] = 1
        state['batches'][0]['source']['path'] = '../原稿（第一章）.txt'
        manifest.write_text(json.dumps(state), encoding='utf-8')
        with self.assertRaisesRegex(ProjectError, '不安全'):
            ProjectWorkflow.open(flow.root)

    def test_invalid_batch_identity_is_reported_before_ui_load(self):
        flow, _ = self.imported()
        for invalid in ('', 7):
            with self.subTest(identity=invalid):
                state = flow.state
                state['batches'][0]['id'] = invalid
                (flow.root / 'project.json').write_text(json.dumps(state), encoding='utf-8')
                with self.assertRaisesRegex(ProjectError, '欄位不完整'):
                    ProjectWorkflow.open(flow.root)


if __name__ == '__main__':
    unittest.main()
