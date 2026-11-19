"""Render static UI proposals. No application or external service is started."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
INK, MUTED, LINE, GREEN = '#243449', '#5a6b7c', '#d7dfe8', '#23635d'
FONTS = {}

def render(kind):
    im = Image.new('RGB', (1600, 1060), '#eef2f6')
    d = ImageDraw.Draw(im)
    def text(x, y, value, size=21, color=INK, bold=False):
        key = size, bold
        if key not in FONTS:
            FONTS[key] = ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc' if bold else 'C:/Windows/Fonts/msjh.ttc', size)
        d.text((x, y), value, fill=color, font=FONTS[key])
    def rect(x, y, w, h, color='white', border=LINE, radius=7):
        d.rounded_rectangle((x,y,x+w,y+h), radius, fill=color, outline=border)
    def button(x,y,w,label,primary=False):
        rect(x,y,w,43,GREEN if primary else 'white', GREEN if primary else LINE)
        text(x+14,y+9,label,19,'white' if primary else INK)
    def field(x,y,w,value,select=True):
        rect(x,y,w,40)
        text(x+12,y+8,value,19)
        if select:
            d.polygon([(x+w-25,y+17),(x+w-13,y+17),(x+w-19,y+24)], fill=MUTED)
    def rule(y,x1=542,x2=1518):
        d.line((x1,y,x2,y),fill=LINE,width=1)
    def check(x,y,label):
        rect(x,y+4,18,18,GREEN,GREEN,3)
        d.line([(x+4,y+13),(x+8,y+17),(x+15,y+8)],fill='white',width=2)
        text(x+29,y,label,20)

    names={'versions':'版本記錄','settings':'文稿設定','source':'來源處理'}
    title=names[kind]
    text(44,24,title+'展開時的主畫面',32,bold=True)
    text(44,76,'第三版設計 / 所有資料均為示意 / 工具在右側下方展開，可切換或收合',20,MUTED)
    rect(40,124,1520,866)
    d.rectangle((41,125,1559,189),fill='#e8efee')
    text(64,146,'ebook2mp4 / 我的書籍',22,bold=True)
    text(1015,146,'1 文稿',22,GREEN,True)
    text(1225,146,'2 試聽與製作',22,MUTED)
    button(64,208,142,'匯入文稿')
    button(222,208,272,'AI 全文校對（Gemini）')
    button(1220,208,145,'隱藏原稿')
    button(1381,208,155,'更多工具')
    text(65,268,'第一章.pdf / 12 頁 / 8,246 字',19,MUTED)
    # Original remains a full-height left pane in all three states.
    rect(64,310,440,601,'#f4f6f8')
    text(83,326,'PDF 原稿',21,bold=True)
    text(291,329,'<  1 / 12  >',20)
    rect(110,381,348,469)
    text(161,416,'第一章  出發',24,bold=True)
    for i in range(16):
        d.line((146,480+i*20,422 if i%4 else 385,480+i*20),fill='#b9c5cf',width=2)
    text(84,875,'縮放：適合整頁',18,MUTED)
    # Same editor geometry, scroll position and footer for every tool.
    rect(526,310,1010,244)
    text(546,326,'文稿 · 可直接編輯',21,bold=True)
    text(1340,329,'草稿已暫存',19,GREEN)
    text(550,373,'第一章  出發',25,bold=True)
    text(550,425,'清晨的陽光穿過窗簾，落在書桌上。',23)
    text(550,470,'我翻開筆記，重新讀了一遍昨天寫下的文字。',23)
    text(550,516,'每一次出發，都從一個簡單的決定開始。',21)
    d.line((1523,367,1523,537),fill='#e2e7ec',width=6)
    d.line((1523,369,1523,407),fill='#9aabb9',width=6)
    rect(526,568,1010,343,'#fafbfd')
    tabs=[('versions','版本記錄',542,151),('settings','文稿設定',705,151),('source','來源處理',868,151)]
    for key,label,x,w in tabs:
        rect(x,581,w,42,'#e3efec' if key==kind else '#fafbfd', GREEN if key==kind else '#fafbfd')
        text(x+19,591,label,20,GREEN if key==kind else MUTED,key==kind)
    button(1438,582,82,'收合')
    rule(635)

    if kind=='versions':
        text(548,648,'版本',18,MUTED)
        text(942,648,'與目前文稿的差異 · 唯讀預覽',18,MUTED)
        rect(542,681,374,61,'#e3efec','#c4dcd4')
        text(556,689,'朗讀稿 v3',20,GREEN,True)
        text(556,717,'今天 14:30 / 已儲存',17,MUTED)
        text(556,755,'朗讀稿 v2',20)
        text(556,784,'今天 13:10',17,MUTED)
        text(556,821,'重新擷取前備份',20)
        text(556,850,'昨天 17:45',17,MUTED)
        d.line((930,650,930,862),fill=LINE)
        rect(946,684,569,44,'#f9e9e5','#f9e9e5')
        text(958,694,'版本 v3：我翻開筆記，又讀了一遍。',20,'#8a4436')
        rect(946,740,569,44,'#e1f1e7','#e1f1e7')
        text(958,750,'目前文稿：我翻開筆記，重新讀了一遍。',20,GREEN)
        text(948,803,'還原前會先保留目前草稿。',18,MUTED)
        button(1308,849,210,'還原到編輯稿')
    elif kind=='settings':
        text(548,653,'編輯器字級',19)
        field(548,683,190,'18 pt')
        text(782,653,'AI 校對服務',19)
        field(782,683,218,'Gemini')
        text(1044,653,'模型（可自行輸入）',19)
        field(1044,683,470,'目前使用的模型')
        text(548,746,'校對文字',19)
        field(548,776,190,'自動判斷')
        check(784,782,'統一標點')
        button(1044,775,175,'服務連線設定')
        text(548,859,'設定已儲存',18,GREEN)
    else:
        text(548,652,'PDF 頁面範圍',19)
        field(548,683,98,'1',False)
        text(659,691,'至',19)
        field(695,683,98,'12',False)
        text(832,652,'擷取方式',19)
        field(832,683,260,'自動')
        text(1134,652,'辨識語言',19)
        field(1134,683,380,'繁中＋英文')
        text(548,747,'辨識版面',19)
        field(548,777,245,'自動版面')
        text(832,747,'處理範圍',19)
        field(832,777,260,'指定頁面範圍')
        text(548,861,'完成後預覽差異，再決定是否套用。',18,MUTED)
        button(1280,848,238,'重新擷取並預覽')

    d.line((64,928,1536,928),fill=LINE)
    text(67,951,'尚未儲存為朗讀稿',19,MUTED)
    button(1296,940,240,'儲存為朗讀稿',True)
    notes={
        'versions':'選版本只預覽；按「還原到編輯稿」才更新右上文稿，之後可編輯並儲存為朗讀稿。',
        'settings':'設定自動保存。服務連線設定在同一工具面板內展開；完成後返回此處。',
        'source':'這張是 PDF 的來源處理。TXT 會改顯示編碼與重新載入，不出現 PDF 或 OCR 欄位。',
    }
    text(44,1014,notes[kind],20,MUTED)
    im.save(OUT/(kind+'.png'))

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for kind in ('versions','settings','source'):
        render(kind)
        print(OUT/(kind+'.png'))
