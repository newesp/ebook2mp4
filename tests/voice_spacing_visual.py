from pathlib import Path
import json
from PIL import ImageGrab
from test_voice_spacing import VoiceSpacing,measure,controls
out=Path('docs/verification/v2-voice-spacing');c=VoiceSpacing();c.setUp();rows=[]
try:
 r,a,p=c.root,c.app,c.dialog
 for size in ['max','1360x820','1280x720','1040x640','900x640']:
  if size=='max':r.state('zoomed')
  else:r.state('normal');r.geometry(size)
  for _ in range(3):r.update();a.layout_workspace()
  r.update();m=measure(p);m.update(size=size,client=[r.winfo_width(),r.winfo_height()],dpi=r.winfo_fpixels('1i'))
  assert m['width_difference']<=2 and m['footer_horizontal_gap']==4 and m['content_vertical_gap']==8
  assert abs(m['first']['y']-m['second']['y'])<=2
  for widget in (*controls(p),p.save_button,p.produce_button):
   assert widget.winfo_ismapped()
   assert widget.winfo_rootx()+widget.winfo_width()<=r.winfo_rootx()+r.winfo_width()+2
   assert widget.winfo_rooty()+widget.winfo_height()<=r.winfo_rooty()+r.winfo_height()+2
  rows.append(m)
  if size in ('1360x820','900x640'):ImageGrab.grab(window=int(r.frame(),16)).save(out/('native-'+size+'.png'))
 p.scope.set('全書預設');p.load_settings();p.update_controls();r.update()
 assert p.apply_defaults_button.winfo_ismapped() and not p.produce_button.winfo_ismapped()
 assert p.apply_defaults_button.winfo_rootx()-(p.save_button.winfo_rootx()+p.save_button.winfo_width())==4
 for first,second in [controls(p)]:
  before=[(w.winfo_width(),w.winfo_height()) for w in (first,second)]
  for state in ['disabled','normal']:
   for w in (first,second):w.configure(state=state)
   r.update();assert before==[(w.winfo_width(),w.winfo_height()) for w in (first,second)]
 (out/'native.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
finally:c.doCleanups()
