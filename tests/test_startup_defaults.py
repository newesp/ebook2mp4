"""Visible startup defaults."""
import unittest
from ebook2mp4.desktop import make_app


class StartupDefaults(unittest.TestCase):
    def test_main_window_starts_maximized(self):
        root,app=make_app()
        try:
            root.update()
            self.assertEqual(root.state(),'zoomed')
        finally:
            app.close()
