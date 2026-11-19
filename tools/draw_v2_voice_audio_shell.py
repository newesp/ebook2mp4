from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
O=Path('docs/ui-review/v2-voice-settings-audio-shell');O.mkdir(parents=True,exist_ok=True)
f=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',14);b=ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc',16)
measure=[]
def draw(w,h,local=False,narrow_view='settings',long=False):
 im=Image.new('RGB',(w,h),'#f5f6f2');d=ImageDraw.Draw(im);ink='#263d34';line='#c7d2c6';green='#315d43'
 def text(x,y,s,font=f,color=ink):d.text((x,y),s,font=font,fill=color)
 def button(x,y,width,s,primary=False,drop=False):
  d.rectangle((x,y,x+width-1,y+36),fill=green if primary else 'white',outline=line);text(x+9,y+8,s,color='white' if primary else ink)
  if drop:d.polygon([(x+width-18,y+15),(x+width-8,y+15),(x+width-13,y+21)],fill=ink)
 button(16,16,100,'1 文稿');button(124,16,130,'2 試聽與製作',True)
 d.line((264,16,264,52),fill=line)
 button(276,16,150,'語音設定與試聽',True);text(430,25,'→');button(452,16,114,'音訊製做');text(570,25,'→');button(592,16,114,'全書合併');d.line((716,16,716,52),fill=line);button(728,16,114,'影片製作')
 text(w-375,25,'合成驗收書籍');button(w-266,16,126,'專案',drop=True);button(w-132,16,116,'訊息記錄')
 button(16,72,40,'‹');button(60,72,78,'匯入',drop=True);button(142,72,82,'管理',drop=True)
 d.rectangle((16,121,223,h-104),fill='white',outline=line);d.rectangle((17,122,222,197),fill='#e7efe4')
 for i,label in enumerate(['第一章 · PDF 1–9','第二章 · PDF 1–2','第三章 · TXT','第四章 · PDF 1–1']):
  text(32,138+i*90,label);text(32,162+i*90,'已儲存 · 可朗讀' if i<3 else '尚未確認')
 d.rectangle((236,121,w-16,h-104),fill='white',outline=line)
 x=236;y=72;button(x,y,260,'已存設定／歷史任務',drop=True);button(x+264,y,110,'載入設定');text(x+390,y+9,'目前：本批次')
 x=252
 y=132;text(x,y+9,'服務');button(x+48,y,200,'Kokoro · 本機' if local else 'Edge TTS',drop=True)
 if not local:text(x+260,y+9,'模型');button(x+308,y,min(270,w-580),'預設模型',drop=True)
 button(w-184,y,168,'管理語音包' if local else '新增／管理服務',drop=not local)
 top=184;foot=h-68;bodybottom=foot-36
 if w>=1100:
  leftx=252;leftw=320;rightx=584;rightw=w-rightx-32; panels=['settings','text']
 else:
  button(16,207,130,'聲音設定',narrow_view=='settings');button(150,207,130,'試聽文字',narrow_view=='text');top=254
  leftx=rightx=16;leftw=rightw=w-32;panels=[narrow_view]
 if 'settings' in panels:
  d.rectangle((leftx,top,leftx+leftw,bodybottom),fill='white',outline=line);lx=leftx+16;cw=leftw-32
  text(lx,top+10,'設定聲音與節奏',b)
  text(lx,top+40,'音色（可選或輸入 ID）');button(lx,top+60,cw,'zf_001' if local else 'zh-TW-HsiaoChenNeural',drop=True)
  col=(cw-8)//2;text(lx,top+105,'語速');text(lx+col+8,top+105,'節奏');button(lx,top+125,col,'正常',drop=True);button(lx+col+8,top+125,col,'自然',drop=True)
  text(lx,top+170,'句尾停頓（ms）');text(lx+col+8,top+170,'段落停頓（ms）');button(lx,top+190,col,'0');button(lx+col+8,top+190,col,'500')
  if bodybottom-top>290:
   text(lx,top+232,'音色來源');button(lx,top+252,col,'全部語系' if not local else '本機語音包',drop=not local);button(lx+col+8,top+252,col,'更新線上音色' if not local else '管理語音包')
 if 'text' in panels:
  d.rectangle((rightx,top,rightx+rightw,bodybottom),fill='white',outline=line);rx=rightx+16;rw=rightw-32;text(rx,top+10,'編輯文字並試聽',b)
  button(rx,top+35,150,'使用固定試聽範例');button(rx+154,top+35,145,'帶入選取文字')
  vy=top+80;vend=bodybottom-108;vh=max(1,vend-vy);d.rectangle((rx,vy,rx+rw,vend),fill='#ffffff',outline=line)
  mode=long if isinstance(long,str) else 'long' if long else 'short'
  count=2 if mode=='short' else max(1,(vh-8)//28) if mode=='fit' else (vh-8)//28+2 if mode=='overflow' else 50
  lines=[f'第 {i} 段。這是合成資料的語音試聽範例。' for i in range(1,count+1)]
  lh=28;content=(vh-8) if mode=='fit' else len(lines)*lh;layer=Image.new('RGB',(rw-24,content),'white');ld=ImageDraw.Draw(layer)
  for i,s in enumerate(lines):ld.text((4,i*lh+3),s,font=f,fill=ink)
  im.paste(layer.crop((0,0,rw-24,min(content,vh-8))),(rx+5,vy+4));d=ImageDraw.Draw(im)
  if content>vh-8:
   track=vh-8;thumb=round(track*track/content);d.rectangle((rx+rw-12,vy+4,rx+rw-3,vend-4),fill='#edf0ed',outline=line);d.rectangle((rx+rw-10,vy+5,rx+rw-5,vy+4+thumb),fill='#b7bcb3')
  if local:text(rx,vend+8,'文字僅在本機處理')
  else:
   d.rectangle((rx,vend+10,rx+13,vend+23),fill='white',outline=line);d.line([(rx+2,vend+16),(rx+6,vend+20),(rx+12,vend+12)],fill=green,width=2);text(rx+20,vend+8,'同意傳送試聽文字（可能計費）')
  button(rx,vend+34,160,'產生並播放試聽',True);button(rx+164,vend+34,68,'重播');button(rx+236,vend+34,68,'停止')
  text(rx,vend+76,'尚未產生試聽。')
  measure.append(dict(page='語音設定與試聽',state=f'{w}-{narrow_view}-{local}-{mode}',owner='試聽文字',measurement_source='draw_v2_voice_settings.py 行數×28，文字框高度減內距',viewport_height=vh-8,content_height=content,scrollbar_visible=content>vh-8,max_offset=max(0,content-(vh-8)),**({'thumb_fraction':(vh-8)/content} if content>vh-8 else {})))
 text(18,h-94,'第一章 · PDF 1–9 · 文稿已儲存，可朗讀')
 button(16,foot+8,130,'← 返回文稿');button(w-475,foot+8,100,'本批次',drop=True);button(w-371,foot+8,120,'只儲存設定');button(w-247,foot+8,230,'前往音訊製做 →',True)
 name=f'{w}-'+('local' if local else 'online')+'-'+('wide' if w>=1100 else narrow_view)+('-'+mode if mode!='short' else '')
 measure.append(dict(page='語音設定與試聽',state=name,owner='聲音設定',measurement_source='同份繪圖資料：最後控制項底部top+289',viewport_height=bodybottom-top,content_height=289,scrollbar_visible=False,max_offset=0))
 measure.append(dict(page='語音設定與試聽',state=name,owner='文件列表',measurement_source='同份繪圖資料：四列90像素',viewport_height=h-104-121,content_height=360,scrollbar_visible=False,max_offset=0))
 im.save(O/(name+'.png'))
for w,h in ((1360,820),(1920,1000)):
 for loc in (False,True):
  for mode in ('short','fit','overflow','long'):draw(w,h,loc,long=mode)
(O/'scroll-contract.json').write_text(json.dumps({'coverage_complete':True,'regions':measure},ensure_ascii=False,indent=2),encoding='utf-8')
