"""Narrow number rules for the K01 synthesis copy."""
import re


_YUAN_AMOUNT = re.compile(r'(?<![A-Za-z0-9.,])[0-9]{1,3}(?:,[0-9]{3})+(?=元)')
_IDENTIFIER = re.compile(r'(编号(?:是|为|[:：])?\s*)(0[0-9]+)(?![A-Za-z0-9]|[.,][0-9])')
_EXTENSION = re.compile(r'(分机(?:是|为|[:：])?\s*)([0-9]+)(?![A-Za-z0-9]|[.,][0-9])')
_DIGITS = str.maketrans('0123456789', '零一二三四五六七八九')


def normalize_numbers(text: str) -> str:
    """Normalize explicit yuan amounts, zero-prefixed IDs and phone extensions."""
    text = _YUAN_AMOUNT.sub(lambda match: match[0].replace(',', ''), text)
    for pattern in (_IDENTIFIER, _EXTENSION):
        text = pattern.sub(lambda match: match[1] + match[2].translate(_DIGITS), text)
    return text
