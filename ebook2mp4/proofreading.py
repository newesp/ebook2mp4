"""Deterministic, local Chinese normalization for review candidates only."""
from collections import Counter
from functools import lru_cache
from importlib.resources import files
import re

from .workflow import ProjectError

HAN = re.compile(r'[\u3400-\u9fff\U00020000-\U0003134f]')
PROTECTED = re.compile(r'```[\s\S]*?```|`[^`\r\n]*`|https?://[^\s，。！？；「」『』（）]+|'
                       r'[A-Za-z]:[\\/][^\s,，。！？；「」『』（）"<>|]+|'
                       r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(?:[A-Za-z]\.){2,}|'
                       r'(?<![A-Za-z0-9])[-+]?(?:\d+\.\d+|\.\d+)(?:[eE][-+]?\d+)?|'
                       r'(?:[\w.-]+[\\/])+[\w.-]+|[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+|'
                       r'[\w-]+(?:\.[A-Za-z_][A-Za-z0-9_-]*)+(?![\w.@])')


@lru_cache(maxsize=2)
def converter(direction):
    try:
        from opencc import OpenCC  # type: ignore[import-untyped]
        return OpenCC(direction)
    except (ImportError, OSError):
        raise ProjectError('缺少繁簡校對詞庫，請重新安裝完整程式；仍可人工校對。') from None


@lru_cache(maxsize=1)
def ambiguous_characters() -> frozenset[str]:
    """OpenCC explicitly lists shared forms among alternatives, e.g. 里/后/干."""
    shared = set()
    try:
        for name in ('STCharacters.txt', 'TSCharacters.txt'):
            for line in files('opencc').joinpath('dictionary', name).read_text(encoding='utf-8').splitlines():
                source, alternatives = line.split('\t', 1)
                if source in alternatives.split():
                    shared.add(source)
    except (ImportError, OSError, ValueError):
        raise ProjectError('繁簡證據詞庫遺失或損壞，請重新安裝完整程式。') from None
    return frozenset(shared)


def profile(text: str, script: str = 'auto', punctuation: bool = True) -> dict:
    if script not in ('auto', 'traditional', 'simplified', 'preserve') or type(punctuation) is not bool:
        raise ProjectError('請選擇有效的字體與中文標點統一設定。')
    plain = PROTECTED.sub('', text)
    s2t, t2s = converter('s2t'), converter('t2s')
    traditional = simplified = 0
    for character, count in Counter(HAN.findall(plain)).items():
        if character in ambiguous_characters():
            continue
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
        if left == "'":
            pattern = r'(?<![A-Za-z0-9])' + pattern + r'(?![A-Za-z0-9])'
        text = re.sub(pattern, lambda m: replacement_left+m[1]+replacement_right if HAN.search(m[1]) else m[0], text)
    text = re.sub(r'([\u3400-\u9fff）」』”’])([ \t]*)\.{3,}', r'\1\2……', text)
    marks = {',': '，', ':': '：', ';': '；', '?': '？', '!': '！', '.': '。'}
    result = list(text)
    for index, character in enumerate(text):
        if character not in marks:
            continue
        if character == '.' and (text[index-1:index] == '.' or text[index+1:index+2] == '.'):
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
