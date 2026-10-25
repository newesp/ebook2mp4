"""Local PDFium adapter. Native calls are serialized; handles never escape a call."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import threading
import unicodedata
from copy import deepcopy
from contextlib import closing

from .workflow import ProjectError


_native_lock = threading.Lock()


def engine():
    try:
        import pypdfium2  # type: ignore[import-untyped]
        return pypdfium2
    except ImportError:
        raise ProjectError('缺少 PDF 元件，請重新安裝完整程式；仍可使用 TXT。') from None


def open_document(data: bytes):
    pdfium = engine()
    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as error:
        reason = '文件受密碼保護，不提供解密' if error.err_code == 4 else 'PDF 損毀或格式無法讀取'
        raise ProjectError(reason + '。請更換 PDF 來源。') from None
    return document


@dataclass(frozen=True)
class PdfPreview:
    path: Path
    data: bytes
    page_count: int

    @property
    def size(self):
        return len(self.data)


def inspect(filename: str | Path) -> PdfPreview:
    path = Path(filename).resolve()
    if path.suffix.lower() != '.pdf':
        raise ProjectError('請選擇 PDF 來源。')
    try:
        data = path.read_bytes()
    except OSError:
        raise ProjectError('PDF 不可讀，請檢查讀取權限或更換來源。') from None
    with _native_lock, closing(open_document(data)) as doc:
        count = len(doc)
        if count < 1:
            raise ProjectError('PDF 沒有頁面，請更換來源。')
    return PdfPreview(path, data, count)


def validate_range(start, end, count):
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= count:
        raise ProjectError(f'頁碼必須為整數，且 1 ≤ 起始頁 ≤ 結束頁 ≤ {count}。')


def render(data: bytes, number: int, count: int, *, ocr: bool = False) -> bytes:
    validate_range(number, number, count)
    with _native_lock, closing(open_document(data)) as doc, closing(doc[number - 1]) as page:
        width, height = page.get_size()
        # Bound dimensions and memory even for unusually large page boxes.
        scale = (min(300 / 72, (25_000_000 / max(width * height, 1)) ** .5) if ocr else
                 min(900 / max(width, 1), 1100 / max(height, 1), 2))
        try:
            with closing(page.render(scale=scale)) as bitmap:
                with bitmap.to_pil() as image, BytesIO() as output:
                    image.save(output, format='PNG')
                    return output.getvalue()
        except Exception:
            raise ProjectError('此頁無法產生預覽，請更換來源或檢查 PDF。') from None


class PdfExtraction:
    """A cancellable candidate; only the workflow publishes it as a new batch."""
    def __init__(self, preview: PdfPreview, start: int, end: int, *, mode='text-layer', language='繁中＋英文'):
        validate_range(start, end, preview.page_count)
        if mode not in ('text-layer', 'ocr'):
            raise ProjectError('請選擇文字層或全部強制 OCR。')
        self.mode, self.language = mode, language
        self.settings: dict = dict(line_breaks='original')
        if mode == 'ocr':
            from .ocr import model_info, MODEL_REVISION
            info = model_info(language)
            if not info['ready']:
                raise ProjectError(info['engine_error'] or '缺少或損壞 OCR 語言模型，請先從介面下載／安裝。')
            self.settings.update(language=info['codes'], model_revision=MODEL_REVISION,
                                 engine='Tesseract 5 LSTM', dpi=300, max_pixels=25_000_000, psm=6)
        self.preview, self.start, self.end = preview, start, end
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._pages: list[dict] = []
        self._status = 'running'
        self._thread = threading.Thread(target=self._run, name='PDF extraction', daemon=False)
        self._thread.start()

    @property
    def status(self):
        with self._lock:
            return self._status

    @property
    def pages(self):
        with self._lock:
            return deepcopy(self._pages)

    def cancel(self):
        self._cancel.set()
        with self._lock:
            if self._status == 'running':
                self._status = 'cancelling'

    def wait(self, timeout: float | None = None):
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self):
        for number in range(self.start, self.end + 1):
            if self._cancel.is_set():
                break
            result = dict(number=number, method=self.mode, text='', status='failed', error='',
                          settings=self.settings.copy())
            try:
                if self.mode == 'ocr':
                    from .ocr import recognize, OcrCancelled
                    try:
                        text = recognize(render(self.preview.data, number, self.preview.page_count, ocr=True),
                                         self.language, self._cancel)
                    except OcrCancelled:
                        break
                    result['text'] = text
                    result['status'] = 'success' if any(c.isalnum() for c in text) else 'pending'
                    if result['status'] == 'pending':
                        result['error'] = '空白／無可用 OCR 文字，請對照原頁後處理或明確略過。'
                    with self._lock:
                        self._pages.append(result)
                    continue
                with _native_lock, closing(open_document(self.preview.data)) as doc, closing(doc[number - 1]) as page:
                    with closing(page.get_textpage()) as textpage:
                        text = textpage.get_text_bounded(errors='strict')
                    result['text'] = text
                    usable = sum(c.isalnum() for c in text)
                    result['status'] = 'success' if usable >= 20 else 'pending'
                    if usable < 20:
                        result['error'] = '無可用文字或文字稀少，正文可能為圖片；請對照頁圖，必要時使用後續 OCR。'
                    elif '\ufffd' in text or any(unicodedata.category(c) == 'Cc' and c not in '\t\r\n' for c in text):
                        result['status'] = 'pending'
                        result['error'] = '文字層含替代符號或異常控制字元，請對照頁圖檢查。'
            except Exception as error:
                result['error'] = (str(error) if isinstance(error, ProjectError) else
                                   'OCR 辨識失敗，請檢查原頁或模型後重試。' if self.mode == 'ocr' else
                                   '文字層擷取失敗，請檢查頁圖或更換來源。')
            with self._lock:
                self._pages.append(result)
        with self._lock:
            self._status = 'cancelled' if self._cancel.is_set() else 'completed'
