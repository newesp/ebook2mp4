"""Local Tesseract and verified, per-user language models. No manuscript network calls."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import urllib.request
import subprocess
import time
import csv
from io import StringIO, BytesIO
import re

from .workflow import ProjectError


LANGUAGES = {'繁中＋英文': 'chi_tra+eng', '簡中＋英文': 'chi_sim+eng', '英文': 'eng',
             '自動中英': 'chi_sim+chi_tra+eng'}
# Official tessdata_fast 4.1.0, pinned to its commit (Apache-2.0).
MODEL_REVISION = '65727574dfcd264acbb0c3e07860e4e9e9b22185'
MODELS = {
    'eng': (4113088, '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'),
    'chi_tra': (2366642, '529c5b5797d64b126065cd55f2bb4c7fd7b15790798091b1ff259941a829330b'),
    'chi_sim': (2469156, 'a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730'),
}


def model_home() -> Path:
    return Path(os.environ.get('EBOOK2MP4_OCR_HOME') or
                str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ebook2mp4' / 'ocr' / MODEL_REVISION))


def executable() -> Path:
    bundle = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return Path(os.environ.get('EBOOK2MP4_TESSERACT') or str(bundle / 'tools' / 'tesseract' / 'tesseract.exe'))


def valid_model(path: Path, code: str) -> bool:
    size, sha = MODELS[code]
    try:
        return path.stat().st_size == size and hashlib.sha256(path.read_bytes()).hexdigest() == sha
    except OSError:
        return False


def model_info(language: str) -> dict:
    if language not in LANGUAGES:
        raise ProjectError('請選擇繁中＋英文、簡中＋英文或英文 OCR。')
    codes = LANGUAGES[language]
    missing = [c for c in codes.split('+') if not valid_model(model_home() / f'{c}.traineddata', c)]
    error = '' if executable().is_file() else '缺少 OCR 引擎，請重新安裝完整程式；仍可使用文字層與 TXT。'
    return dict(language=language, codes=codes, missing=missing,
                download_bytes=sum(MODELS[c][0] for c in missing),
                engine_error=error, ready=not missing and not error)


class ModelInstall:
    """One cancellable download; each verified model is published atomically."""
    def __init__(self, language: str):
        info = model_info(language)
        self.home = model_home()
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._state = dict(status='running', downloaded=0, total=info['download_bytes'],
                           phase='準備下載', error='')
        self._missing = info['missing']
        self._thread = threading.Thread(target=self._run, name='OCR model install', daemon=False)
        self._thread.start()

    @property
    def state(self):
        with self._lock:
            return self._state.copy()

    def _update(self, **changes):
        with self._lock:
            self._state.update(changes)

    def cancel(self):
        self._cancel.set()

    def wait(self, timeout: float | None = None):
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self):
        acquired = False
        lock = self.home / '.install.lock'
        try:
            self.home.mkdir(parents=True, exist_ok=True)
            try:
                with lock.open('x'):
                    acquired = True
            except FileExistsError:
                raise ProjectError('另一個模型安裝正在執行；請等待後重試。若程式曾中斷，關閉所有視窗後移除模型目錄的 .install.lock。') from None
            downloaded = 0
            for code in self._missing:
                if self._cancel.is_set():
                    break
                self._update(phase=f'下載 {code}')
                url = f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{MODEL_REVISION}/{code}.traineddata'
                with tempfile.TemporaryDirectory(prefix='.download-', dir=self.home) as directory:
                    target = Path(directory) / f'{code}.traineddata'
                    size = 0
                    with urllib.request.urlopen(url, timeout=15) as response, target.open('wb') as output:
                        while not self._cancel.is_set():
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > MODELS[code][0]:
                                raise ProjectError('模型下載大小不符，請重試或檢查網路。')
                            output.write(chunk)
                            downloaded += len(chunk)
                            self._update(downloaded=downloaded)
                        output.flush()
                        os.fsync(output.fileno())
                    if self._cancel.is_set():
                        break
                    self._update(phase=f'驗證並安裝 {code}')
                    if not valid_model(target, code):
                        raise ProjectError('模型下載不完整或 SHA-256 不符，請重試或檢查網路。')
                    os.replace(target, self.home / target.name)
            self._update(status='cancelled' if self._cancel.is_set() else 'completed',
                         phase='已取消；完整安裝的模型保留' if self._cancel.is_set() else '安裝完成')
        except ProjectError as error:
            self._update(status='failed', error=str(error))
        except Exception:
            self._update(status='cancelled' if self._cancel.is_set() else 'failed',
                         error='下載／安裝失敗，請檢查網路、磁碟空間與模型目錄寫入權限後重試。')
        finally:
            if acquired:
                lock.unlink(missing_ok=True)


class OcrCancelled(Exception):
    """The current page is incomplete and must not be published as success."""


def recognize(image: bytes, language: str, cancelled: threading.Event) -> str:
    return recognize_page(image, language, cancelled)['text']


def _execute(image: bytes, codes: str, cancelled: threading.Event, *, psm: int, tsv: bool, deadline: float) -> str:
    with tempfile.TemporaryDirectory(prefix='ebook2mp4-ocr-') as directory:
        source = Path(directory) / 'page.png'
        source.write_bytes(image)
        command = [str(executable()), str(source), 'stdout', '--tessdata-dir', str(model_home()),
                   '-l', codes, '--oem', '1', '--psm', str(psm), '--dpi', '300'] + (['-c', 'tessedit_create_tsv=1'] if tsv else [])
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError:
            raise ProjectError('OCR 引擎無法啟動，請重新安裝完整程式；TXT 仍可使用。') from None
        try:
            while True:
                if cancelled.is_set():
                    raise OcrCancelled()
                if time.monotonic() > deadline:
                    raise ProjectError('此頁 OCR 超過 120 秒，請縮小範圍重試或人工校對。')
                try:
                    output, _ = process.communicate(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if cancelled.is_set():
                raise OcrCancelled()
            if process.returncode:
                raise ProjectError('此頁 OCR 失敗，請檢查模型、原頁或重新安裝完整程式後重試。')
            try:
                return output.decode('utf-8').strip()
            except UnicodeError:
                raise ProjectError('OCR 輸出編碼異常，請重試或人工校對。') from None
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()


def suspicious_lines(text: str) -> list[str]:
    han = sum('\u3400' <= c <= '\u9fff' for c in text)
    if han < 8:
        return []
    return [line.strip() for line in text.splitlines() if re.fullmatch(
        r'\s*(?:\d+[.、]\s*)?(?:[A-Za-z]{1,4}\s+){1,}[A-Za-z]{1,4}[.!?]?\s*', line)]


def _table_result(table: str, *, region=None, size=None) -> dict:
    lines: dict[tuple[str, ...], dict] = {}
    weight = confidence = 0.0
    for row in csv.DictReader(StringIO(table), delimiter='\t', quoting=csv.QUOTE_NONE):
        if row.get('level') != '5' or not row.get('text', '').strip():
            continue
        if region is not None:
            center_x = (int(row['left'])+int(row['width'])/2)/size[0]
            center_y = (int(row['top'])+int(row['height'])/2)/size[1]
            if not region[0] <= center_x <= region[2] or not region[1] <= center_y <= region[3]:
                continue
        token = row['text'].strip()
        key = tuple(row[k] for k in ('block_num', 'par_num', 'line_num'))
        token_weight = min(len(token), 32)
        left, top, width, height = (int(row[k]) for k in ('left', 'top', 'width', 'height'))
        line = lines.setdefault(key, dict(words=[], weight=0, total=0, box=[left, top, left+width, top+height]))
        line['words'].append(token)
        line['weight'] += token_weight
        line['total'] += max(0, float(row['conf'])) * token_weight
        box = line['box']
        line['box'] = [min(box[0], left), min(box[1], top), max(box[2], left+width), max(box[3], top+height)]
        weight += token_weight
        confidence += max(0, float(row['conf'])) * token_weight
    details = [dict(text=' '.join(line['words']), confidence=line['total']/line['weight'], box=line['box'])
               for line in lines.values()]
    text = '\n'.join(line['text'] for line in details)
    suspicious = suspicious_lines(text)
    mean = confidence / weight if weight else 0
    return dict(text=text, confidence=round(mean, 2), suspicious_lines=suspicious,
                score=mean - min(20, len(suspicious)*5), lines=details)


def _combine_layouts(best: dict, choices: list[dict]) -> None:
    """Use alternate layout only for a matching, substantially more confident line."""
    count = 0
    for line in best['lines']:
        if line['confidence'] >= 85:
            continue
        x0, y0, x1, y1 = line['box']
        alternatives = []
        for candidate in choices:
            if candidate is best or candidate['selected_language'] != best['selected_language']:
                continue
            for other in candidate['lines']:
                a, b, c, d = other['box']
                if (min(y1, d)-max(y0, b) >= .65*max(y1-y0, d-b)
                        and min(x1, c)-max(x0, a) >= .65*max(x1-x0, c-a)
                        and other['confidence'] >= line['confidence']+10):
                    alternatives.append(other)
        if alternatives:
            selected = max(alternatives, key=lambda item: item['confidence'])
            line.update(selected)
            count += 1
    best['text'] = '\n'.join(line['text'] for line in best['lines'])
    weights = sum(len(line['text']) for line in best['lines'])
    best['confidence'] = round(sum(line['confidence']*len(line['text']) for line in best['lines'])/weights, 2) if weights else 0
    best['suspicious_lines'] = suspicious_lines(best['text'])
    best['layout_fallbacks'] = count


def recognize_page(image: bytes, language: str, cancelled: threading.Event, *, layout='block', region=None) -> dict:
    psm = {'block': 6, 'auto': 3, 'line': 7}[layout]
    full_image, size = image, None
    if region is not None:
        from PIL import Image, ImageOps
        with Image.open(BytesIO(image)) as original:
            size = original.size
            x0, y0, x1, y1 = region
            bounds = (int(x0*original.width), int(y0*original.height), int(x1*original.width), int(y1*original.height))
            with original.crop(bounds) as crop, ImageOps.expand(crop, border=20, fill='white') as padded, BytesIO() as output:
                padded.save(output, format='PNG')
                image = output.getvalue()
    deadline = time.monotonic() + 120
    if language != '自動中英' and layout == 'block' and region is None:
        text = _execute(image, LANGUAGES[language], cancelled, psm=psm, tsv=False, deadline=deadline)
        return dict(text=text, selected_language=LANGUAGES[language], psm=psm,
                    suspicious_lines=suspicious_lines(text))
    languages = ['chi_sim+eng', 'chi_tra+eng'] if language == '自動中英' else [LANGUAGES[language]]
    choices = []
    for codes in languages:
        if cancelled.is_set():
            raise OcrCancelled()
        candidate = _table_result(_execute(image, codes, cancelled, psm=psm, tsv=True, deadline=deadline))
        candidate.update(selected_language=codes, psm=psm, selected_source='crop' if region else 'page')
        choices.append(candidate)
        if layout == 'auto' and region is None:
            block = _table_result(_execute(full_image, codes, cancelled, psm=6, tsv=True, deadline=deadline))
            block.update(selected_language=codes, psm=6, selected_source='page')
            choices.append(block)
        if region is not None:
            for context_psm in (3, 6):
                contextual = _table_result(_execute(full_image, codes, cancelled, psm=context_psm, tsv=True, deadline=deadline),
                                           region=region, size=size)
                contextual.update(selected_language=codes, psm=context_psm, selected_source='page-context')
                choices.append(contextual)
    best = max(choices, key=lambda item: item['score'])
    if cancelled.is_set():
        raise OcrCancelled()
    if layout == 'auto' and region is None:
        _combine_layouts(best, choices)
    best['alternatives'] = [dict(language=c['selected_language'], source=c['selected_source'], confidence=c['confidence']) for c in choices]
    best.pop('score')
    best.pop('lines')
    return best
