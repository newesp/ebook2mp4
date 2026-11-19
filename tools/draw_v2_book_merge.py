"""Design-only book assembly drawings. Geometry and scroll evidence share data."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'docs/ui-review/v2-book-merge-redraw'
OUT.mkdir(parents=True, exist_ok=True)
INK, MUTED, GREEN = '#263d34', '#58695f', '#315d43'
LINE, BG, SEL, WARN = '#c7d2c6', '#f5f6f2', '#e7efe4', '#704c14'
F = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 14)
B = ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc', 16)
REGIONS, CONTROLS, SHOTS = [], [], []


class Drawing:
    def __init__(self, w, h, name):
        self.w, self.h, self.name = w, h, name
        self.im = Image.new('RGB', (w, h), BG)
        self.d = ImageDraw.Draw(self.im)
        self.controls = []

    def rect(self, box, fill='white', edge=LINE):
        self.d.rectangle((box[0], box[1], box[2]-1, box[3]-1), fill=fill, outline=edge)

    def text(self, x, y, s, bold=False, color=INK):
        self.d.text((x, y), s, font=B if bold else F, fill=color)

    def button(self, x, y, w, label, active=False, drop=False, disabled=False, role='action'):
        self.rect((x, y, x+w, y+36), GREEN if active else '#e1e5de' if disabled else 'white')
        tw = self.d.textlength(label, font=F)
        assert tw+20+(16 if drop else 0) <= w, (self.name, label, tw, w)
        self.text(x+10, y+8, label, color='white' if active else '#68736c' if disabled else INK)
        if drop:
            self.d.polygon([(x+w-20, y+15), (x+w-10, y+15), (x+w-15, y+21)], fill=INK)
        self.controls.append(dict(label=label, x=x, y=y, width=w, height=36, role=role))

    def check(self, x, y, checked=True, disabled=False):
        self.rect((x, y, x+14, y+14), '#e1e5de' if disabled else 'white')
        if checked:
            self.d.line([(x+2, y+7), (x+6, y+11), (x+12, y+3)], fill=GREEN, width=2)

    def region(self, owner, box, content_h, paint, offset=0, state=''):
        x, y, right, bottom = box
        vh = bottom-y
        assert vh > 0
        offset = min(offset, max(0, content_h-vh))
        overflow = content_h > vh
        self.rect(box)
        layer = Image.new('RGB', (right-x-2-(14 if overflow else 0), max(1, content_h)), 'white')
        paint(ImageDraw.Draw(layer), layer.width, content_h)
        if content_h:
            self.im.paste(layer.crop((0, offset, layer.width, min(content_h, offset+vh))), (x+1, y))
        self.d = ImageDraw.Draw(self.im)
        if overflow:
            track = vh
            thumb = track*vh/content_h
            start = y+(track-thumb)*offset/(content_h-vh)
            self.rect((right-13, y, right, bottom), '#edf1e9')
            # A one-pixel raster minimum only; the mathematical ratio is retained.
            self.rect((right-11, min(bottom-1, round(start)), right-2, min(bottom, max(round(start)+1, round(start+thumb)))), '#9aaa9d', '#9aaa9d')
        REGIONS.append(dict(page=self.name, state=state or self.name, owner=owner, direction='vertical',
                            bounds=list(box), viewport_height=vh, content_height=content_h,
                            scrollbar_visible=overflow, max_offset=max(0, content_h-vh),
                            rendered_offset=offset, measurement_source='tools/draw_v2_book_merge.py: Drawing.region; same box and rendered layer height',
                            **({'thumb_fraction':vh/content_h} if overflow else {})))

    def shell(self, compact=False, file_mode='short'):
        w, h = self.w, self.h
        narrow, two = w < 1040, w < 1360
        self.button(16, 16, 104, '1 文稿', role='global')
        self.button(124, 16, 140, '2 試聽與製作', True, role='global')
        navy = 64 if two else 16
        nx = 16 if two else 280
        if not two:
            self.d.line((272, navy, 272, navy+36), fill=LINE)
        for index, (bw, s, selected) in enumerate([(156, '語音設定與試聽', False), (112, '音訊製做', False), (112, '全書合併', True), (112, '影片製作', False)]):
            self.button(nx, navy, bw, s, selected, role='navigation')
            nx += bw
            if index < 2:
                self.text(nx+4, navy+8, '→')
                nx += 28
            elif index == 2:
                self.d.line((nx+12, navy, nx+12, navy+36), fill=LINE)
                nx += 24
        self.button(w-236, 16, 108, '專案', drop=True, role='global')
        self.button(w-124, 16, 108, '訊息記錄', role='global')
        self.text(w-352, 24, '靈性開悟')
        top = 117 if compact and narrow else 166 if two else 121
        y = top-49
        if compact and narrow:
            x = 16
        elif narrow:
            self.button(16, y, 36, '›', role='icon')
            x = 64
        else:
            self.button(16, y, 36, '‹', role='icon')
            self.button(56, y, 80, '匯入', drop=True)
            self.button(140, y, 84, '管理', drop=True)
            x = 236
            file_vh=h-104-top
            file_n=5 if file_mode=='short' else file_vh//64 if file_mode=='fit' else file_vh//64+1 if file_mode=='overflow' else 40
            def files(d, rw, ch):
                for i in range(file_n):
                    t=['第一章 · PDF 1–8', '第二章 · PDF 9–15', '第三章 · PDF 16–24', '第四章 · TXT', '第五章 · TXT'][i] if i<5 else f'第 {i+1} 章 · TXT'
                    yy = i*64
                    d.text((12, yy+10), t, font=F, fill=INK)
                    d.text((12, yy+34), '音訊可用' if i < 4 else '音訊待更新', font=F, fill=MUTED)
            self.region('文件清單', (16, top, 224, h-104), file_vh if file_mode=='fit' else file_n*64, files, state=file_mode)
        if not (compact and narrow):
            self.text(x, y+7, '全書合併', True)
            self.text(x+110, y+9, '選批與排序 → 檢查接點 → 製作輸出')
        self.rect((x if not narrow else 16, top, w-16, h-104))
        return (x if not narrow else 16), top, w-16, h-104

    def footer(self, summary, primary='製作所選輸出 →', join=False, busy=False, disabled=False):
        h, w = self.h, self.w
        self.text(16, h-93, summary, color=MUTED)
        self.button(16, h-60, 168, '← 返回全書合併' if join else '← 返回音訊製做', role='footer-back')
        if busy:
            self.button(w-184, h-60, 168, '取消任務', role='footer-action')
        else:
            labels = [('儲存設定並返回 →', 196)] if join else [('儲存合併設定', 196), (primary, 196)]
            start = w-16-sum(v for _, v in labels)-4*(len(labels)-1)
            for i, (s, bw) in enumerate(labels):
                off=s=='輸出均已完成' or disabled
                self.button(start, h-60, bw, s, active=i==len(labels)-1 and not off, disabled=off, role='footer-action')
                start += bw+4

    def save(self):
        for i, a in enumerate(self.controls):
            assert 0 <= a['x'] and a['x']+a['width'] <= self.w
            assert 0 <= a['y'] and a['y']+a['height'] <= self.h
            for b in self.controls[i+1:]:
                overlap = min(a['x']+a['width'], b['x']+b['width']) > max(a['x'], b['x']) and min(a['y']+a['height'], b['y']+b['height']) > max(a['y'], b['y'])
                assert not overlap, (self.name, a['label'], b['label'])
        self.im.save(OUT / (self.name+'.png'))
        CONTROLS.append(dict(page=self.name, controls=self.controls))
        SHOTS.append(dict(name=self.name, size=[self.w, self.h]))


def merge(w, h, mode='short', settings=False, status='ready', bottom=False, file_mode='short', video_route='unified', route_menu=False):
    name = f'{w}-merge-'+('settings' if settings else status if status != 'ready' else mode)+('-end' if bottom else '')+('-files-'+file_mode if file_mode!='short' else '')+('-batch-videos' if video_route=='batches' else '')+('-route-menu' if route_menu else '')
    a = Drawing(w, h, name)
    x, top, right, base = a.shell(file_mode=file_mode)
    lx, rx = x+12, right-12
    y = top+12
    a.text(lx, y+8, '1 選取批次與順序', True)
    bwidth = 152 if w < 1040 else 168
    start = rx-bwidth*4-12
    for s in ['重新檢查來源' if mode=='empty' else '選取有效批次', '上移', '下移', '來源詳情']:
        a.button(start, y, bwidth, s, disabled=status=='running' or mode=='empty' and s!='重新檢查來源', role='source-action')
        start += bwidth+4
    table_y = y+44
    outputs_top = base-142
    settings_y = outputs_top-48
    table_b = settings_y-8
    heading_h, rowh = 32, 40
    vh = table_b-(table_y+heading_h)
    names = ['第一章', '第二章', '第三章', '第四章', '第五章']
    n = 5 if mode=='short' else vh//rowh if mode=='fit' else vh//rowh+1 if mode=='overflow' else 48 if mode=='long' else 0
    content = vh if mode=='fit' else 48 if mode=='empty' else n*rowh
    a.rect((lx, table_y, rx, table_y+heading_h), '#edf1e9')
    cols = [lx+12, lx+64, lx+120, rx-310, rx-216]
    for cx, t in zip(cols, ['選取', '順序', '批次', '時長', '音訊／影片來源' if video_route=='batches' else '音訊來源']):
        a.text(cx, table_y+6, t)
    def paint(d, rw, ch):
        for i in range(n):
            yy=i*rowh
            invalid = mode=='short' and i==4
            if i==1:
                d.rectangle((0, yy, rw, yy+rowh-1), fill=SEL)
            d.line((0, yy+rowh-1, rw, yy+rowh-1), fill='#e7ebe4')
            d.rectangle((12, yy+12, 25, yy+25), fill='white', outline=LINE)
            if not invalid:
                d.line([(14, yy+18), (18, yy+22), (24, yy+14)], fill=GREEN, width=2)
            vals = ['—' if invalid else str(i+1), names[i] if i<5 else f'第 {i+1} 章', '—' if invalid else '12:40', '待更新 · 尚未選取' if invalid else '可用 · MP3／SRT']
            if video_route=='batches' and not invalid:vals[-1]='MP3 可用 · MP4 缺項' if i==2 else 'MP3／MP4 可用'
            for cx, t in zip([64,120,rx-lx-310,rx-lx-216], vals):
                d.text((cx, yy+(rowh-20)//2), t, font=F, fill=WARN if invalid and cx>200 else INK)
        if n==0:
            d.text((16, 16), '尚未載入來源。請先按「重新檢查來源」。', font=F, fill=MUTED)
    a.region('合併來源清單', (lx, table_y+heading_h, rx, table_b), content, paint,
             offset=max(0,content-vh) if bottom else 0, state=mode)
    if settings:
        a.text(lx, settings_y+9, '額外交接停頓')
        a.button(lx+104, settings_y, 92, '0.5', drop=True, role='input')
        a.text(lx+204, settings_y+9, '秒')
        if w>=1040:
            a.text(lx+236, settings_y+9, '全書共用 · 0～5 秒，可手動輸入', color=MUTED)
    else:
        picked=4 if mode=='short' else n
        a.text(lx, settings_y+9, f'停頓 0.5 秒 · 接點 {max(0,picked-1)}／{max(0,picked-1)} 已檢查', color=MUTED)
    a.button(rx-340, settings_y, 168, '檢查接點', disabled=status=='running' or mode=='empty', role='join-action')
    a.button(rx-168, settings_y, 168, '收合停頓設定' if settings else '調整停頓', disabled=status=='running', role='join-action')
    oy=outputs_top
    a.text(lx, oy+7, '2 選擇輸出', True)
    if w>=1040:
        a.text(lx+146, oy+9, '本機處理 · 不傳送文字', color=MUTED)
    a.button(rx-168, oy, 168, '成品版本', disabled=status=='running')
    for i, fmt in enumerate(['MP3／SRT', 'MP4／SRT']):
        yy=oy+42+i*44
        a.check(lx+4, yy+11, disabled=status=='running')
        a.text(lx+26, yy+8, '總 '+fmt)
        outcome = '已完成' if status in ('partial','done') and i==0 or status=='done' else '執行中 · 65%' if status=='running' and i==0 else '失敗 · 可重試' if status=='partial' and i==1 else '尚未製作'
        if video_route=='batches' and i==1:outcome='缺項 · 第三章影片'
        a.text(lx+166, yy+8, outcome, color=WARN if '失敗' in outcome else MUTED)
        if i==1:
            a.button(rx-340, yy, 168, '沿用各批影片' if video_route=='batches' else '統一素材', drop=True, disabled=status=='running', role='video-route')
        a.button(rx-168, yy, 168, '檢查批次影片' if video_route=='batches' and i==1 else '成品操作' if outcome=='已完成' else '素材設定' if i==1 else '輸出詳情', drop=outcome=='已完成', disabled=status=='running', role='output-action')
        if outcome=='執行中 · 65%':
            a.rect((lx+340, yy+15, rx-180, yy+22), '#edf1e9')
            a.rect((lx+340, yy+15, lx+340+round((rx-180-lx-340)*.65), yy+22), GREEN, GREEN)
    summary = '部分完成 · MP3 已保存，MP4 失敗。成功成品保留。' if status=='partial' else '製作中 · 正在組裝總音訊；來源、排序與設定已鎖定。' if status=='running' else '全部要求已完成 · MP3／SRT、MP4／SRT 已保存。' if status=='done' else '已選 4 批 · 共 50:41.5 · 設定已儲存 · 可製作'
    if mode=='empty':summary='尚未載入來源 · 請先重新檢查來源'
    elif mode!='short':summary=f'已選 {n} 批 · 停頓 0.5 秒 · 設定已儲存 · 可製作'
    if video_route=='batches':summary='第三章影片缺項 · 可先製作 MP3 · 沿用各批影片不要求總音訊或全片素材'
    a.footer(summary, '先製作可用音訊 →' if video_route=='batches' else '只重試未完成輸出 →' if status=='partial' else '輸出均已完成' if status=='done' else '製作所選輸出 →', busy=status=='running', disabled=mode=='empty')
    if route_menu:
        # Native menu overlay; intentionally covers content until selection closes it.
        mx,my=rx-340,oy+42+44-74
        a.rect((mx,my,mx+168,my+72))
        a.rect((mx+1,my+1,mx+167,my+36),SEL,SEL)
        a.text(mx+12,my+8,'統一素材')
        a.text(mx+12,my+44,'沿用各批影片')
    a.save()


def prose(a, owner, box, mode, side=0, end=False):
    lh=28
    vh=box[3]-box[1]
    count=3 if mode=='short' else vh//lh if mode=='fit' else vh//lh+1 if mode=='overflow' else 38
    content=vh if mode=='fit' else count*lh
    lines = ['我們沿著文字的節奏，', '走過一段又一段故事。', '這一章，我們先讀到這裡。'] if not side else ['晨光落在翻開的書頁上。', '新的一章，從此刻開始。', '我們繼續向前閱讀。']
    def paint(d, rw, ch):
        for i in range(count):
            t=lines[i] if i<3 else f'第 {i+1} 行。保留朗讀稿的順序。'
            d.text((12,i*lh+4), t, font=F, fill=INK)
    a.region(owner, box, content, paint, max(0,content-vh) if end else 0, mode)


def joins(w, h, mode='short', end=False):
    a=Drawing(w,h,f'{w}-joins-{mode}'+('-end' if end else ''))
    x, top, right, base = a.shell(compact=True)
    lx, rx=x+12, right-12
    if w>=1040:
        a.text(lx,top+10,'檢查接點',True)
        a.text(lx+112,top+12,'對照音訊對應的朗讀稿，再試聽',color=MUTED)
    sy=top+40 if w>=1040 else top+4
    a.button(lx,sy,rx-lx-344,'1／3　第一章 → 第二章',drop=True,role='pair')
    a.button(rx-340,sy,168,'上一個',disabled=True,role='pair-nav')
    a.button(rx-168,sy,168,'下一個',role='pair-nav')
    py=sy+44
    tools_y=base-(150 if w>=1040 else 126)
    warning_y=tools_y-54
    pb=warning_y-8
    mid=(lx+rx)//2
    for side,(left,rr,title) in enumerate([(lx,mid-6,'前批結尾 · 第一章'),(mid+6,rx,'後批開頭 · 第二章')]):
        a.text(left,py,title,True)
        prose(a,'前批結尾' if side==0 else '後批開頭',(left,py+28,rr,pb-44),mode,side,end)
        a.button(left,pb-36,rr-left,'校對前批結尾' if side==0 else '校對後批開頭',role='edit-excerpt')
    a.rect((lx,warning_y,rx,tools_y-6),'#faf4e5')
    a.text(lx+10,warning_y+4,'頁碼重疊 · 第 8 頁可能重讀',color=WARN)
    a.check(lx+10,warning_y+27,False)
    a.text(lx+32,warning_y+24,'我已檢查此接點，保留內容並繼續',color=WARN)
    a.text(lx,tools_y+9,'額外交接停頓')
    a.button(lx+108,tools_y,92,'0.5',drop=True,role='input')
    a.text(lx+208,tools_y+9,'秒 · 全書共用')
    a.text(rx-236,tools_y+9,'前後各播')
    a.button(rx-136,tools_y,92,'5',drop=True,role='input')
    a.text(rx-36,tools_y+9,'秒')
    a.text(lx,tools_y+44,'前批結尾 → 新增靜音 0.5 秒 → 後批開頭',color=MUTED)
    a.text(lx,tools_y+68 if w>=1040 else tools_y+98,'實際間隔另含來源頭尾靜音；新增靜音不顯示字幕。',color=MUTED)
    play_y=tools_y+(102 if w>=1040 else 62)
    a.button(lx,play_y,168,'播放接點試聽',True,role='playback')
    a.button(lx+172,play_y,168,'停止試聽',disabled=True,role='playback')
    a.text(lx+352,play_y+9,'重用批次音訊，不呼叫 TTS。',color=MUTED)
    a.footer('接點 1／3 · 頁碼警告待確認 · 返回保留輸入與閱讀位置',join=True)
    a.save()


def details(mode):
    a=Drawing(1360,820,'1360-source-'+mode)
    x,top,right,base=a.shell()
    lx,rx=x+12,right-12
    a.text(lx,top+12,'來源詳情 · 第五章',True)
    lines=['音訊待更新', '目前朗讀稿已變更。請重新製作此批次音訊。', '來源：晨間隨筆.txt', '成功任務：第 2 次 · 2026-11-10', '版本：朗讀稿 v4 → 目前 v5', '上一份 MP3／SRT 保留，可在成品版本查看。']
    vh=base-12-(top+48)
    if mode in ('long','fit','overflow'):
        lines += [f'驗證明細 {i}：來源對應資訊與媒體檢查結果。' for i in range(1,45)]
        if mode in ('fit','overflow'):lines=lines[:(vh-20)//28+(mode=='overflow')]
    def paint(d,rw,ch):
        for i,s in enumerate(lines):d.text((12,10+i*28),s,font=F,fill=INK)
    a.region('來源詳情',(lx,top+48,rx,base-12),vh if mode=='fit' else len(lines)*28+20,paint,state=mode)
    a.text(16,727,'第五章未加入合併 · 原選批、順序與停頓保留',color=MUTED)
    a.button(16,760,168,'← 返回全書合併',role='footer-back')
    a.button(1148,760,196,'前往此批次製作 →',True,role='footer-action')
    a.save()


if __name__=='__main__':
    for mode in ('empty','short','fit','overflow','long'):
        merge(1360,820,mode)
    merge(1360,820,'long',bottom=True)
    for w,h in ((1920,1000),(1280,720),(900,640)):
        merge(w,h)
    for w,h in ((1360,820),(900,640)):
        merge(w,h,settings=True)
    merge(1360,820,status='partial')
    merge(1360,820,status='running')
    merge(1360,820,status='done')
    merge(1360,820,route_menu=True)
    merge(1360,820,video_route='batches')
    for mode in ('fit','overflow','long'):merge(1360,820,file_mode=mode)
    for mode in ('short','fit','overflow','long'):
        joins(1360,820,mode)
    joins(900,640,'long',end=True)
    for mode in ('short','fit','overflow','long'):details(mode)
    (OUT/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,regions=REGIONS),ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'measurements.json').write_text(json.dumps(dict(images=SHOTS,controls=CONTROLS,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),ensure_ascii=False,indent=2),encoding='utf-8')
    checks=[]
    for page in CONTROLS:
        for role in ('source-action','join-action','pair-nav','playback','edit-excerpt','footer-action'):
            group=sorted([c for c in page['controls'] if c['role']==role],key=lambda c:c['x'])
            if len(group)<2:continue
            assert len({(c['width'],c['height']) for c in group})==1
            for left,right in zip(group,group[1:]):
                gap=right['x']-left['x']-left['width']
                expected=12 if role=='edit-excerpt' else 4
                assert gap==expected
                checks.append(dict(page=page['page'],role=role,pair=[left['label'],right['label']],width=left['width'],height=left['height'],gap=gap,expected_gap=expected))
        if 'merge' in page['page']:
            table=next(r for r in REGIONS if r['page']==page['page'] and r['owner']=='合併來源清單')
            toolbar=[c for c in page['controls'] if c['role']=='source-action']
            gap=table['bounds'][1]-32-max(c['y']+c['height'] for c in toolbar)
            assert gap==8
            checks.append(dict(page=page['page'],role='toolbar-table',vertical_gap=gap))
    (OUT/'design-checks.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),checks=checks,scope='static drawing coordinates; no native UI assertion'),ensure_ascii=False,indent=2),encoding='utf-8')
    # Index sheets aid discovery; original-size PNGs remain the review evidence.
    for p in range(0,len(SHOTS),6):
        sheet=Image.new('RGB',(1360,3*438),BG)
        d=ImageDraw.Draw(sheet)
        for j,shot in enumerate(SHOTS[p:p+6]):
            im=Image.open(OUT/(shot['name']+'.png'))
            im.thumbnail((672,402))
            xx=(j%2)*680;yy=(j//2)*438
            d.text((xx+8,yy+4),shot['name'],font=F,fill=INK)
            sheet.paste(im,(xx+4,yy+30))
        sheet.save(OUT/f'index-{p//6+1}.png')
    print(f'Rendered {len(SHOTS)} designs, {len(REGIONS)} measured regions.')
