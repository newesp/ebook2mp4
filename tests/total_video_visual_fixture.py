"""Open only the owned synthetic T16 project for native visual inspection."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

root, app = make_app()
app.flow = ProjectWorkflow.open('.scratch/t16-native/book')
app.batch_id = app.flow.state['batches'][0]['id']
app.refresh()
root.update()
app.total_audio()
root.state('normal')
root.geometry('1040x640')
root.title('T16 兩步驟 · 原生驗證')
root.mainloop()
