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
                if batch['id'] in seen or batch['kind'] != 'txt' or not isinstance(batch['name'], str):
                    raise ValueError()
                seen.add(batch['id'])
                if type(batch['revision']) is not int or batch['revision'] < 1:
                    raise ValueError()
                source = flow._read(batch['source'])
                if len(source) != batch['source']['size']:
                    raise ValueError()
                decode_txt(source, batch['source']['encoding'])
                flow._read(batch['draft']).decode('utf-8')
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

    def texts(self, batch_id: str) -> tuple[str, str]:
        batch = self._batch(batch_id)
        return (decode_txt(self._read(batch['source']), batch['source']['encoding']),
                self._read(batch['draft']).decode('utf-8'))

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
        self._commit(manifest, [(path, content)])
