"""The project workflow shared by the desktop UI and behavioral tests.

Immutable content files are committed by atomically replacing project.json last.
An interrupted write may leave an unreferenced file, never a half-saved project.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unicodedata
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pdf import PdfPreview, PdfExtraction
    from .gemini import ReviewJob
    from .voice import VoiceJob
    from .narration import NarrationJob


class ProjectError(Exception):
    """An actionable error safe to display without manuscript content."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')


def text_encoding(data: bytes, selection: str) -> str:
    if selection in ('auto', 'UTF-8', 'UTF-8 BOM'):
        if data.startswith(b'\xef\xbb\xbf'):
            return 'UTF-8 BOM'
        if selection == 'auto' and data.startswith((b'\xff\xfe', b'\xfe\xff')):
            return 'UTF-16 BOM'
        return 'UTF-8'
    if selection not in ('UTF-16 BOM', 'Big5', 'CP950'):
        raise ProjectError('不支援的文字編碼，請從清單重新選擇。')
    return selection


def decode_txt(data: bytes, encoding: str = 'auto') -> str:
    encoding = text_encoding(data, encoding)
    if encoding == 'UTF-16 BOM' and not data.startswith((b'\xff\xfe', b'\xfe\xff')):
        raise ProjectError('UTF-16 來源缺少 BOM。請選擇正確編碼或另存含 BOM 的 UTF-16。')
    try:
        text = data.decode({'UTF-8': 'utf-8', 'UTF-8 BOM': 'utf-8-sig',
                            'UTF-16 BOM': 'utf-16', 'Big5': 'big5', 'CP950': 'cp950'}[encoding])
    except UnicodeError:
        raise ProjectError(f'無法以 {encoding} 讀取。請切換編碼重新預覽，或將來源另存為 UTF-8 TXT。') from None
    if '\x00' in text:
        raise ProjectError('來源含有 NUL 字元，可能選錯編碼。請切換編碼重新預覽。')
    return text


@dataclass(frozen=True)
class ImportPreview:
    path: Path
    data: bytes
    text: str
    sha256: str
    encoding: str
    warnings: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return len(self.data)


class ProjectWorkflow:
    """Public create → inspect → import → edit → save → reopen operations."""

    def __init__(self, root: Path, manifest: dict, committed: str):
        self.root = root
        self._manifest = manifest
        self._committed = committed
        self._pdf_job: PdfExtraction | None = None
        self._gemini_job: ReviewJob | None = None
        self._voice_job: VoiceJob | None = None
        self._narration_job: NarrationJob | None = None

    @property
    def state(self) -> dict:
        return deepcopy(self._manifest)

    @staticmethod
    def _space(root: Path, required: int):
        if shutil.disk_usage(root).free < required + 65536:
            raise ProjectError(f'磁碟空間不足，至少需要 {required + 65536:,} 位元組。請釋放空間後重試。')

    @staticmethod
    def _atomic(path: Path, data: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.writing-', delete=False) as f:
                temp = Path(f.name)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    @classmethod
    def create(cls, folder: str | Path, name: str) -> ProjectWorkflow:
        root = Path(folder).resolve()
        if not name.strip():
            raise ProjectError('請輸入書籍名稱。')
        try:
            if root.exists() and (not root.is_dir() or any(root.iterdir())):
                raise ProjectError('請選擇空資料夾，或指定新的專案資料夾，避免覆寫既有資料。')
            root.mkdir(parents=True, exist_ok=True)
            cls._space(root, 4096)
            manifest = dict(format_version=1, id=uuid.uuid4().hex, name=name.strip(),
                            created_at=now(), updated_at=now(), batches=[])
            data = encode(manifest)
            cls._atomic(root / 'project.json', data)
            return cls(root, manifest, digest(data))
        except OSError:
            raise ProjectError('無法建立專案。請檢查資料夾寫入權限與磁碟空間，或選擇其他位置。') from None

    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(self.root) or path == self.root:
            raise ProjectError('專案包含不安全的檔案路徑，請還原可信任的專案備份。')
        return path

    def _read(self, ref: dict) -> bytes:
        path = self._path(ref['path'])
        try:
            data = path.read_bytes()
        except OSError:
            raise ProjectError(f'無法讀取專案檔案：{ref["path"]}。請還原檔案並重新開啟。') from None
        if digest(data) != ref['sha256']:
            raise ProjectError(f'專案檔案內容已變更：{ref["path"]}。請還原備份，避免覆寫原有校對資料。')
        return data

    @classmethod
    def open(cls, folder: str | Path) -> ProjectWorkflow:
        root = Path(folder).resolve()
        if root.is_file():
            root = root.parent
        try:
            data = (root / 'project.json').read_bytes()
            manifest = json.loads(data)
            if type(manifest.get('format_version')) is not int or manifest['format_version'] != 1:
                raise ProjectError('不支援此專案格式版本。請使用相容版本的程式開啟。')
            if not all(isinstance(manifest[k], str) for k in ('id', 'name', 'created_at', 'updated_at')):
                raise ValueError()
            if not isinstance(manifest['batches'], list):
                raise ValueError()
            flow = cls(root, manifest, digest(data))
            seen = set()
            for batch in manifest['batches']:
                if not isinstance(batch['id'], str) or not batch['id']:
                    raise ValueError()
                if batch['id'] in seen or batch['kind'] not in ('txt', 'pdf') or not isinstance(batch['name'], str):
                    raise ValueError()
                seen.add(batch['id'])
                if type(batch['revision']) is not int or batch['revision'] < 1:
                    raise ValueError()
                source = flow._read(batch['source'])
                if len(source) != batch['source']['size']:
                    raise ValueError()
                if batch['kind'] == 'txt':
                    decode_txt(source, batch['source']['encoding'])
                else:
                    flow.pdf_pages(batch['id'])
                flow._read(batch['draft']).decode('utf-8')
                flow.gemini_reviews(batch['id'])
                readings = batch.get('readings', [])
                copies = batch.get('draft_copies', [])
                issues = batch.get('source_issues', [])
                if not all(isinstance(items, list) for items in (readings, copies, issues)):
                    raise ValueError()
                ids = set()
                for ref in readings + copies:
                    if not isinstance(ref['id'], str) or not ref['id'] or ref['id'] in ids:
                        raise ValueError()
                    ids.add(ref['id'])
                    flow._read(ref).decode('utf-8')
                for ref in readings:
                    if type(ref['revision']) is not int or not 1 <= ref['revision'] <= batch['revision']:
                        raise ValueError()
                    if not isinstance(ref['confirmed_at'], str):
                        raise ValueError()
                if any(not isinstance(ref['created_at'], str) for ref in copies):
                    raise ValueError()
                for issue in issues:
                    if not isinstance(issue['reason'], str) or not issue['reason'].strip():
                        raise ValueError()
                    if issue['status'] not in ('pending', 'resolved', 'skipped'):
                        raise ValueError()
                current = batch.get('current_reading')
                if current is not None:
                    snapshot = next((s for s in readings if s['id'] == current), None)
                    if (snapshot is None or snapshot['revision'] != batch['revision']
                            or snapshot['sha256'] != batch['draft']['sha256']
                            or flow.confirmation_blockers(batch['id'])):
                        raise ValueError()
            return flow
        except ProjectError:
            raise
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise ProjectError('無法開啟專案：索引遺失、損壞或欄位不完整。請選擇含 project.json 的資料夾或還原備份。') from None

    @staticmethod
    def inspect_txt(filename: str | Path, encoding: str = 'auto') -> ImportPreview:
        path = Path(filename).resolve()
        if path.suffix.lower() != '.txt':
            raise ProjectError('目前僅支援 TXT。PDF 擷取與 OCR 將於 T04／T05 提供。')
        try:
            data = path.read_bytes()
        except OSError:
            raise ProjectError('無法讀取來源檔。請檢查檔案是否存在及讀取權限，再重新選擇。') from None
        selected = text_encoding(data, encoding)
        text = decode_txt(data, selected)
        warnings: tuple[str, ...] = ()
        if '\ufffd' in text or any(unicodedata.category(c) == 'Cc' and c not in '\t\r\n' for c in text):
            warnings = ('文字含替代符號或異常控制字元，可能為亂碼；請換編碼，或確認原文確實如此。',)
        return ImportPreview(path, data, text, digest(data), selected, warnings)

    def import_requirements(self, preview: ImportPreview) -> dict:
        required = preview.size + len(preview.text.encode('utf-8')) + len(encode(self._manifest)) + 8192
        return dict(project_location=str(self.root), source_copy_bytes=preview.size,
                    required_bytes=required, free_bytes=shutil.disk_usage(self.root).free)

    def _check_current(self):
        if digest((self.root / 'project.json').read_bytes()) != self._committed:
            raise ProjectError('專案已由另一個視窗變更。請保留目前編輯內容，再重新開啟專案。')

    def _commit(self, manifest: dict, files: list[tuple[str, bytes]]):
        """Single-writer commit. Content paths are unique to this attempt."""
        old_ids = {b['id'] for b in self._manifest['batches']}
        for batch in manifest['batches']:
            if batch['id'] not in old_ids:
                batch['voice_settings'] = self.voice_settings()
        lock = None
        try:
            lock = os.open(self.root / '.write.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            self._check_current()
            manifest['updated_at'] = now()
            data = encode(manifest)
            self._space(self.root, sum(len(b) for _, b in files) + len(data))
            # Probe write access before touching any content. No manuscript is logged.
            with tempfile.TemporaryFile(dir=self.root):
                pass
            for relative, content in files:
                self._atomic(self._path(relative), content)
            self._atomic(self.root / 'project.json', data)
            self._manifest = manifest
            self._committed = digest(data)
        except FileExistsError:
            raise ProjectError('專案正被寫入，請稍後重試。若程式曾中斷，關閉所有視窗後移除專案內 .write.lock 再重開。') from None
        except OSError:
            raise ProjectError('儲存失敗，前次成功資料仍保留。請檢查寫入權限與磁碟空間，保留目前編輯並重試。') from None
        finally:
            if lock is not None:
                os.close(lock)
                (self.root / '.write.lock').unlink(missing_ok=True)

    def import_txt(self, preview: ImportPreview, *, accept_warnings: bool = False) -> str:
        if preview.warnings and not accept_warnings:
            raise ProjectError('文字疑似亂碼，請更換編碼，或核對並明確確認原文後再匯入。')
        # Import the exact bytes the user reviewed, even if the external file changes.
        batch_id = uuid.uuid4().hex
        source_path = f'sources/{batch_id}.txt'
        draft_path = f'batches/{batch_id}/draft-{uuid.uuid4().hex}.txt'
        draft = preview.text.encode('utf-8')
        manifest = self.state
        manifest['batches'].append(dict(
            id=batch_id, kind='txt', name=preview.path.stem, revision=1,
            source=dict(path=source_path, original_name=preview.path.name,
                        size=preview.size, encoding=preview.encoding, sha256=preview.sha256),
            draft=dict(path=draft_path, sha256=digest(draft))))
        self._commit(manifest, [(source_path, preview.data), (draft_path, draft)])
        return batch_id

    def rename_batch(self, batch_id: str, name: str) -> None:
        self._batch(batch_id)
        if not name.strip():
            raise ProjectError('請輸入製作批次名稱。')
        manifest = self.state
        next(b for b in manifest['batches'] if b['id'] == batch_id)['name'] = name.strip()
        self._commit(manifest, [])

    def reorder_batches(self, batch_ids: list[str]) -> None:
        current = {b['id']: b for b in self._manifest['batches']}
        if len(batch_ids) != len(current) or set(batch_ids) != set(current):
            raise ProjectError('排序必須包含每個製作批次各一次，請重新選擇。')
        manifest = self.state
        manifest['batches'] = [deepcopy(current[batch_id]) for batch_id in batch_ids]
        self._commit(manifest, [])

    def remove_pdf_batch(self, batch_id: str) -> None:
        """Detach one PDF batch atomically; retain immutable files as project history."""
        if self._batch(batch_id)['kind'] != 'pdf':
            raise ProjectError('請選擇要移除的 PDF 文件批次。')
        manifest = self.state
        manifest['batches'] = [b for b in manifest['batches'] if b['id'] != batch_id]
        self._commit(manifest, [])

    def texts(self, batch_id: str) -> tuple[str, str]:
        batch = self._batch(batch_id)
        original = ('\n\n'.join(p['text'] for p in self.pdf_pages(batch_id)) if batch['kind'] == 'pdf'
                    else decode_txt(self._read(batch['source']), batch['source']['encoding']))
        return (original,
                self._read(batch['draft']).decode('utf-8'))

    @staticmethod
    def inspect_pdf(filename: str | Path) -> PdfPreview:
        from .pdf import inspect
        return inspect(filename)

    @staticmethod
    def preview_pdf_page(preview: PdfPreview, number: int) -> bytes:
        from .pdf import render
        return render(preview.data, number, preview.page_count)

    @staticmethod
    def ocr_models(language: str) -> dict:
        from .ocr import model_info
        return model_info(language)

    @staticmethod
    def start_ocr_model_install(language: str):
        from .ocr import ModelInstall
        return ModelInstall(language)

    def start_pdf_extraction(self, preview: PdfPreview, start: int, end: int, *,
                             mode: str = 'text-layer', language: str = '繁中＋英文', layout: str = 'block') -> PdfExtraction:
        from .pdf import PdfExtraction
        if self._pdf_job is not None:
            raise ProjectError('已有 PDF 擷取待完成或保存，請先完成或取消。')
        self._check_current()
        self._space(self.root, preview.size + 8192)
        self._pdf_job = PdfExtraction(preview, start, end, mode=mode, language=language, layout=layout)
        return self._pdf_job

    def start_pdf_retry(self, batch_id: str, *, pages: list[int] | None = None,
                        failed_only: bool = False, language: str = '繁中＋英文',
                        rotation: int = 0, layout: str = 'block',
                        region: tuple[float, float, float, float] | None = None,
                        text_range: tuple[int, int] | None = None) -> PdfExtraction:
        """Retry selected physical pages into a candidate; never mutate the source batch."""
        from .pdf import PdfExtraction, PdfPreview
        if self._pdf_job is not None:
            raise ProjectError('已有 PDF 擷取待完成或保存，請先完成或取消。')
        self._check_current()
        original = self.pdf_pages(batch_id)
        batch = self._batch(batch_id)
        if failed_only and pages is not None:
            raise ProjectError('請選擇指定頁或只重試失敗頁其中一種。')
        numbers = ([p['number'] for p in original if p['status'] == 'failed'] if failed_only else pages)
        if numbers is None:
            raise ProjectError('請指定要強制 OCR 的頁次，或選擇只重試失敗頁。')
        data = self._read(batch['source'])
        self._space(self.root, len(data) + 8192)
        preview = PdfPreview(Path(batch['source']['original_name']), data, batch['pdf']['page_count'])
        issues = deepcopy(batch.get('source_issues', []))
        if not batch['pdf']['mapping_valid']:
            # Resolutions may depend on corrections absent from the raw-page new draft.
            for issue in issues:
                if issue['status'] == 'resolved':
                    issue['status'] = 'pending'
        self._pdf_job = PdfExtraction(preview, batch['pdf']['start'], batch['pdf']['end'],
                                      mode='ocr', language=language, numbers=numbers, rotation=rotation,
                                      base_pages=original, base_issues=issues,
                                      source_batch=batch_id, layout=layout, region=region, text_range=text_range,
                                      publication_baseline=original, source_fingerprint=self._pdf_source_fingerprint(batch_id))
        return self._pdf_job

    def _pdf_source_fingerprint(self, batch_id: str) -> dict:
        batch = self._batch(batch_id)
        if batch['kind'] != 'pdf':
            raise ProjectError('請選擇 PDF 來源批次。')
        return dict(source=batch['source']['sha256'], extracted=batch['pdf']['extracted']['sha256'],
                    start=batch['pdf']['start'], end=batch['pdf']['end'], count=batch['pdf']['page_count'])

    def _check_pdf_source(self, job: PdfExtraction) -> None:
        self._check_current()
        if job.source_batch is not None:
            if job.source_fingerprint != self._pdf_source_fingerprint(job.source_batch):
                raise ProjectError('原 PDF 批次的來源或逐頁原稿已變更；候選仍可檢視，請重新開啟原批次後重辨。')
            # Draft saves and reading snapshots do not change the immutable page baseline.
            self._read(self._batch(job.source_batch)['source'])
            self.pdf_pages(job.source_batch)

    @staticmethod
    def _pdf_accepted_pages(job: PdfExtraction, accepted_pages: list[int] | None) -> set[int]:
        selection = job.candidate_numbers if accepted_pages is None else accepted_pages
        if any(type(n) is not int for n in selection):
            raise ProjectError('只能採用此候選已辨識的有效頁次。')
        accepted = set(selection)
        if not accepted <= set(job.candidate_numbers):
            raise ProjectError('只能採用此候選已辨識的有效頁次。')
        return accepted

    def start_pdf_candidate_retry(self, base_job: PdfExtraction, *, pages: list[int],
                                  accepted_pages: list[int] | None = None,
                                  language: str = '繁中＋英文', rotation: int = 0, layout: str = 'block',
                                  region: tuple[float, float, float, float] | None = None,
                                  text_range: tuple[int, int] | None = None) -> PdfExtraction:
        """Freeze current page choices, then refine the unpublished candidate in place.

        Text offsets address the effective working pages after those choices. A successful
        construction retires base_job. Rejected regions return to their operation input,
        while whole-page choices retain the original publication baseline.
        """
        from .pdf import PdfExtraction
        current = self.pdf_extraction_pages(base_job)  # Checks ownership and terminated worker.
        self._check_pdf_source(base_job)
        accepted = self._pdf_accepted_pages(base_job, accepted_pages)
        if (not pages or any(type(n) is not int or not base_job.start <= n <= base_job.end for n in pages)
                or list(sorted(set(pages))) != list(pages)):
            raise ProjectError('請選擇候選範圍內不重複的有效頁次。')
        baseline = base_job.decision_baseline if base_job.decision_baseline is not None else current
        originals = {p['number']: p for p in baseline}
        working = [p if p['number'] in accepted else originals[p['number']] for p in current]
        self._space(self.root, base_job.preview.size + 8192)
        # PdfExtraction validates and checks OCR availability before starting its worker.
        # Leave the active candidate untouched if any of those steps fails.
        job = PdfExtraction(base_job.preview, base_job.start, base_job.end,
                            mode='ocr', language=language, numbers=pages, rotation=rotation,
                            base_pages=working, base_issues=base_job.base_issues,
                            source_batch=base_job.source_batch, layout=layout, region=region, text_range=text_range,
                            publication_baseline=(base_job.publication_baseline if base_job.publication_baseline is not None else baseline),
                            candidate_numbers=tuple(sorted(set(base_job.candidate_numbers) | set(pages))),
                            source_fingerprint=base_job.source_fingerprint, preserve_on_failure=True)
        self._pdf_job = job
        return job

    def pdf_source_preview(self, batch_id: str) -> PdfPreview:
        """Verified project source, usable even after the external PDF has moved."""
        from .pdf import PdfPreview
        self.pdf_pages(batch_id)
        batch = self._batch(batch_id)
        return PdfPreview(Path(batch['source']['original_name']), self._read(batch['source']), batch['pdf']['page_count'])

    def pdf_extraction_pages(self, job: PdfExtraction) -> list[dict]:
        """Completed candidate pages, including explicit placeholders for incomplete pages."""
        if job is not self._pdf_job or not job.wait(0):
            raise ProjectError('PDF 擷取仍在執行或不屬於此專案，請等待取消／完成。')
        completed = {p['number']: p for p in job.pages}
        pages = {p['number']: p for p in job.base_pages or []}
        for number in job.numbers:
            pages[number] = completed.get(number, dict(number=number,
                method='ocr' if job.mode == 'ocr' else 'text-layer',
                text=pages.get(number, {}).get('text', '') if job.region is not None or job.preserve_on_failure else '', status='cancelled',
                error='擷取已取消，此頁尚未處理完成。', settings=job.settings.copy()))
        return deepcopy([pages[n] for n in range(job.start, job.end + 1)])

    def finish_pdf_extraction(self, job: PdfExtraction, *, accepted_pages: list[int] | None = None) -> str:
        pages = self.pdf_extraction_pages(job)
        self._check_pdf_source(job)
        accepted = self._pdf_accepted_pages(job, accepted_pages)
        baseline_pages = job.decision_baseline
        if accepted_pages is not None and baseline_pages is None:
            raise ProjectError('只能採用本次重試的有效頁次。')
        if baseline_pages is not None:
            baseline = {p['number']: p for p in baseline_pages}
            pages = [p if p['number'] in accepted else baseline[p['number']] for p in pages]
        original_pages = {p['number']: p for p in (job.publication_baseline or job.base_pages or [])}
        issues = []
        for page in pages:
            if page['status'] != 'success':
                previous = next((i for i in job.base_issues if i.get('page') == page['number']), None)
                issues.append(deepcopy(previous) if previous and page['number'] not in accepted
                              and page == original_pages.get(page['number']) else
                              dict(page=page['number'], reason=f'PDF 第 {page["number"]} 頁：{page["error"]}', status='pending'))
        # Batch-wide issues cannot be silently cleared by a page retry.
        issues.extend(deepcopy(i) for i in job.base_issues if 'page' not in i)
        batch_id = uuid.uuid4().hex
        source_path = f'sources/{batch_id}.pdf'
        pages_path = f'batches/{batch_id}/extracted.json'
        draft_path = f'batches/{batch_id}/draft-{uuid.uuid4().hex}.txt'
        draft = '\n\n'.join(p['text'] for p in pages).encode('utf-8')
        extracted = encode(dict(pages=pages))
        batch = dict(id=batch_id, kind='pdf', name=f'{job.preview.path.stem} · {job.start}–{job.end}',
                     revision=1, source=dict(path=source_path, original_name=job.preview.path.name,
                     size=job.preview.size, sha256=digest(job.preview.data)),
                     draft=dict(path=draft_path, sha256=digest(draft)),
                     pdf=dict(start=job.start, end=job.end, page_count=job.preview.page_count,
                              extraction_status=job.status, mapping_valid=True,
                              mode=job.mode, language=job.language, source_batch=job.source_batch,
                              extracted=dict(path=pages_path, sha256=digest(extracted))),
                     source_issues=issues)
        manifest = self.state
        # Insert PDF batches in physical-page order; users can subsequently reorder.
        index = next((i for i, b in enumerate(manifest['batches'])
                      if b['kind'] == 'pdf' and b['pdf']['start'] > job.start), len(manifest['batches']))
        manifest['batches'].insert(index, batch)
        self._commit(manifest, [(source_path, job.preview.data), (pages_path, extracted), (draft_path, draft)])
        self._pdf_job = None
        return batch_id

    def discard_pdf_extraction(self, job: PdfExtraction) -> None:
        if job is not self._pdf_job:
            raise ProjectError('找不到此專案的 PDF 擷取任務。')
        job.cancel()
        if not job.wait(0):
            raise ProjectError('正在取消 PDF 擷取，請等待目前頁完成。')
        self._pdf_job = None

    def pdf_pages(self, batch_id: str) -> list[dict]:
        batch = self._batch(batch_id)
        if batch['kind'] != 'pdf':
            raise ProjectError('TXT 來源沒有 PDF 頁碼。')
        pdf = batch['pdf']
        from .pdf import validate_range
        validate_range(pdf['start'], pdf['end'], pdf['page_count'])
        pages = json.loads(self._read(pdf['extracted']))['pages']
        if (not isinstance(pages, list) or [p['number'] for p in pages] != list(range(pdf['start'], pdf['end'] + 1))
                or type(pdf['mapping_valid']) is not bool
                or pdf['extraction_status'] not in ('completed', 'cancelled')):
            raise ProjectError('PDF 逐頁記錄損壞，請還原專案備份。')
        for page in pages:
            if (page['method'] not in ('text-layer', 'ocr') or not isinstance(page['text'], str)
                    or not isinstance(page['error'], str) or not isinstance(page['settings'], dict)
                    or page['status'] not in ('success', 'pending', 'failed', 'cancelled')):
                raise ProjectError('PDF 逐頁記錄損壞，請還原專案備份。')
        return pages

    def pdf_page_image(self, batch_id: str, number: int) -> bytes:
        from .pdf import render
        batch = self._batch(batch_id)
        self.pdf_pages(batch_id)
        return render(self._read(batch['source']), number, batch['pdf']['page_count'])

    @staticmethod
    def preview_line_breaks(text: str, mode: str = 'layout') -> str:
        """Only join single layout breaks; preserve all existing characters/spaces."""
        if mode == 'original':
            return text
        if mode != 'layout':
            raise ProjectError('請選擇原始換行或版面換行整理。')
        import re
        parts = re.split(r'(\n[ \t]*\n(?:[ \t]*\n)*)', text.replace('\r\n', '\n').replace('\r', '\n'))
        return ''.join(part if index % 2 else part.replace('\n', ' ') for index, part in enumerate(parts))

    def _batch(self, batch_id: str) -> dict:
        for batch in self._manifest['batches']:
            if batch['id'] == batch_id:
                return batch
        raise ProjectError('找不到製作批次，請重新開啟專案。')

    def save_draft(self, batch_id: str, text: str):
        self._batch(batch_id)
        content = text.encode('utf-8')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        # Verify existing data before replacing its reference.
        self.texts(batch_id)
        if batch['draft']['sha256'] == digest(content):
            return
        path = f'batches/{batch_id}/draft-{uuid.uuid4().hex}.txt'
        batch['draft'] = dict(path=path, sha256=digest(content))
        batch['revision'] += 1
        batch['current_reading'] = None
        if batch['kind'] == 'pdf':
            batch['pdf']['mapping_valid'] = False
        self._commit(manifest, [(path, content)])

    def invalidate_reading(self, batch_id: str) -> None:
        """Persist cancellation even when an editor change has not been saved."""
        current = self._batch(batch_id)
        if current.get('current_reading') is None and not current.get('pdf', {}).get('mapping_valid'):
            return
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        batch['current_reading'] = None
        if batch['kind'] == 'pdf':
            batch['pdf']['mapping_valid'] = False
        self._commit(manifest, [])

    def confirmation_blockers(self, batch_id: str) -> list[str]:
        return [issue['reason'] for issue in self._batch(batch_id).get('source_issues', [])
                if issue['status'] == 'pending']

    def record_source_issues(self, batch_id: str, reasons: list[str]) -> None:
        """PDF/OCR adapters report unresolved source problems through this rule."""
        self._batch(batch_id)
        if not all(isinstance(reason, str) and reason.strip() for reason in reasons):
            raise ProjectError('每項來源異常都必須提供原因。')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        batch.setdefault('source_issues', []).extend(dict(reason=r, status='pending') for r in reasons)
        if reasons:
            batch['current_reading'] = None
        self._commit(manifest, [])

    def resolve_source_issue(self, batch_id: str, index: int, disposition: str) -> None:
        issues = self._batch(batch_id).get('source_issues', [])
        if disposition not in ('resolved', 'skipped') or not 0 <= index < len(issues):
            raise ProjectError('請選擇有效的來源異常及處理方式。')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        batch['source_issues'][index]['status'] = disposition
        self._commit(manifest, [])

    def resolve_all_source_issues(self, batch_id: str, disposition: str) -> None:
        """Apply one decision to all pending issues in a single commit."""
        self._batch(batch_id)
        if disposition not in ('resolved', 'skipped'):
            raise ProjectError('請選擇有效的來源異常處理方式。')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        for issue in batch.get('source_issues', []):
            if issue['status'] == 'pending':
                issue['status'] = disposition
        self._commit(manifest, [])

    def confirm_reading(self, batch_id: str) -> dict:
        blockers = self.confirmation_blockers(batch_id)
        if blockers:
            raise ProjectError('來源異常尚未處理，不能確認朗讀稿：\n' + '\n'.join(blockers))
        _, text = self.texts(batch_id)
        if not text.strip():
            raise ProjectError('校對稿為空，請加入內容後再確認朗讀稿。')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        snapshot_id = uuid.uuid4().hex
        content = text.encode('utf-8')
        snapshot = dict(id=snapshot_id, revision=batch['revision'], confirmed_at=now(),
                        path=f'batches/{batch_id}/reading-{snapshot_id}.txt', sha256=digest(content))
        batch.setdefault('readings', []).append(snapshot)
        batch['current_reading'] = snapshot_id
        self._commit(manifest, [(snapshot['path'], content)])
        return deepcopy(snapshot)

    def delete_reading(self, batch_id: str, snapshot_id: str) -> str:
        """Commit version removal first; never delete content on a failed index write."""
        batch = self._batch(batch_id)
        snapshot = next((s for s in batch.get('readings', []) if s['id'] == snapshot_id), None)
        if snapshot is None:
            raise ProjectError('找不到要刪除的朗讀稿版本，請重新開啟版本清單。')
        path = self._path(snapshot['path'])
        manifest = self.state
        changed = next(b for b in manifest['batches'] if b['id'] == batch_id)
        changed['readings'] = [s for s in changed['readings'] if s['id'] != snapshot_id]
        if changed.get('current_reading') == snapshot_id:
            changed['current_reading'] = None
        # A shared file must survive while any other project record still uses it.
        def referenced(value):
            if isinstance(value, dict):
                return any((key == 'path' and self._path(item) == path) or referenced(item)
                           for key, item in value.items())
            return isinstance(value, list) and any(referenced(item) for item in value)
        shared = referenced(manifest)
        self._commit(manifest, [])
        if not shared:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                return f'版本已從專案刪除，但內容檔無法移除：{snapshot["path"]}。請解除檔案占用後再手動清理。'
        return ''

    def reading_text(self, batch_id: str, snapshot_id: str | None = None) -> str:
        if snapshot_id is None:
            try:
                self._check_current()
            except OSError:
                raise ProjectError('無法檢查目前朗讀確認。請檢查專案索引後重新開啟。') from None
        batch = self._batch(batch_id)
        selected = snapshot_id if snapshot_id is not None else batch.get('current_reading')
        for snapshot in batch.get('readings', []):
            if snapshot['id'] == selected:
                return self._read(snapshot).decode('utf-8')
        raise ProjectError('此批次尚未確認目前朗讀稿，請回到校對並明確確認。')

    def export_txt(self, batch_id: str, filename: str | Path, *, text: str | None = None) -> None:
        """Export saved or explicitly supplied editor text without overwriting a file."""
        _, saved = self.texts(batch_id)
        path = Path(filename).resolve()
        if path.suffix.lower() != '.txt':
            raise ProjectError('請使用 .txt 副檔名。')
        created = False
        try:
            content = (saved if text is None else text).encode('utf-8')
            self._space(path.parent, len(content))
            # Exclusive creation protects source files and exports, including races.
            with path.open('xb') as f:
                created = True
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            created = False
        except FileExistsError:
            raise ProjectError('匯出檔案已存在。請選擇新檔名，以保留來源與既有內容。') from None
        except OSError:
            raise ProjectError('無法匯出 TXT。請檢查目標資料夾、寫入權限與磁碟空間。') from None
        finally:
            if created:
                path.unlink(missing_ok=True)

    def reload_draft(self, batch_id: str, preview: ImportPreview, *, unsaved_text: str | None = None,
                     conflict: str = 'cancel', accept_warnings: bool = False) -> str | None:
        _, saved = self.texts(batch_id)
        dirty = unsaved_text is not None and unsaved_text != saved
        if dirty and conflict not in ('keep-copy', 'replace'):
            raise ProjectError('校對稿有未存編輯，請保留副本或明確取代；目前尚未重載。')
        if preview.warnings and not accept_warnings:
            raise ProjectError('文字疑似亂碼，請核對並明確確認原文後再重載。')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        content = preview.text.encode('utf-8')
        path = f'batches/{batch_id}/draft-{uuid.uuid4().hex}.txt'
        files = [(path, content)]
        copy_id = None
        if dirty and conflict == 'keep-copy':
            assert unsaved_text is not None
            copy_id = uuid.uuid4().hex
            copy_path = f'batches/{batch_id}/copy-{copy_id}.txt'
            copy = unsaved_text.encode('utf-8')
            batch.setdefault('draft_copies', []).append(dict(
                id=copy_id, path=copy_path, sha256=digest(copy), created_at=now()))
            files.append((copy_path, copy))
        batch['draft'] = dict(path=path, sha256=digest(content))
        batch['revision'] += 1
        batch['current_reading'] = None
        if batch['kind'] == 'pdf':
            batch['pdf']['mapping_valid'] = False
        self._commit(manifest, files)
        return copy_id

    def draft_copy_text(self, batch_id: str, copy_id: str) -> str:
        for copy in self._batch(batch_id).get('draft_copies', []):
            if copy['id'] == copy_id:
                return self._read(copy).decode('utf-8')
        raise ProjectError('找不到保留的未存稿副本。')

    @staticmethod
    def voice_catalog() -> dict:
        from .voice import catalog
        return catalog()

    @staticmethod
    def start_voice_refresh():
        from .voice import refresh
        return refresh()

    def voice_settings(self, batch_id: str | None = None) -> dict:
        from .voice import DEFAULT_SETTINGS, settings
        owner = self._batch(batch_id) if batch_id is not None else self._manifest
        return settings(owner.get('voice_settings', DEFAULT_SETTINGS))

    def save_voice_settings(self, voice: str, rate: str = '+0%', *, batch_id: str | None = None,
                            sentence_pause_ms: int | None = None, paragraph_pause_ms: int | None = None, settings_override: dict | None = None):
        from .voice import require_voice, settings
        value = self.voice_settings(batch_id) if settings_override is None else settings(settings_override)
        value.update(voice=voice, rate=rate)
        if sentence_pause_ms is not None:
            value['sentence_pause_ms'] = sentence_pause_ms
        if paragraph_pause_ms is not None:
            value['paragraph_pause_ms'] = paragraph_pause_ms
        value = settings(value)
        require_voice(voice, value)
        manifest = self.state
        owner = next(b for b in manifest['batches'] if b['id'] == batch_id) if batch_id is not None else manifest
        owner['voice_settings'] = value
        self._commit(manifest, [])

    def start_voice_preview(self, batch_id: str, *, start: int | None = None, end: int | None = None,
                            text: str | None = None, settings_override: dict | None = None):
        from .voice import VoiceJob, EXAMPLE, require_voice
        from .voice_media import ffmpeg, synthesize
        if self._voice_job is not None:
            raise ProjectError('已有試聽工作待完成，請先取消或保存。')
        self._check_current()
        batch = self._batch(batch_id)
        from .voice import settings
        value = self.voice_settings(batch_id) if settings_override is None else settings(settings_override)
        require_voice(value['voice'], value)
        tool = ffmpeg()
        if start is None and end is None and text is None:
            selected, source = EXAMPLE, 'example'
        else:
            draft = self.texts(batch_id)[1] if text is None else text
            if (not isinstance(draft, str) or type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(draft)):
                raise ProjectError('請在校對稿選取要試聽的文字範圍。')
            selected, source = draft[start:end], 'selection'
        if not selected.strip() or len(selected) > 3000:
            raise ProjectError('試聽請選擇 1～3,000 字元；超過時請縮短範圍，不會自動截斷。')
        from .narration import plan
        preview_plan = plan(selected, value, 'preview', batch_id)
        self._space(self.root, 25_000_000)
        snapshot = dict(id=uuid.uuid4().hex, batch_id=batch_id, created_at=now(), text=selected,
                        source=source, start=start, end=end, revision=batch['revision'], settings=value,
                        rules=preview_plan['rules'], chunks=preview_plan['chunks'])
        async def operation():
            audio = await synthesize(selected, value, tool, self._path(f'batches/{batch_id}/voice-blocks'))
            return snapshot, audio
        self._voice_job = VoiceJob(operation)
        return self._voice_job

    def finish_voice_preview(self, job: VoiceJob) -> dict:
        if job is not self._voice_job or not job.wait(0):
            raise ProjectError('請等待所屬試聽工作停止。')
        snapshot, audio = job.result
        batch_id = snapshot['batch_id']
        self._batch(batch_id)
        path = f'batches/{batch_id}/voice-preview-{snapshot["id"]}.mp3'
        snapshot['audio'] = dict(path=path, sha256=digest(audio))
        manifest = self.state
        next(b for b in manifest['batches'] if b['id'] == batch_id)['voice_preview'] = snapshot
        self._commit(manifest, [(path, audio)])
        self._voice_job = None
        return deepcopy(snapshot)

    def discard_voice_preview(self, job: VoiceJob):
        if job is not self._voice_job or not job.wait(0):
            raise ProjectError('請等待所屬試聽工作停止後再捨棄。')
        self._voice_job = None

    def voice_preview(self, batch_id: str) -> dict | None:
        value = self._batch(batch_id).get('voice_preview')
        if value is None:
            return None
        from .voice import settings
        try:
            settings(value['settings'])
            if not isinstance(value['text'], str) or not value['text'].strip() or not value['id']:
                raise ValueError()
            self._read(value['audio'])
            return deepcopy(value)
        except (KeyError, TypeError, ValueError):
            raise ProjectError('試聽記錄損壞，請重新試聽。') from None

    def voice_preview_path(self, batch_id: str) -> Path:
        preview = self.voice_preview(batch_id)
        if preview is None:
            raise ProjectError('尚無成功試聽，請先產生試聽音訊。')
        return self.root / preview['audio']['path']

    def start_narration(self, batch_id: str):
        from .narration import NarrationJob, plan
        from .voice import require_voice
        from .voice_media import ffmpeg
        if self._narration_job is not None:
            raise ProjectError('已有產生成品任務，請先保存或捨棄結果。')
        text = self.reading_text(batch_id)
        batch = self._batch(batch_id)
        value = self.voice_settings(batch_id)
        require_voice(value['voice'], value)
        tool = ffmpeg()
        snapshot = plan(text, value, batch['current_reading'], batch_id)
        self._space(self.root, 25_000_000)
        lock_path = self.root / '.production.lock'
        lock = None
        folder = self._path(f'batches/{batch_id}/narration-{snapshot["id"]}')
        committed = False
        try:
            lock = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock, str(os.getpid()).encode('ascii'))
            folder.mkdir()
            progress = folder / 'progress.json'
            self._atomic(progress, encode(dict(status='pending', chunks=[])))
            data = encode(snapshot)
            relative = (folder / 'plan.json').relative_to(self.root).as_posix()
            ref = dict(id=snapshot['id'], path=relative, sha256=digest(data),
                       progress_path=progress.relative_to(self.root).as_posix())
            manifest = self.state
            next(b for b in manifest['batches'] if b['id'] == batch_id).setdefault('narration_runs', []).append(ref)
            self._commit(manifest, [(relative, data)])
            committed = True
            job = NarrationJob(snapshot, folder, tool, lock, lock_path)
            self._narration_job = job
            return job
        except FileExistsError:
            raise ProjectError('專案已有產生成品任務。若程序曾中斷，請關閉所有視窗後移除 .production.lock 再重開。') from None
        except OSError:
            raise ProjectError('無法準備合成任務，請檢查磁碟空間與寫入權限。') from None
        finally:
            if self._narration_job is None and lock is not None:
                os.close(lock)
                lock_path.unlink(missing_ok=True)
                if not committed and folder.exists():
                    shutil.rmtree(folder)

    def narration_runs(self, batch_id: str) -> list[dict]:
        from .narration import read_run
        return [read_run(self, ref) for ref in self._batch(batch_id).get('narration_runs', [])]

    def finish_narration(self, job: NarrationJob) -> dict:
        if job is not self._narration_job or not job.wait(0):
            raise ProjectError('請等待所屬合成任務停止。')
        report = job.result
        snapshot = deepcopy(job.snapshot)
        batch_id = snapshot['batch_id']
        self._batch(batch_id)
        if job.published:
            product = self.narration(batch_id)
            if product is None:
                raise ProjectError('已發布的成品記錄遺失，請重新開啟專案。')
            job.release(discard=False)
            self._narration_job = None
            return product
        snapshot.update(chunks=report['chunks'], duration_ms=report['duration_ms'], completed_at=now())
        for kind in ('mp3', 'srt'):
            path = job.folder / 'media' / ('narration.' + kind)
            snapshot[kind] = dict(path=path.relative_to(self.root).as_posix(), sha256=digest(path.read_bytes()))
        manifest = self.state
        next(b for b in manifest['batches'] if b['id'] == batch_id)['narration'] = snapshot
        self._commit(manifest, [])
        job.published = True
        job.release(discard=False)
        self._narration_job = None
        return deepcopy(snapshot)

    def discard_narration(self, job: NarrationJob):
        if job is not self._narration_job or not job.wait(0):
            raise ProjectError('請等待所屬合成任務停止後再捨棄。')
        job.release(discard=True)
        self._narration_job = None

    def narration(self, batch_id: str) -> dict | None:
        product = self._batch(batch_id).get('narration')
        if product is None:
            return None
        try:
            from .voice import settings
            settings(product['settings'])
            if (not product['chunks'] or any(c['status'] != 'completed' or c['duration_ms'] <= 0
                                             for c in product['chunks'])
                    or digest(product['text'].encode('utf-8')) != product['text_sha256']):
                raise ValueError()
            for kind in ('mp3', 'srt'):
                if not self._read(product[kind]):
                    raise ValueError()
            return deepcopy(product)
        except (KeyError, TypeError, ValueError):
            raise ProjectError('批次音訊／字幕記錄損壞，請還原備份或重新合成。') from None

    def narration_path(self, batch_id: str, kind: str = 'mp3') -> Path:
        if kind not in ('mp3', 'srt'):
            raise ProjectError('成品格式僅支援 MP3 或 SRT。')
        product = self.narration(batch_id)
        if product is None:
            raise ProjectError('尚無成功批次成品，請先確認朗讀稿並合成。')
        return self._path(product[kind]['path'])

    def export_narration(self, batch_id: str, folder: str | Path):
        """Export a pair into a new folder; never overwrite an existing destination."""
        product = self.narration(batch_id)
        if product is None:
            raise ProjectError('尚無成功批次成品。')
        target = Path(folder).resolve()
        if target.exists():
            raise ProjectError('另存資料夾已存在，請選擇新的資料夾名稱。')
        temporary = None
        try:
            temporary = Path(tempfile.mkdtemp(prefix='.narration-export-', dir=target.parent))
            for kind in ('mp3', 'srt'):
                self._atomic(temporary / ('narration.' + kind), self._read(product[kind]))
            temporary.rename(target)
            temporary = None
        except OSError:
            raise ProjectError('無法另存成品，請檢查資料夾權限與磁碟空間。') from None
        finally:
            if temporary is not None:
                shutil.rmtree(temporary)

    @staticmethod
    def gemini_settings() -> dict:
        from .gemini import load_settings
        return load_settings()

    @staticmethod
    def save_gemini_settings(key: str, model: str) -> None:
        from .gemini import save_settings
        save_settings(key, model)

    @staticmethod
    def test_gemini_connection():
        from .gemini import load_settings, ReviewJob
        settings = load_settings()
        if not settings['key']:
            raise ProjectError('請先設定 Gemini API Key；仍可人工校對。')
        return ReviewJob(settings['key'], dict(model=settings['model'], paragraphs=[dict(original='連線測試。')]))

    def gemini_scope(self, batch_id: str, *, start: int = 0, end: int | None = None,
                     script: str = 'auto', punctuation: bool = True) -> dict:
        from .proofreading import profile
        _, text = self.texts(batch_id)
        end = len(text) if end is None else end
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or not text[start:end].strip():
            raise ProjectError('請選取有效且非空白的校對範圍。')
        settings = self.gemini_settings()
        return dict(service='Gemini', model=settings['model'], start=start, end=end,
                    characters=end-start, revision=self._batch(batch_id)['revision'],
                    normalization=profile(text, script, punctuation))

    def start_gemini_review(self, batch_id: str, *, start: int = 0, end: int | None = None,
                           script: str = 'auto', punctuation: bool = True):
        from .gemini import load_settings, plan_requests
        if self._gemini_job is not None:
            raise ProjectError('請先保存前次 Gemini 結果。')
        scope = self.gemini_scope(batch_id, start=start, end=end, script=script, punctuation=punctuation)
        settings = load_settings()
        if not settings['key']:
            raise ProjectError('請先設定 Gemini API Key；仍可人工校對。')
        _, text = self.texts(batch_id)
        paragraphs, requests = plan_requests(text, scope['start'], scope['end'])
        batch = self._batch(batch_id)
        review = dict(id=uuid.uuid4().hex, batch_id=batch_id, created_at=now(), **scope,
                      before=deepcopy(batch['draft']), expected=deepcopy(batch['draft']),
                      expected_revision=batch['revision'], paragraphs=paragraphs, requests=requests,
                      notes=[], history=[], status='running', error='')
        return self._start_gemini_job(settings['key'], review)

    def _start_gemini_job(self, key: str, review: dict, targets=None):
        from .gemini import ReviewJob
        # The manifest pins the source and plan before any network request. Only this
        # job writes its atomic progress journal, so manuscript commits stay on the UI thread.
        review['progress_path'] = f'batches/{review["batch_id"]}/gemini-progress-{uuid.uuid4().hex}.json'
        review.update(status='running', error='')
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == review['batch_id'])
        self._write_review(manifest, batch, review, [])
        path = self._path(review['progress_path'])
        def checkpoint(value):
            import time
            data = encode(dict(review=value, sha256=digest(encode(value))))
            for attempt in range(6):
                try:
                    self._atomic(path, data)
                    return
                except PermissionError:
                    if attempt == 5:
                        raise
                    # A Windows reader may briefly deny replacement. Only the
                    # background journal writer waits; the UI never waits here.
                    time.sleep(.02)
        self._gemini_job = ReviewJob(key, review, checkpoint=checkpoint, targets=targets)
        return self._gemini_job

    def start_gemini_retry(self, batch_id: str, review_id: str, *, failed_only: bool = False):
        from .gemini import load_settings
        if self._gemini_job is not None:
            raise ProjectError('請先保存前次 Gemini 結果。')
        review = self._gemini_record(batch_id, review_id, require_candidate=False)
        if 'requests' not in review:
            raise ProjectError('此舊版候選沒有分段計畫，請重新送出校對。')
        targets = [i for i, r in enumerate(review['requests'])
                   if r['status'] == 'failed' or (not failed_only and r['status'] != 'completed')]
        if not targets:
            raise ProjectError('沒有需要重試的範圍。')
        settings = load_settings()
        if not settings['key']:
            raise ProjectError('請先設定 Gemini API Key；仍可人工校對。')
        old_path = review.pop('progress_path', None)
        job = self._start_gemini_job(settings['key'], review, targets)
        if old_path:
            # Old journal is no longer referenced; cleanup must not lose a running job.
            try:
                self._path(old_path).unlink(missing_ok=True)
            except OSError:
                pass
        return job

    def finish_gemini_review(self, job: ReviewJob) -> str:
        if job is not self._gemini_job or not job.wait(0):
            raise ProjectError('Gemini 工作不屬於此專案或仍在執行。')
        review = job.review
        progress_path = review.pop('progress_path', None)
        if review.pop('checkpoint_error', False):
            review['error'] = '' if review['status'] == 'completed' else '進度曾中斷；成功候選已保存，可續作未完成範圍。'
        manifest = self.state
        batch = next((b for b in manifest['batches'] if b['id'] == review['batch_id']), None)
        if batch is None:
            raise ProjectError('原批次已移除，請重新建立校對工作。')
        self._write_review(manifest, batch, review, [])
        self._gemini_job = None
        if progress_path:
            try:
                self._path(progress_path).unlink(missing_ok=True)
            except OSError:
                pass  # Final immutable review is already committed.
        return review['id']

    def discard_gemini_review(self, job: ReviewJob) -> None:
        if job is not self._gemini_job or not job.wait(0):
            raise ProjectError('請先等待 Gemini 取消或完成，再捨棄候選。')
        self._gemini_job = None

    def _write_review(self, manifest: dict, batch: dict, review: dict, files: list[tuple[str, bytes]]):
        path = f'batches/{batch["id"]}/gemini-{uuid.uuid4().hex}.json'
        data = encode(review)
        refs = batch.setdefault('gemini_reviews', [])
        ref = dict(id=review['id'], path=path, sha256=digest(data))
        index = next((i for i, existing in enumerate(refs) if existing['id'] == review['id']), None)
        if index is None:
            refs.append(ref)
        else:
            refs[index] = ref
        self._commit(manifest, files + [(path, data)])

    def gemini_reviews(self, batch_id: str) -> list[dict]:
        """Validated, portable before/candidate/after records; never credentials."""
        reviews = []
        for ref in self._batch(batch_id).get('gemini_reviews', []):
            review = json.loads(self._read(ref))
            if review['id'] != ref['id'] or review['batch_id'] != batch_id:
                raise ProjectError('Gemini 校對記錄與批次不符，請還原備份。')
            review = self._gemini_progress(review)
            text = self._read(review['before']).decode('utf-8')
            self._read(review['expected']).decode('utf-8')
            if not 0 <= review['start'] < review['end'] <= len(text):
                raise ProjectError('Gemini 校對範圍損壞，請還原備份。')
            for paragraph in review['paragraphs']:
                if (not review['start'] <= paragraph['start'] < paragraph['end'] <= review['end']
                        or text[paragraph['start']:paragraph['end']] != paragraph['original']
                        or paragraph['decision'] not in ('pending', 'accepted', 'rejected')
                        or (paragraph['candidate'] is not None and not isinstance(paragraph['candidate'], str))
                        or ('applied_candidate' in paragraph and (paragraph['decision'] == 'rejected'
                            or not isinstance(paragraph['applied_candidate'], str)
                            or not paragraph['applied_candidate'].strip()))):
                    raise ProjectError('Gemini 校對段落損壞，請還原備份。')
            self._validate_gemini_plan(review, text)
            for item in review['history']:
                self._read(item['before']).decode('utf-8')
                self._read(item['after']).decode('utf-8')
            review['stale'] = (review['expected'] != self._batch(batch_id)['draft']
                               or review['expected_revision'] != self._batch(batch_id)['revision'])
            reviews.append(review)
        return reviews

    def _gemini_progress(self, review: dict) -> dict:
        if 'progress_path' not in review:
            return review
        path = self._path(review['progress_path'])
        if path.exists():
            try:
                envelope = json.loads(path.read_bytes())
                progress = envelope['review']
                if (digest(encode(progress)) != envelope['sha256'] or any(
                        progress[k] != review[k] for k in ('id', 'batch_id', 'before', 'expected',
                            'revision', 'expected_revision', 'start', 'end', 'model', 'progress_path'))):
                    raise ValueError()
                if [(p['start'], p['end'], p['original'], p['decision']) for p in progress['paragraphs']] != [
                        (p['start'], p['end'], p['original'], p['decision']) for p in review['paragraphs']]:
                    raise ValueError()
                review = progress
            except (OSError, ValueError, KeyError, TypeError):
                raise ProjectError('Gemini 進度檔損壞，請還原備份；原稿未變更。') from None
        active = self._gemini_job
        if review['status'] == 'running' and not (active and active.snapshot['id'] == review['id'] and not active.wait(0)):
            review['status'] = 'interrupted'
            review['error'] = '上次工作未完成；已保存成功候選，可繼續未完成範圍。'
            for request in review['requests']:
                if request['status'] == 'running':
                    request['status'] = 'pending'
        return review

    @staticmethod
    def _validate_gemini_plan(review: dict, text: str):
        if 'requests' not in review:
            return  # T07 immutable records remain readable.
        cursor, first = review['start'], 0
        paragraph_end = review['start']
        for part in review['paragraphs']:
            if part['start'] < paragraph_end or text[paragraph_end:part['start']].strip():
                raise ProjectError('Gemini 分段計畫有遺漏或重複，請還原備份。')
            paragraph_end = part['end']
        if text[paragraph_end:review['end']].strip():
            raise ProjectError('Gemini 分段計畫未覆蓋全文，請還原備份。')
        for request in review['requests']:
            if (request['start'] != cursor or request['first'] != first
                    or not first < request['last'] <= len(review['paragraphs'])
                    or not cursor < request['end'] <= review['end']
                    or request['status'] not in ('pending', 'running', 'completed', 'failed', 'cancelled')):
                raise ProjectError('Gemini 請求範圍損壞，請還原備份。')
            for part in review['paragraphs'][first:request['last']]:
                if not request['start'] <= part['start'] < part['end'] <= request['end']:
                    raise ProjectError('Gemini 請求與段落範圍不符，請還原備份。')
                if (request['status'] == 'completed') != (isinstance(part['candidate'], str) and bool(part['candidate'].strip())):
                    raise ProjectError('Gemini 成功範圍缺少完整候選，請還原備份。')
            cursor, first = request['end'], request['last']
        if cursor != review['end'] or first != len(review['paragraphs']):
            raise ProjectError('Gemini 請求計畫未覆蓋全文，請還原備份。')

    def _gemini_record(self, batch_id: str, review_id: str, *, require_candidate: bool = True) -> dict:
        for review in self.gemini_reviews(batch_id):
            if review['id'] == review_id:
                if self._gemini_job is not None and self._gemini_job.snapshot['id'] == review_id:
                    raise ProjectError('請先等待並保存目前 Gemini 工作，再操作候選。')
                if review.pop('stale'):
                    raise ProjectError('原稿版本已變更，候選與目前稿有差異。請比較後重新送出，不能直接覆蓋。')
                if require_candidate and not any(p['candidate'] is not None for p in review['paragraphs']):
                    raise ProjectError('本次 Gemini 尚無完整有效候選，原稿未變更。')
                return review
        raise ProjectError('找不到 Gemini 候選校對稿。')

    def edit_gemini_candidates(self, batch_id: str, review_id: str, edits: dict[int, str]) -> None:
        """Save human corrections without adopting them into the source draft."""
        review = self._gemini_record(batch_id, review_id)
        for index, text in edits.items():
            if (type(index) is not int or not 0 <= index < len(review['paragraphs'])
                    or not isinstance(text, str) or not text.strip()):
                raise ProjectError('候選文字不可空白，請選擇有效段落。')
            part = review['paragraphs'][index]
            if part['candidate'] is None:
                raise ProjectError('本段尚無成功候選，請先重試此範圍。')
            if part['decision'] == 'accepted':
                part['applied_candidate'] = part['candidate']
                part['decision'] = 'pending'
            part.setdefault('ai_candidate', part['candidate'])
            part['candidate'] = text
        review.pop('progress_path', None)
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        self._write_review(manifest, batch, review, [])

    def decide_gemini(self, batch_id: str, review_id: str, paragraph: int | None, decision: str) -> None:
        review = self._gemini_record(batch_id, review_id)
        if decision not in ('accepted', 'rejected') or (paragraph is not None and
                (type(paragraph) is not int or not 0 <= paragraph < len(review['paragraphs']))):
            raise ProjectError('請選擇有效段落及採用或拒絕。')
        if paragraph is not None and review['paragraphs'][paragraph]['candidate'] is None:
            raise ProjectError('本段尚無成功候選，請先重試此範圍。')
        for index, part in enumerate(review['paragraphs']):
            if part['candidate'] is not None and (index == paragraph or (paragraph is None and part['decision'] == 'pending')):
                part['decision'] = decision
                if decision == 'accepted':
                    part['applied_candidate'] = part['candidate']
                else:
                    part.pop('applied_candidate', None)
        text = self._read(review['before']).decode('utf-8')
        for part in reversed(review['paragraphs']):
            if part['decision'] == 'accepted' or 'applied_candidate' in part:
                text = text[:part['start']] + part.get('applied_candidate', part['candidate']) + text[part['end']:]
        self._publish_gemini_draft(batch_id, review, text, 'decision')

    def undo_gemini(self, batch_id: str, review_id: str) -> None:
        review = self._gemini_record(batch_id, review_id)
        for part in review['paragraphs']:
            part['decision'] = 'pending'
            part.pop('applied_candidate', None)
        self._publish_gemini_draft(batch_id, review, self._read(review['before']).decode('utf-8'), 'undo')

    def _publish_gemini_draft(self, batch_id: str, review: dict, text: str, action: str):
        review.pop('progress_path', None)
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        content = text.encode('utf-8')
        before = deepcopy(batch['draft'])
        files = []
        if digest(content) != before['sha256']:
            path = f'batches/{batch_id}/draft-{uuid.uuid4().hex}.txt'
            files.append((path, content))
            batch['draft'] = dict(path=path, sha256=digest(content))
            batch['revision'] += 1
            batch['current_reading'] = None
            if batch['kind'] == 'pdf':
                batch['pdf']['mapping_valid'] = False
        review.update(expected=deepcopy(batch['draft']), expected_revision=batch['revision'])
        review['history'].append(dict(action=action, before=before, after=deepcopy(batch['draft']), created_at=now()))
        self._write_review(manifest, batch, review, files)
