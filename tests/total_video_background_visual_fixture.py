"""Open the owned T17 synthetic project, then shut down when its local stop marker appears."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

root, app = make_app()
app.flow = ProjectWorkflow.open('.scratch/t17-native/book')
app.batch_id = app.flow.state['batches'][0]['id']
app.refresh()
root.update()
app.total_video()
root.state('normal')
root.geometry('1040x640')
root.title('T17 背景影片 · 原生驗證')
def control():
    marker = Path('.scratch/t17-native/size.txt')
    if marker.exists():
        value = marker.read_text().strip()
        marker.unlink()
        root.geometry(value)
    if Path('.scratch/t17-native/stop').exists():
        app.close()
        return
    root.after(200, control)
root.after(200, control)
root.mainloop()
