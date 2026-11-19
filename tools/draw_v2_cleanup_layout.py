"""Static approval drawings only; these are not native acceptance evidence."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/ui-review/v2-linebreak-preview'
BG, INK, LINE, GREEN = '#f5f6f2', '#263d34', '#c7d2c6', '#315d43'


def draw(name, width, height, *, collapsed=False, unchanged=False, large=False, error=False):
    image = Image.new('RGB', (width, height), BG)
    pen = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 14)
    heading = ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc', 16)
    body = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 24 if large else 18)

    def text(x, y, value, fill=INK, face=font):
        pen.text((x, y), value, font=face, fill=fill)

    def button(x, y, value, w, *, primary=False, active=False, dropdown=False):
        pen.rectangle((x, y, x+w-1, y+36), fill=GREEN if primary else '#e2ebdf' if active else 'white', outline=LINE)
        text(x+12, y+8, value, 'white' if primary else INK)
        if dropdown:
            pen.polygon(((x+w-22,y+15),(x+w-12,y+15),(x+w-17,y+21)),fill=INK)

    def paragraph(x, y, value, max_width, *, fill=INK, highlight=None):
        line = ''
        advance = 34 if large else 28
        for char in value:
            if line and pen.textlength(line+char, font=body) > max_width:
                if highlight:
                    pen.rectangle((x,y,x+pen.textlength(line,font=body)+4,y+advance-2),fill=highlight)
                text(x,y,line,fill,body)
                line = ''
                y += advance
            line += char
        if highlight:
            pen.rectangle((x,y,x+pen.textlength(line,font=body)+4,y+advance-2),fill=highlight)
        text(x,y,line,fill,body)
        return y+advance

    button(16,16,'1 文稿',114,active=True)
    button(138,16,'2 試聽與製作',142)
    text(width-400,25,'合成驗收書籍')
    button(width-266,16,'專案',126,dropdown=True)
    button(width-132,16,'訊息記錄',116)
    top, start, bottom = 72, 121, height-65
    left, list_width = 16, 208
    work = 16 if collapsed else left+list_width+12
    if not collapsed:
        button(left,top,'‹',40)
        button(left+44,top,'匯入',78,dropdown=True)
        button(left+126,top,'管理',82,dropdown=True)
        pen.rectangle((left,start,left+list_width-1,bottom),fill='white',outline=LINE)
        for index, (name_text,state) in enumerate((('第一章 · 換行整理範例','TXT · 未確認'),('第二章 · 無須整理範例','TXT · 已確認'),('第三章 · 保留現稿','PDF 1–3 · 未確認'))):
            y=start+index*76
            if index==0:
                pen.rectangle((left+1,y+1,left+list_width-2,y+75),fill='#e7efe4')
            text(left+16,y+18,name_text)
            text(left+16,y+42,state)
    back_x=work
    if collapsed:
        button(work,top,'›',40)
        back_x+=44
    button(back_x,top,'← 返回文稿',130)
    text(back_x+146,top+8,'整理換行預覽',face=heading)
    pen.rectangle((work,start,width-17,bottom),fill='white',outline=LINE)
    text(work+20,start+13,'目前文件 · 第一章 · 換行整理範例')
    pen.line((work,start+42,width-17,start+42),fill=LINE)
    footer_top=bottom-58
    text(work+20,start+58,'整理前後比較',face=heading)
    if unchanged:
        paragraph(work+20,start+102,'目前沒有需要整理的換行，文稿未變更。',width-work-64)
    else:
        # Content is clipped within its designated vertical scroll owner.
        layer=Image.new('RGB',(width,height),'white')
        original_pen=pen
        pen=ImageDraw.Draw(layer)
        y=start+100
        for line in ('--- 目前文稿','+++ 整理結果','@@ -1,8 +1,6 @@',''):
            y=paragraph(work+24,y,line,width-work-78)
        for index in range(1,8):
            y=paragraph(work+24,y,f'- 第 {index} 段。清晨的陽光穿過窗簾，',width-work-78,highlight='#f8e8e3')
            y=paragraph(work+24,y,'- 落在書桌上。保留原字元與空白段落。',width-work-78,highlight='#f8e8e3')
            y=paragraph(work+24,y,f'+ 第 {index} 段。清晨的陽光穿過窗簾，落在書桌上。保留原字元與空白段落。',width-work-78,highlight='#e7efe4')
            y+=18
        pen=original_pen
        image.paste(layer.crop((work+20,start+96,width-44,footer_top-12)),(work+20,start+96))
        pen.rectangle((width-38,start+100,width-24,footer_top-12),fill='#f0f1ed',outline=LINE)
        pen.rectangle((width-36,start+102,width-26,start+166),fill='#b7bcb3')
    pen.line((work,footer_top,width-17,footer_top),fill=LINE)
    result='無須整理 · 原稿未變更' if unchanged else '7 處變更 · 原稿尚未變更'
    if error:
        text(work+20,footer_top+8,'無法儲存。現稿保留。',fill='#993c30')
        text(work+20,footer_top+30,'請排除問題後重試，或返回文稿。',fill='#993c30')
    else:
        text(work+20,footer_top+20,result)
    if not unchanged:
        button(width-182,footer_top+10,'套用換行整理',146,primary=True)
    text(18,height-49,'第一章 · 換行整理範例 · 文稿 v3 · 目前預覽尚未套用')
    text(18,height-25,'已載入合成專案 · 原始來源檔不會被改寫',fill='#58695f')
    image.save(OUT/(name+'.png'))
    return dict(name=name,client=[width,height],list_collapsed=collapsed,unchanged=unchanged,
        content_font_pt=18 if large else 12,header_controls_top=top,header_controls_height=37,
        left_and_right_content_top=start,content_bottom=bottom,
        diff_height=footer_top-12-(start+96) if not unchanged else None)


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    drawings=[draw('normal',1536,793),draw('reduced-18pt',900,640,large=True),
        draw('collapsed-18pt',900,640,collapsed=True,large=True),
        draw('unchanged',1360,820,unchanged=True),draw('save-failure',900,640,error=True)]
    (OUT/'design-geometry.json').write_text(json.dumps(dict(kind='static design; not native measurements',drawings=drawings),ensure_ascii=False,indent=2),encoding='utf-8')
