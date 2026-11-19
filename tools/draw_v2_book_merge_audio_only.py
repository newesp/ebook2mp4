"""Audio-only assembly mock: shared label, value, information and action columns."""
from pathlib import Path
import hashlib
import json
import draw_v2_book_merge as base

OUT=Path(__file__).resolve().parents[1]/'docs/ui-review/v2-book-merge-audio-only'
OUT.mkdir(parents=True,exist_ok=True)
base.OUT=OUT
LAYOUT=[]


class AudioDrawing(base.Drawing):
    def shell(self,compact=False,file_mode='short'):
        x,top,right,bottom=super().shell(compact,file_mode)
        if not (compact and self.w<1040):
            yy=top-49
            self.rect((x+100,yy,right,yy+36),base.BG,base.BG)
            self.text(x+110,yy+9,'選取批次、調整順序，再製作合併音訊')
        return x,top,right,bottom


base.Drawing=AudioDrawing


def render(w,h,mode='short',state='ready',end=False,file_mode='short'):
    name=f'{w}-{state if state!="ready" else mode}'+('-end' if end else '')+('-files-'+file_mode if file_mode!='short' else '')
    a=AudioDrawing(w,h,name)
    busy=state=='running'
    x,top,right,bottom=a.shell(compact=w<1040,file_mode=file_mode)
    if w<1040:a.button(592,64,36,'›',role='icon')
    lx,rx=x+12,right-12
    cols=[lx,lx+112,lx+260,lx+408,lx+556]
    toolbar_y=top+12
    a.text(cols[0],toolbar_y+8,'合併來源',True)
    for i,label in enumerate(['重新檢查來源' if mode=='empty' else '選取有效批次','上移','下移','來源詳情 →']):
        a.button(lx+112+i*148,toolbar_y,144,label,disabled=busy or mode=='empty' and i>0,role='source-action')
    join_y=bottom-96
    result_y=join_y+44
    table_y=toolbar_y+44
    table_end=join_y-8
    view=table_end-table_y-32
    n=5 if mode=='short' else view//40 if mode=='fit' else view//40+1 if mode=='overflow' else 48 if mode=='long' else 0
    content=view if mode=='fit' else 48 if mode=='empty' else n*40
    picked=4 if mode=='short' else n
    a.rect((lx,table_y,rx,table_y+32),'#edf1e9')
    for cx,label in [(12,'選取'),(64,'順序'),(120,'批次'),(rx-lx-310,'時長'),(rx-lx-216,'來源狀態')]:a.text(lx+cx,table_y+6,label)
    def paint(d,rw,ch):
        for i in range(n):
            yy=i*40;invalid=mode=='short' and i==4
            if i==1:d.rectangle((0,yy,rw,yy+39),fill=base.SEL)
            d.line((0,yy+39,rw,yy+39),fill='#e7ebe4')
            d.rectangle((12,yy+12,25,yy+25),fill='#e1e5de' if busy else 'white',outline=base.LINE)
            if not invalid:d.line([(14,yy+18),(18,yy+22),(24,yy+14)],fill=base.GREEN,width=2)
            vals=[(64,'—' if invalid else str(i+1)),(120,['第一章','第二章','第三章','第四章','第五章'][i] if i<5 else f'第 {i+1} 章'),(rx-lx-310,'—' if invalid else '12:40'),(rx-lx-216,'待更新 · 未選取' if invalid else '有效 · MP3／SRT')]
            if state=='missing' and i==2:vals[-1]=(rx-lx-216,'待更新 · 已選取')
            for cx,t in vals:d.text((cx,yy+10),t,font=base.F,fill=base.WARN if invalid else base.INK)
        if not n:d.text((16,14),'尚未載入來源。請按「重新檢查來源」。',font=base.F,fill=base.MUTED)
    a.region('合併來源清單',(lx,table_y+32,rx,table_end),content,paint,max(0,content-view) if end else 0,mode)
    a.text(cols[0],join_y+8,'交接停頓',True)
    a.button(cols[1],join_y,144,'0.5 秒',drop=True,disabled=busy,role='value')
    a.text(cols[2],join_y+8,f'{max(0,picked-1)} 個接點',color=base.MUTED)
    a.button(cols[3],join_y,144,'檢查接點 →',disabled=busy or picked<2,role='detail-action')
    status,summary='準備','來源齊全，可製作合併音訊。'
    action='查看詳情 →'
    if state=='done':status,summary,action='已完成','合併 MP3 與同版 SRT 已保存。','成品操作'
    elif state=='missing':status,summary,action='缺項','第三章音訊待更新，請先補齊來源。','補齊缺項 →'
    elif state=='running':status,summary='製作中 · 65%','正在組裝合併音訊；來源與設定已鎖定。'
    elif state=='failed':status,summary='失敗','合併失敗；請查看詳情，上次成功成品保留。'
    elif state=='cancelled':status,summary='已取消','任務已取消，上次成功成品保留。'
    elif state=='pending':status,summary='保存失敗','音訊已完成；請重試保存，不需重新合併。'
    if not picked:status,summary='未檢查','尚未載入來源，請先重新檢查來源。'
    a.text(cols[0],result_y+8,'合併音訊',True)
    # Read-only status uses the same column bounds as the value control above it.
    a.rect((cols[1],result_y,cols[1]+144,result_y+36),'#f5f6f2')
    a.text(cols[1]+10,result_y+8,status,color=base.WARN if state in ('failed','missing','pending') else base.INK)
    a.text(cols[2],result_y+8,'MP3／SRT',color=base.MUTED)
    a.button(cols[3],result_y,144,action,drop=state=='done',disabled=busy or not picked,role='detail-action')
    a.button(cols[4],result_y,144,'成品版本 →',disabled=busy,role='detail-action')
    a.text(16,h-93,summary,color=base.MUTED)
    a.button(16,h-60,168,'← 返回音訊製做',role='footer-back')
    if busy:a.button(w-212,h-60,196,'取消任務',role='footer-action')
    else:
        a.button(w-412,h-60,196,'儲存合併設定',disabled=not picked,role='footer-action')
        label='重試保存' if state=='pending' else '製作合併音訊'
        disabled=not picked or state in ('missing','done')
        a.button(w-212,h-60,196,label,active=not disabled,disabled=disabled,role='footer-action')
    if busy:
        for c in list(a.controls):
            if c['label'] in ('匯入','管理'):
                a.controls.remove(c);a.button(c['x'],c['y'],c['width'],c['label'],drop=True,disabled=True)
    LAYOUT.append(dict(page=name,columns=cols,row_tops=[join_y,result_y],row_height=36,row_pitch=44,value_bounds=[cols[1],cols[1]+144],action_bounds=[cols[3],cols[3]+144],source_viewport=view,table_toolbar_gap=8,only_audio=True))
    a.save()


if __name__=='__main__':
    for mode in ('empty','short','fit','overflow','long'):render(1360,820,mode)
    render(1360,820,'long',end=True)
    for w,h in ((1920,1000),(1280,720),(900,640)):render(w,h)
    for state in ('missing','running','failed','cancelled','pending','done'):render(1360,820,state=state)
    for mode in ('fit','overflow','long'):render(1360,820,file_mode=mode)
    for mode in ('short','fit','overflow','long'):base.joins(1360,820,mode)
    base.joins(900,640,'long',end=True)
    checks=[]
    for row in LAYOUT:
        assert row['row_tops'][1]-row['row_tops'][0]==44
        assert row['columns'][1]==row['value_bounds'][0]
        assert row['columns'][3]==row['action_bounds'][0]
        assert row['columns'][4]-row['columns'][3]-144==4
        cc=next(p['controls'] for p in base.CONTROLS if p['page']==row['page'])
        actions=[c for c in cc if c['role']=='detail-action']
        assert len({(c['width'],c['height']) for c in actions})==1
        assert [c['x'] for c in actions]==[row['columns'][3],row['columns'][3],row['columns'][4]]
    for page in base.CONTROLS:
        for role in ('source-action','footer-action'):
            cc=sorted([c for c in page['controls'] if c['role']==role],key=lambda c:c['x'])
            if len(cc)>1:
                assert len({(c['width'],c['height']) for c in cc})==1
                for left,right in zip(cc,cc[1:]):
                    gap=right['x']-left['x']-left['width'];assert gap==4
                    checks.append(dict(page=page['page'],pair=[left['label'],right['label']],width=left['width'],height=36,gap=gap))
        if 'joins' not in page['page']:
            labels=[c['label'] for c in page['controls']]
            assert not any(t in label for label in labels for t in ('MP4','統一素材','素材設定','輸出詳情','製作所選輸出'))
            assert all('→' not in label or label in ('來源詳情 →','檢查接點 →','查看詳情 →','補齊缺項 →','成品版本 →') for label in labels)
    manifest=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),shared_source_sha256=hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),images=base.SHOTS,controls=base.CONTROLS,layout=LAYOUT,button_pairs=checks)
    (OUT/'measurements.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,regions=base.REGIONS),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(base.SHOTS)} designs; {len(base.REGIONS)} scroll regions; {len(checks)} button pairs')
