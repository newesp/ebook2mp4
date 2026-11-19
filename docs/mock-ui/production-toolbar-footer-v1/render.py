"""Draw design-only UI mockups. Does not import or launch the product."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 2
BG, INK, GREEN = '#f5f6f2', '#263d34', '#315d43'
EDGE, MUTED = '#c7d2c6', '#58695f'


def render(width, height, name, expanded=False):
    im = Image.new('RGB', (width*S, height*S), BG)
    d = ImageDraw.Draw(im)
    def rect(box, fill, edge=None):
        d.rectangle(tuple(int(n*S) for n in box), fill=fill, outline=edge, width=S)
    def text(x, y, value, size=14, color=INK, bold=False):
        font = ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc' if bold else 'C:/Windows/Fonts/msjh.ttc', size*S)
        d.text((x*S, y*S), value, font=font, fill=color)
    def button(x, y, w, label, active=False, disabled=False, menu=False):
        rect((x,y,x+w,y+36), GREEN if active else '#ffffff', EDGE)
        color = '#ffffff' if active else '#8b968e' if disabled else INK
        font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 14*S)
        tw = d.textlength(label, font=font)/S
        text(x+(w-tw-(14 if menu else 0))/2,y+8,label,color=color)
        if menu:
            px, py = x+w-16, y+18
            d.polygon([(int((px-4)*S),int((py-2)*S)),(int((px+4)*S),int((py-2)*S)),(int(px*S),int((py+3)*S))],fill=color)
    small = width < 1000
    rail = 190 if small else 220
    main = rail+24
    right = width-16
    button(16,16,112,'1 文稿')
    button(136,16,132,'2 試聽與製作',True)
    text(width-330,24,'靈性開悟')
    button(width-240,16,112,'專案',menu=True)
    button(width-120,16,104,'訊息記錄')
    # Navigation and workspace controls share the same 36px vertical bounds.
    button(16,68,36,'‹')
    button(60,68,68 if small else 76,'匯入',menu=True)
    button(136 if small else 144,68,70 if small else 76,'管理',menu=True)
    button(main,68,144,'語音設定與試聽')
    text(main+152,76,'→')
    button(main+176,68,116,'音訊製做',True)
    text(main+300,76,'→')
    button(main+324,68,116,'全書合併')
    # Fixed footer uses the space formerly occupied by the two-line status strip.
    footer_top = height-(142 if small else 94)
    rect((0,footer_top,width,height),'#edf1e9')
    rect((0,footer_top,width,footer_top+1),EDGE)
    text(16,footer_top+10,'book1-ch3 · PDF 1–12 · 文稿 v4 · 6,842 字元 · 已儲存 · 可朗讀',13)
    text(right-140,footer_top+10,'已載入專案',13,MUTED)
    button(16,footer_top+42,116,'← 語音設定')
    button(140,footer_top+42,124,'重新開始…')
    action_y = footer_top+(90 if small else 42)
    action_widths = [104,120,120,166]
    start = right-sum(action_widths)-24
    for w,label,active,disabled,menu in [
        (104,'播放成品',False,True,False),
        (120,'成品操作',False,False,True),
        (120,'製作 MP4 →',False,False,False),
        (166,'繼續未完成區塊 →',True,False,False),
    ]:
        button(start,action_y,w,label,active,disabled,menu)
        start += w+8
    # Document list owns its own scrolling; footer spans the whole window.
    rect((16,116,rail,footer_top-12),'#ffffff',EDGE)
    for i, label in enumerate(['book1-ch1 · 1–9','book1-ch2 · 1–2','book1-ch3 · 1–12']):
        y = 124+i*68
        if i == 2:
            rect((17,y-4,rail-1,y+60),'#e7efe4')
        text(28,y+5,label,13)
        text(28,y+26,('PDF 1–9 · 未確認' if i==0 else 'PDF 1–2 · 已確認' if i==1 else 'PDF 1–12 · 已確認'),13)
    text(main,124,'製作任務',13)
    select_right = right-(190 if not small else 168)
    button(main+70,116,select_right-main-70,'第 1 次 · 失敗' if small else '第 1 次 · 2026-11-09 07:40 · 失敗',menu=True)
    button(select_right+8,116,right-select_right-8,'返回區塊清單 ‹' if expanded else '朗讀稿與任務設定 ›')
    content_bottom = footer_top-116
    rect((main,164,right,content_bottom),'#ffffff',EDGE)
    if expanded:
        button(main+12,176,144,'← 返回區塊清單')
        button(right-220,176,208,'重新檢查目前稿件與設定')
        button(main+12,224,150,'朗讀稿與設定',True)
        button(main+170,224,156,'狀態與錯誤詳情')
        text(main+24,278,'book1-ch3 · 文稿 v4 · 已確認 · 6,842 字元',14)
        text(main+24,306,'Gemini TTS · 原任務語音設定',14,MUTED)
        lines = ['第一章　閱讀與聲音','', '清晨的光穿過窗戶，落在翻開的書頁上。',
                 '我們沿著文字的節奏，讀過一段又一段故事。',
                 '每個段落保留原有順序，供製作前核對。']
        for i,line in enumerate(lines):
            if 350+i*29 < content_bottom-20:
                text(main+24,350+i*29,line,16)
    else:
        rect((main+1,165,right-14,194),'#f0f1ed',EDGE)
        xs = [main+8,main+72,main+174,main+270]
        for x,label in zip(xs,['區塊','狀態','嘗試次數','說明']):
            text(x,170,label,13)
        n = int((content_bottom-202)/26)
        for i in range(n):
            y = 202+i*26
            for x,value in zip(xs,[str(i+1),'已完成','0','—']):
                text(x,y,value,14)
    # Visible scrollbar within the content region only.
    rect((right-12,165,right-1,content_bottom-1),'#f0f1ed',EDGE)
    rect((right-11,182,right-2,220),'#bcc6b8')
    y = content_bottom+12
    text(main,y,'TTS HTTP 429 · 配額已用盡；已停止自動重試。',13,MUTED)
    button(right-104,y-4,104,'狀態詳情')
    rect((main,y+44,main+12,y+56),'#ffffff',EDGE)
    d.line([(int((main+2)*S),int((y+50)*S)),(int((main+5)*S),int((y+53)*S)),(int((main+10)*S),int((y+46)*S))],fill=GREEN,width=2*S)
    text(main+20,y+40,'同意傳送待處理文字（可能計費）',13)
    if not small:
        text(right-186,y+40,'尚無成功的批次成品。',13,MUTED)
    else:
        text(main,y+64,'尚無成功的批次成品。',12,MUTED)
    im.resize((width,height),Image.Resampling.LANCZOS).save(OUT/name)


if __name__ == '__main__':
    render(1360,820,'normal.png')
    render(900,640,'reduced.png')
    render(1360,820,'expanded.png',True)
