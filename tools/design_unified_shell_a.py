"""Ticket 13 A: measured design artifacts only; never imports application code.

All geometry, wrapping, scroll ranges and drawings share the same model.
Run with python -B tools/design_unified_shell_a.py. No product/user data is read.
"""
from pathlib import Path
import ast
import hashlib
import html
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/ui-review/v2-unified-shell-a'
EVIDENCE = ROOT / 'docs/verification/v2-unified-shell-a'
FONT = 'C:/Windows/Fonts/msjh.ttc'
BOLD = 'C:/Windows/Fonts/msjhbd.ttc'
BG, INK, MUTED, LINE = '#f5f6f2', '#263d34', '#58695f', '#c7d2c6'
GREEN, ERROR, PAPER = '#315d43', '#963b32', '#fffef9'

# id, title, family, matrix row, section, toolbar, secondary, primary
PAGES = [
 ('manuscript', '文稿', 'compare', 1, 1, ['搜尋取代', '編輯', 'AI 校對', '暫存草稿'], [], '儲存為朗讀稿'),
 ('cleanup', '整理換行預覽', 'text', 2, 1, ['整理前後差異'], [], '套用換行整理'),
 ('versions', '版本紀錄', 'text', 3, 1, ['文稿 v3／備份／AI 候選', '版本操作'], [], '還原到編輯稿'),
 ('ai', 'AI 設定', 'form', 4, 1, ['偏好設定', '服務連線設定'], ['測試連線'], '儲存設定'),
 ('pdf', '來源處理 · PDF 設定', 'form', 5, 1, ['PDF 來源', '處理設定', '框選文字'], [], '擷取並預覽'),
 ('pdf-region', '來源處理 · 框選與結果', 'compare', 5, 1, ['上一頁', '1 / 12', '下一頁', '符合頁寬', '處理設定'], ['放棄預覽', '保留選擇並繼續'], '套用預覽'),
 ('txt', '來源處理 · TXT 匯入／重載', 'form', 5, 1, ['來源檔案', '重新讀取預覽'], ['放棄預覽'], '套用預覽'),
 ('issues', '來源異常', 'compare', 6, 1, ['異常 1 / 4', '上一項', '下一項'], ['明確略過'], '已處理'),
 ('project-info', '專案位置與來源資訊', 'text', 7, 1, ['專案資訊', '來源資訊'], ['複製位置'], ''),
 ('voice', '語音設定與試聽', 'voice', 8, 2, ['本批次', '已存設定／歷史任務', '載入設定', '管理服務'], ['儲存設定'], '前往音訊製做 →'),
 ('narration', '音訊製做', 'table', 9, 2, ['目前製作任務', '朗讀稿與任務設定', '恢復設定'], ['成品操作'], '開始製作 MP3／SRT'),
 ('narration-detail', '朗讀稿與任務設定', 'text', 10, 2, ['朗讀稿與設定', '狀態與錯誤詳情'], [], ''),
 ('assembly', '全書合併音訊', 'table', 11, 2, ['選取有效批次', '上移', '下移', '檢查接點'], ['儲存合併設定', '成品操作'], '製作合併音訊'),
 ('joins', '檢查接點', 'compare', 12, 2, ['接點 1 / 2', '上一個', '下一個', '警告詳情'], [], '儲存並返回'),
 ('join-detail', '接點警告與詳情', 'text', 12, 2, ['來源簽章', '警告說明'], [], ''),
 ('video-batch', '影片製作 · 本批', 'video', 13, 2, ['本批', '畫面與素材', '來源與順序', '任務與成品'], ['保存製作設定', '成品操作'], '製作本批 MP4'),
 ('video-book', '影片製作 · 全書統一素材', 'video', 14, 2, ['全書', '統一素材', '畫面與素材', '來源與順序', '任務與成品'], ['保存製作設定', '成品操作'], '製作全書 MP4'),
 ('video-merge', '影片製作 · 沿用各批影片', 'table', 15, 2, ['全書', '沿用各批影片', '來源與順序', '檢查影音接點'], ['保存製作設定', '成品操作'], '合併各批 MP4'),
 ('video-joins', '檢查影音接點', 'compare', 15, 2, ['接點 1 / 2', '上一個', '下一個'], [], '儲存並返回'),
 ('outputs', '成品版本', 'table', 16, 2, ['音訊／影片', '重新檢查', '查看來源與版本'], ['播放成品', '另存成品／SRT'], '前往製作 →'),
 ('output-detail', '成品來源與版本', 'text', 16, 2, ['來源比較', '技術版本（展開）'], [], ''),
 ('services', '服務管理', 'form', 17, 2, ['服務清單', '新增服務', '編輯目前服務'], ['刪除此服務'], '儲存並返回試聽'),
 ('packages', 'Kokoro 本機語音包', 'form', 18, 2, ['選擇離線語音包', '版本與授權詳情'], ['移除語音包'], '檢查並匯入'),
 ('defaults', '套用全書語音預設', 'table', 19, 2, ['全書語音預設', '選取批次'], [], '套用至選取批次'),
 ('create', '建立書籍專案', 'form', 20, 1, ['選擇新專案資料夾'], [], '建立專案'),
 ('imports', '文稿 · 文件管理展開', 'compare', 20, 1, ['搜尋取代', '編輯', 'AI 校對', '暫存草稿'], [], '儲存為朗讀稿'),
 ('messages', '操作訊息記錄', 'text', 20, 1, ['最近操作', '複製選取訊息'], [], ''),
 ('movie-player', '成品播放', 'video', 16, 2, ['播放', '停止'], [], ''),
]

FORMS = {
 'ai': [('AI 校對服務', 'Gemini'), ('模型（可選或輸入）', 'gemini-2.5-flash'), ('校對文字', '保留原樣'), ('編輯器字級', '12 pt'), ('中文標點', '統一全形標點'), ('偏好保存', '變更即保存')],
 'pdf': [('擷取範圍', '第 1–12 頁'), ('處理方式', '文字層／本機 OCR'), ('辨識語言', '繁中＋英文'), ('版面', '自動'), ('OCR 模型', '模型已就緒'), ('旋轉角度', '0°')],
 'txt': [('來源檔案', '示範書稿.txt'), ('文字編碼', '自動 UTF-8／BOM'), ('匯入範圍', '完整文字'), ('重載方式', '保留現稿副本'), ('解碼狀態', '預覽成功'), ('警告確認', '僅有警告時顯示')],
 'services': [('服務類型', 'Google Gemini TTS'), ('顯示名稱', '我的語音服務'), ('API Key（本機保存）', '••••••••'), ('金鑰來源', '自行輸入'), ('連線檢查', '不產生語音'), ('未存修改', '離頁時保留選擇')],
 'packages': [('離線 ZIP 路徑', '範例路徑／voice.zip'), ('包狀態', '尚未安裝'), ('執行方式', '本機 CPU'), ('品質驗證', '尚無人工聽感證據'), ('版本與授權', '按需展開'), ('文字處理', '僅在本機執行')],
 'create': [('書籍名稱', '示範書籍'), ('新專案資料夾', '選擇空白資料夾')],
 'voice-settings': [('服務', 'Edge-TTS'), ('音色（可選或輸入）', 'zh-TW-HsiaoChenNeural'), ('語速', '正常'), ('節奏', '自然'), ('句尾停頓（ms）', '0'), ('段落停頓（ms）', '500')],
}

PROFILES = [
 ('normal', 1360, 820, False, 12),
 ('reduced', 900, 640, False, 12),
]
# Extra views cover shared geometry, exact 1280 client, reference maximized,
# reclaimed list track, 18pt content and tools; no screenshot is labelled native.
EXTRA = [
 ('manuscript', 'max-reference', 1536, 864, False, 12, 'long'),
 ('narration', '1280', 1280, 720, False, 12, 'long'),
 ('joins', '1280', 1280, 720, False, 12, 'long'),
 ('video-book', '1280', 1280, 720, False, 12, 'short'),
 ('ai', '1280-expanded', 1280, 720, False, 12, 'expanded'),
 ('manuscript', 'collapsed', 900, 640, True, 12, 'long'),
 ('voice', 'collapsed', 900, 640, True, 12, 'long'),
 ('joins', 'collapsed', 900, 640, True, 12, 'long'),
 ('manuscript', '18pt', 900, 640, True, 18, 'long'),
 ('cleanup', '18pt', 900, 640, False, 18, 'long'),
 ('versions', '18pt', 1280, 720, False, 18, 'long'),
 ('joins', '18pt', 900, 640, True, 18, 'long'),
 ('voice', '18pt', 900, 640, True, 18, 'preview-long'),
 ('voice', 'local', 1360, 820, False, 12, 'local'),
 ('voice', 'reduced-preview', 900, 640, False, 12, 'preview'),
 ('ai', 'expanded', 900, 640, False, 12, 'expanded'),
 ('ai', 'connection-error', 900, 640, False, 12, 'error-long'),
 ('packages', 'expanded', 900, 640, False, 12, 'expanded'),
 ('services', 'delete', 900, 640, False, 12, 'delete'),
 ('issues', 'empty', 900, 640, False, 12, 'empty'),
 ('cleanup', 'empty', 900, 640, False, 12, 'empty'),
 ('narration', 'busy', 900, 640, True, 12, 'busy'),
 ('assembly', 'failed', 900, 640, True, 12, 'failed'),
 ('packages', 'cancelled', 900, 640, False, 12, 'cancelled'),
]


def font(size=14, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(value, f, width):
    lines = []
    for paragraph in value.split('\n'):
        line = ''
        for char in paragraph:
            if line and f.getlength(line + char) > width:
                lines.append(line)
                line = ''
            line += char
        lines.append(line)
    return lines


class Drawing:
    def __init__(self, page, label, w, h, collapsed, pt, mode):
        self.page = page
        self.id, self.title, self.family, self.matrix, self.section, self.tools, self.secondary, self.primary = page
        self.label, self.w, self.h = label, w, h
        self.collapsed, self.pt, self.mode = collapsed, pt, mode
        self.image = Image.new('RGB', (w, h), BG)
        self.d = ImageDraw.Draw(self.image)
        self.f, self.heading, self.body = font(), font(16, True), font(round(pt*96/72))
        self.lh = self.body.getbbox('國Ag')[3] + 9
        self.controls, self.regions, self.fields = [], [], []
        self.name = f'{self.id}--{label}'

    def text(self, x, y, value, f=None, color=INK):
        self.d.text((x, y), value, font=f or self.f, fill=color)

    def button(self, x, y, value, width=None, role='secondary', drop=False, group='tools'):
        width = width or int(self.f.getlength(value))+28+(16 if drop else 0)
        color = GREEN if role in ('primary', 'active') else '#e1e5de' if role == 'disabled' else '#ffffff'
        self.d.rectangle((x, y, x+width-1, y+35), fill=color, outline=LINE)
        self.text(x+12, y+8, value, color='#ffffff' if role in ('primary','active') else ERROR if role=='destructive' else INK)
        if drop:
            self.d.polygon([(x+width-17,y+16),(x+width-9,y+16),(x+width-13,y+21)], fill=INK)
        self.controls.append(dict(label=value, group=group, role=role, rect=[x,y,width,36]))
        return x+width+4

    def panel(self, box, fill='white'):
        self.d.rectangle(box, fill=fill, outline=LINE)

    def record(self, owner, box, content_height, mode, visible=True):
        x,y,r,b = box
        view = b-y-8
        overflow = max(0, content_height-view)
        self.regions.append(dict(page=self.id, state=self.name+'/'+mode, owner=owner,
            measurement_source=f'layout-measurements.json#{self.name}/{owner}; Pillow msjh text wrapping / row geometry',
            viewport_height=view, content_height=content_height, max_offset=overflow,
            scrollbar_visible=bool(overflow and visible), thumb_fraction=min(1,view/max(1,content_height)),
            rect=list(box), content_mode=mode))

    def scroll_content(self, owner, box, lines, f=None, lh=None, paper=False):
        x,y,r,b = box
        self.panel(box, PAPER if paper else 'white')
        view = b-y-8
        f, lh = f or self.body, lh or self.lh
        content_height = len(lines)*lh
        self.record(owner, box, content_height, self.mode)
        layer = Image.new('RGB', (r-x-24, max(1,min(view,content_height))), PAPER if paper else 'white')
        draw = ImageDraw.Draw(layer)
        for i, line in enumerate(lines):
            if i*lh >= view: break
            draw.text((3,i*lh),line,font=f,fill=INK)
        self.image.paste(layer,(x+4,y+4))
        self.d = ImageDraw.Draw(self.image)
        if content_height > view:
            self.d.rectangle((r-13,y+4,r-4,b-4),fill='#edf0ed')
            thumb=max(1,round(view*view/content_height))
            self.d.rectangle((r-12,y+4,r-5,y+3+thumb),fill='#8c9b8e')

    def paragraph(self, width):
        if self.mode == 'empty':
            return ['目前沒有異常。原稿與保存狀態保留。'] if self.id=='issues' else ['目前沒有需要整理的換行。文稿未變更。']
        if self.id=='issues':
            value='第 8 頁 · OCR 低信心文字\n請對照原頁核對此段。\n狀態：尚未處理\n「已處理」與「明確略過」均保留來源文字。'
        elif self.id=='project-info':
            value='專案位置：E:/Books/示範書籍\n來源：示範書稿.pdf\n原始來源不會被改寫。\n完整路徑可選取複製。'
        elif self.id in ('messages','join-detail','output-detail','narration-detail'):
            value='第 1 筆紀錄。這是合成的驗證內容。\n來源版本與工作範圍會保留。\n返回前頁後，還原原來的選取與閱讀位置。'
        elif self.id=='cleanup':
            value='－ 清晨，風從窗邊走過。\n＋ 清晨，風從窗邊走過。樹葉輕輕晃動。\n換行整理只在按下套用後生效。'
        else:
            value='清晨，風從窗邊走過。樹葉輕輕晃動。\n這是供布局核對的合成書稿。Hello, welcome to this book.\n第 2 段。原始來源、人工稿與朗讀快照各自保存。'
        if self.mode in ('long','busy','failed','preview-long'):
            value='\n\n'.join(f'第 {i+1} 節\n'+value for i in range(18))
        return wrap(value, self.body, width)

    def draw(self):
        w,h = self.w,self.h
        # The same two-row navigation and two-line header budget for every page.
        self.button(16,12,'1 文稿',144, 'active' if self.section==1 else 'secondary',group='nav-main')
        self.button(164,12,'2 試聽與製作',144,'active' if self.section==2 else 'secondary',group='nav-main')
        self.text(324,21,'示範書籍 · v2')
        self.button(w-228,12,'專案',96,drop=True,group='nav-global')
        self.button(w-128,12,'訊息記錄',112,group='nav-global')
        nav = ['編輯文稿','整理換行預覽','版本紀錄','AI 設定','來源處理'] if self.section==1 else ['語音設定與試聽','音訊製做','全書合併','影片製作']
        size=max(int(self.f.getlength(s))+28 for s in ['整理換行預覽','語音設定與試聽'])
        x=16
        for s in nav:
            active = (s=='編輯文稿' and self.id in ('manuscript','imports') or s=='整理換行預覽' and self.id=='cleanup'
                or s=='版本紀錄' and self.id=='versions' or s=='AI 設定' and self.id=='ai'
                or s=='來源處理' and self.id in ('pdf','pdf-region','txt','issues')
                or s=='語音設定與試聽' and self.id in ('voice','services','packages','defaults')
                or s=='音訊製做' and self.id.startswith('narration')
                or s=='全書合併' and self.id in ('assembly','joins','join-detail')
                or s=='影片製作' and self.id.startswith('video'))
            x=self.button(x,52,s,size,'active' if active else 'secondary',group='nav-local')
        left=16
        cw=216 if not self.collapsed else 0
        start=left+cw+12 if cw else left
        end=w-16
        self.text(start,100,self.title,self.heading)
        tools=list(self.tools)
        if self.mode=='empty' and self.id=='issues':tools=[]
        if self.collapsed: tools=['顯示文件列表']+tools
        available=end-start
        # Secondary tools compact to a named, context-specific command menu.
        widths=[int(self.f.getlength(s))+44 for s in tools]
        if sum(widths)+4*(len(widths)-1)>available:
            tools=tools[:1]+['本頁操作']
        tool_width=max([int(self.f.getlength(s))+44 for s in tools] or [0])
        if len(tools)*(tool_width+4)-4>available:
            tools=tools[:1]+['本頁操作']
            tool_width=max(int(self.f.getlength(s))+44 for s in tools)
        x=start
        for s in tools:
            role='disabled' if self.mode=='busy' and s in ('恢復設定','上移','下移','選取有效批次') else 'secondary'
            x=self.button(x,124,s,tool_width,role=role,drop=s in ('本頁操作','編輯','成品操作','管理服務') or '／' in s,group='page-tools')
        if not tools:self.text(start,132,'沒有待處理的來源異常。',color=MUTED)
        top=168
        bottom=h-100
        if cw:
            self.text(16,100,'文件列表 · '+('0' if self.mode=='empty' else '24' if self.mode=='long' else '3')+' 個文件',self.heading)
            self.button(16,124,'‹',38,group='document-toggle')
            self.button(58,124,'匯入',80,drop=True,group='document-tools')
            self.button(142,124,'管理',80,drop=True,group='document-tools')
            rows=['第一章 · PDF 1–12','已儲存，可朗讀','','第二章 · TXT','草稿已暫存','','第三章 · PDF 13–20','尚未確認']
            if self.mode=='long': rows=rows*8
            if self.mode=='empty': rows=['尚未匯入文件。','從「匯入」加入來源。']
            self.scroll_content('documents',(16,top,232,bottom),rows,font(),27)
        content=(start,top,end,bottom)
        self.content(content)
        self.d.line((16,h-88,w-16,h-88),fill=LINE)
        default_message={
            'ai':'偏好變更即保存；服務連線設定按「儲存設定」後保存。',
            'cleanup':'有 3 處變更 · 原稿尚未變更。',
            'versions':'正在預覽文稿 v3；還原前先備份目前編輯稿。',
            'pdf':'來源原檔保留；擷取完成後先預覽。',
            'pdf-region':'框選原頁及對應文字；結果尚未套用。',
            'txt':'解碼預覽成功；套用前保留現稿副本。',
            'issues':'來源異常 4 項；未處理前不能儲存為朗讀稿。',
            'voice':'本批設定已儲存；試聽文字可自由修改。',
            'assembly':'已選取 3 批 · 交接停頓 0.5 秒 · 合併設定已儲存。',
            'joins':'接點 1 / 2 · 尚未確認 · 交接停頓 0.5 秒。',
            'services':'儲存不會產生語音；返回後可重新試聽。',
            'packages':'本機 CPU · 尚未安裝可用語音包。',
            'defaults':'已選取 2 批；只套用設定，不會開始合成。',
            'create':'輸入書名並選擇空白資料夾。',
        }.get(self.id,'目前沒有進行中的操作。')
        message={'busy':'正在製作 · 完成 3 / 12；可取消任務。','failed':'儲存失敗。輸入與上一份成功成品保留。','error-long':'連線失敗。設定與現稿保留；請檢查設定後重試連線。','cancelled':'已取消匯入。原有效安裝保留。',
                 'delete':'刪除只影響所選服務。請先核對確認區。','empty':'目前沒有待處理項目。'}.get(self.mode,'第一章 · 文稿 v3 · 草稿已暫存，尚未儲存為朗讀稿。' if self.id in ('manuscript','imports') else default_message)
        self.text(16,h-80,message,color=ERROR if self.mode in ('failed','error-long') else MUTED)
        back={'voice':'返回文稿','narration':'返回語音設定','narration-detail':'返回區塊清單','assembly':'返回音訊製做','joins':'返回全書合併','join-detail':'返回接點','video-batch':'返回音訊製做','video-book':'返回全書合併','video-merge':'返回原製作頁','video-joins':'返回影片合併','outputs':'返回原製作頁','output-detail':'返回成品版本','services':'返回語音設定','packages':'返回語音設定','defaults':'返回語音設定','project-info':'返回原頁','messages':'返回原頁','movie-player':'返回成品'}.get(self.id,'返回文稿')
        if self.id not in ('manuscript','imports'):self.button(16,h-52,back,148,group='back')
        labels=self.secondary+([self.primary] if self.primary else [])
        if self.mode=='busy': labels=['取消任務']
        if self.mode=='failed': labels=['重試儲存']
        if self.mode=='delete': labels=['保留服務','確認刪除服務']
        if self.mode=='empty' and self.id in ('issues','cleanup'): labels=[]
        bw=max([int(self.f.getlength(s))+28 for s in labels] or [0])
        x=w-16-len(labels)*bw-max(0,len(labels)-1)*4
        for i,s in enumerate(labels):
            role='primary' if i==len(labels)-1 and self.primary else 'destructive' if s in ('刪除此服務','移除語音包') else 'secondary'
            if s=='確認刪除服務':role='destructive'
            if s=='移除語音包' and self.id=='packages' and self.mode!='cancelled':role='disabled'
            x=self.button(x,h-52,s,bw,role,group='footer-actions')
        if self.id=='imports':
            self.panel((142,160,370,296))
            for i,label in enumerate(('重新命名','上移','下移','移除 PDF 批次…')):
                self.text(154,170+i*30,label,color=ERROR if i==3 else INK)
        self.image.save(OUT/(self.name+'.png'))
        return dict(id=self.name,page=self.id,title=self.title,matrix_row=self.matrix,
                    size=[w,h],content_pt=self.pt,design_dpi=96,list_collapsed=self.collapsed,
                    content_origin=top,header=[start,100,end-start,60],content_box=list(content),
                    fixed_footer_y=h-88,controls=self.controls,fields=self.fields,regions=self.regions,mode=self.mode)

    def content(self, box):
        x,y,r,b=box
        width=r-x
        family=self.family
        if self.mode=='empty':
            self.scroll_content('empty-message',box,self.paragraph(width-28))
            return
        if self.id in ('assembly','video-merge'):
            self.text(x,y+8,'交接停頓')
            self.button(x+84,y,'0.5 秒',100,drop=True,group='pause-field')
            if self.id=='video-merge':self.button(x+188,y,'1080p',100,drop=True,group='resolution-field')
            y+=44;box=(x,y,r,b)
        if self.id in ('joins','video-joins'):
            self.text(x,y+8,'交接停頓')
            self.button(x+84,y,'0.5 秒',84,drop=True,group='pause-field')
            self.text(x+180,y+8,'片段長度')
            self.button(x+264,y,'5 秒',84,drop=True,group='clip-field')
            px=self.button(x+352,y,'播放接點',112,group='join-playback')
            self.button(px,y,'停止試聽',112,group='join-playback')
            self.text(x,b-24,'□ 已檢查此接點；確認後才能合併。')
            y+=44;b-=32;box=(x,y,r,b)
        if family=='form':
            fields=list(FORMS[self.id])
            if self.id=='packages' and self.mode=='cancelled':fields=[(k,'已安裝' if k=='包狀態' else v) for k,v in fields]
            self.form(box,fields)
        elif family=='voice':
            split=width>=980
            if not split:
                self.button(x,y,'聲音設定',132,'active' if not self.mode.startswith('preview') else 'secondary',group='content-tabs')
                self.button(x+136,y,'試聽文字',132,'active' if self.mode.startswith('preview') else 'secondary',group='content-tabs')
                y+=44
            if split or not self.mode.startswith('preview'):
                fields=list(FORMS['voice-settings'])
                if self.mode=='local':fields=[(k,'Kokoro · 本機' if k=='服務' else 'zf_001（品質未驗）' if k.startswith('音色') else v) for k,v in fields]
                self.form((x,y,x+360 if split else r,b),fields,'voice-settings')
            if split or self.mode.startswith('preview'):
                tx=x+372 if split else x
                ww=max(int(self.f.getlength(s))+28 for s in ['使用固定試聽範例','帶入選取文字'])
                self.button(tx,y,'使用固定試聽範例',ww,group='preview-text-actions')
                self.button(tx+ww+4,y,'帶入選取文字',ww,group='preview-text-actions')
                text_box=(tx,y+44,r,b-96)
                self.scroll_content('audition-text',text_box,self.paragraph(r-tx-28))
                if self.mode=='local':self.text(tx,b-84,'本機 CPU；不傳送文字。')
                else:
                    self.d.rectangle((tx,b-82,tx+12,b-70),outline=LINE,fill='white')
                    self.d.line([(tx+2,b-76),(tx+5,b-72),(tx+11,b-80)],fill=GREEN,width=2)
                    self.text(tx+20,b-84,'同意傳送試聽文字（可能計費）')
                px=self.button(tx,b-56,'產生並播放試聽',group='playback-primary')
                px=self.button(px,b-56,'重播',60,group='playback')
                self.button(px,b-56,'停止',60,group='playback')
        elif family=='compare':
            min_width=round(self.body.getlength('國'*20))+28
            split=width>=2*min_width+12
            if not split:
                tabs=('前批結尾','後批開頭') if 'join' in self.id else ('PDF 原頁','對應文字') if self.id=='pdf-region' else ('異常資訊','PDF 原頁') if self.id=='issues' else ('原稿','文稿')
                self.button(x,y,tabs[0],140,'active' if self.id=='pdf-region' else 'secondary',group='content-tabs')
                self.button(x+144,y,tabs[1],140,'active' if self.id!='pdf-region' else 'secondary',group='content-tabs')
                y+=44
            gap=12
            regions=[(x,y,(x+r-gap)//2,b),( (x+r+gap)//2,y,r,b)] if split else [(x,y,r,b)]
            for i,reg in enumerate(regions):
                xx,yy,rr,bb=reg
                first=i==0 if split else self.id=='pdf-region'
                label=('前批結尾' if first else '後批開頭') if 'join' in self.id else ('PDF 原頁' if first else '對應文字與結果') if self.id=='pdf-region' else ('異常資訊' if first else 'PDF 原頁') if self.id=='issues' else ('原稿' if first else '文稿')
                self.text(xx,yy,label,self.heading)
                header=44 if 'join' in self.id else 32
                if 'join' in self.id:self.button(rr-112,yy,'校對本批',112,group='edit-'+str(i))
                if (self.id=='pdf-region' and first) or (self.id=='issues' and not first):
                    pb=(xx,yy+header,rr,bb)
                    self.panel(pb,PAPER)
                    # Fitted source page, not a fabricated source Text scrollbar.
                    ph=bb-yy-header-20;pw=min(rr-xx-20,ph*.707)
                    px=xx+(rr-xx-pw)/2;py=yy+header+10
                    self.panel((px,py,px+pw,py+ph))
                    self.text(px+12,py+12,'合成 PDF · 第 8 頁')
                    for n,line in enumerate(wrap('清晨，風從窗邊走過。\n這是合成原頁，供核對框選與縮放位置。',font(),max(40,pw-24))):self.text(px+12,py+48+n*23,line)
                    self.record('fitted-source-page',pb,0,self.mode)
                else:self.scroll_content(label,(xx,yy+header,rr,bb),self.paragraph(rr-xx-28),paper=first)
        elif family=='table':
            self.text(x,y,'批次／任務' if self.id!='outputs' else '成品路徑',self.heading)
            rows=[]
            count=48 if self.mode in ('long','busy') else 4
            for i in range(count):
                status='執行中' if self.mode=='busy' and i==3 else '等待' if self.mode=='busy' and i>3 else '已完成'
                rows += wrap(f'{i+1:02}  第一章 · {status} · 來源 v3 · 保留有效成品', self.body, width-28)
            self.scroll_content('rows',(x,y+32,r,b),rows)
        elif family=='video':
            if self.id=='movie-player':
                self.panel(box,PAPER)
                vh=min(b-y-24,(width-24)*9/16);vw=vh*16/9
                ix=x+(width-vw)/2;iy=y+(b-y-vh)/2
                self.d.rectangle((ix,iy,ix+vw,iy+vh),fill='#dce7db',outline=LINE)
                self.text(ix+16,iy+16,'成品播放 · 00:03 / 00:12',self.heading)
                self.record('fit-video',box,0,self.mode)
                return
            self.button(x,y,'圖片／背景影片',180,drop=True,group='material')
            self.button(x+184,y,'選擇素材',116,group='material')
            self.button(x+304,y,'1080p',100,drop=True,group='material')
            self.panel((x,y+44,r,b-44),PAPER)
            aw,ah=width-24,b-44-(y+44)-24
            vw=min(aw,ah*16/9);vh=vw*9/16
            ix=x+(width-vw)/2;iy=y+44+(b-44-y-44-vh)/2
            self.d.rectangle((ix,iy,ix+vw,iy+vh),fill='#dce7db',outline=LINE)
            self.text(ix+16,iy+16,'素材預覽 · 符合畫面',self.heading)
            self.button(x,b-36,'播放預覽',116,group='video-playback')
            self.button(x+120,b-36,'停止',80,group='video-playback')
            self.record('fit-video',(x,y+44,r,b-44),0,self.mode)
        else:
            self.scroll_content('text',box,self.paragraph(width-28))

    def form(self,box,fields,owner='form'):
        x,y,r,b=box
        width=r-x
        cols=2 if width>=620 else 1
        colw=(width-40-12*(cols-1))//cols
        rows=[]
        for label,value in fields:
            lines=wrap(label,self.f,colw-8)
            rows.append((label,value,lines,len(lines)*22+44))
        heights=[max(v[3] for v in rows[i:i+cols]) for i in range(0,len(rows),cols)]
        content=sum(heights)+max(0,len(heights)-1)*12+24
        extra=[]
        if self.mode in ('expanded','delete','error-long'):
            details={'ai':'API Key（僅在本機保存）\n••••••••\n測試連線不會提交校對內容。',
                     'packages':'版本與授權詳情\n人工品質驗證：尚無\n移除語音包前須確認。書稿、有效快取與成品保留。',
                     'services':'刪除此服務？\n本機保存的此服務與金鑰將被移除。\n保留服務　／　確認刪除服務'}
            value=details.get(self.id,'詳細設定')
            if self.mode=='error-long':value+='\n\n連線失敗。設定與現稿保留。\n'+'\n'.join('連線診斷範例：無法連線至服務。請檢查連線及本機設定後，再按測試連線。' for _ in range(16))
            extra=wrap(value,self.body,width-48)
            # The detail starts at the actual next row origin. Its complete
            # extent is the final glyph bottom plus four pixels, not an
            # unrelated allowance that creates a scrollbar on a fitting form.
            next_row=12+sum(heights)+12*len(heights)
            content=next_row+(len(extra)-1)*self.lh+self.body.getbbox('國Ag')[3]+4
        self.panel(box)
        view=b-y-8
        layer=Image.new('RGB',(width-24,max(1,min(view,content))),'white')
        d=ImageDraw.Draw(layer)
        cy=12
        for start in range(0,len(rows),cols):
            for j,(label,value,lines,height) in enumerate(rows[start:start+cols]):
                xx=8+j*(colw+12)
                for n,line in enumerate(lines):d.text((xx,cy+n*22),line,font=self.f,fill=INK)
                ty=cy+max(len(v[2]) for v in rows[start:start+cols])*22+8
                readonly=label in ('偏好保存','包狀態','執行方式','品質驗證','版本與授權','文字處理','解碼狀態','警告確認','連線檢查','未存修改')
                if not readonly:d.rectangle((xx,ty,xx+colw-1,ty+35),fill=BG,outline=LINE)
                self.fields.append(dict(label=label,owner=owner,role='readonly' if readonly else 'model-action' if label=='OCR 模型' else 'field',
                                        rect=[x+4+xx,y+4+ty,colw,36],viewport=list(box),group=owner+'-row-'+str(start//cols)))
                # Field values wrap/abbreviate without resizing the control.
                val=value
                while val and self.f.getlength(val)>colw-24: val=val[:-1]
                if val!=value:val=val[:-1]+'…'
                d.text((xx+8,ty+8),val,font=self.f,fill=INK)
                dropdown=not readonly and label!='OCR 模型' and any(k in label for k in ('服務','模型','編碼','校對文字','字級','語速','節奏','音色','處理方式','辨識語言','版面','旋轉','來源','方式')) and '檔案' not in label
                if dropdown:d.polygon([(xx+colw-17,ty+16),(xx+colw-9,ty+16),(xx+colw-13,ty+21)],fill=INK)
            cy+=heights[start//cols]+12
        if extra:
            for n,line in enumerate(extra):d.text((8,cy+n*self.lh),line,font=self.body,fill=INK)
        self.image.paste(layer,(x+4,y+4));self.d=ImageDraw.Draw(self.image)
        self.record(owner,box,content,self.mode)
        if content>view:
            self.d.rectangle((r-13,y+4,r-4,b-4),fill='#edf0ed')
            thumb=max(1,round(view*view/content))
            self.d.rectangle((r-12,y+4,r-5,y+3+thumb),fill='#8c9b8e')


def baseline():
    sources={}
    crossings=[]
    for p in sorted((ROOT/'ebook2mp4').glob('*.py')):
        source=p.read_text(encoding='utf-8-sig')
        sources[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        if not any(v in p.name for v in ('desktop','workspace','shell')): continue
        tree=ast.parse(source)
        lines=source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
            target=ast.unparse(node.func.value)
            method=node.func.attr
            geometry=method in ('grid','grid_remove','grid_configure','grid_forget','pack','pack_forget','pack_configure','rowconfigure','columnconfigure','grid_rowconfigure','grid_columnconfigure')
            shared=any(v in target for v in ('app.actions','app.list_header','app.shell','app.footer','app.stats','app.status','app.workspace_header','app.production','self.left_panel','self.center','self.list_header'))
            cross=any(k.arg=='in_' for k in node.keywords)
            if geometry and (shared or cross):
                function=next((n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.lineno<=node.lineno<=n.end_lineno),'module')
                crossings.append(dict(file=p.relative_to(ROOT).as_posix(),line=node.lineno,function=function,call=lines[node.lineno-1].strip(),classification='review: shared or cross-container geometry; content-local calls require manual triage'))
    return dict(application_sources_sha256=sources,shared_geometry_candidates=crossings,
                excludes='archives/v1 and dist are not opened, hashed, run, or changed')


def main():
    OUT.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True)
    measurements=[]
    for page in PAGES:
        for label,w,h,collapsed,pt in PROFILES:
            measurements.append(Drawing(page,label,w,h,collapsed,pt,'short' if page[2]=='form' else 'long').draw())
    by_id={p[0]:p for p in PAGES}
    for pid,label,w,h,collapsed,pt,mode in EXTRA:
        measurements.append(Drawing(by_id[pid],label,w,h,collapsed,pt,mode).draw())
    # Four actual content cases for every drawn scroll owner. The same row/line
    # generator sets complete heights; fit is a viewport with the exact measured
    # content extent, not a guessed nominal height. These cases are numeric
    # fixtures, separate from the rendered screen's real content measurement.
    contract=[]
    for m in measurements:
        for region in m['regions']:
            contract.append(region)
            view=region['viewport_height']
            lineheight=font(round(m['content_pt']*96/72)).getbbox('國Ag')[3]+9
            for case,count in [('short',1),('fit',max(1,int(view//lineheight))),('overflow',max(2,int(view//lineheight)+1)),('long',max(40,int(view//lineheight)*6))]:
                ch=count*lineheight
                vh=ch if case=='fit' else view
                contract.append(dict(page=m['page'],state=m['id']+'/fixture-'+case,owner=region['owner'],
                    measurement_source=f'design_unified_shell_a.py: {count} measured rows × {lineheight}; fit fixture viewport={ch}; rendered real geometry recorded separately',
                    viewport_height=vh,content_height=ch,scrollbar_visible=ch>vh,max_offset=max(0,ch-vh),thumb_fraction=min(1,vh/ch)))
    (OUT/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,coverage_scope='A design frames listed in layout-measurements; not native/runtime or every future D inner-content state',regions=contract),ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'layout-measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2),encoding='utf-8')
    (EVIDENCE/'source-baseline.json').write_text(json.dumps(baseline(),ensure_ascii=False,indent=2),encoding='utf-8')
    audit=[]
    for m in measurements:
        errors=[]
        for c in m['controls']:
            x,y,w,h=c['rect']
            if x<0 or y<0 or x+w>m['size'][0] or y+h>m['size'][1]:errors.append('out of bounds: '+c['label'])
            if font().getlength(c['label'])+24>w:errors.append('label clipped: '+c['label'])
        for group in ('nav-main','nav-local','document-tools','page-tools','preview-text-actions','footer-actions','playback'):
            controls=sorted([c for c in m['controls'] if c['group']==group],key=lambda c:c['rect'][0])
            if len({tuple(c['rect'][2:]) for c in controls})>1:errors.append('unequal size: '+group)
            for a,z in zip(controls,controls[1:]):
                if z['rect'][0]-(a['rect'][0]+a['rect'][2])!=4:errors.append('gap not 4: '+group)
        for region in m['regions']:
            if region['max_offset']!=max(0,region['content_height']-region['viewport_height']):errors.append('scroll mismatch')
        for field in m['fields']:
            if field['rect'][3]!=36:errors.append('field height not 36')
        audit.append(dict(id=m['id'],errors=errors,header=m['header'],content_origin=m['content_origin']))
    (EVIDENCE/'design-checks.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    index='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>v2 全頁外框 A 設計</title><style>body{font:16px "Microsoft JhengHei",sans-serif;margin:20px;background:#f5f6f2;color:#263d34}header{position:sticky;top:0;background:#f5f6f2;padding:8px;z-index:2}select,button{font:inherit;padding:8px}img{display:block;border:1px solid #c7d2c6;max-width:none}#viewport{overflow:auto}a{color:#315d43}</style><header><b>Ticket #13 A｜待確認設計，非原生驗收</b><p>選擇頁面與狀態。圖為原尺寸；瀏覽器捲動只用於檢閱圖片，不代表產品整頁捲動。</p><select id="frame"></select> <a href="README.md">設計說明</a> · <a href="inventory.md">實際入口盤點</a><p id="meta"></p></header><div id="viewport"><img id="image" alt="全頁外框設計圖"></div><script>const data=DATA;const s=document.getElementById('frame');for(const m of data){const o=document.createElement('option');o.value=m.id;o.textContent=m.title+' · '+m.id+' · '+m.size.join('×');s.append(o)}function show(){const m=data.find(x=>x.id===s.value);document.getElementById('image').src=m.id+'.png';document.getElementById('meta').textContent='設計 DPI 96｜正文 '+m.content_pt+'pt｜內容起點 '+m.content_origin+'｜底列 '+m.fixed_footer_y+'｜'+m.mode;location.hash=m.id}s.onchange=show;if(data.some(x=>x.id===location.hash.slice(1)))s.value=location.hash.slice(1);show();</script></html>'''
    (OUT/'index.html').write_text(index.replace('DATA',json.dumps([{k:v for k,v in m.items() if k not in ('controls','regions')} for m in measurements],ensure_ascii=False)),encoding='utf-8')
    failures=[a for a in audit if a['errors']]
    print(f'{len(measurements)} design frames; {len(contract)} measured/fixture scroll cases; {len(baseline()["shared_geometry_candidates"])} geometry candidates; {len(failures)} layout failures')
    if failures:
        print(json.dumps(failures,ensure_ascii=False))
        raise SystemExit(1)


if __name__=='__main__':main()
