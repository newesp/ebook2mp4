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
from .voice import VoiceJob
from .voice_media import media_command, speech_block

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
                    if char in '。！？' or word.endswith(tuple('。！？.!?')):
                        sentences.append(index + 1)
                    elif char in '；，、' or word.endswith(tuple('；，、,;:')):
                        clauses.append(index + 1)
        elif not stack and char in CLOSERS:
            before = index - 1
            while before >= 0 and text[before] in CLOSERS:
                before -= 1
            if before >= 0 and text[before] in '。！？.!?':
                result.append(index + 1)
                sentences.append(index + 1)
        if (not stack and char in '。！？；，、' and
                (index+1 == len(text) or not text[index+1].isspace())):
            token_start = index + 1
    if text and text[-1] in '。！？.!?':
        token = text[token_start:].rstrip(CLOSERS)
        if token.lower() not in ABBREVIATIONS and not token.endswith(('..', '…')):
            sentences.append(len(text))
    # One spoken boundary includes its punctuation run, closing marks and spaces.
    # Otherwise a quote followed by a space can become a whitespace-only request.
    complete_sentences = set()
    for end in sentences:
        while (end < len(text) and not text[end-1].isspace()
               and text[end] in CLOSERS + '。！？.!?'):
            end += 1
        while end < len(text) and text[end].isspace():
            end += 1
        complete_sentences.add(end)
    return sorted(set(result)), sorted(complete_sentences), clauses


def plan(text: str, settings: dict, reading_id: str, batch_id: str) -> dict:
    if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
        raise ProjectError('朗讀稿含語音服務不支援的控制字元，請修正後重新確認。')
    from .voice import settings as validate_settings
    settings = validate_settings(settings)
    from .tts_backend import capabilities
    policy = capabilities(settings['provider'])
    rules = dict(RULES, version='rhythm-block-v2', sentence_pause_ms=settings['sentence_pause_ms'],
                 paragraph_pause_ms=settings['paragraph_pause_ms'],
                 request_escaped_utf8_bytes=policy.request_escaped_utf8_bytes, max_attempts=policy.max_attempts)
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
            limit = bisect_right(costs, costs[offset] + rules['request_escaped_utf8_bytes']) - 1
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
                if end<=offset and not policy.requires_network:
                    end=limit
                if end <= offset or not paragraph[offset:end].strip():
                    raise ProjectError('朗讀稿有過長且無法安全切分的引文、網址或句段。請加入自然分句後重新確認。')
            if settings['sentence_pause_ms']:
                next_sentence = bisect_right(sentences, offset)
                if next_sentence < len(sentences) and sentences[next_sentence] < end:
                    end = sentences[next_sentence]
            sent = paragraph[offset:end]
            chunks.append(dict(id=digest(f'{len(chunks)}\0{sent}'.encode('utf-8')), order=len(chunks),
                               text=sent, separator_after=separator if end == len(paragraph) else '',
                               text_sha256=digest(sent.encode('utf-8')),
                               pause_after_ms=max(settings['sentence_pause_ms'] if end in sentences else 0,
                                                  settings['paragraph_pause_ms'] if end == len(paragraph) else 0)))
            offset = end
    if not chunks or ''.join(c['text'] + c['separator_after'] for c in chunks) != text:
        raise ProjectError('朗讀稿無法完整規劃，請檢查段落內容。')
    chunks[-1]['pause_after_ms'] = 0
    settings_hash, rules_hash = digest(encode(settings)), digest(encode(rules))
    for chunk in chunks:
        chunk.update(settings_sha256=settings_hash, rules_sha256=rules_hash)
    return dict(id=uuid.uuid4().hex, batch_id=batch_id, reading_id=reading_id,
                created_at=now(), text=text, text_sha256=digest(text.encode('utf-8')),
                settings=settings, settings_sha256=settings_hash, rules=rules,
                rules_sha256=rules_hash, chunks=chunks)


def timestamp(milliseconds: int) -> str:
    seconds, ms = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


class NarrationJob(VoiceJob):
    def __init__(self, snapshot: dict, folder: Path, tool: str, lock, lock_path: Path, previous=None, *, allow_network=True):
        self.snapshot, self.folder, self.tool = deepcopy(snapshot), folder, tool
        self.production_lock = lock
        self.lock_path = lock_path
        self.published = False
        self.allow_network = allow_network
        self.report: dict = dict(status='running', phase='準備', current=0, total=len(snapshot['chunks']),
                           completed=0, failed=0, error='', chunks=[dict(c, status='pending', attempts=0,
                           duration_ms=None) for c in snapshot['chunks']])
        if previous is not None:
            self.report['resume_history'] = previous.get('resume_history', []) + [
                {k: deepcopy(v) for k, v in previous.items() if k != 'resume_history'}]
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
        from .kokoro_runtime import local_session
        async with local_session(self.snapshot['settings']):
            return await self.produce_blocks()

    async def produce_blocks(self):
        media = self.folder / 'media'
        success = False
        try:
            validate_plan(self.snapshot)
            if media.exists():
                shutil.rmtree(media)
            media.mkdir()
            self.save_progress()
            settings = self.snapshot['settings']
            cues, frames = [], 0
            assembled_path = media / 'assembled.wav'
            with wave.open(str(assembled_path), 'wb') as assembled:
                assembled.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                for index, chunk in enumerate(self.report['chunks']):
                    await asyncio.sleep(0)
                    self.save_progress(phase='驗證音訊區塊', current=index + 1)
                    def progress(attempt):
                        chunk.update(status='running', attempts=attempt)
                        self.save_progress(phase='本機合成' if settings['provider']=='kokoro' else '線上合成')
                    decoded, reused = await speech_block(
                        chunk['text'], settings, self.tool, self.folder.parent / 'voice-blocks',
                        progress, allow_network=self.allow_network)
                    chunk.update(reused=reused)
                    with wave.open(str(decoded), 'rb') as source:
                        count = source.getnframes()
                        if count <= 0:
                            raise ProjectError('區塊音訊為空，請重試。')
                        # Copy bounded buffers; a long book need not fit into memory.
                        while data := source.readframes(24000):
                            await asyncio.sleep(0)
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
        except Exception as error:
            for chunk in self.report['chunks']:
                if chunk['status'] == 'running':
                    chunk['status'] = 'failed'
                    chunk['error'] = str(error) if isinstance(error, ProjectError) else '區塊處理失敗。'
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
                self.production_lock.release()
                self.production_lock = None
        except OSError:
            raise ProjectError('無法清理合成暫存或任務鎖；已發布成品保留。請解除檔案占用後重試。') from None


def validate_plan(snapshot: dict):
    expected = plan(snapshot['text'], snapshot['settings'], snapshot['reading_id'], snapshot['batch_id'])
    if snapshot['rules'] == RULES and snapshot['settings']['sentence_pause_ms'] == 0 and snapshot['settings']['paragraph_pause_ms'] == 500:
        # T10 used the same natural rhythm under its original rule-version name.
        expected['rules'] = dict(RULES)
        expected['rules_sha256'] = digest(encode(RULES))
        for chunk in expected['chunks']:
            chunk['rules_sha256'] = expected['rules_sha256']
    for key in ('chunks', 'text_sha256', 'settings_sha256', 'rules', 'rules_sha256'):
        if snapshot[key] != expected[key]:
            raise ProjectError('合成計畫驗證失敗，請還原專案備份。')


def read_run(flow: ProjectWorkflow, ref: dict, *, verify_audio=True) -> dict:
    try:
        snapshot = json.loads(flow._read(ref))
        progress = json.loads(flow._path(ref['progress_path']).read_bytes())
        from .production_lock import production_active
        from .voice_media import cached_block
        if verify_audio:
            validate_plan(snapshot)
        if progress['status'] not in ('pending', 'running', 'cancelling', 'cancelled', 'failed', 'completed'):
            raise ValueError()
        if progress['status'] in ('pending', 'running', 'cancelling') and not production_active(flow.root / '.production.lock'):
            progress['status'] = 'interrupted'
        cache = flow._path(f'batches/{snapshot["batch_id"]}/voice-blocks')
        reusable = sum(cached_block(c['text'], snapshot['settings'], cache) is not None for c in snapshot['chunks']) if verify_audio else 0
        batch = flow._batch(snapshot['batch_id'])
        stale = (batch.get('current_reading') != snapshot['reading_id'] or
                 flow.voice_settings(snapshot['batch_id']) != snapshot['settings'])
        published = ref.get('published', False) or batch.get('narration', {}).get('id') == snapshot['id']
        return dict(snapshot=snapshot, progress=progress, reusable=reusable,
                    stale=stale, published=published, remaining=len(snapshot['chunks'])-reusable)
    except (OSError, ValueError, KeyError, TypeError):
        raise ProjectError('合成任務記錄無法讀取，請還原專案備份。') from None
