"""Draw design-only UI mockups. Does not import or launch the product."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
S = 2
BG, INK, GREEN = '#f5f6f2', '#263d34', '#315d43'
EDGE, MUTED = '#c7d2c6', '#58695f'


def render(width, height, name, playing=False, details=False):
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
    nav_x, nav_y = (main,68) if small else (311,16)
    if not small:
        rect((290,16,291,52),EDGE)
    button(nav_x,nav_y,144,'語音設定與試聽')
    text(nav_x+152,nav_y+8,'→')
    button(nav_x+176,nav_y,116,'音訊製做',True)
    text(nav_x+300,nav_y+8,'→')
    button(nav_x+324,nav_y,116,'全書合併')
    # Fixed footer uses the space formerly occupied by the two-line status strip.
    footer_top = height-94
    rect((0,footer_top,width,height),'#edf1e9')
    rect((0,footer_top,width,footer_top+1),EDGE)
    text(16,footer_top+10,'book1-ch3 · PDF 1–12 · 文稿 v4 · 6,842 字元 · 已儲存 · 可朗讀',13)
    text(right-140,footer_top+10,'已載入專案',13,MUTED)
    button(16,footer_top+42,116,'← 語音設定')
    button(140,footer_top+42,124,'重新開始…')
    action_y = footer_top+42
    action_widths = [104,120,120,166]
    start = right-sum(action_widths)-24
    for w,label,active,disabled,menu in [
        (104,'停止播放' if playing else '播放成品',playing,False,False),
        (120,'成品操作',False,False,True),
        (120,'製作 MP4 →',False,False,False),
        (166,'全書合併 →',True,False,False),
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
    task_y = 116 if small else 68
    text(main,task_y+8,'製作任務',13)
    select_right = right-182
    button(main+70,task_y,select_right-main-70,'第 1 次 · 已完成' if small else '第 1 次 · 2026-11-09 07:40 · 已完成',menu=True)
    button(select_right+8,task_y,right-select_right-8,'← 返回區塊清單')
    top = task_y+48
    content_bottom = footer_top-(84 if small else 52)
    # Notebook tabs attach to their shared content border, not button widgets.
    rect((main,top+36,right,content_bottom),'#ffffff',EDGE)
    def tab(x, w, label, selected):
        rect((x,top,x+w,top+36),'#ffffff' if selected else '#e6e9e2',EDGE)
        text(x+16,top+8,label,14,GREEN if selected else MUTED,bold=selected)
        if selected:
            rect((x+1,top+35,x+w-1,top+37),'#ffffff')
            rect((x+1,top+1,x+w-1,top+3),GREEN)
    tab(main,150,'朗讀稿與設定',not details)
    tab(main+150,172,'狀態與錯誤詳情',details)
    if details:
        text(main+16,top+58,'已完成 · 共 251 塊 · 成品已儲存',14,bold=True)
        text(main+16,top+94,'本次任務已完成，沒有待處理區塊。',14)
        text(main+16,top+124,'此區顯示完整狀態與錯誤訊息，可選取及複製。',14,MUTED)
    else:
        if small:
            text(main+16,top+58,'已完成 · 251 塊 · 文稿 v4 · 已確認 · 6,842 字元',13)
        else:
            text(main+16,top+58,'已完成 · 共 251 塊 · Gemini TTS · Zephyr',14)
            text(main+16,top+84,'文稿 v4 · 已確認 · 6,842 字元',13,MUTED)
        tx,ty = main+12,top+(90 if small else 116)
        rect((tx,ty,right-18,content_bottom-12),'#ffffff',EDGE)
        lines = [
            '第一章　閱讀與聲音', '',
            '清晨的光穿過窗戶，落在翻開的書頁上。',
            '我們沿著文字的節奏，讀過一段又一段故事。',
            '每個段落保留原有順序，供製作前核對。', '',
            '這是設計示意文稿。正式內容會依目前選取的任務顯示。',
            '切換頁籤後，保留原先的閱讀位置。', '',
            '讀到最後一段時，仍可使用固定的底部操作列。',
        ]
        line_height = 24 if small else 28
        for i,line in enumerate(lines):
            if ty+12+i*line_height < content_bottom-30:
                text(tx+12,ty+10+i*line_height,line,14 if small else 15)
        rect((right-30,ty+1,right-19,content_bottom-13),'#f0f1ed',EDGE)
        rect((right-29,ty+16,right-20,min(ty+65,content_bottom-14)),'#bcc6b8')
    y = content_bottom+12
    if small:
        text(main,y,'播放中 · 00:18 / 12:40' if playing else '製作完成 · 成品可播放',13,MUTED)
        by = y+28
    else:
        text(main,y+4,'播放中 · 00:18 / 12:40' if playing else '製作完成 · 成品可播放',13,MUTED)
        by = y-4
    button(right-328,by,216,'重新檢查目前稿件與設定')
    button(right-104,by,104,'狀態詳情')
    cx,cy = right-574,by+9
    rect((cx,cy+4,cx+12,cy+16),'#ffffff',EDGE)
    d.line([(int((cx+2)*S),int((cy+10)*S)),(int((cx+5)*S),int((cy+13)*S)),(int((cx+10)*S),int((cy+6)*S))],fill=GREEN,width=2*S)
    text(cx+20,cy,'同意傳送待處理文字（可能計費）',13)
    im.resize((width,height),Image.Resampling.LANCZOS).save(OUT/name)


if __name__ == '__main__':
    render(1360,820,'ready.png')
    render(1360,820,'playing.png',playing=True)
    render(900,640,'reduced.png',playing=True)
    render(1360,820,'details.png',details=True)
