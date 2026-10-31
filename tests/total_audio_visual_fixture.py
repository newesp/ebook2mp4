"""Owned, synthetic visual fixture. Close normally to clean its temporary book."""
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_total_audio as fixture
from ebook2mp4.desktop import make_app


case = fixture.TotalAudioJourney()
case.setUp()
try:
    ids = case.prepare(3)
    for index, identity in enumerate(ids, 1):
        case.flow.rename_batch(identity, f'第{index}章')
    missing = case.flow.import_txt(case.flow.inspect_txt(case.source))
    case.flow.rename_batch(missing, '第4章（尚無音訊）')
    case.flow.save_assembly_settings(ids)
    case.merge()
    root, app = make_app()
    app.flow, app.batch_id = case.flow, ids[0]
    app.refresh()
    root.update()
    app.total_audio()
    root.state('normal')
    root.geometry('1040x640')
    root.title('T14 全書合併 · 原生驗證')
    print(json.dumps(dict(root=str(case.flow.root)), ensure_ascii=False), flush=True)
    root.mainloop()
finally:
    case.doCleanups()
