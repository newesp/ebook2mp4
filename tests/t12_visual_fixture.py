"""Synthetic native single-window fixture; removes its project on normal exit."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import AsyncMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

base=Path('.scratch/T12-visual')
base.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=base) as directory:
    path=Path(directory)
    with patch.dict('os.environ',EBOOK2MP4_VOICE_HOME=str(path/'voice')):
        root,app=make_app()
        app.flow=ProjectWorkflow.create(path/'book','T12 原生驗證範例')
        source=path/'第一章.txt'
        source.write_text('清晨的風穿過窗邊。\n\n我們從第一章開始閱讀。',encoding='utf-8')
        app.batch_id=app.flow.import_txt(app.flow.inspect_txt(source))
        with patch('edge_tts.list_voices',new=AsyncMock(return_value=[dict(ShortName='zh-TW-HsiaoChenNeural',FriendlyName='台灣華語 曉臻',Locale='zh-TW',Gender='Female')])):
            job=app.flow.start_voice_refresh()
            job.wait(10)
        app.flow.save_voice_settings('zh-TW-HsiaoChenNeural',batch_id=app.batch_id)
        app.flow.confirm_reading(app.batch_id)
        app.refresh()
        root.geometry('1040x640+30+30')
        app.voice_settings()
        root.after(480000,app.close)
        root.mainloop()
