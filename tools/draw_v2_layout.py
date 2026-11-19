"""Reproducible structural drawings; native screenshots are separate evidence."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1]/'docs/ui-review'
BG, INK, LINE, GREEN = '#f5f6f2', '#263d34', '#c7d2c6', '#315d43'


def draw(name, w, h, tool=False):
    im = Image.new('RGB', (w, h), BG)
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 14)
    title = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 18)
    def text(x, y, value, color=INK, f=font):
        d.text((x, y), value, font=f, fill=color)
    def button(x, y, label, width=None, primary=False, active=False):
        width = width or int(d.textlength(label, font=font))+28
        d.rectangle((x, y, x+width, y+37), fill=GREEN if primary else '#e2ebdf' if active else 'white', outline=LINE)
        dropdown = '▾' in label
        text(x+12, y+9, label.replace(' ▾',''), 'white' if primary else INK)
        if dropdown:d.polygon(((x+width-18,y+16),(x+width-8,y+16),(x+width-13,y+22)),fill=INK)
        return x+width+4
    def panel(x, y, right, bottom):
        d.rectangle((x,y,right,bottom),fill='white',outline=LINE)
    text(16, 8, f'v2 文稿 · 沿用 v1 結構設計 · {w}×{h}', f=title)
    x=button(16,42,'1 文稿',active=True)
    button(x,42,'2 試聽與製作')
    x=button(w-258,42,'專案 ▾',110)
    button(x,42,'訊息記錄',128)
    left=188 if w<1000 else 220
    x=button(16,100,'‹',38);x=button(x,100,'匯入 ▾',72);button(x,100,'管理 ▾',72)
    panel(16,164,left,h-88)
    for i,label in enumerate(('合成 PDF · 1–3','第二份 TXT','第三份 TXT')):
        if i==0:d.rectangle((17,165,left-1,237),fill='#e7efe4')
        text(28,180+i*80,label);text(28,202+i*80,'已確認')
    start=left+12
    if tool:
        button(start,100,'← 返回文稿')
        text(start+160,109,'版本紀錄')
        panel(start,164,w-16,h-142)
        text(start+20,183,'選取版本  文稿 v3    還原前先備份現稿')
        for i in range(6):text(start+20,224+i*36,f'第 {i+1} 段。版本差異內容只在此區捲動。')
        button(w-200,h-130,'還原到編輯稿',184,primary=True)
    elif w<950:
        text(start,109,'文稿')
        x=start+75
        for label in ('原稿','編輯 ▾','校對 ▾','版本 ▾','暫存草稿'): x=button(x,100,label)
        panel(start,164,w-16,h-88)
        for i in range(8):text(start+20,184+i*38,f'第 {i+1} 段。文稿取得剩餘寬度。')
        text(start, h-115,'原稿與文稿沿用 v1 窄版切換')
    else:
        middle=(start+w-16)//2
        text(start,109,'PDF 原稿')
        x=middle-374
        for label,width in (('‹',38),('1 / 3',72),('›',38),('符合頁寬 ▾',126),('來源 ▾',76)):
            x=button(x,100,label,width)
        text(middle+4,109,'文稿')
        labels=('隱藏原稿','編輯 ▾','校對 ▾','版本 ▾','暫存草稿')
        x=w-16-sum(int(d.textlength(label,font=font))+32 for label in labels)
        for label in labels:x=button(x,100,label)
        panel(start,164,middle-4,h-88);panel(middle+2,164,w-16,h-88)
        text(start+24,203,'合成 PDF 原頁')
        for i in range(8):
            text(start+24,244+i*42,'原頁內容與文稿並列。')
            text(middle+24,203+i*42,f'第 {i+1} 段。保留 v1 編輯與工具入口。')
        text(start, h-115,'相鄰操作控制項間隔 4 Tk 單位；頁碼為一個群組')
    text(16,h-71,'合成文件 · 文稿 v3 · 已儲存，可朗讀')
    text(16,h-44,'結構設計圖；實際元件以 Tk 原生驗收為準。')
    button(w-206,h-62,'前往試聽與製作 →',190,primary=True)
    im.save(OUT/(name+'.png'))


if __name__=='__main__':
    draw('v2-manuscript-normal',1536,864)
    draw('v2-manuscript-reduced',900,640)
    draw('v2-manuscript-tools',1280,720,True)
