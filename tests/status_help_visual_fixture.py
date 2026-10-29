"""Synthetic TXT-only workbench for native hover inspection; closes cleanly."""
from pathlib import Path
import argparse
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hover', choices=('unconfirmed', 'pending'))
    args = parser.parse_args()
    base = Path('.scratch/status-help-visual')
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as folder:
        path = Path(folder)
        flow = ProjectWorkflow.create(path / 'project', '批次狀態說明')
        ids = []
        for number in range(1, 4):
            source = path / f'第{number}章.txt'
            source.write_text('這是合成書稿，用於驗證狀態說明。\n原稿與校對稿分開保存。', encoding='utf-8')
            ids.append(flow.import_txt(flow.inspect_txt(source)))
        flow.record_source_issues(ids[1], ['請核對來源字形。'])
        flow.confirm_reading(ids[2])
        root, app = make_app()
        root.geometry('1040x640+30+30')
        app.flow, app.batch_id = flow, ids[0]
        app.refresh()
        if args.hover:
            def preview_help():
                row = ids[0 if args.hover == 'unconfirmed' else 1]
                x, y, width, height = app.batch_list.bbox(row, 'status')
                app.batch_list.event_generate('<Motion>', x=x+width//2, y=y+height//2)
            root.after(1000, preview_help)
        root.after(600000, root.destroy)
        root.mainloop()


if __name__ == '__main__':
    main()
