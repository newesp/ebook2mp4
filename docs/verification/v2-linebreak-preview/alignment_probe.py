from pathlib import Path
import json
import sys

root_path = Path.cwd()
version = sys.argv[1]
source = root_path/'archives/v1/source' if version == 'v1' else root_path
sys.path.insert(0, str(source))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

base = root_path/'.scratch/v2-cleanup-work'/('alignment-'+version)
base.mkdir(parents=True, exist_ok=True)
text = base/'source.txt'
text.write_text('第一行。\n第二行。\n\n保留段落。', encoding='utf-8')
flow = ProjectWorkflow.create(base/'book', '合成齊頭回歸')
batch = flow.import_txt(flow.inspect_txt(text))
root, app = make_app()
try:
    app.flow, app.batch_id = flow, batch
    app.refresh()
    root.update()
    root.state('normal')
    root.geometry('900x640')
    app.cleanup_line_breaks()
    for _ in range(3):
        root.update()
        app.layout_workspace()
    back = app.inner_host.back if hasattr(app, 'inner_host') else app.tool_back
    panel = app.inner_host.panel if hasattr(app, 'inner_host') else app.cleanup_preview
    data = dict(version=version, client=[root.winfo_width(),root.winfo_height()],
        toolbar_top_gap=abs(app.focus_button.winfo_rooty()-back.winfo_rooty()),
        content_top_gap=abs(app.batch_list.winfo_rooty()-panel.winfo_rooty()))
    print(json.dumps(data), flush=True)
    assert data['toolbar_top_gap'] <= 2 and data['content_top_gap'] <= 2, 'Peer header/content origins differ'
finally:
    app.close()
