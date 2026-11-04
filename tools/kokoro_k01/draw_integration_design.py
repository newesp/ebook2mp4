"""Draw review-only native UI wireframes; does not modify the application."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/mock-ui/kokoro-v1'
INK='#263d34'; MUTED='#58695f'; GREEN='#315d43'; LINE='#dfe5dd'; BG='#f5f6f2'
FONT='C:/Windows/Fonts/msjh.ttc'


class Diagram:
    def __init__(self,w,h):
        self.im=Image.new('RGB',(w,h),BG); self.d=ImageDraw.Draw(self.im)
    def text(self,x,y,text,size=16,color=INK):
        if text.startswith('▸ '):
            self.d.polygon([(x+2,y+5),(x+2,y+15),(x+8,y+10)],fill=color)
            x+=14;text=text[2:]
        self.d.text((x,y),text,font=ImageFont.truetype(FONT,size),fill=color)
    def box(self,x,y,w,h,fill='white',line=LINE):
        self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=line,width=1)
    def button(self,x,y,w,text,primary=False,disabled=False,danger=False):
        fill='#e1e5de' if disabled else '#963b32' if danger else GREEN if primary else 'white'
        color='#68736c' if disabled else 'white' if primary or danger else INK
        self.box(x,y,w,36,fill)
        font=ImageFont.truetype(FONT,14)
        bounds=self.d.textbbox((0,0),text,font=font)
        assert bounds[2]-bounds[0] <= w-16,(text,w)
        self.text(x+(w-(bounds[2]-bounds[0]))/2,y+8,text,14,color)
    def field(self,x,y,w,text):
        self.box(x,y,w,36); self.text(x+10,y+7,text,14)
        self.d.polygon([(x+w-23,y+15),(x+w-13,y+15),(x+w-18,y+21)],fill=INK)
    def panel(self,x,y,w,h,title):
        self.box(x,y,w,h,BG); self.text(x+12,y+10,title,18)
    def save(self,name):
        self.im.save(OUT/name)


def shell(w,h,active='voice'):
    c=Diagram(w,h); small=w<1200
    c.text(16,12,'書籍製作工作台  ·  Kokoro 整合設計提案',16)
    c.text(w-180,14,'設計圖，尚未實作',14,MUTED)
    for i,title in enumerate(('1 匯入來源','2 校對文字','3 確認朗讀稿','4 試聽與製作')):
        c.button(16+i*160,48,152,title,i==3)
    side=160 if small else 208
    c.text(16,112,'書籍與製作批次',16)
    c.box(16,148,side-16,h-220)
    c.box(17,149,side-18,44,GREEN); c.text(24,159,'第 1 章 · 已確認',14,'white')
    x=side+24
    for dx,title,key in ((0,'語音設定與試聽','voice'),(176,'製作與成品','production'),(328,'全書合併','assembly')):
        c.button(x+dx,100,164 if dx==0 else 140,title,key==active)
    return c,x


def voice(w,h,name):
    c,x=shell(w,h); small=w<1200; right=w-16; width=right-x
    c.panel(x,152,width,88,'1 選擇服務')
    c.field(x+16,192,248,'Kokoro · 本機 CPU')
    c.text(x+280,201,'已安裝 · 可離線使用',14,GREEN)
    c.button(right-152,192,136,'管理語音包')
    y=252; bottom=h-(132 if small else 100); left=280 if small else 352
    c.panel(x,y,left,bottom-y,'2 設定聲音與節奏')
    c.text(x+16,y+44,'音色 · 全部官方中文音色',14)
    c.field(x+16,y+70,left-32,'zf_001  ·  女聲')
    c.text(x+16,y+114,'可輸入 ID 搜尋 · 共 100 種',14,MUTED)
    c.text(x+16,y+138,'人工品質驗證：尚無',14,MUTED)
    c.text(x+16,y+176,'語速',14); c.field(x+16,y+202,112,'正常')
    c.text(x+144,y+176,'節奏',14); c.field(x+144,y+202,left-160,'自然')
    c.text(x+16,y+254,'▸ 自訂停頓',14)
    c.text(x+16,y+292,'▸ 模型、版本與已知發音限制',14)
    if not small:
        c.text(x+16,y+344,'本機 CPU 處理',16,GREEN)
        c.text(x+16,y+374,'文字不會傳送至雲端。',14,MUTED)
    tx=x+left+12; tw=right-tx
    c.panel(tx,y,tw,bottom-y,'3 編輯文字並試聽')
    c.button(tx+16,y+44,124,'使用固定範例')
    c.button(tx+148,y+44,124,'帶入選取文字')
    text_y=y+92; text_h=(bottom-y)-220
    c.box(tx+16,text_y,tw-32,text_h,'#fffef9')
    lines=['今天，讓我們一起聽一本好書。', 'Hello, welcome to your audiobook.', '這是語音試聽範例。']
    for i,line in enumerate(lines):c.text(tx+28,text_y+14+i*28,line,16)
    c.box(right-28,text_y+4,6,text_h-8,'#e1e5de')
    c.text(tx+16,bottom-118,'文字僅在本機處理 · 試聽不改寫朗讀稿',14,GREEN)
    c.button(tx+16,bottom-82,156,'產生並播放試聽',True)
    c.button(tx+180,bottom-82,64,'重播')
    c.button(tx+252,bottom-82,64,'停止')
    c.text(tx+16,bottom-34,'尚未產生試聽 · 請先選音色，再試聽。',14,MUTED)
    fy=bottom+16
    if small:
        c.text(x,fy+8,'儲存範圍',14);c.field(x+84,fy,124,'本批次');c.button(x+220,fy,132,'只儲存設定')
        c.button(x,fy+48,188,'← 返回確認朗讀稿');c.button(right-236,fy+48,236,'儲存並前往製作 →',True)
    else:
        c.button(x,fy,188,'← 返回確認朗讀稿');c.field(x+352,fy,124,'本批次')
        c.button(x+488,fy,132,'只儲存設定');c.button(right-236,fy,236,'儲存並前往製作 →',True)
    c.save(name)


def package(w=1440,h=900):
    c,x=shell(w,h);right=w-16;width=right-x;small=w<1200
    c.text(x,156,'本機語音包 · 移除確認示例',24)
    c.text(x,196,'匯入已下載的語音包。檢查通過後，才可在語音設定中使用。',16,MUTED)
    c.panel(x,244,width,152 if small else 172,'Kokoro 官方中文模型')
    c.text(x+16,292,'已安裝 · CPU · 可離線使用 · 100 種中文音色',16,GREEN)
    c.text(x+16,332,'人工品質驗證：尚無。試聽後再決定是否用於正式書稿。',14,MUTED)
    c.text(x+16,372,'▸ 版本、完整性與授權詳情',14)
    c.button(right-152,348 if small else 364,136,'移除語音包')
    iy=412 if small else 440
    c.panel(x,iy,width,152 if small else 188,'匯入離線語音包')
    c.box(x+16,iy+48,width-204,36);c.text(x+26,iy+56,'選擇已下載的語音包檔案…',14,MUTED)
    c.button(right-164,iy+48,148,'選擇檔案',disabled=True)
    c.text(x+16,iy+(100 if small else 108),'先檢查完整性、版本與相容性；通過後再安裝。',16)
    c.text(x+16,iy+(128 if small else 144),'不會上傳書稿。失敗或取消時清除未完成安裝。',14,MUTED)
    cy=580 if small else 652
    c.box(x,cy,width,104 if small else 136,'#fffef9')
    c.text(x+16,cy+(8 if small else 16),'移除「Kokoro 官方中文模型」？',16)
    c.text(x+16,cy+(34 if small else 48),'只移除此語音包。書稿、有效快取與完成成品會保留。',14,MUTED)
    c.button(right-272,cy+(60 if small else 88),124,'取消移除')
    c.button(right-136,cy+(60 if small else 88),120,'確認移除',danger=True)
    fy=h-(64 if small else 88)
    c.button(x,fy,188,'← 返回語音設定');c.button(right-188,fy,188,'檢查並匯入',disabled=True)
    c.save('package-restored.png' if small else 'package-wide.png')


def production(w=1440,h=900):
    c,x=shell(w,h,'production');right=w-16;width=right-x;small=w<1200;shift=88 if small else 0
    c.text(x,156,'朗讀稿預覽',24);c.text(x,200,'Kokoro · zf_001 · 正常語速 · 本機 CPU',16,GREEN)
    c.button(right-164,152,164,'任務與設定詳情')
    c.box(x,240,width,152 if small else 240,'#fffef9')
    for i,line in enumerate(('已確認朗讀稿（唯讀）','清晨，臺北的圖書館剛開門。','讀者輕輕翻開書頁，窗外的雨聲逐漸停了。')):
        c.text(x+16,256+i*36,line,16,MUTED if i==0 else INK)
    c.box(right-12,248,6,136 if small else 224,'#e1e5de')
    c.text(x,500-shift,'本次任務 · 已確認朗讀稿 · 12 區塊 · 可沿用 2 區塊',16)
    c.box(x,536-shift,width,168 if small else 192)
    c.box(x+1,537-shift,width-2,36,'#e9f0e5')
    for dx,label in ((16,'區塊'),(112,'狀態'),(320,'說明')):c.text(x+dx,544-shift,label,14)
    for i,(block,status,detail) in enumerate((('1','可沿用','完整音訊已驗證'),('2','可沿用','完整音訊已驗證'),('3','待製作','需以本機模型合成'),('4–12','待製作','其餘區塊可在清單捲動查看'))):
        yy=584+i*32-shift
        c.text(x+16,yy,block,14);c.text(x+112,yy,status,14);c.text(x+320,yy,detail,14)
    c.text(x,624 if small else 752,'就緒 · 尚需合成 10 區塊 · 文字僅在本機處理',16,GREEN)
    c.text(x,652 if small else 780,'完成所有區塊並驗證後，才發布 MP3 與 SRT。',14,MUTED)
    c.button(x,h-76,188,'← 返回語音設定');c.button(right-188,h-76,188,'開始製作',True)
    c.save('production-restored.png' if small else 'production-wide.png')


def states():
    c=Diagram(1440,1120);c.text(24,20,'Kokoro 狀態與操作規則',24)
    cards=[
        ('未安裝','缺少此模型版本的本機語音包。','音色與試聽停用；保留專案原選值。','匯入語音包'),
        ('檢查中／安裝中','正在檢查完整性與相容性…','停用切服務、移除與重複匯入。','取消安裝'),
        ('安裝成功','語音包已就緒，可離線使用。','顯示全部 100 種音色；不自動選聲。','返回語音設定'),
        ('缺少／損毀／不相容','語音包未啟用；原設定與成品保留。','分別顯示缺少檔案、校驗或版本原因。','重新匯入'),
        ('載入中','正在載入本機模型，首次可能較久。','停用設定、重複開始及移除；可取消。','取消'),
        ('合成中','正在合成第 3／12 區塊。','只在本機處理；設定鎖定，進度可見。','取消'),
        ('完成','本次合成完成。','顯示音長；可重播、保存及前往製作。','重播'),
        ('失敗','合成失敗；上一份成功結果保留。','展開失敗原因；不自動改用雲端。','重試'),
        ('取消中／已取消','正在停止推論… → 已取消，資源已釋放。','停止確認前仍鎖定設定；保留完整區塊。','返回設定'),
    ]
    for i,(title,status,rule,action) in enumerate(cards):
        x=24+(i%2)*708;y=76+(i//2)*204;ww=684
        c.panel(x,y,ww,188,title)
        c.text(x+16,y+48,status,16,GREEN if i not in (3,7) else '#963b32')
        c.text(x+16,y+84,rule,14,MUTED)
        c.button(x+16,y+132,164,action)
    c.save('states.png')


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    voice(1440,900,'voice-wide.png')
    voice(1040,760,'voice-restored.png')
    package();package(1040,760);production();production(1040,760);states()
