"""Launch the real desktop against a retained, synthetic QA book."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

base = Path(__file__).resolve().parents[1] / '.scratch' / ('t03-visual' if '--proofread' in sys.argv else 't02-visual' if '--multiple' in sys.argv else 't01-visual')
base.mkdir(parents=True, exist_ok=True)
source = base / '風與樹 第一章.txt'
source.write_text('第一章　風與樹\n\n清晨，山谷裡的風帶著露水的氣息。\n他推開窗，看見樹影落在書頁上。\n\n「今天就從這一頁開始吧。」她說。\n\nHello, world! 數字 3.14、姓名與標點都保留。\n\n這是用於桌面驗證的合成測試文字。', encoding='utf-8')
folder = base / '風與樹 書籍專案'
if (folder / 'project.json').exists():
    flow = ProjectWorkflow.open(folder)
else:
    flow = ProjectWorkflow.create(folder, '風與樹')
    flow.import_txt(flow.inspect_txt(source))
if '--multiple' in sys.argv and len(flow.state['batches']) == 1:
    source2 = base / '風與樹 第二章 CP950.txt'
    source2.write_bytes('第二章　林間的棋局\n\n樹下有一局碁。\n這份原稿使用 CP950 編碼。'.encode('cp950'))
    flow.import_txt(flow.inspect_txt(source2, encoding='CP950'))
if '--confirmed' in sys.argv:
    flow.confirm_reading(flow.state['batches'][0]['id'])
if '--issues' in sys.argv:
    flow.record_source_issues(flow.state['batches'][0]['id'], ['第 2 頁擷取失敗：請比對來源後重試或明確略過。'])
root, app = make_app()
root.geometry('1360x780+0+0')
app.flow = flow
app.step = 2
app.refresh()
if '--proofread' in sys.argv:
    app.find_text.set('山谷')
    app.replace_text.set('溪谷')
if '--versions' in sys.argv:
    root.after(200, app.show_versions)
if '--reload-preview' in sys.argv:
    from unittest.mock import patch

    def open_reload():
        app.editor.insert('end', '\n\n這段未存編輯將在重載時保留副本或明確取代。')
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(source)):
            app.import_txt(True)
    root.after(200, open_reload)
if '--narrow' in sys.argv:
    root.geometry('1040x640+0+0')
if '--empty' in sys.argv:
    app.flow = None
    app.refresh()
if '--preview' in sys.argv or '--preview-ready' in sys.argv:
    from unittest.mock import patch

    def open_preview():
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(base / '風與樹 第二章 CP950.txt')):
            app.import_txt()
        if '--preview-ready' in sys.argv:
            def children(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from children(child)
            selector = next(w for w in children(root) if w.winfo_class() == 'TCombobox')
            selector.set('CP950')
            selector.event_generate('<<ComboboxSelected>>')
    root.after(200, open_preview)
root.mainloop()
