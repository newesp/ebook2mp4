"""Check measured scroll geometry; visual and native input QA remain separate."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys


def coverage_key(row):
    fields = tuple(row[field] for field in ('page', 'size', 'owner', 'state'))
    if not all(isinstance(field, str) and field.strip() for field in fields):
        raise ValueError('page、size、owner、state 須為非空字串')
    return fields


def check(data, expected=None):
    errors = []
    if not isinstance(data, dict) or not isinstance(data.get('regions', []), list):
        return ['捲動契約須為含 regions 陣列的物件']
    if expected is None and data.get('coverage_complete') is not True:
        errors.append('尚未完成全部頁面／尺寸／狀態的捲動盤點')
    regions = data.get('regions', [])
    if not regions:
        errors.append('缺少來源布局量測')
    for index, row in enumerate(regions):
        if not isinstance(row, dict):
            errors.append(f'第 {index + 1} 筆量測須為物件')
            continue
        label = f'{row.get("page", index)} / {row.get("state", "?")}'
        try:
            for key in ('page', 'state', 'owner', 'measurement_source'):
                if not row.get(key):
                    raise ValueError(f'缺少 {key}')
            view, content, offset = (float(row[k]) for k in (
                'viewport_height', 'content_height', 'max_offset'))
            if not all(map(math.isfinite, (view, content, offset))) or view <= 0 or content < 0 or offset < 0:
                raise ValueError('幾何值無效')
            visible = row['scrollbar_visible']
            if not isinstance(visible, bool):
                raise ValueError('scrollbar_visible 必須為布林值')
            expected_offset = max(0, content-view)
            if visible != (expected_offset > 0):
                errors.append(f'{label}: 捲軸顯隱與實際溢出不符')
            if abs(offset-expected_offset) > 1:
                errors.append(f'{label}: 行程與完整內容範圍不符')
            if visible:
                fraction = float(row['thumb_fraction'])
                if not 0 < fraction <= 1 or abs(fraction-min(1, view/max(1, content))) > .02:
                    errors.append(f'{label}: 滑塊比例與可見內容不符')
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f'{label}: {error}')
    if expected is not None:
        try:
            required = set(map(coverage_key, expected))
            measured = Counter(coverage_key(row) for row in regions)
            if not required:
                errors.append('預期情境清單為空')
            for key in sorted(required - measured.keys()):
                errors.append('漏測：' + ' / '.join(key))
            for key in sorted(measured.keys() - required):
                errors.append('未列入預期情境：' + ' / '.join(key))
            for key, count in measured.items():
                if count > 1:
                    errors.append('重複量測：' + ' / '.join(key))
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f'無法比對預期情境：{error}')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--expected-coverage', type=Path, help='JSON list of expected page/size/owner/state cases')
    args = parser.parse_args()
    try:
        expected = (json.loads(args.expected_coverage.read_text(encoding='utf-8-sig'))
                    if args.expected_coverage else None)
        if args.expected_coverage and not isinstance(expected, list):
            raise ValueError('預期情境須為 JSON 陣列')
        errors = check(json.loads(args.contract.read_text(encoding='utf-8-sig')), expected)
    except (OSError, ValueError) as error:
        errors = [str(error)]
    if errors:
        print('SCROLL QA FAILED\n'+'\n'.join(errors))
        sys.exit(1)
    print('Scroll geometry contract passed; visual/native verification still required.')
