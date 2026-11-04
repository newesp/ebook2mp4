"""Launch only a synthetic project for native visual inspection."""
import os
from pathlib import Path
from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.desktop import make_app

ROOT=Path(__file__).resolve().parents[1]
os.environ['EBOOK2MP4_KOKORO_HOME']=str(ROOT/'.scratch/kokoro-integration/real-home')
base=ROOT/'.scratch/kokoro-integration/ui-book'
source=ROOT/'.scratch/kokoro-integration/ui-source.txt'
source.write_text('清晨，臺北的圖書館剛開門。Hello world。',encoding='utf-8')
flow=ProjectWorkflow.open(base) if (base/'project.json').exists() else ProjectWorkflow.create(base,'Kokoro 整合驗證')
batch=flow.state['batches'][0]['id'] if flow.state['batches'] else flow.import_txt(flow.inspect_txt(source))
root,app=make_app();app.flow=flow;app.batch_id=batch;app.refresh();app.show_step(4)
page=app.voice_dialog
page.service.set(page.service_labels['kokoro']);page.change_service();page.voice.set('zf_001')
root.title('Kokoro 整合驗證')
root.after(100,lambda:(root.state('normal'),root.geometry('1040x760+30+30')))
root.mainloop()
