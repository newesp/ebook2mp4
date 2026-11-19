"""Unapproved drawings: scroll QA failed. See docs/ui-scroll-qa.md before reuse.

Current scrollbar rendering is schematic and does not measure overflow. Generated
images cannot be released as UI-compliant until the layout/scroll model is fixed.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parents[1]/'docs/ui-review/v2-manuscript-tools-design'
FONT='C:/Windows/Fonts/msjh.ttc'
F=ImageFont.truetype(FONT,14)
H=ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc',16)
INK='#263d34'; BG='#f5f6f2'; LINE='#c7d2c6'; GREEN='#315d43'
PAGES={
 'versions':('版本紀錄',['版本｜朗讀稿 v3 · 2026-11-11','比較基準：目前編輯稿','所選版本唯讀；還原前先備份現稿。'],['刪除此朗讀版本','還原到編輯稿']),
 'history':('歷史 AI 候選',['候選｜2026-11-11 · 部分完成','完成 8 段 · 失敗 1 段 · 未完成 1 段','過期候選僅能還原為人工編輯稿。'],['還原到編輯稿']),
 'settings':('AI 設定',['AI 校對服務｜Gemini','模型（可輸入）｜gemini-2.5-flash','校對文字｜自動','編輯器字級｜18','☑ 統一中文全形標點','服務連線設定'],[]),
 'connection':('AI 設定',['服務連線設定（已展開）','Gemini API Key｜●●●●●●●●','模型（可輸入）｜gemini-2.5-flash','金鑰僅保存在本機，不放入書籍專案。'],['儲存連線','測試連線']),
 'pdf':('PDF 來源處理',['處理範圍｜指定頁面','起始頁｜1','結束頁（含）｜9','擷取方式｜自動','語言｜繁中＋英文','版面｜自動版面','旋轉角度｜0°','OCR 模型｜已安裝'],['重新擷取，預覽差異']),
 'region':('框選重辨',['處理範圍｜框選區域','旋轉角度｜90°','語言｜繁中＋英文','版面｜單一區塊','框選原頁後，反白對應文字。'],['辨識框選，預覽差異']),
 'region-text':('框選重辨',['原頁　　對應文字（目前）','反白與原頁框選相符的文字：','清晨的陽光穿過窗簾，','落在書桌上。','先保留前次選擇，再修正下一區。'],['辨識框選，預覽差異']),
 'source-preview':('來源結果預覽',['結果｜第 1–9 頁重新擷取','套用頁面選擇｜已選 8／9 頁','PDF 結果存成新批次；原人工稿保留。'],['放棄預覽','保留選擇，繼續修正','套用為新批次']),
 'txt':('TXT 匯入／重載預覽',['檔案｜合成外部稿.txt','操作｜重載目前文件','TXT 編碼｜CP950','異常字元：請核對後再套用。','☐ 已核對異常字元，確認原文如此'],['重新載入預覽','套用預覽']),
 'issues':('來源異常',['異常｜第 3 頁 · OCR 信心不足','尚有 2 項待處理；朗讀保存仍阻擋。','選取異常後定位原頁；確認後處理。'],['已處理','明確略過']),
 'project':('專案位置與來源資訊',['專案名稱｜合成驗收書籍','專案位置（可選取）','E:\\合成資料\\書籍專案\\第一冊\\project.json','目前來源｜第一章.pdf','原始檔名｜第一章.pdf · 2.4 MB','內容範圍｜PDF 第 1–9 頁','技術詳細資料（展開）','來源副本相對路徑、檔案雜湊、識別'],[]),
 'search':('搜尋與取代',['搜尋｜陽光','取代｜晨光','下一筆　　上一筆　　取代一處　　全部取代　　復原　　收合'],[]),
}

def draw(key,w,h,collapsed=False,state='normal',large=False):
 title,fields,actions=PAGES[key]
 im=Image.new('RGB',(w,h),BG); d=ImageDraw.Draw(im)
 def text(x,y,s,font=F,color=INK): d.text((x,y),s,font=font,fill=color)
 def btn(x,y,s,width=None,primary=False,disabled=False,dropdown=False):
  width=width or int(d.textlength(s,font=F))+24
  destructive='刪除' in s
  d.rectangle((x,y,x+width-1,y+36),fill='#edf0eb' if disabled else GREEN if primary and not destructive else 'white',outline=LINE)
  text(x+12,y+8,s,color='#68736c' if disabled else '#963b32' if destructive else 'white' if primary else INK)
  if dropdown:d.polygon([(x+width-18,y+15),(x+width-8,y+15),(x+width-13,y+21)],fill=INK)
  return x+width+4
 btn(16,16,'1 文稿',114,disabled=state=='busy');btn(138,16,'2 試聽與製作',142,disabled=state=='busy')
 text(w-395,25,'合成驗收書籍');btn(w-266,16,'專案',126,dropdown=True,disabled=state=='busy');btn(w-132,16,'訊息記錄',116)
 x=16 if collapsed else 236; top=121; bottom=h-65; foot=bottom-62
 if not collapsed:
  btn(16,72,'‹',40);btn(60,72,'匯入',78,dropdown=True,disabled=state=='busy');btn(142,72,'管理',82,dropdown=True,disabled=state=='busy')
  d.rectangle((16,top,223,bottom),fill='white',outline=LINE)
  d.rectangle((17,top+1,222,top+75),fill='#e7efe4')
  for i,s in enumerate(('第一章 · PDF 1–9','第二章 · TXT','第三章 · PDF 10–18')):
   text(32,top+18+i*76,s);text(32,top+42+i*76,'待處理' if i==0 else '已儲存')
 bx=x
 if collapsed:bx=btn(bx,72,'›',40)
 if key!='search':
  bx=btn(bx,72,'← 返回原頁' if key=='project' else '← 返回文稿',130,disabled=state=='busy')
 text(bx+12,80,'文稿' if key=='search' else 'PDF 匯入' if state=='import' and key=='pdf' else title,font=H)
 if key=='search':
  sx=w-16-412
  for label,bw,arrow in (('原稿',82,False),('編輯',68,True),('校對',68,True),('版本',68,True),('暫存草稿',106,False)):
   sx=btn(sx,72,label,bw,dropdown=arrow)
 d.rectangle((x,top,w-17,bottom),fill='white',outline=LINE)
 text(x+20,top+13,'待匯入檔案 · 合成來源.pdf · 9 頁' if state=='import' and key=='pdf' else '待匯入檔案 · 合成外部稿.txt' if state=='import' else '目前專案 · 合成驗收書籍' if key=='project' else '目前文件 · 第一章 · 合成驗收內容')
 d.line((x,top+42,w-17,top+42),fill=LINE)
 if key=='search': foot=bottom
 d.line((x,foot,w-17,foot),fill=LINE)
 result={'normal':'唯讀資訊' if key=='project' else '設定變更即保存' if key=='settings' else '現稿保留 · 請檢查目前內容',
 'error':'儲存失敗。輸入與預覽保留；請排除問題後重試。',
 'busy':'處理中 · 已完成 3／9 頁', 'empty':'目前沒有可用記錄；文稿保留。',
 'confirm':'確認略過／刪除前，請檢查影響範圍。','details':'唯讀資訊','long-path':'唯讀資訊','models':'缺少所選語言模型，安裝後才能辨識。','cancelled':'已取消 · 已完成內容保留','import':'匯入會建立新批次，既有文稿保留。'}[state]
 if key=='connection' and state=='busy':result='測試連線中…'
 actual=list(actions)
 if state=='import':actual=['匯入為新批次'] if key=='txt' else ['擷取並匯入']
 if state=='models':actual=['下載／安裝 OCR 模型']
 if key=='pdf' and state=='error':result='擷取失敗。已完成頁面保留；請重試失敗頁。'
 if state=='busy':actual=['取消作業']
 if state=='empty':actual=[]
 if state=='confirm':actual=['保留原狀','確認刪除' if key=='versions' else '確認略過']
 action_width=sum(int(d.textlength(a,font=F))+28 for a in actual)
 footer_rows=2 if action_width+210>w-x-40 else 1
 if footer_rows==2 and key!='search':
  foot-=30;d.rectangle((x+1,foot,w-18,bottom-1),fill='white');d.line((x,foot,w-17,foot),fill=LINE)
 if key!='search':
  text(x+20,foot+9 if footer_rows==2 else foot+22,result,color='#963b32' if state=='error' else INK)
  ax=w-36-action_width
  for i,a in enumerate(actual):
   ax=btn(ax,bottom-46,a,primary=i==len(actual)-1,disabled=key=='txt' and a in ('套用預覽','匯入為新批次') and state in ('normal','import'))
 # Bounded content surface: only this layer scrolls, never the shell/footer.
 layer=Image.new('RGB',(w,h),'white'); main_d=d; d=ImageDraw.Draw(layer)
 y=top+56; left=x+20; right=w-44
 pdf=key in ('pdf','region','issues') and w>=1100
 if pdf:right=(x+w-16)//2-12
 narrow_page=key=='region' and w<1100
 if key in ('pdf','issues') and w<1100:
  text(left,y,'異常（目前）　　原頁' if key=='issues' else '處理設定（目前）　　原頁',font=H);y+=36
 if narrow_page:
  text(left,y,'設定　　原頁（目前）　　對應文字',font=H);y+=42
  fields=[]
 if state=='empty':
  text(left,y,'尚未開啟專案。請從右上「專案」建立或開啟。' if key=='project' else '目前沒有記錄。返回後可繼續編輯文稿。');fields=[]
 elif state=='confirm':
  text(left,y,'此操作不會刪除目前編輯稿。',font=H);y+=40
  text(left,y,'取消為預設；只在明確確認後執行。');fields=[]
 if key=='project' and state!='details':fields=[a for a in fields if a!='來源副本相對路徑、檔案雜湊、識別']
 grid_fields=key=='settings' and w>=1100
 form_y=y
 scroll_top=top+56
 if key=='search':
  for row,label,value in ((0,'搜尋','陽光'),(1,'取代','晨光')):
   yy=y+row*43;text(left,yy+9,label);btn(left+44,yy,value,180)
   sx=left+228
   for a in (('下一筆','上一筆') if row==0 else ('取代一處','全部取代','復原','收合')):
    sx=btn(sx,yy,a)
  y+=90;fields=[]
 if key=='txt':
  text(left,y,'外部稿.txt · 新批次匯入' if state=='import' else '外部稿.txt · 重載目前文件');y+=28
  text(left,y+9,'編碼');btn(left+44,y,'CP950',200,dropdown=True);y+=45
  text(left,y,'異常字元：請核對後再套用。');y+=26
  d.rectangle((left,y+2,left+13,y+15),outline=LINE)
  text(left+22,y,'已核對異常字元，確認原文如此');y+=30;fields=[]
 if key=='source-preview':
  text(left,y,'PDF 第 1–9 頁 · 結果另存新批次，原人工稿保留。');y+=30
  btn(left,y,'套用頁面選擇 · 已選 8／9 頁',300,dropdown=True);y+=45;fields=[]
 if key in ('versions','history') and state not in ('empty','confirm'):
  text(left,y+9,'版本' if key=='versions' else '候選')
  btn(left+52,y,'朗讀稿 v3 · 2026-11-11' if key=='versions' else '2026-11-11 · 部分完成',right-left-52,dropdown=True);y+=43
  for line in fields[1:]:text(left,y,line);y+=24
  fields=[]
 for index,item in enumerate(fields):
  if state=='long-path' and item.startswith('E:'):
   item='E:\\合成資料\\'+('很長的書籍名稱與章節資料夾\\'*6)+'project.json'
  if grid_fields and index<4:
   left=x+20+(index%2)*((w-x-70)//2+12);right=left+(w-x-90)//2;y=form_y+(index//2)*82
  elif grid_fields and index==4:
   left=x+20;right=w-44;y=form_y+164
  if key=='project':
   item=item.replace('｜','：').replace('技術詳細資料（展開）','技術詳細資料（展開）' if state=='details' else '技術詳細資料（收合）')
  if '｜' in item:
   label,value=item.split('｜',1);text(left,y,label);y+=23
   boxw=right-left
   if key=='settings' and w>=1100:boxw=min(440,boxw)
   btn(left,y,value,boxw,disabled=state=='busy',dropdown=label in ('版本','候選','模型（可輸入）','處理範圍','擷取方式','套用頁面選擇','TXT 編碼','語言','版面','旋轉角度','校對文字','編輯器字級'))
   y+=51
  else:
   if key=='search' and index==2:
    sx=left
    for action in ('下一筆','上一筆','取代一處','全部取代','復原','收合'):
     aw=int(d.textlength(action,font=F))+24
     if sx+aw>right:sx=left;y+=43
     sx=btn(sx,y,action,aw)
    y+=49
    continue
   if item=='服務連線設定' or item.startswith('技術詳細資料'):
    btn(left,y,item,disabled=state=='busy');y+=49
    continue
   if item.startswith(('☐','☑')):
    d.rectangle((left,y+2,left+13,y+15),outline=LINE,fill='white')
    if item[0]=='☑':d.line([(left+2,y+8),(left+6,y+12),(left+12,y+4)],fill=GREEN,width=2)
    text(left+22,y,item[1:].strip());y+=32
    continue
   # Wrap long paths and explanatory prose; never horizontal scroll.
   line=''
   for c in item:
    if d.textlength(line+c,font=F)>right-left:
     text(left,y,line);y+=24;line=''
    line+=c
   text(left,y,line);y+=32
 if key in ('versions','history','source-preview','txt','search') and state not in ('empty','confirm'):
  text(left,y,'目前文稿　→　所選結果' if key!='search' else '找到 3 筆 · 第 1 筆',font=H);y+=34
  scroll_top=y
  for i in range(1,18):
   sample=('- 舊版文字。' if i%2 else '+ 修正後文字。') if key!='search' else f'第 {i} 段。陽光穿過窗簾，落在書桌上。'
   bf=ImageFont.truetype(FONT,24) if large else F
   segment=''
   for c in sample:
    if d.textlength(segment+c,font=bf)>right-left:
     text(left,y,segment,font=bf);y+=34;segment=''
    segment+=c
   text(left,y,segment,font=bf);y+=34
 if key=='region-text':
  d.rectangle((left,y-110,right,y-62),fill='#e7efe4');text(left+4,y-106,'清晨的陽光穿過窗簾，落在書桌上。')
 if pdf or narrow_page:
  px=(x+w-16)//2+12 if pdf else left; py=top+56 if pdf else y
  text(px,py,'來源原頁',font=H);py+=26
  nx=btn(px,py,'‹',40);nx=btn(nx,py,'1／9',65);nx=btn(nx,py,'›',40);btn(nx,py,'符合頁寬',118,dropdown=True)
  py+=45
  d.rectangle((px,py,w-45,foot-14),fill='#edf0ed',outline=LINE)
  if foot-py>80:
   d.rectangle((px+16,py+12,w-61,foot-26),fill='white',outline=LINE)
   text(px+30,py+30,'第一章 · 合成原頁',font=H)
   for i in range(max(0,(foot-py-100)//32)):text(px+30,py+78+i*32,'原頁文字，可定位並框選。')
   if key=='region':d.rectangle((px+25,py+64,w-73,min(foot-35,py+143)),outline=GREEN,width=2)
 im.paste(layer.crop((x+1,top+44,w-18,foot)),(x+1,top+44));d=main_d
 if state not in ('empty','confirm'):
  if pdf and key=='pdf':
   d.rectangle((right+1,top+56,right+11,foot-12),fill='#edf0ed',outline=LINE)
   d.rectangle((right+3,top+58,right+9,top+100),fill='#b7bcb3')
  d.rectangle((w-35,scroll_top,w-24,foot-12),fill='#edf0ed',outline=LINE)
  d.rectangle((w-33,scroll_top+2,w-26,min(foot-13,scroll_top+44)),fill='#b7bcb3')
 text(18,h-49,'合成驗收書籍 · 第一章 · 文稿與保存狀態保留')
 text(18,h-25,'靜態設計圖 · 功能、原生布局及 EXE 驗收待實作後執行')
 if key=='search':btn(w-172,h-54,'儲存為朗讀稿',150,primary=True)
 name=f'{key}-{w}'+('-collapsed' if collapsed else '')+('-'+state if state!='normal' else '')+('-18pt' if large else '')
 im.save(OUT/(name+'.png'))
 return name

if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True)
 names=[]
 for key in PAGES:
  for w,h,c in ((1360,820,False),(900,640,False),(900,640,True)):
   names.append(draw(key,w,h,c))
 for key,state in [('versions','empty'),('versions','confirm'),('history','empty'),('connection','busy'),('connection','error'),('pdf','busy'),('source-preview','error'),('issues','empty'),('issues','confirm'),('project','empty')]:
  names.append(draw(key,900,640,state=state))
 names.append(draw('project',900,640,state='details'))
 names.append(draw('project',900,640,state='long-path'))
 for key in ('versions','history','source-preview','txt','search'):
  names.append(draw(key,900,640,large=True))
 for state in ('models','error','cancelled'):
  names.append(draw('pdf',900,640,state=state))
 for key in ('txt','pdf'):
  for w,h in ((900,640),(1360,820)):
   names.append(draw(key,w,h,state='import'))
 (OUT/'drawings.json').write_text(json.dumps(names,indent=2),encoding='utf-8')
 # Overview is for navigation; original-size drawings remain authoritative.
 sheet=Image.new('RGB',(1360,((len(PAGES)+1)//2)*300),'#ffffff'); p=ImageDraw.Draw(sheet)
 for i,key in enumerate(PAGES):
  thumb=Image.open(OUT/(key+'-1360.png')).resize((640,258))
  xx=20+(i%2)*680;yy=(i//2)*300
  p.text((xx,yy+2),PAGES[key][0],font=H,fill=INK);sheet.paste(thumb,(xx,yy+28))
 sheet.save(OUT/'overview.png')
