"""Deterministic, local Chinese normalization for review candidates only."""
from collections import Counter
from functools import lru_cache
import re

from .workflow import ProjectError

HAN = re.compile(r'[\u3400-\u9fff\U00020000-\U0003134f]')
PROTECTED = re.compile(r'```[\s\S]*?```|`[^`\r\n]*`|https?://[^\s，。！？；「」『』（）]+|'
                       r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[A-Za-z0-9_/-]+(?:\.[A-Za-z0-9_-]+)+')


@lru_cache(maxsize=2)
def converter(direction):
    try:
        from opencc import OpenCC  # type: ignore[import-untyped]
        return OpenCC(direction)
    except (ImportError, OSError):
        raise ProjectError('缺少繁簡校對詞庫，請重新安裝完整程式；仍可人工校對。') from None


def profile(text: str, script: str = 'auto', punctuation: bool = True) -> dict:
    if script not in ('auto', 'traditional', 'simplified', 'preserve') or type(punctuation) is not bool:
        raise ProjectError('請選擇有效的字體與中文標點統一設定。')
    plain = PROTECTED.sub('', text)
    s2t, t2s = converter('s2t'), converter('t2s')
    traditional = simplified = 0
    for character, count in Counter(HAN.findall(plain)).items():
        if t2s.convert(character) != character and s2t.convert(character) == character:
            traditional += count
        elif s2t.convert(character) != character and t2s.convert(character) == character:
            simplified += count
    total = traditional + simplified
    detected = ('traditional' if traditional / total >= .8 else 'simplified' if simplified / total >= .8 else 'uncertain') if total >= 4 else 'uncertain'
    target = detected if script == 'auto' and detected != 'uncertain' else 'preserve' if script == 'auto' else script
    return dict(script=script, target=target, detected=detected, traditional=traditional,
                simplified=simplified, punctuation=punctuation, basis='batch-draft', version=1)


def punctuation_text(text: str, target: str) -> str:
    for left, right, replacement_left, replacement_right in (
            ('(', ')', '（', '）'), ('[', ']', '［', '］'), ('{', '}', '｛', '｝'),
            ('"', '"', '「' if target != 'simplified' else '“', '」' if target != 'simplified' else '”'),
            ("'", "'", '『' if target != 'simplified' else '‘', '』' if target != 'simplified' else '’')):
        pattern = re.escape(left) + r'([^' + re.escape(left+right) + r'\r\n]*)' + re.escape(right)
        text = re.sub(pattern, lambda m: replacement_left+m[1]+replacement_right if HAN.search(m[1]) else m[0], text)
    marks = {',': '，', ':': '：', ';': '；', '?': '？', '!': '！', '.': '。'}
    result = list(text)
    for index, character in enumerate(text):
        if character not in marks:
            continue
        preceding, following_index = index-1, index+1
        while preceding >= 0 and text[preceding] in ' \t':
            preceding -= 1
        while following_index < len(text) and text[following_index] in ' \t':
            following_index += 1
        previous = text[preceding] if preceding >= 0 else ' '
        following = text[following_index] if following_index < len(text) else ' '
        if (HAN.fullmatch(previous) or HAN.fullmatch(following) or previous in '）」』”’］｝'
                or (following in '」』”’' and HAN.search(text[text.rfind('\n', 0, index)+1:index]))):
            result[index] = marks[character]
    return ''.join(result)


def describe(options: dict) -> str:
    names = dict(traditional='繁體', simplified='簡體', preserve='保留原字體', uncertain='證據不足')
    return (f'本批全文字體：{names[options["detected"]]}（繁 {options["traditional"]}／簡 {options["simplified"]}）'
            f'；本次採 {names[options["target"]]}；中文標點' + ('統一' if options['punctuation'] else '保留'))


def normalize(text: str, options: dict) -> str:
    target = options['target']
    prefix = '\ue000'
    while prefix in text:
        prefix += '\ue000'
    saved: list[str] = []
    def protect(match):
        saved.append(match[0])
        return f'{prefix}{len(saved)-1}\ue001'
    plain = PROTECTED.sub(protect, text)
    if target in ('traditional', 'simplified'):
        plain = converter('s2t' if target == 'traditional' else 't2s').convert(plain)
    if options['punctuation']:
        plain = punctuation_text(plain, target)
    return re.sub(re.escape(prefix)+r'(\d+)\ue001', lambda m: saved[int(m[1])], plain)
