"""Batch selection keeps the visible workflow step and production subpage."""
import unittest
from unittest.mock import patch

import test_production_pages as fixture


class BatchStepRetention(unittest.TestCase):
    setUp = fixture.ProductionPages.setUp
    stop_ui = fixture.ProductionPages.stop_ui
    collect_ui = fixture.ProductionPages.collect_ui

    def add_second_batch(self):
        first = self.app.batch_id
        source = self.folder / 'book1-ch2.txt'
        source.write_text('第二批的朗讀內容。', encoding='utf-8')
        second = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        for batch in (first, second):
            self.app.flow.confirm_reading(batch)
        self.app.refresh()
        self.root.update()
        return first, second

    def select(self, batch):
        self.app.batch_list.selection_set(batch)
        self.app.batch_list.event_generate('<<TreeviewSelect>>')
        self.root.update()
        self.assertEqual(self.app.batch_id, batch)

    def test_production_subpages_survive_batch_switch_in_both_directions(self):
        first, second = self.add_second_batch()
        for kind, open_page in (
            ('voice', self.app.voice_settings),
            ('narration', self.app.narration),
            ('assembly', self.app.total_audio),
            ('video', self.app.total_video),
            ('batch_video', self.app.batch_video),
        ):
            with self.subTest(kind=kind):
                self.select(first)
                open_page()
                self.root.update()
                original = self.app.production.current
                for batch in (second, first):
                    self.select(batch)
                    self.assertEqual(self.app.step, 4)
                    key = (id(self.app.flow), None if kind in ('assembly', 'video') else batch, kind)
                    self.assertIs(self.app.production.current, self.app.production.pages.get(key))
                    self.assertTrue(self.app.production.current.winfo_ismapped())
                    self.assertIs(type(self.app.production.current), type(original))
                self.assertIs(self.app.production.current, original)

    def test_main_steps_survive_batch_switch(self):
        first, second = self.add_second_batch()
        for step in (1,):
            with self.subTest(step=step):
                self.app.show_step(step)
                for batch in (second, first):
                    self.select(batch)
                    self.assertEqual(self.app.step, step)
                    self.assertEqual(self.app.current_text, self.app.flow.texts(batch)[1])

    def test_autosaved_switch_keeps_draft_in_original_batch(self):
        first, second = self.add_second_batch()
        self.app.show_step(2)
        self.app.editor.insert('end', '尚未儲存。')
        self.root.update()
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=None):
            self.app.batch_list.selection_set(second)
            self.app.batch_list.event_generate('<<TreeviewSelect>>')
            self.root.update()
        self.assertEqual(self.app.batch_id, second)
        self.assertEqual(self.app.step, 1)
        self.assertTrue(self.app.flow.workspace_state(first)['text'].endswith('尚未儲存。'))


if __name__ == '__main__':
    unittest.main()
