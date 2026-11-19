"""Run native checks and write an item-by-item UI acceptance report."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from check_ui_scroll_contract import check

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from run_suite import NativeResult

VOICE = 'test_voice_spacing.VoiceSpacing.test_spacing_at_acceptance_sizes'
JOIN = 'test_audio_join_workspace.AudioJoinWorkspace.'
CASES = {
    'voice': ('試聽區', [
        (VOICE, '開啟語音設定 → 切換視窗尺寸與字級 → 量測試聽列及底部操作列',
         ('native-layout-regression.json',), ('button-size', 'horizontal-gap', 'vertical-gap', 'viewport-matrix')),
        ('test_voice_desktop.VoiceDesktop.test_service_controls_and_editable_models_follow_selected_provider',
         '開啟語音設定 → 切換服務 → 輸入自訂值 → 儲存 → 重開設定', (), ()),
    ]),
    'join': ('檢查接點', [
        (JOIN + 'test_mock_parent_grid_and_native_red_green',
         '開啟音訊組裝 → 選取批次 → 檢查接點 → 量測操作列與文字區',
         ('native-layout-regression.json', 'native-maximized.png'),
         ('row-alignment', 'column-alignment', 'horizontal-gap', 'vertical-gap', 'viewport-matrix')),
        (JOIN + 'test_native_scroll_owners_and_short_fit_overflow_contract',
         '開啟檢查接點 → 輸入不同長度內容 → 量測捲動區的顯隱、比例與行程',
         ('scroll-contract.json', 'native-scroll.json'), ('scroll-short', 'scroll-overflow')),
        (JOIN + 'test_disclosures_scroll_and_empty_transitions_preserve_context',
         '開啟檢查接點 → 捲至長文末端 → 收合及返回 → 切換空狀態',
         (), ('scroll-short', 'scroll-transition', 'scroll-resize')),
        ('test_audio_join_corrections.JoinCorrections.test_shared_header_and_content_anchors',
         '從 PDF 文稿進入檢查接點 → 收合及展開文件列表 → 量測標頭與內容起點',
         ('shell-anchors.json',), ('panel-alignment', 'viewport-matrix')),
        (JOIN + 'test_preview_content_scope_stop_on_edit_and_save_failure',
         '開啟檢查接點 → 試聽 → 修改設定 → 模擬儲存失敗 → 重試儲存',
         ('native-save-failed.png',), ()),
    ]),
}


def source_digest():
    digest = hashlib.sha256()
    files = [*ROOT.glob('ebook2mp4/**/*.py'), *ROOT.glob('ebook2mp4/**/*.json'),
             *ROOT.glob('tests/*.py'), Path(__file__), ROOT / 'tools/check_ui_scroll_contract.py',
             ROOT / 'check-list.md', ROOT / 'docs/ui-components.md', ROOT / 'docs/ui-scroll-qa.md']
    for path in sorted(files):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def join_coverage():
    return [dict(page='檢查接點', size='900x640', owner=owner, state=state)
            for owner in ('前批', '後批', '警告詳情', '文件列表')
            for state in ('short', 'fit', 'overflow', 'long')]


def run_cases(pages, evidence, log):
    results = []
    for page in pages:
        name, cases = CASES[page]
        output = evidence / page
        output.mkdir()
        for test, route, files, checks in cases:
            print(f'Running {test}', flush=True)
            suite = unittest.defaultTestLoader.loadTestsFromName(test)
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=NativeResult).run(suite)
            errors = [f'缺少本次證據 {file}' for file in files if not (output / file).is_file()]
            if 'scroll-contract.json' in files:
                contract = output / 'scroll-contract.json'
                try:
                    data = json.loads(contract.read_text(encoding='utf-8')) if contract.is_file() else {}
                    errors.extend(check(data, join_coverage()))
                except ValueError as error:
                    errors.append(f'無法讀取捲動量測：{error}')
            status = '未測' if result.skipped else '通過'
            if not result.wasSuccessful() or errors and not result.skipped:
                status = '不通過'
            results.append(dict(page=name, test=test, route=route, status=status, checks=checks,
                                category='原生布局與捲動' if checks else '功能回歸',
                                evidence=[f'{page}/{file}' for file in files if (output / file).is_file()],
                                errors=errors))
    return results


def write_report(evidence, results, digest):
    lines = ['# UI 驗收清單', '', f'來源與驗收程式 SHA-256 `{digest}`', '',
             '整體 UI 驗收未完成。表中的測試結果涵蓋已量測的案例。其餘情境、畫面判讀及正式 EXE 操作待驗。',
             '', '## 已執行的原生測試', '']
    for category in ('功能回歸', '原生布局與捲動'):
        statuses = [item['status'] for item in results if item['category'] == category]
        lines.append(f"- {category}　通過 {statuses.count('通過')}　不通過 {statuses.count('不通過')}　未測 {statuses.count('未測')}")
    lines.extend(['- 正式 EXE　未測', ''])
    for number, item in enumerate(results, 1):
        links = [f'[{file}]({file})' for file in item['evidence']]
        lines.extend([f"- 案例 {number}　**{item['status']}**　{item['page']}　{item['route']}",
                      f"  [測試紀錄](native-tests.txt) · `{item['test']}`"
                      + (f" · {' · '.join(links)}" if links else '')])
        lines.extend(f'  - {error}' for error in item['errors'])

    try:
        docs = Path(os.path.relpath(ROOT / 'docs', evidence)).as_posix()
    except ValueError:  # Evidence and source can be on different Windows drives.
        docs = (ROOT / 'docs').as_uri()
    for line in (ROOT / 'check-list.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            lines.extend(['', line, ''])
        if line.startswith('- [ ] '):
            label = re.search(r' <!-- qa:([\w-]+) -->$', line)
            key = label[1] if label else None
            hits = [str(number) for number, item in enumerate(results, 1) if key in item['checks']]
            detail = f"（部分量測見案例 {'、'.join(hits)}）" if hits else ''
            wording = line[6:label.start()] if label else line[6:]
            lines.append(f"- **未測**{detail}　{wording.replace('(docs/', f'({docs}/')}")
    (evidence / 'check-list.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write_json(evidence / 'results.json', dict(source_sha256=digest, cases=results,
                                                full_ui_acceptance='未完成', packaged_exe='未測'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page', action='append', choices=CASES,
                        help='Page to run (repeatable). Default: voice and join.')
    parser.add_argument('--evidence', type=Path, required=True, help='New directory for the results')
    args = parser.parse_args()
    pages = list(dict.fromkeys(args.page or CASES))
    evidence = args.evidence.resolve()
    digest = source_digest()
    evidence.mkdir(parents=True, exist_ok=False)
    if 'join' in pages:
        write_json(evidence / 'expected-scroll-coverage.json', join_coverage())

    with tempfile.TemporaryDirectory(prefix='fixtures-', dir=evidence) as temp:
        with patch.dict(os.environ, EBOOK2MP4_TEST_RUNS=temp,
                        EBOOK2MP4_APP_HOME=str(Path(temp) / 'app'),
                        EBOOK2MP4_KOKORO_HOME=str(Path(temp) / 'kokoro'),
                        VOICE_QA_EVIDENCE=str(evidence / 'voice'),
                        JOIN_QA_EVIDENCE=str(evidence / 'join')):
            with (evidence / 'native-tests.txt').open('w', encoding='utf-8') as log:
                results = run_cases(pages, evidence, log)
    if source_digest() != digest:
        results.append(dict(page='來源版本', category='證據', status='不通過', route='檢查來源雜湊',
                            test='source_digest', checks=(), evidence=(),
                            errors=['驗收期間來源有變更，請重新執行。']))
    write_report(evidence, results, digest)
    print(evidence / 'check-list.md')
    return int(any(item['status'] != '通過' for item in results))


if __name__ == '__main__':
    sys.exit(main())
