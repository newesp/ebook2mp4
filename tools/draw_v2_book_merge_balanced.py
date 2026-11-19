"""Replacement assembly design; local actions follow their content horizontally."""
from pathlib import Path
import hashlib
import json
import draw_v2_book_merge as base

OUT = Path(__file__).resolve().parents[1]/'docs/ui-review/v2-book-merge-balanced'
OUT.mkdir(parents=True,exist_ok=True)
base.OUT=OUT
METRICS=[]


def render(w,h,mode='short',both=False,state='ready',expanded=False,end=False,file_mode='short'):
    name=f'{w}-'+('both-' if both else '')+(state if state!='ready' else mode)+('-settings' if expanded else '')+('-end' if end else '')+('-files-'+file_mode if file_mode!='short' else '')
    a=base.Drawing(w,h,name)
    busy=state=='running'
    x,top,right,bottom=a.shell(compact=w<1040,file_mode=file_mode)
    if w<1040:a.button(592,64,36,'›',role='icon')
    lx,rx=x+12,right-12
    y=top+12
    a.text(lx,y+8,'1 選批與順序',True)
    for i,label in enumerate(['重新檢查來源' if mode=='empty' else '選取有效批次','上移','下移','來源詳情']):
        a.button(lx+156+i*148,y,144,label,disabled=busy or mode=='empty' and i>0,role='source-action')
    rows=2 if both else 1
    output_y=bottom-8-44-rows*44
    join_y=output_y-44-(32 if expanded else 0)
    table_y=y+44
    table_end=join_y-8
    viewport=table_end-table_y-32
    rowh=40
    n=5 if mode=='short' else viewport//rowh if mode=='fit' else viewport//rowh+1 if mode=='overflow' else 48 if mode=='long' else 0
    content=viewport if mode=='fit' else 48 if mode=='empty' else n*rowh
    a.rect((lx,table_y,rx,table_y+32),'#edf1e9')
    for cx,label in [(12,'選取'),(64,'順序'),(120,'批次'),(rx-lx-310,'時長'),(rx-lx-216,'來源狀態')]:a.text(lx+cx,table_y+6,label)
    def paint(d,rw,ch):
        for i in range(n):
            yy=i*40
            invalid=mode=='short' and i==4
            if i==1:d.rectangle((0,yy,rw,yy+39),fill=base.SEL)
            d.line((0,yy+39,rw,yy+39),fill='#e7ebe4')
            d.rectangle((12,yy+12,25,yy+25),fill='#e1e5de' if busy else 'white',outline=base.LINE)
            if not invalid:d.line([(14,yy+18),(18,yy+22),(24,yy+14)],fill=base.GREEN,width=2)
            texts=[(64,'—' if invalid else str(i+1)),(120,['第一章','第二章','第三章','第四章','第五章'][i] if i<5 else f'第 {i+1} 章'),(rx-lx-310,'—' if invalid else '12:40'),(rx-lx-216,'待更新 · 未選取' if invalid else '有效 · MP3／SRT')]
            if state=='missing' and i==2:texts[-1]=(rx-lx-216,'待更新 · 已選取')
            for cx,t in texts:d.text((cx,yy+10),t,font=base.F,fill=base.WARN if invalid else base.INK)
        if n==0:d.text((16,14),'尚未載入來源。請按「重新檢查來源」。',font=base.F,fill=base.MUTED)
    a.region('合併來源清單',(lx,table_y+32,rx,table_end),content,paint,max(0,content-viewport) if end else 0,mode)
    # One bounded row for the shared join controls. No far-right button rail.
    a.text(lx,join_y+8,'2 交接停頓',True)
    a.button(lx+100,join_y,88,'0.5',drop=True,disabled=busy,role='input')
    a.text(lx+196,join_y+9,'秒')
    picked=4 if mode=='short' else n
    a.text(lx+232,join_y+9,f'{max(0,picked-1)} 個接點',color=base.MUTED)
    a.button(lx+332,join_y,144,'檢查接點',disabled=busy or picked<2,role='join-action')
    if expanded:a.text(lx,join_y+42,'全書共用 · 0～5 秒，可輸入小數；實際間隔另含來源頭尾靜音。',color=base.MUTED)
    a.text(lx,output_y+8,'3 要求輸出',True)
    for cx,label,checked in [(100,'總 MP3／SRT',True),(276,'總 MP4／SRT',both)]:
        a.check(lx+cx,output_y+11,checked,disabled=busy)
        a.text(lx+cx+20,output_y+8,label)
    a.button(lx+452,output_y,144,'成品版本',disabled=busy)
    formats=['MP3','MP4'] if both else ['MP3']
    for i,fmt in enumerate(formats):
        yy=output_y+44+i*44
        status='準備';reason='來源齊全，可開始製作。';action='查看詳情'
        if state in ('done','partial') and (i==0 or state=='done'):status='完成';reason='成功成品與同版 SRT 已保存。';action='成品操作'
        elif state=='partial':status='失敗';reason='影片製作失敗，成功音訊保留。'
        elif state=='missing':status='缺項';reason='請先更新第三章音訊。' if i==0 else '請至「影片製作」補齊設定。';action='補齊缺項'
        elif state=='running':status='執行中' if i==0 else '等待';reason='正在組裝總音訊 · 65%' if i==0 else '總音訊完成後接續製片。'
        elif state=='cancelled':status='已取消';reason='上一份成功成品保留。'
        elif state=='pending':status='保存失敗';reason='媒體已完成；請重試保存。'
        if mode=='empty':status='未檢查';reason='請先載入來源。'
        a.text(lx,yy+8,'總 '+fmt+'／SRT')
        a.text(lx+156,yy+8,status,color=base.WARN if status in ('缺項','失敗','保存失敗') else base.MUTED)
        a.button(lx+276,yy,144,action,drop=action=='成品操作',disabled=busy or mode=='empty',role='format-action')
        a.text(lx+432,yy+8,reason,color=base.MUTED)
        METRICS.append(dict(page=name,kind='status-action',status=status,distance=276-156-a.d.textlength(status,font=base.F)))
    primary='只重試未完成輸出 →' if state in ('partial','cancelled') else '重試保存' if state=='pending' else '輸出均已完成' if state=='done' else '製作所選輸出 →'
    summary='製作中 · 請等待或取消任務' if busy else '部分完成 · 成功成品保留' if state=='partial' else '缺項尚未補齊 · 請先處理來源／影片設定' if state=='missing' else '保存失敗 · 不需重新合成或編碼' if state=='pending' else '已取消 · 上次成功成品保留' if state=='cancelled' else '全部要求格式已完成並保存' if state=='done' else f'已選 {picked} 批 · 合併設定已儲存 · 本機處理'
    if mode=='empty':summary='尚未載入來源 · 請先重新檢查來源'
    a.footer(summary,primary,busy=busy,disabled=mode=='empty')
    if state=='missing':
        c=next(c for c in a.controls if c['label']==primary)
        a.controls.remove(c)
        a.button(c['x'],c['y'],c['width'],primary,disabled=True,role='footer-action')
    if busy:
        # Busy global commands that would change sources are also disabled.
        for c in list(a.controls):
            if c['label'] in ('匯入','管理'):
                a.controls.remove(c)
                a.button(c['x'],c['y'],c['width'],c['label'],drop=True,disabled=True)
    METRICS.append(dict(page=name,kind='space-budget',source_viewport=viewport,fixed_output_height=44+44*rows,join_top=join_y,output_top=output_y,toolbar_content_gap=8,full_width_action_columns=False))
    a.save()


if __name__=='__main__':
    for mode in ('empty','short','fit','overflow','long'):render(1360,820,mode)
    render(1360,820,'long',end=True)
    for w,h in ((1920,1000),(1280,720),(900,640)):render(w,h)
    for w,h in ((1360,820),(900,640)):
        render(w,h,both=True)
    for state in ('missing','partial','running','cancelled','pending','done'):render(1360,820,both=True,state=state)
    for mode in ('fit','overflow','long'):render(1360,820,file_mode=mode)
    # Existing join comparison is retained; it does not contain the rejected rail.
    for mode in ('short','fit','overflow','long'):base.joins(1360,820,mode)
    base.joins(900,640,'long',end=True)
    sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,regions=base.REGIONS),ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'measurements.json').write_text(json.dumps(dict(source_sha256=sha,shared_drawing_sha256=hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),images=base.SHOTS,controls=base.CONTROLS,layout=METRICS),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(base.SHOTS)} designs; {len(base.REGIONS)} scroll regions')
