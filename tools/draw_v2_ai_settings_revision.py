from pathlib import Path
p=Path('tools/draw_v2_manuscript_tools.py');s=p.read_text(encoding='utf-8')
s=s.replace("grid_fields=key=='settings' and w>=1100", "grid_fields=key in ('settings','connection')")
s=s.replace("if key=='settings' and w>=1100:boxw=min(440,boxw)", "if key in ('settings','connection'):boxw=min(440,boxw)")
s=s.replace("if item=='服務連線設定' or item.startswith", "if item.startswith('服務連線設定') or item.startswith")
s=s.replace("if state not in ('empty','confirm'):\n  if pdf", "if state not in ('empty','confirm') and key not in ('settings','connection'):\n  if pdf")
s=s.replace("im.save(OUT/(name+'.png'))", "im.save(OUT/(name+'.png'))\n print(name, 'content_end', y, 'viewport_end', foot)")
ns={'__file__':str(p.resolve()),'__name__':'revision'};exec(compile(s,str(p),'exec'),ns)
out=Path('docs/ui-review/v2-ai-settings-revision');out.mkdir(parents=True,exist_ok=True);ns['draw'].__globals__['OUT']=out
pages=ns['PAGES']; settings=pages['settings'][1]; pages['settings']=(pages['settings'][0],settings[:-1]+['服務連線設定（展開）'],[]); pages['connection']=('AI 設定',settings[:-1]+['服務連線設定（收合）','Gemini API Key｜●●●●●●●●'],['儲存連線','測試連線'])
for key in ['settings','connection']:
 for w,h in [(1360,820),(900,640)]:ns['draw'](key,w,h)

for key in ['settings','connection']:ns['draw'](key,900,640,collapsed=True)
