"""Confirmed-text planning and measured, cancellable MP3/SRT production."""
from __future__ import annotations

import asyncio
from bisect import bisect_right
from copy import deepcopy
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import uuid
import wave

from .workflow import ProjectError, ProjectWorkflow, digest, encode, now
from .voice import VoiceJob, edge_module
from .voice_media import media_command

RULES: dict = dict(version='natural-block-v1', request_escaped_utf8_bytes=3000,
             sentence_pause_ms=0, paragraph_pause_ms=500, timing='measured-block-pcm',
             sample_rate=24000, max_attempts=3)
PARAGRAPH = re.compile(r'(?:\r?\n)[ \t]*(?:\r?\n)(?:[ \t]*\r?\n)*')
CLOSERS = '\"\'”’」』）)]}》】'
ABBREVIATIONS = frozenset(('dr.', 'mr.', 'mrs.', 'ms.', 'prof.', 'sr.', 'jr.', 'st.',
                           'vs.', 'etc.', 'e.g.', 'i.e.', 'fig.', 'no.', 'pp.', 'vol.',
                           'ch.', 'inc.', 'ltd.', 'ph.d.', 'a.m.', 'p.m.'))


def request_size(text: str) -> int:
    return len(escape(text, quote=False).encode('utf-8'))


def safe_boundaries(text: str) -> tuple[list[int], list[int], list[int]]:
    """Only divide outside paired punctuation, at sentence/clause/word boundaries.

    Sentence ends take precedence over clauses and word boundaries. Abbreviations,
    decimals, URLs and paired punctuation are never divided internally.
    """
    pairs = {'(': ')', '[': ']', '{': '}', '「': '」', '『': '』',
             '（': '）', '【': '】', '“': '”', '‘': '’', '《': '》'}
    stack: list[str] = []
    result = []
    sentences, clauses = [], []
    token_start = 0
    last_token = ''
    urls = iter(re.finditer(r'(?:https?://|www\.)[^\s<>「」“”]+', text))
    url = next(urls, None)
    for index, char in enumerate(text):
        if char.isspace() and (index == 0 or not text[index-1].isspace()):
            last_token = text[token_start:index]
        elif not char.isspace() and index > 0 and text[index-1].isspace():
            token_start = index
        if url is not None and index >= url.end():
            url = next(urls, None)
        in_url = url is not None and url.start() <= index < url.end()
        if char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
        elif char == '"':
            if stack and stack[-1] == '"':
                stack.pop()
            else:
                stack.append('"')
        # An apostrophe inside a word is not a quotation mark.
        elif char == "'" and not (0 < index < len(text)-1 and
                                   text[index-1].isalnum() and text[index+1].isalnum()):
            if stack and stack[-1] == "'":
                stack.pop()
            else:
                stack.append("'")
        # URL punctuation cannot form a technical split, but surrounding closing
        # quotes/brackets must still close the paragraph's paired context.
        if in_url:
            continue
        if not stack and (char in '。！？；，、' or char.isspace()):
            # Never divide a run of whitespace; keep it with the preceding text.
            if index + 1 == len(text) or not text[index+1].isspace():
                token = last_token if char.isspace() else ''
                word = token.rstrip(CLOSERS)
                abbreviation = (word.lower() in ABBREVIATIONS or
                                re.fullmatch(r'(?:[A-Za-z]\.)+', word) is not None)
                # Avoid separating a title/abbreviation or an ellipsis from its context.
                if not abbreviation and not word.endswith(('..', '…')):
                    result.append(index + 1)
                    if char in '。！？' or word.endswith(('.', '!', '?')):
                        sentences.append(index + 1)
                    elif char in '；，、' or word.endswith((',', ';', ':')):
                        clauses.append(index + 1)
        elif not stack and char in CLOSERS:
            before = index - 1
            while before >= 0 and text[before] in CLOSERS:
                before -= 1
            if before >= 0 and text[before] in '。！？.!?':
                result.append(index + 1)
                sentences.append(index + 1)
        if not stack and char in '。！？；，、':
            token_start = index + 1
    return result, sentences, clauses


def plan(text: str, settings: dict, reading_id: str, batch_id: str) -> dict:
    if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
        raise ProjectError('朗讀稿含語音服務不支援的控制字元，請修正後重新確認。')
    chunks: list[dict] = []
    # Separators are saved separately, so the exact confirmed text is recoverable.
    start = 0
    pieces = []
    for match in PARAGRAPH.finditer(text):
        if text[start:match.start()].strip():
            pieces.append((text[start:match.start()], match.group()))
            start = match.end()
    if text[start:].strip():
        pieces.append((text[start:], ''))
    elif pieces:
        paragraph, separator = pieces[-1]
        pieces[-1] = (paragraph, separator + text[start:])
    for paragraph, separator in pieces:
        boundaries, sentences, clauses = safe_boundaries(paragraph)
        boundaries.append(len(paragraph))
        costs = [0]
        for char in paragraph:
            costs.append(costs[-1] + request_size(char))
        offset = 0
        while offset < len(paragraph):
            limit = bisect_right(costs, costs[offset] + RULES['request_escaped_utf8_bytes']) - 1
            if limit >= len(paragraph):
                end = len(paragraph)
            else:
                at = bisect_right(boundaries, limit) - 1
                sentence = bisect_right(sentences, limit) - 1
                clause = bisect_right(clauses, limit) - 1
                if sentence >= 0 and sentences[sentence] > offset:
                    end = sentences[sentence]
                elif clause >= 0 and clauses[clause] > offset:
                    end = clauses[clause]
                else:
                    end = boundaries[at] if at >= 0 else offset
                if end <= offset or not paragraph[offset:end].strip():
                    raise ProjectError('朗讀稿有過長且無法安全切分的引文、網址或句段。請加入自然分句後重新確認。')
            sent = paragraph[offset:end]
            chunks.append(dict(id=digest(f'{len(chunks)}\0{sent}'.encode('utf-8')), order=len(chunks),
                               text=sent, separator_after=separator if end == len(paragraph) else '',
                               text_sha256=digest(sent.encode('utf-8')),
                               pause_after_ms=500 if end == len(paragraph) else 0))
            if end != len(paragraph):
                chunks[-1]['pause_after_ms'] = 0
            offset = end
    if not chunks or ''.join(c['text'] + c['separator_after'] for c in chunks) != text:
        raise ProjectError('朗讀稿無法完整規劃，請檢查段落內容。')
    chunks[-1]['pause_after_ms'] = 0
    settings_hash, rules_hash = digest(encode(settings)), digest(encode(RULES))
    for chunk in chunks:
        chunk.update(settings_sha256=settings_hash, rules_sha256=rules_hash)
    return dict(id=uuid.uuid4().hex, batch_id=batch_id, reading_id=reading_id,
                created_at=now(), text=text, text_sha256=digest(text.encode('utf-8')),
                settings=settings, settings_sha256=settings_hash, rules=deepcopy(RULES),
                rules_sha256=rules_hash, chunks=chunks)


def timestamp(milliseconds: int) -> str:
    seconds, ms = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


class NarrationJob(VoiceJob):
    def __init__(self, snapshot: dict, folder: Path, tool: str, lock: int, lock_path: Path):
        self.snapshot, self.folder, self.tool = deepcopy(snapshot), folder, tool
        self.production_lock: int | None = lock
        self.lock_path = lock_path
        self.published = False
        self.report: dict = dict(status='running', phase='準備', current=0, total=len(snapshot['chunks']),
                           completed=0, failed=0, error='', chunks=[dict(c, status='pending', attempts=0,
                           duration_ms=None) for c in snapshot['chunks']])
        super().__init__(self.produce, timeout=None)

    def _run(self):
        super()._run()
        # Also record cancellation that arrived before the coroutine began.
        state = self.state
        try:
            self.save_progress(status=state['status'], error=state['error'])
        except OSError:
            with self._lock:
                self._state.update(status='failed', error='無法保存合成進度，請檢查磁碟空間與寫入權限。')
                self._result = None

    def save_progress(self, **changes):
        self.report.update(changes)
        ProjectWorkflow._atomic(self.folder / 'progress.json', encode(self.report))
        with self._lock:
            self._state.update({k: deepcopy(v) for k, v in self.report.items() if k != 'status'})

    async def produce(self):
        media = self.folder / 'media'
        success = False
        try:
            media.mkdir()
            self.save_progress()
            edge = edge_module()
            from aiohttp import ClientError
            from edge_tts.exceptions import EdgeTTSException
            settings = self.snapshot['settings']
            cues, frames = [], 0
            assembled_path = media / 'assembled.wav'
            with wave.open(str(assembled_path), 'wb') as assembled:
                assembled.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                for index, chunk in enumerate(self.report['chunks']):
                    self.save_progress(phase='線上合成', current=index + 1)
                    raw, decoded = media / 'chunk.mp3', media / 'chunk.wav'
                    for attempt in range(1, 4):
                        chunk.update(status='running', attempts=attempt)
                        self.save_progress()
                        try:
                            async def receive():
                                size = 0
                                with raw.open('wb') as stream:
                                    speaker = edge.Communicate(chunk['text'], settings['voice'], rate=settings['rate'],
                                                               connect_timeout=10, receive_timeout=30)
                                    async for packet in speaker.stream():
                                        if packet['type'] == 'audio':
                                            size += len(packet['data'])
                                            if size > 30_000_000:
                                                raise ProjectError('區塊音訊回應過大，請縮短段落後重試。')
                                            stream.write(packet['data'])
                                    if not size:
                                        raise ProjectError('Edge-TTS 未傳回音訊，請更新音色後重試。')
                            await asyncio.wait_for(receive(), 90)
                            break
                        except (OSError, asyncio.TimeoutError, ClientError, EdgeTTSException):
                            if attempt == 3:
                                raise ProjectError('區塊連線或服務錯誤，3 次嘗試後仍失敗。請檢查連線、更新音色後重試。') from None
                            await asyncio.sleep(attempt)
                    self.save_progress(phase='解碼區塊')
                    await media_command(self.tool, ['-y', '-i', str(raw), '-ac', '1', '-ar', '24000',
                                                    '-c:a', 'pcm_s16le', str(decoded)])
                    with wave.open(str(decoded), 'rb') as source:
                        count = source.getnframes()
                        if count <= 0:
                            raise ProjectError('區塊音訊為空，請重試。')
                        # Copy bounded buffers; a long book need not fit into memory.
                        while data := source.readframes(24000):
                            assembled.writeframesraw(data)
                    start_ms, end_ms = round(frames / 24), round((frames + count) / 24)
                    caption = chunk['text'].strip().replace('\r\n', '\n').replace('\r', '\n')
                    caption = re.sub(r'\n[ \t]*\n+', '\n', caption)
                    cues.append(f'{index+1}\n{timestamp(start_ms)} --> {timestamp(end_ms)}\n{caption}\n\n')
                    chunk.update(status='completed', duration_ms=round(count / 24), frames=count,
                                 start_ms=start_ms, end_ms=end_ms)
                    pause_frames = 24 * chunk['pause_after_ms']
                    assembled.writeframesraw(b'\0\0' * pause_frames)
                    frames += count + pause_frames
                    self.save_progress(completed=index + 1)
                    raw.unlink()
                    decoded.unlink()
            self.save_progress(phase='組裝 MP3／SRT')
            output = media / 'narration.mp3'
            await media_command(self.tool, ['-y', '-i', str(assembled_path), '-c:a', 'libmp3lame', '-b:a', '96k', str(output)], timeout=3600)
            self.save_progress(phase='驗證成品')
            await media_command(self.tool, ['-i', str(output), '-f', 'null', '-'], timeout=3600)
            if output.stat().st_size == 0:
                raise ProjectError('MP3 成品為空，請重試。')
            ProjectWorkflow._atomic(media / 'narration.srt', ''.join(cues).encode('utf-8'))
            assembled_path.unlink()
            self.save_progress(status='completed', phase='等待保存', duration_ms=round(frames / 24))
            success = True
            return deepcopy(self.report)
        except asyncio.CancelledError:
            self.save_progress(status='cancelled', phase='已取消')
            raise
        except Exception:
            for chunk in self.report['chunks']:
                if chunk['status'] == 'running':
                    chunk['status'] = 'failed'
            self.save_progress(status='failed', phase='失敗', failed=sum(c['status'] == 'failed' for c in self.report['chunks']))
            raise
        finally:
            for chunk in self.report['chunks']:
                if chunk['status'] == 'running':
                    chunk['status'] = 'cancelled'
            if not success:
                try:
                    self.save_progress()
                finally:
                    if media.exists():
                        shutil.rmtree(media)

    def release(self, *, discard: bool):
        if not self.wait(0):
            raise ProjectError('請等待產生任務停止後再釋放。')
        try:
            if discard and not self.published and (self.folder / 'media').exists():
                shutil.rmtree(self.folder / 'media')
            if self.production_lock is not None:
                os.close(self.production_lock)
                self.production_lock = None
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            raise ProjectError('無法清理合成暫存或任務鎖；已發布成品保留。請解除檔案占用後重試。') from None


def read_run(flow: ProjectWorkflow, ref: dict) -> dict:
    try:
        snapshot = json.loads(flow._read(ref))
        progress = json.loads(flow._path(ref['progress_path']).read_bytes())
        return dict(snapshot=snapshot, progress=progress)
    except (OSError, ValueError, KeyError, TypeError):
        raise ProjectError('合成任務記錄無法讀取，請還原專案備份。') from None
