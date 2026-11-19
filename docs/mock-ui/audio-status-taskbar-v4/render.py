"""Normal-window design evidence only; never imports or starts the product."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H, S = 1360, 820, 2
BG, INK, GREEN, EDGE, MUTED = '#f5f6f2', '#263d34', '#315d43', '#c7d2c6', '#58695f'


def render(mode, filename):
    im = Image.new('RGB', (W*S, H*S), BG)
    d = ImageDraw.Draw(im)
    def rect(box, fill, edge=None):
        d.rectangle(tuple(int(v*S) for v in box), fill=fill, outline=edge, width=S)
    def text(x, y, value, size=14, color=INK, bold=False):
        font = ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc' if bold else 'C:/Windows/Fonts/msjh.ttc', size*S)
        d.text((x*S,y*S),value,font=font,fill=color)
    def button(x,y,w,label,primary=False,disabled=False,menu=False):
        fill = '#e1e5de' if disabled else GREEN if primary else '#ffffff'
        color = '#869087' if disabled else '#ffffff' if primary else INK
        rect((x,y,x+w,y+36),fill,EDGE)
        font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',14*S)
        tw=d.textlength(label,font=font)/S
        text(x+(w-tw-(14 if menu else 0))/2,y+8,label,color=color)
        if menu:
            px,py=x+w-16,y+18
            d.polygon([(int((px-4)*S),int((py-2)*S)),(int((px+4)*S),int((py-2)*S)),(int(px*S),int((py+3)*S))],fill=color)
    running, background = mode=='running', mode=='background'
    selected = 1 if background else 2
    main,right=244,1344
    footer=726
    bar_top=footer-48 if background else footer
    bottom=bar_top-60
    button(16,16,112,'1 文稿')
    button(136,16,132,'2 試聽與製作',True)
    rect((290,16,291,52),EDGE)
    button(311,16,144,'語音設定與試聽')
    text(463,24,'→')
    button(487,16,116,'音訊製做',True)
    text(611,24,'→')
    button(635,16,116,'全書合併')
    text(1030,24,'靈性開悟')
    button(1120,16,112,'專案',menu=True)
    button(1240,16,104,'訊息記錄')
    button(16,68,36,'‹')
    button(60,68,76,'匯入',menu=True)
    button(144,68,76,'管理',menu=True)
    rect((16,116,220,bar_top-12),'#ffffff',EDGE)
    labels=['book1-ch1 · 1–9','book1-ch2 · 1–2','book1-ch3 · 1–12']
    scopes=['PDF 1–9 · 未確認','PDF 1–2 · 已確認','PDF 1–12 · 已確認']
    for i,(label,scope) in enumerate(zip(labels,scopes)):
        y=124+i*68
        if i==selected:
            rect((17,y-4,219,y+60),'#e7efe4')
        text(28,y+5,label,13)
        text(28,y+26,scope,13)
    text(main,76,'製作任務',13)
    choice='第 3 次 · 處理中' if running else '目前確認稿（新任務）'
    button(main+70,68,840,choice,disabled=running,menu=True)
    button(1162,68,182,'朗讀稿與任務設定 ›')
    rect((main,116,right,bottom),'#ffffff',EDGE)
    rect((main+1,117,right-14,145),'#f0f1ed',EDGE)
    xs=[main+8,main+80,main+180,main+280]
    for x,label in zip(xs,['區塊','狀態','嘗試次數','說明']):
        text(x,122,label,13)
    n=int((bottom-151)/26)
    for i in range(n):
        number=(128+i) if running else i+1
        y=151+i*26
        if running:
            status='已完成' if number<=134 else '驗證中' if number==135 else '等待'
            reason='已驗證原音' if number<=134 else '核對原音與區塊內容' if number==135 else '—'
            if number==135:
                rect((main+1,y-2,right-14,y+24),'#e7efe4')
        else:
            status='重用' if not background and number<=12 else '需合成'
            reason='原音已驗證' if status=='重用' else '使用目前確認稿與設定'
        for x,value in zip(xs,[str(number),status,'0',reason]):
            text(x,y,value,14)
    rect((right-12,117,right-1,bottom-1),'#f0f1ed',EDGE)
    thumb_y=bottom//2 if running else 150
    rect((right-11,thumb_y,right-2,thumb_y+48),'#bcc6b8')
    by=bottom+10
    summary=('驗證音訊區塊 · 完成 134/251 · 失敗 0' if running else
             '本書另有任務執行中；此批次暫停製作。' if background else '可重用 190 塊 · 需合成 61 塊；舊成品保留。')
    text(main,by+9,summary,13,MUTED)
    if running:
        rect((main+344,by+14,main+416,by+22),'#dfe5dd')
        rect((main+344,by+14,main+378,by+22),GREEN)
    cx=right-574
    cy=by+9
    rect((cx,cy+4,cx+12,cy+16),'#e1e5de' if running else '#ffffff',EDGE)
    d.line([(int((cx+2)*S),int((cy+10)*S)),(int((cx+5)*S),int((cy+13)*S)),(int((cx+10)*S),int((cy+6)*S))],fill=MUTED if running else GREEN,width=2*S)
    text(cx+20,cy,'同意傳送待處理文字（可能計費）',13,MUTED if running else INK)
    button(right-328,by,104,'狀態詳情')
    button(right-216,by,216,'重新檢查目前稿件與設定',disabled=running or background)
    # Dedicated track above the footer: never shares the action bar's grid cell.
    if background:
        rect((0,bar_top,W,footer),'#e7efe4')
        rect((0,bar_top,W,bar_top+1),EDGE)
        text(16,bar_top+15,'背景任務 · book1-ch3 · 驗證音訊區塊 · 完成 134/251',14)
        button(right-144,bar_top+6,144,'返回任務 →')
    rect((0,footer,W,H),'#edf1e9')
    rect((0,footer,W,footer+1),EDGE)
    # One expanding summary; no reserved right-hand status column.
    metadata=('book1-ch2 · PDF 1–2 · 文稿 v2 · 1,206 字元 · 已儲存 · 可朗讀' if background else
              'book1-ch3 · PDF 1–12 · 文稿 v4 · 6,842 字元 · 已儲存 · 可朗讀')
    text(16,footer+10,metadata,13)
    button(16,footer+42,116,'← 語音設定')
    button(140,footer+42,124,'重新開始…',disabled=running or background)
    actions=[(104,'播放成品',False,False,False)]
    if running:
        actions.append((104,'取消任務',False,False,False))
    actions.extend([(154,'繼續未完成區塊' if running else '更新 MP3／SRT',True,running or background,False),
                    (120,'成品操作',False,False,True),(120,'製作 MP4 →',False,False,False)])
    x=right-sum(a[0] for a in actions)-8*(len(actions)-1)
    for w,label,primary,disabled,menu in actions:
        button(x,footer+42,w,label,primary,disabled,menu)
        x+=w+8
    im.resize((W,H),Image.Resampling.LANCZOS).save(OUT/filename)


if __name__=='__main__':
    render('ready','ready.png')
    render('running','running.png')
    render('background','background.png')
