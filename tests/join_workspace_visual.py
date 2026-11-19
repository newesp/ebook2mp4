"""Capture native comparison states from the approved mock's sample content."""
import json
import os
from pathlib import Path
import time
from tkinter import ttk
from PIL import ImageGrab

from test_assembly_joins_desktop import AssemblyJoinsDesktop
from join_workspace_fixture import bounds


def main():
    c=AssemblyJoinsDesktop();c.setUp()
    out=Path(os.environ.get('JOIN_QA_EVIDENCE','docs/verification/audio-join-workspace'))
    try:
        ids=c.pdf_batches();c.narrate(ids)
        for i,b in enumerate(ids):c.flow.rename_batch(b,f'第 {i+1} 章')
        c.flow.save_assembly_settings(ids)
        c.app.refresh()
        c.app.total_audio();p=c.app.production.current;c.wait_page(p);p.join_button.invoke();j=p.join_page;c.wait_join(j)
        records=[]
        for size,points,expanded in [('1360x820',10,False),('1360x820',10,True),('1280x720',10,False),('900x640',10,False),('900x640',10,True),('900x640',13,False),('900x640',13,True)]:
            c.root.state('normal');c.root.geometry(size)
            ttk.Style(c.root).configure('.',font=('Microsoft JhengHei',points))
            j.fill(j.left_text,'當你停止追逐念頭，\n注意力便回到此刻。\n覺察，就從這一刻開始。')
            j.fill(j.right_text,'先留意你的呼吸，\n感受吸氣與吐氣的節奏。\n讓注意力安穩地停在當下。')
            ws=j.workspace;ws.details_open=expanded
            for _ in range(3):c.root.update();ws.resized();time.sleep(.08)
            c.root.update()
            name=f'native-{size}-{points}pt'+('-expanded' if expanded else '')
            ImageGrab.grab(window=c.root.winfo_id()).save(out/(name+'.png'))
            widgets={n:bounds(getattr(j,n)) for n in ['left_text','right_text','left_edit','right_edit','pause_control','clip_control','play_button','stop_button','save_button','previous','next']}
            widgets.update(main=bounds(ws.main),documents=bounds(c.app.batch_list),disclosure=bounds(ws.disclosure),ack=bounds(j.ack_control),detail=bounds(ws.detail_text))
            records.append(dict(name=name,size=size,font_points=points,dpi=c.root.winfo_fpixels('1i'),scaling=c.root.tk.call('tk','scaling'),dedicated=ws.dedicated,widgets=widgets,detail_yview=ws.detail_text.yview(),source_scrollbars=[bool(t.scroll.winfo_ismapped()) for t in ws.panes]))
        (out/'native-visual.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'{len(records)} native states captured',flush=True)
    finally:c.doCleanups()


if __name__=='__main__':main()
