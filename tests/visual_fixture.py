"""Launch the real desktop against a retained, synthetic QA book."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

base = Path(__file__).resolve().parents[1] / '.scratch' / 't01-visual'
base.mkdir(parents=True, exist_ok=True)
source = base / '風與樹 第一章.txt'
source.write_text('第一章　風與樹\n\n清晨，山谷裡的風帶著露水的氣息。\n他推開窗，看見樹影落在書頁上。\n\n「今天就從這一頁開始吧。」她說。\n\nHello, world! 數字 3.14、姓名與標點都保留。\n\n這是用於桌面驗證的合成測試文字。', encoding='utf-8')
folder = base / '風與樹 書籍專案'
if (folder / 'project.json').exists():
    flow = ProjectWorkflow.open(folder)
else:
    flow = ProjectWorkflow.create(folder, '風與樹')
    flow.import_txt(flow.inspect_txt(source))
root, app = make_app()
app.flow = flow
app.step = 2
app.refresh()
if '--narrow' in sys.argv:
    root.geometry('1040x680')
if '--empty' in sys.argv:
    app.flow = None
    app.refresh()
root.mainloop()
