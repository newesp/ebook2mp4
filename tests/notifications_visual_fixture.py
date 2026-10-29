"""Synthetic notification captures; paused countdown, no live cloud requests."""
import argparse
from pathlib import Path
import sys
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', choices=('main', 'gemini', 'pdf', 'voice', 'settings'), default='gemini')
    args = parser.parse_args()
    if args.screen == 'gemini':
        from test_ui_layout_gemini import GeminiLayout
        fixture = GeminiLayout()
    elif args.screen == 'pdf':
        from test_ui_layout_pdf import PdfReadingLayout
        fixture = PdfReadingLayout()
    elif args.screen == 'voice':
        from test_voice_desktop import VoiceDesktop
        fixture = VoiceDesktop()
    else:
        from test_ui_layout import WorkbenchLayout
        fixture = WorkbenchLayout()
    try:
        fixture.setUp()
        root, app = fixture.root, fixture.app
        owner = getattr(fixture, 'dialog', root)
        if args.screen == 'settings':
            with patch('ebook2mp4.workflow.ProjectWorkflow.gemini_settings', return_value=dict(key='', model='gemini-3.8-flash')):
                app.gemini_settings()
            owner = app.gemini_settings_dialog
        if args.screen in ('gemini', 'pdf'):
            owner.geometry('740x570+20+20')
        if owner is not root:
            root.geometry('1040x640+900+80')
        else:
            root.geometry('1040x640+20+20')
        owner.title(f'通知驗證 · {args.screen}')
        root.update()
        def sample(_event=None):
            if args.screen == 'gemini':
                owner.accept_button.invoke()
                layer = owner._notification_layer
            else:
                layer = app.notify({'main': '校對稿已儲存。', 'pdf': 'PDF 修正已儲存為新批次。',
                                    'voice': '語音設定已儲存。', 'settings': 'Gemini 設定已儲存。'}[args.screen], owner=owner)
            layer.duration = 0  # Capture only: pointer movement must not restart dismissal.
            layer.cancel_timer()
        owner.bind('<F9>', sample)
        sample()
        root.after(500, owner.lift)
        root.after(60000, root.quit)
        root.mainloop()
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
