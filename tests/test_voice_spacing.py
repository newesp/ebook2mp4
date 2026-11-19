"""Measure the three reported spacing defects on the native voice page."""
import json
import os
from pathlib import Path
from tkinter import ttk
import unittest
import test_voice_desktop as fixture
from ebook2mp4.workspace_layout import TOOLBAR_GAP


def controls(page):
    def find(widget, label):
        for child in widget.winfo_children():
            if 'text' in child.keys() and child.cget('text') == label:
                return child
            result = find(child, label)
            if result is not None:
                return result
        return None
    return (find(page.preview_panel, '使用固定試聽範例'),
            find(page.preview_panel, '帶入選取文字'))


def measure(page):
    first, second = controls(page)
    bounds = lambda w: dict(x=w.winfo_rootx(), y=w.winfo_rooty(),
                            width=w.winfo_width(), height=w.winfo_height())
    a, b, save, next_action, text = map(bounds,
        (first, second, page.save_button, page.produce_button, page.outgoing))
    return dict(first=a, second=b, save=save, next=next_action, textarea=text,
        width_difference=abs(a['width']-b['width']),
        top_horizontal_gap=b['x']-a['x']-a['width'],
        footer_horizontal_gap=next_action['x']-save['x']-save['width'],
        content_vertical_gap=text['y']-max(a['y']+a['height'], b['y']+b['height']))


class VoiceSpacing(unittest.TestCase):
    setUp = fixture.VoiceDesktop.setUp

    def settle(self):
        self.root.state('normal')
        self.root.geometry('1360x820')
        for _ in range(3):
            self.root.update()
            self.app.layout_workspace()
        self.root.update()
        return measure(self.dialog)

    def test_same_group_button_dimensions(self):
        m = self.settle()
        self.assertLessEqual(m['width_difference'], 2, m)
        self.assertLessEqual(abs(m['first']['height']-m['second']['height']),2)

    def test_adjacent_action_gaps(self):
        m = self.settle()
        self.assertEqual(m['top_horizontal_gap'], TOOLBAR_GAP, m)
        self.assertEqual(m['footer_horizontal_gap'], TOOLBAR_GAP, m)

    def test_action_to_content_gap(self):
        m = self.settle()
        self.assertEqual(m['content_vertical_gap'], 2*TOOLBAR_GAP, m)

    def test_spacing_at_acceptance_sizes(self):
        rows = []
        if evidence := os.environ.get('VOICE_QA_EVIDENCE'):
            path = Path(evidence) / 'native-layout-regression.json'
            self.addCleanup(lambda: path.write_text(
                json.dumps(rows, indent=2), encoding='utf-8'))
        for size in ('maximized', '1360x820', '1280x720', '900x640'):
            for points in (10, 13):
                with self.subTest(size=size, font_points=points):
                    ttk.Style(self.root).configure('.', font=('Microsoft JhengHei', points))
                    self.root.state('zoomed' if size == 'maximized' else 'normal')
                    if size != 'maximized':
                        self.root.geometry(size)
                    for _ in range(3):
                        self.root.update()
                        self.app.layout_workspace()
                    self.root.update()
                    actual_size = f'{self.root.winfo_width()}x{self.root.winfo_height()}'
                    m = measure(self.dialog)
                    viewable = bool(self.dialog.outgoing.winfo_viewable())
                    m.update(size=size, actual_size=actual_size, font_points=points,
                             dpi=self.root.winfo_fpixels('1i'), scaling=float(self.root.tk.call('tk', 'scaling')),
                             height_difference=abs(m['first']['height']-m['second']['height']),
                             textarea_viewable=viewable,
                             expected=dict(max_button_difference=2, horizontal_gap=TOOLBAR_GAP,
                                           vertical_gap=2*TOOLBAR_GAP, textarea_viewable=True))
                    rows.append(m)
                    if size != 'maximized':
                        self.assertEqual(actual_size, size)
                    else:
                        self.assertEqual(self.root.state(), 'zoomed')
                    self.assertTrue(viewable, '試聽文字框應可見')
                    for widget in (*controls(self.dialog), self.dialog.save_button,
                                   self.dialog.produce_button, self.dialog.outgoing):
                        self.assertTrue(widget.winfo_viewable(), str(widget))
                        self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                                             self.root.winfo_rootx() + self.root.winfo_width())
                        self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                             self.root.winfo_rooty() + self.root.winfo_height())
                    self.assertLessEqual(m['width_difference'], 2, m)
                    self.assertLessEqual(m['height_difference'], 2, m)
                    self.assertEqual(m['top_horizontal_gap'], TOOLBAR_GAP, m)
                    self.assertEqual(m['footer_horizontal_gap'], TOOLBAR_GAP, m)
                    self.assertEqual(m['content_vertical_gap'], 2 * TOOLBAR_GAP, m)
