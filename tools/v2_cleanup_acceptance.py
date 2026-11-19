"""Synthetic native/EXE acceptance fixture. No network or private manuscript."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'.scratch/v2-cleanup-work'
OUT = ROOT/'docs/verification/v2-linebreak-preview'


def environment(home, package=False):
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(ROOT/'.scratch/build-tools')+os.pathsep+str(ROOT/'tests'),
        EBOOK2MP4_APP_HOME=str(home), EBOOK2MP4_VOICE_HOME=str(home/'voice'),
        EBOOK2MP4_KOKORO_HOME=str(home/'kokoro'), EBOOK2MP4_OCR_HOME=str(home/'ocr'),
        LOCALAPPDATA=str(home/'local'), APPDATA=str(home/'roaming'))
    if package:
        env['PATH'] = r'C:\Windows\System32;C:\Windows'
        env.pop('PYTHONPATH', None)
        for key in ('EBOOK2MP4_FFMPEG', 'EBOOK2MP4_FFPROBE', 'EBOOK2MP4_TESSERACT'):
            env.pop(key, None)
    return env


def fixtures():
    from ebook2mp4.workflow import ProjectWorkflow
    target = BASE/'source'
    target.mkdir(parents=True, exist_ok=True)
    if (target/'book/project.json').exists():
        return ProjectWorkflow.open(target/'book'), json.loads((target/'batches.json').read_text(encoding='utf-8'))
    flow = ProjectWorkflow.create(target/'book', 'v2 換行預覽合成驗收')
    batches = []
    for name, text in [('第一章 · 換行整理範例', '\n\n'.join(
            f'第 {i} 段。清晨的陽光穿過窗簾，落在書桌上。\n保留原字元與空白段落。' for i in range(1,401))),
            ('第二章 · 無須整理範例', '第一段保留原文。\n\n第二段沒有版面換行。')]:
        source = target/(name+'.txt')
        source.write_bytes(text.encode('utf-8'))
        batches.append(flow.import_txt(flow.inspect_txt(source)))
    flow.save_reading_manuscript(batches[1], flow.texts(batches[1])[1])
    (target/'batches.json').write_text(json.dumps(batches), encoding='utf-8')
    return flow, batches


def native():
    from unittest.mock import patch
    from ebook2mp4.desktop import make_app
    from ebook2mp4.workflow import ProjectError
    flow, batches = fixtures()
    root, app = make_app()
    app.flow, app.batch_id = flow, batches[0]
    app.refresh()
    errors = []
    root.report_callback_exception = lambda *args: errors.append(str(args))

    def bounds(w):
        return dict(x=w.winfo_rootx(), y=w.winfo_rooty(), width=w.winfo_width(), height=w.winfo_height(),
                    mapped=bool(w.winfo_ismapped()))

    def measure(name):
        host = app.inner_host
        widgets = dict(list_header=app.list_header, list=app.batch_list, host=host, header=host.header,
            back=host.back, panel=host.panel, context=host.context, content=host.content,
            result=host.actions.stats, actions=host.actions, diff=app.cleanup_preview.diff,
            empty=app.cleanup_preview.empty, global_next=app.next_button)
        if 'manuscript.cleanup.apply' in host.actions.buttons:
            widgets['apply'] = host.actions.buttons['manuscript.cleanup.apply']
        data = dict(client=[root.winfo_width(),root.winfo_height()],dpi=root.winfo_fpixels('1i'),
            scaling=root.tk.call('tk','scaling'),font=app.font_size.get(),active_id=host.active_id,
            result=app.cleanup_preview.message, callbacks=list(host.actions.callbacks),
            widgets={key:bounds(w) for key,w in widgets.items()},diff_yview=app.cleanup_preview.diff.yview(),
            cursor=app.editor.index('insert'),editor_yview=app.editor.yview(),
            selection=list(map(str,app.editor.tag_ranges('sel'))),
            text_sha256=hashlib.sha256(app.current_text.encode()).hexdigest(),
            callback_errors=errors)
        if app.cleanup_preview.diff.winfo_ismapped():
            text = app.cleanup_preview.diff
            data['display_lines'] = text.count('@0,0', f'@0,{text.winfo_height()-1}', 'displaylines')[0]
        (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

    def commands():
        path = BASE/'command.json'
        if path.exists():
            command = json.loads(path.read_text(encoding='utf-8'))
            path.unlink()
            action = command['action']
            if action == 'measure':
                measure(command['name'])
            elif action == 'size':
                root.state('normal')
                root.geometry(command['geometry'])
            elif action == 'max':
                root.state('zoomed')
            elif action == 'font':
                app.font_size.set(str(command['size']))
                if app.tools_open:
                    app.close_tools()
                app.cleanup_line_breaks()
            elif action == 'failure':
                with patch.object(flow,'save_workspace',side_effect=ProjectError(
                        '無法儲存。現稿保留。請排除問題後重試，或返回文稿。')):
                    app.cleanup_preview.apply()
            elif action == 'close':
                app.close()
                return
        root.after(100, commands)
    root.after(100, commands)
    root.mainloop()
    (OUT/'source-exit.json').write_text(json.dumps(dict(normal_exit=True, callback_errors=errors)),encoding='utf-8')


def launch(kind):
    import shutil
    target = BASE/kind
    target.mkdir(parents=True,exist_ok=True)
    if not (target/'book').exists():
        shutil.copytree(BASE/'source/book', target/'book')
        (OUT/(kind+'-before.json')).write_bytes((target/'book/project.json').read_bytes())
    home = target/'home'
    env = environment(home, package=True)
    (home/'session.json').write_text(json.dumps(dict(last_project=str(target/'book'))),encoding='utf-8')
    executable = ROOT/('archives/v1/ebook2mp4/ebook2mp4.exe' if kind=='v1' else 'dist/ebook2mp4/ebook2mp4.exe')
    with (OUT/(kind+'-stderr.txt')).open('w',encoding='utf-8') as errors:
        child = subprocess.Popen([str(executable)],cwd=target,env=env,stderr=errors)
        data = dict(pid=child.pid, executable=str(executable), cwd=str(target), isolated_settings=True,system_only_path=True)
        number = len(list(OUT.glob(kind+'-launch-*.json')))+1
        path = OUT/(kind+f'-launch-{number}.json')
        path.write_text(json.dumps(data,indent=2),encoding='utf-8')
        print(json.dumps(data),flush=True)
        data['exit_code'] = child.wait()
        path.write_text(json.dumps(data,indent=2),encoding='utf-8')


def verify():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    baseline = json.loads((OUT/'design-baseline.json').read_text(encoding='utf-8-sig'))
    archive = ROOT/'archives/v1'
    manifest = json.loads((archive/'manifest.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path = archive/row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
    expected = {row['path'] for row in manifest['files']}
    actual = {p.relative_to(archive).as_posix() for p in archive.rglob('*')
              if p.is_file() and p != archive/'manifest.json'}
    assert actual == expected
    changed = [name for name, digest in baseline['product_sources'].items() if sha(ROOT/name) != digest]
    assert set(changed) == {'ebook2mp4/'+name+'.py' for name in (
        'desktop_shell','workspace_layout','manuscript_cleanup','manuscript_desktop','ui_controls')}, changed
    geometry = []
    for name in ('native-max','native-1360','native-1280','native-900-end'):
        data = json.loads((OUT/(name+'.json')).read_text(encoding='utf-8'))
        widgets = data['widgets']
        header_gap = abs(widgets['list_header']['y']-widgets['header']['y'])
        content_gap = abs(widgets['list']['y']-widgets['panel']['y'])
        assert header_gap <= 2 and content_gap <= 2
        assert not data['callback_errors']
        geometry.append(dict(name=name, client=data['client'],header_gap=header_gap,
            content_gap=content_gap,diff_height=widgets['diff']['height'],display_lines=data['display_lines']))
    end = json.loads((OUT/'native-900-end.json').read_text(encoding='utf-8'))
    wheel = json.loads((OUT/'native-900-wheel.json').read_text(encoding='utf-8'))
    assert wheel['diff_yview'][0] < end['diff_yview'][0]
    assert end['diff_yview'][1] == 1
    for name in ('header','back','panel','actions','apply'):
        assert end['widgets'][name] == wheel['widgets'][name], name
    result = dict(v1_archive_files=len(expected),v1_hashes_unchanged=True,
        preserved_other_product_sources=True,changed_product_sources=changed,
        native_geometry=geometry,keyboard_end_reachable=True,wheel_only_moves_diff=True)
    (OUT/'verified-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


def package_data(stage):
    from ebook2mp4.workflow import ProjectWorkflow
    flow = ProjectWorkflow.open(BASE/'package/book')
    batches = json.loads((BASE/'source/batches.json').read_text(encoding='utf-8'))
    source = ProjectWorkflow.open(BASE/'source/book')
    original = source.texts(batches[0])[0]
    text = flow.workspace_state(batches[0])['text']
    expected = original if stage == 'undo' else ProjectWorkflow.preview_line_breaks(original)
    assert text == expected
    before = json.loads((OUT/'package-before.json').read_text(encoding='utf-8'))
    noop = flow._batch(batches[1])
    original_noop = next(b for b in before['batches'] if b['id']==batches[1])
    assert {k:v for k,v in noop.items() if k!='workspace'} == {
        k:v for k,v in original_noop.items() if k!='workspace'}
    noop_workspace = flow.workspace_state(batches[1])
    if noop_workspace:
        assert noop_workspace['text'] == flow.reading_text(batches[1])
    current = flow._batch(batches[0])
    before_copies = len(next(b for b in before['batches'] if b['id']==batches[0]).get('draft_copies',[]))
    assert len(current['draft_copies']) > before_copies
    for batch in flow.state['batches']:
        path = flow.root/batch['source']['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == batch['source']['sha256']
    result = dict(stage=stage,characters=len(text),sha256=hashlib.sha256(text.encode()).hexdigest(),
        expected_exact=True,noop_versions_and_readiness_unchanged=True,
        noop_exit_autosave_only_change=noop.get('workspace')!=original_noop.get('workspace'),
        new_backups=len(current['draft_copies'])-before_copies,
        original_source_hashes_unchanged=True)
    (OUT/('package-data-'+stage+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    sys.path[:0] = [str(ROOT), str(ROOT/'.scratch/build-tools')]
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=('source','package','v1','verify','verify-undo','verify-package'))
    args = parser.parse_args()
    BASE.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    if args.action=='source':
        os.environ.update(environment(BASE/'source-home'))
        native()
    elif args.action == 'verify':
        verify()
    elif args.action.startswith('verify-'):
        package_data('undo' if args.action == 'verify-undo' else 'applied')
    else:
        launch(args.action)
