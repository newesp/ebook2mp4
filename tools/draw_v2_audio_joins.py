"""Design-only audio joins: one measured layout drives PNGs and QA evidence."""
from pathlib import Path
import hashlib
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ui-review/v2-audio-joins'
BG,INK,MUTED,GREEN,LINE,SEL,WARN='#f5f6f2','#263d34','#58695f','#315d43','#c7d2c6','#e7efe4','#704c14'
REGIONS=[];PAGES=[]


class Drawing:
    def __init__(self,w,h,name,fs=14):
        self.w,self.h,self.name,self.fs=w,h,name,fs
        self.f=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',fs)
        self.b=ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc',fs)
        self.title=ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc',fs+2)
        self.hc=36 if fs==14 else 44
        self.lh=22 if fs==14 else 28
        self.im=Image.new('RGB',(w,h),BG);self.d=ImageDraw.Draw(self.im)
        self.controls=[];self.texts=[];self.regions=[];self.pairs=[]

    def rect(self,box,fill='white',edge=LINE):
        x,y,r,b=map(round,box)
        self.d.rectangle((x,y,r-1,b-1),fill=fill,outline=edge)

    def text(self,x,y,s,font=None,color=INK):
        font=font or self.f
        width=self.d.textlength(s,font=font)
        assert x>=0 and x+width<=self.w,(self.name,'text overflow',s,x,width)
        self.d.text((x,y),s,font=font,fill=color)
        self.texts.append(dict(text=s,x=x,y=y,width=width,font_px=font.size))

    def wrap(self,s,width,font=None):
        font=font or self.f
        lines=[]
        for paragraph in s.split('\n'):
            line=''
            for c in paragraph:
                if line and self.d.textlength(line+c,font=font)>width:lines.append(line);line=''
                line+=c
            lines.append(line)
        return lines

    def button(self,x,y,w,label,role='action',active=False,disabled=False,drop=False,up=False,focus=False):
        h=self.hc;tw=self.d.textlength(label,font=self.f)
        assert tw+24+(16 if drop else 0)<=w,(self.name,'clipped control',label,tw,w)
        self.rect((x,y,x+w,y+h),GREEN if active else '#e1e5de' if disabled else 'white')
        self.text(x+10,y+(h-self.lh)//2,label,color='white' if active else '#68736c' if disabled else INK)
        if drop:
            yy=y+h//2
            pts=[(x+w-20,yy-3),(x+w-10,yy-3),(x+w-15,yy+3)]
            if up:pts=[(xx,2*yy-yy2) for xx,yy2 in pts]
            self.d.polygon(pts,fill=INK)
        if focus:self.d.rectangle((x+2,y+2,x+w-3,y+h-3),outline=GREEN,width=1)
        c=dict(label=label,x=x,y=y,width=w,height=h,role=role,disabled=disabled,indicator_count=int(drop),focus=focus)
        self.controls.append(c);return c

    def equal_pair(self,left,right):
        assert left['width']==right['width'] and left['height']==right['height']
        gap=right['x']-left['x']-left['width'];assert gap==4
        self.pairs.append(dict(labels=[left['label'],right['label']],width=left['width'],height=left['height'],gap=gap))

    def region(self,owner,box,lines,state,end=False):
        x,y,r,b=box;view=b-y;pad=12
        content=len(lines)*self.lh+2*pad if lines else 0
        overflow=content>view;offset=max(0,content-view) if end else 0
        self.rect(box)
        width=r-x-2-(14 if overflow else 0)
        layer=Image.new('RGB',(width,max(1,content)),'white');d=ImageDraw.Draw(layer)
        for i,s in enumerate(lines):
            assert d.textlength(s,font=self.f)<=width-2*pad,(self.name,owner,'line overflow',s)
            d.text((pad,pad+i*self.lh),s,font=self.f,fill=INK)
        if content:self.im.paste(layer.crop((0,offset,width,min(content,offset+view))),(x+1,y))
        self.d=ImageDraw.Draw(self.im)
        if overflow:
            thumb=view*view/content;start=y+(view-thumb)*offset/(content-view)
            self.rect((r-14,y,r,b),'#edf1e9')
            self.rect((r-11,round(start),r-3,min(b,max(round(start)+1,round(start+thumb)))),'#9aaa9d','#9aaa9d')
        self.d.rectangle((x,y,r-1,b-1),outline=LINE)
        row=dict(page=self.name,state=state,owner=owner,direction='vertical',bounds=list(box),
                 viewport_height=view,content_height=content,scrollbar_visible=overflow,max_offset=max(0,content-view),
                 rendered_offset=offset,measurement_source='tools/draw_v2_audio_joins.py: Drawing.region; same wrapped lines, padding, line height and bounds',
                 **({'thumb_fraction':view/content} if overflow else {}))
        REGIONS.append(row);self.regions.append(row)
        return row

    def plain_region(self,owner,box,state):
        return self.region(owner,box,[],state)

    def shell(self,files_mode='short',file_view=False,empty=False,preparing=False):
        w,h,H=self.w,self.h,self.hc
        stepw=max(140,math.ceil(self.d.textlength('2 試聽與製作',font=self.f))+24)
        self.equal_pair(self.button(16,16,stepw,'1 文稿',role='global-step'),self.button(20+stepw,16,stepw,'2 試聽與製作',role='global-step',active=True))
        floww=144 if self.fs==14 else 156
        flow_width=floww*4+28*2+24
        wide=w>=16+2*stepw+4+16+flow_width+16+80+12+224+16
        band_gap=8 if self.fs==18 else 12
        ny=16 if wide else 16+H+band_gap;nx=16+2*stepw+4+16 if wide else 16
        for i,(width,label,selected) in enumerate(((floww,'語音設定與試聽',False),(floww,'音訊製做',False),(floww,'全書合併',True),(floww,'影片製作',False))):
            self.button(nx,ny,width,label,role='flow',active=selected);nx+=width
            if i<2:self.text(nx+4,ny+(H-self.lh)//2,'→');nx+=28
            elif i==2:self.d.line((nx+12,ny,nx+12,ny+H),fill=LINE);nx+=24
        self.button(w-236,16,108,'專案',role='project',drop=True)
        self.button(w-124,16,108,'訊息記錄',role='messages')
        self.text(w-352,16+(H-self.lh)//2,'靈性開悟')
        hy=16+H+20 if wide else ny+H+band_gap
        narrow=w<1040
        if narrow:
            if not file_view:
                c=self.button(16,hy,112,'文件列表',role='document-disclosure')
                c.update(accessible_name='顯示文件列表',expanded=False,help='在同一工作區開啟文件列表，返回保留接點。',keyboard='Space / Enter')
            x=16;title_x=16 if file_view else 140
        else:
            c=self.button(16,hy,36,'‹',role='document-icon')
            c.update(accessible_name='隱藏文件列表',expanded=True,help='隱藏文件列表，擴大接點文字區。',keyboard='Space / Enter')
            self.button(56,hy,80,'匯入',role='document-menu',drop=True,disabled=preparing)
            self.button(140,hy,84,'管理',role='document-menu',drop=True,disabled=preparing)
            x=236;title_x=x
        title='文件列表' if file_view else '檢查接點'
        self.text(title_x,hy+(H-self.lh)//2-1,title,font=self.title)
        if not narrow:self.text(title_x+112,hy+(H-self.lh)//2,'對照前後文字，調整停頓並試聽',color=MUTED)
        top=hy+H+12;bottom=h-72 if empty else h-(H+68)
        self.rect((x,top,w-16,bottom))
        if not narrow:
            self.files((16,top,224,bottom),files_mode)
        return x,top,w-16,bottom

    def files(self,box,mode,end=False):
        x,y,r,b=box
        rh=max(64,2*self.lh+16);vh=b-y
        row_lines=max(3,math.ceil(rh/self.lh))
        actual_rh=row_lines*self.lh
        n=4 if mode=='short' else max(1,(vh-24)//actual_rh) if mode=='fit' else max(1,(vh-24)//actual_rh)+1 if mode=='overflow' else 40
        lines=[]
        # Fixed row spacing is represented by actual blank lines, not an invented
        # content=viewport assignment for the fit counterexample.
        for i in range(n):
            lines.extend([f'第 {i+1} 章 · PDF', '音訊可用']+['']*(row_lines-2))
        self.region('文件列表',box,lines,mode,end=end)

    def footer(self,state,warning=False,checked=False,details=False,file_view=False):
        H=self.hc;y=self.h-60
        if file_view:
            self.text(16,self.h-91,'返回會恢復原接點、停頓與閱讀位置。',color=MUTED)
            self.button(16,y,196,'← 返回接點文字',role='footer-back');return
        if warning:
            wy=y-H-4
            self.rect((16,wy-4,self.w-16,y-4),'#faf4e5')
            cy=wy+H//2
            self.rect((26,cy-7,40,cy+7),'white')
            if checked:self.d.line([(28,cy),(32,cy+4),(38,cy-4)],fill=GREEN,width=2)
            text='我已檢查第 8 頁重疊，保留此接點'
            self.text(48,cy-self.lh//2,text,color=WARN)
            tw=math.ceil(self.d.textlength(text,font=self.f))
            self.controls.append(dict(label=text,x=26,y=wy,width=22+tw,height=H,role='acknowledgement',disabled=state=='preparing',indicator_count=0))
            xx=48+tw+4
            c=self.button(xx,wy,112,'收合詳情' if details else '警告詳情',role='warning-disclosure',drop=True,up=details)
            c.update(expanded=details,accessible_name='收合警告詳情' if details else '展開警告詳情',keyboard='Space / Enter')
            self.text(xx+128,wy+(H-self.lh)//2,'此接點已確認' if checked else '未確認將阻擋合併',color=MUTED if checked else WARN)
        elif state!='empty':
            status='請返回選取至少兩個有效批次。' if state=='empty' else '設定保存失敗，輸入已保留。' if state=='save-failed' else '設定尚未儲存；返回會保留輸入。'
            self.text(16,self.h-91,status,color=WARN if state=='save-failed' else MUTED)
        self.button(16,y,168,'← 返回全書合併',role='footer-back')
        if state!='empty':self.button(self.w-212,y,196,'重試儲存並返回' if state=='save-failed' else '儲存並返回',role='footer-commit',active=state!='preparing',disabled=state=='preparing')

    def finish(self,extra):
        for i,c in enumerate(self.controls):
            assert c['x']>=0 and c['y']>=0 and c['x']+c['width']<=self.w and c['y']+c['height']<=self.h,(self.name,c)
            for b in self.controls[i+1:]:
                assert not (min(c['x']+c['width'],b['x']+b['width'])>max(c['x'],b['x']) and min(c['y']+c['height'],b['y']+b['height'])>max(c['y'],b['y'])),(self.name,c['label'],b['label'])
        self.im.save(OUT/(self.name+'.png'))
        PAGES.append(dict(page=self.name,size=[self.w,self.h],font_px=self.fs,control_height=self.hc,controls=self.controls,texts=self.texts,button_pairs=self.pairs,**extra))


def render(w,h,mode='short',state='ready',fs=14,warning=False,details=False,checked=False,file_view=False,files_mode=None,end=False,detail_mode=None):
    name=f'{w}x{h}-{mode if state=="ready" else state}'+('-18px' if fs==18 else '')+('-warning' if warning else '')+('-details' if details else '')+('-checked' if checked else '')+('-files' if file_view else '')+('-end' if end else '')
    a=Drawing(w,h,name,fs);H=a.hc;lh=a.lh
    x,top,right,bottom=a.shell(files_mode or mode,file_view,state=='empty',state=='preparing')
    lx,rx=x+12,right-12;inner=rx-lx
    if file_view:
        a.files((lx,top+12,rx,bottom-12),mode,end)
        a.footer(state,file_view=True);a.finish(dict(view='documents',reader_viewports=[]));return
    sy=top+12
    if state=='empty':
        box=(lx,sy,rx,bottom-12)
        a.plain_region('接點空狀態',box,'empty')
        a.text(lx+16,sy+24,'尚無接點可檢查',font=a.title)
        a.text(lx+16,sy+56,'返回全書合併，選取至少兩個有效批次。',color=MUTED)
        a.footer(state);a.finish(dict(view='empty',reader_viewports=[]));return
    a.text(lx,sy+(H-lh)//2,'接點')
    picker=a.button(lx+64,sy,inner-64-232,'沒有可檢查的接點' if state=='empty' else '1／3　第一章 → 第二章',role='pair-selector',drop=True,disabled=state in ('empty','preparing'))
    prev=a.button(rx-228,sy,112,'上一個',role='pair-navigation',disabled=True)
    nxt=a.button(rx-112,sy,112,'下一個',role='pair-navigation',disabled=state in ('empty','preparing'))
    a.equal_pair(prev,nxt)
    hints='停頓套用全書；實際間隔另含來源頭尾靜音，新增停頓期間字幕留白。'
    if state=='playing':hints='正在試聽：第一章結尾 → 新增停頓 0.5 秒 → 第二章開頭。'
    elif state=='failed':hints='試聽失敗：第二章音訊無法讀取。請更新來源後重試。'
    elif state=='cancelled':hints='試聽準備已取消，停頓與接點選取保留。'
    elif state=='save-failed':hints='設定未寫入，請釋放空間後重試儲存。'
    lines=a.wrap(hints,inner)
    hint_height=len(lines)*lh
    options_top=bottom-12-(H+8+len(lines)*lh)
    labelw=80;valuew=120;gw=16
    a.text(lx,options_top+(H-lh)//2,'交接停頓')
    a.button(lx+labelw,options_top,valuew,'0.5 秒',role='value',drop=True,disabled=state=='preparing',focus=fs==18)
    assert a.d.textlength('0.123 秒',font=a.f)+40<=valuew
    clipx=lx+labelw+valuew+gw
    a.text(clipx,options_top+(H-lh)//2,'前後各播')
    a.button(clipx+labelw,options_top,valuew,'5 秒',role='value',drop=True,disabled=state=='preparing')
    # Form fields align to the left reader. Playback aligns to the right reader.
    playx=lx+(inner-12)//2+12
    assert clipx+labelw+valuew<=playx-12
    p=a.button(playx,options_top,valuew,'準備中' if state=='preparing' else '重試試聽' if state=='failed' else '播放接點',role='playback',active=state not in ('preparing','playing'),disabled=state in ('preparing','playing'))
    s=a.button(playx+valuew+4,options_top,valuew,'取消準備' if state=='preparing' else '停止試聽',role='playback',disabled=state not in ('preparing','playing'))
    a.equal_pair(p,s)
    assert s['x']+s['width']<=rx
    hy=options_top+H+8
    if state=='preparing':
        a.rect((lx,hy+4,lx+112,hy+14),'#e3e9df');a.rect((lx+36,hy+4,lx+72,hy+14),GREEN,GREEN)
        a.text(lx+124,hy,'正在驗證來源並準備試聽…',color=MUTED)
    else:
        for i,line in enumerate(lines):a.text(lx,hy+i*lh,line,color=WARN if state in ('failed','save-failed') else MUTED)
    header_y=sy+H+8;reader_y=header_y+H+8;reader_bottom=options_top-8
    detail_mode=detail_mode or mode
    metadata='來源：晨間讀書筆記.pdf\n前批：第一章 · 物理頁 1～8\n後批：第二章 · 物理頁 8～15\n第 8 頁同時出現在兩批，可能重複朗讀。\n本頁保存接點確認；文字修正請使用校對入口。'
    if detail_mode=='long' and details:metadata+='\n'+'\n'.join(f'來源補充 {i+1}：同一來源文件的實際頁次與批次安排。' for i in range(30))
    detail_lines=a.wrap(metadata,inner-40)
    detail_height=len(detail_lines)*lh+24
    inline=details and detail_mode not in ('fit','overflow','long') and reader_bottom-reader_y-detail_height-8>=6*lh+24
    dedicated=details and not inline
    viewports=[]
    if dedicated:
        a.text(lx,header_y+(H-lh)//2,'頁碼重疊 · 第 8 頁',font=a.b,color=WARN)
        e1=a.button(rx-260,header_y,128,'校對前批 →',role='edit',disabled=state=='preparing')
        e2=a.button(rx-128,header_y,128,'校對後批 →',role='edit',disabled=state=='preparing');a.equal_pair(e1,e2)
        if detail_mode in ('fit','overflow'):
            count=(reader_bottom-reader_y-24)//lh+(detail_mode=='overflow')
            detail_lines=(detail_lines+[f'補充 {i+1}：本次接點的來源範圍。' for i in range(count)])[:count]
        r=a.region('警告詳情',(lx,reader_y,rx,reader_bottom),detail_lines,detail_mode,end)
        viewports.append(r['viewport_height'])
    else:
        if inline:
            wy=reader_bottom-detail_height;reader_bottom=wy-8
            a.region('警告詳情',(lx,wy,rx,wy+detail_height),detail_lines,detail_mode)
        pane_w=(inner-12)//2
        for side,left in enumerate((lx,lx+pane_w+12)):
            rr=left+pane_w
            title=('前批字幕 · 第一章' if side==0 else '後批字幕 · 第二章') if state=='playing' else ('前批結尾 · 第一章' if side==0 else '後批開頭 · 第二章')
            # Wrap only labels; action frames remain the same size on each side.
            title_lines=a.wrap(title,pane_w-132,font=a.b)
            assert len(title_lines)*lh<=H,(name,'reader heading too tall')
            for i,t in enumerate(title_lines):a.text(left,header_y+(H-len(title_lines)*lh)//2+i*lh,t,font=a.b)
            a.button(rr-128,header_y,128,'校對前批 →' if side==0 else '校對後批 →',role='edit',disabled=state=='preparing')
            box=(left,reader_y,rr,reader_bottom);vh=reader_bottom-reader_y
            assert vh>=4*lh+24,(name,'insufficient reader',vh,lh)
            fit=max(1,(vh-24)//lh)
            n=3 if mode=='short' else fit if mode=='fit' else fit+1 if mode=='overflow' and side==0 else fit if mode=='overflow' else 180
            if end and w>=1040 and side==1:n=3
            lines=[('前批' if side==0 else '後批')+f'第 {i+1} 行：把注意力帶回當下。' for i in range(n)]
            if mode=='short':lines=['當你停止追逐念頭，','注意力便回到此刻。','覺察，就從這一刻開始。'] if side==0 else ['先留意你的呼吸，','感受吸氣與吐氣的節奏。','讓注意力安穩地停在當下。']
            for i,line in enumerate(lines):
                if a.d.textlength(line,font=a.f)>pane_w-40:lines[i]=f'第 {i+1} 行：帶回當下。'
            r=a.region('前批結尾' if side==0 else '後批開頭',box,lines,mode,end=end and side==0)
            viewports.append(r['viewport_height'])
            assert reader_y-(header_y+H)==8
    a.footer(state,warning,checked,details)
    a.finish(dict(view='warning-detail' if dedicated else 'comparison',warning_inline=inline,
                  reader_viewports=viewports,panel_content_top=reader_y,options_top=options_top,
                  toolbar_text_gap=8,text_line_height=lh,minimum_full_lines=4,
                  settings_bounds=[lx,options_top,rx,bottom-12],settings_content_height=H+8+hint_height))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for w,h in ((1920,1000),(1360,820),(1280,720),(900,640)):
        for mode in ('short','fit','overflow','long'):render(w,h,mode,end=mode=='long')
    for mode in ('short','fit','overflow','long'):render(900,640,mode,fs=18,end=mode=='long')
    render(1360,820,warning=True)
    render(1360,820,warning=True,details=True)
    render(1360,820,warning=True,checked=True)
    render(900,640,warning=True)
    render(900,640,'long',warning=True,details=True,end=True)
    for mode in ('short','fit','overflow'):render(900,640,mode,warning=True,details=True)
    render(900,640,fs=18,warning=True)
    render(900,640,fs=18,warning=True,details=True)
    for mode in ('fit','overflow','long'):
        render(1360,820,mode,warning=True,details=True,detail_mode='short',end=mode=='long')
        render(900,640,mode,fs=18,warning=True,details=True,end=mode=='long')
    for state in ('empty','preparing','playing','failed','cancelled','save-failed'):render(1360,820,state=state)
    for mode in ('short','fit','overflow','long'):render(900,640,mode,file_view=True,end=mode=='long')
    for page in PAGES:
        if 'settings_bounds' in page:
            x,y,r,b=page['settings_bounds']
            assert b-y==page['settings_content_height']
            REGIONS.append(dict(page=page['page'],state='fixed-controls',owner='設定與試聽操作列',direction='none',
                bounds=[x,y,r,b],viewport_height=b-y,content_height=page['settings_content_height'],
                scrollbar_visible=False,max_offset=0,rendered_offset=0,
                measurement_source='tools/draw_v2_audio_joins.py: control height + 8px gap + actual wrapped hint height'))
    source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/'measurements.json').write_text(json.dumps(dict(source_sha256=source,scope='design only; runtime pending',pages=PAGES),ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,regions=REGIONS),ensure_ascii=False,indent=2),encoding='utf-8')
    role_sizes={};viewports=[]
    for page in PAGES:
        for role in ('value','playback','edit','pair-navigation','flow','global-step'):
            controls=[c for c in page['controls'] if c['role']==role]
            if controls:
                sizes={(c['width'],c['height']) for c in controls};assert len(sizes)==1
                role_sizes.setdefault(role,set()).update(sizes)
        if page['view']=='comparison':
            group=[c for c in page['controls'] if c['role'] in ('value','playback')]
            assert len({(c['width'],c['height']) for c in group})==1
            viewports.append(dict(page=page['page'],heights=page['reader_viewports'],
                full_lines=[(v-24)//page['text_line_height'] for v in page['reader_viewports']],
                header_text_gap=page['toolbar_text_gap']))
    for owner in ('前批結尾','後批開頭','文件列表','警告詳情'):
        assert {'short','fit','overflow','long'}<={r['state'] for r in REGIONS if r['owner']==owner}
    font18=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',18);caption=font18.getlength('校對前批 →')
    assert 112<caption+24<=128
    qa=dict(source_sha256=source,scope='design geometry; native input and EXE pending',images=len(PAGES),regions=len(REGIONS),
        role_sizes={k:sorted(v) for k,v in role_sizes.items()},viewport_checks=viewports,
        counterexample=dict(label='校對前批 →',font_px=18,caption_width=caption,padding=24,old_frame=112,required=caption+24,new_frame=128,old_fails=True,new_passes=True))
    (OUT/'design-checks.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    for start in range(0,len(PAGES),6):
        sheet=Image.new('RGB',(1360,3*438),BG);d=ImageDraw.Draw(sheet)
        for j,page in enumerate(PAGES[start:start+6]):
            im=Image.open(OUT/(page['page']+'.png'));im.thumbnail((672,402))
            x=(j%2)*680;y=(j//2)*438
            d.text((x+8,y+4),page['page'],font=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',14),fill=INK)
            sheet.paste(im,(x+4,y+30))
        sheet.save(OUT/f'index-{start//6+1}.png')
    print(f'{len(PAGES)} designs; {len(REGIONS)} measured regions; source {source}')


if __name__=='__main__':main()
