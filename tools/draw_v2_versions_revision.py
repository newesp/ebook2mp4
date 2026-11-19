from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
out=Path('docs/ui-review/v2-versions-revision');out.mkdir(parents=True,exist_ok=True)
f=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',14);bold=ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc',16)
rows=[]
def draw(w,h,state,collapsed=False,large=False):
 im=Image.new('RGB',(w,h),'#f5f6f2');d=ImageDraw.Draw(im);ink='#263d34';line='#c7d2c6';green='#315d43'
 def txt(x,y,s,font=f,fill=ink):d.text((x,y),s,font=font,fill=fill)
 def btn(x,y,width,label,primary=False,red=False,arrow=False):
  d.rectangle((x,y,x+width-1,y+36),fill=green if primary else 'white',outline=line);txt(x+10,y+8,label,fill='white' if primary else '#963b32' if red else ink)
  if arrow:d.polygon([(x+width-18,y+15),(x+width-8,y+15),(x+width-13,y+21)],fill=ink)
 def finish(view,content,off):
  name=f'{state}-{w}'+('-collapsed' if collapsed else '')+('-18pt' if large else '')
  txt(18,h-49,'合成驗收書籍 · 第一章 · 文稿與保存狀態保留')
  txt(18,h-25,'靜態設計圖 · 原生功能及 EXE 尚待驗收')
  im.save(out/(name+'.png'))
  row=dict(page='版本紀錄',state=name,owner='版本差異',measurement_source='draw_v2_versions_revision.py: 行數×行高與內容區幾何',viewport_height=view,content_height=content,scrollbar_visible=off>0,max_offset=off)
  if off>0:row['thumb_fraction']=view/content
  rows.append(row)
 btn(16,16,114,'1 文稿');btn(138,16,142,'2 試聽與製作');txt(w-392,25,'合成驗收書籍');btn(w-266,16,126,'專案',arrow=True);btn(w-132,16,116,'訊息記錄')
 x=16 if collapsed else 236;top=121;bottom=h-65;footer=bottom-62
 if not collapsed:
  btn(16,72,40,'‹');btn(60,72,78,'匯入',arrow=True);btn(142,72,82,'管理',arrow=True);d.rectangle((16,top,223,bottom),fill='white',outline=line);d.rectangle((17,top+1,222,top+75),fill='#e7efe4')
  for i,t in enumerate(['第一章 · PDF 1–9','第二章 · TXT','第三章 · PDF 10–18']):txt(32,top+18+i*76,t);txt(32,top+42+i*76,'已儲存')
 bx=x
 if collapsed:btn(bx,72,40,'›');bx+=44
 btn(bx,72,130,'← 返回文稿');txt(bx+142,80,'版本紀錄',bold)
 d.rectangle((x,top,w-17,bottom),fill='white',outline=line);txt(x+20,top+13,'目前文件 · 第一章 · 合成驗收內容');d.line((x,top+42,w-17,top+42),fill=line)
 d.line((x,footer,w-17,footer),fill=line);txt(x+20,footer+22,'尚無版本' if state=='empty' else '所選版本唯讀 · 還原前會備份現稿')
 if state not in ('empty','candidate'):btn(w-322,footer+12,142,'刪除此朗讀版本',red=True)
 if state!='empty':btn(w-174,footer+12,138,'還原到編輯稿',primary=True)
 if state=='empty':txt(x+20,top+66,'尚無版本。儲存為朗讀稿後，可在此預覽與還原。');return finish(footer-12-(top+132),0,0)
 txt(x+20,top+58,'選擇版本');btn(x+100,top+48,min(400,w-x-140),'AI 候選 · 2026-11-11 · 部分完成' if state=='candidate' else '朗讀稿 v3 · 2026-11-11',arrow=True)
 txt(x+20,top+103,'目前編輯稿 → 所選版本',bold)
 vy=top+132;end=footer-12;view=end-vy;line_h=36 if large else 28;left=x+24;right=w-45
 base=['--- 目前編輯稿','+++ 所選版本','@@ 第 1 段 @@','  清晨的陽光穿過窗簾。','- 落在書桌上。','+ 落在木桌上。','  窗外傳來鳥鳴。']
 count={'short':len(base),'candidate':len(base),'fit':max(1,view//line_h),'overflow':max(1,view//line_h)+2,'long':70}[state]
 lines=(base* (count//len(base)+1))[:count];content=view if state=='fit' else count*line_h;off=max(0,content-view);visible=off>0
 layer=Image.new('RGB',(right-left,content),'white');ld=ImageDraw.Draw(layer)
 for i,t in enumerate(lines):
  if t.startswith(('+ ','- ')):ld.rectangle((0,i*line_h,min(right-left-1,230),i*line_h+line_h-4),fill='#e7efe4' if t[0]=='+' else '#f8e8e3')
  ld.text((0,i*line_h),t,font=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',24) if large else f,fill=ink)
 im.paste(layer.crop((0,0,right-left,min(content,view))),(left,vy));d=ImageDraw.Draw(im)
 if visible:
  track=view;thumb=max(1,round(track*view/content));d.rectangle((w-34,vy,w-24,end),fill='#edf0ed',outline=line);d.rectangle((w-32,vy+1,w-26,vy+thumb-1),fill='#aeb7ac')
 return finish(view,content,off)

for w,h in ((1360,820),(1280,720),(900,640)):
 for state in ('short','fit','overflow','long','empty','candidate'):draw(w,h,state)
for state in ('short','fit','overflow','long','empty'):draw(900,640,state,True)
for state in ('short','fit','overflow','long','empty'):draw(900,640,state,False,True)
(out/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,regions=rows),ensure_ascii=False,indent=2),encoding='utf-8')
