"""Portable manuscript drafts and a single atomic reading publication."""
from copy import deepcopy
from difflib import SequenceMatcher
import uuid
from typing import TYPE_CHECKING


def change_spans(before, after):
    """Bound diff cost for long books; refine changed lines by common edges."""
    left, right = before.splitlines(True), after.splitlines(True)
    left_offsets, right_offsets = [0], [0]
    for line in left:
        left_offsets.append(left_offsets[-1]+len(line))
    for line in right:
        right_offsets.append(right_offsets[-1]+len(line))
    spans = []
    def append(a, b, c, d):
        while a < b and c < d and before[a] == after[c]:
            a, c = a+1, c+1
        while a < b and c < d and before[b-1] == after[d-1]:
            b, d = b-1, d-1
        if a != b or c != d:
            spans.append(('replace', a, b, c, d))
    for tag, a, b, c, d in SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        if b-a == d-c:
            for i in range(b-a):
                append(left_offsets[a+i], left_offsets[a+i+1], right_offsets[c+i], right_offsets[c+i+1])
        else:
            append(left_offsets[a], left_offsets[b], right_offsets[c], right_offsets[d])
    return spans


def merge_candidate(previous, updated, edited):
    """Apply new AI ranges only where they do not intersect human edits."""
    human = change_spans(previous, edited)
    result = edited
    conflicts = 0
    for tag, start, end, a, b in reversed(change_spans(previous, updated)):
        if tag == 'equal':
            continue
        if any(start <= h[2] and end >= h[1] for h in human):
            conflicts += 1
            continue
        shift = sum((h[4]-h[3])-(h[2]-h[1]) for h in human if h[2] < start)
        result = result[:start+shift] + updated[a:b] + result[end+shift:]
    return result, conflicts


class ManuscriptWorkflow:
    if TYPE_CHECKING:
        @property
        def state(self) -> dict: ...
        def _batch(self, batch_id: str) -> dict: ...
        def _read(self, ref: dict) -> bytes: ...
        def _commit(self, manifest: dict, files: list[tuple[str, bytes]]): ...
        def _gemini_record(self, batch_id: str, review_id: str, *, require_candidate: bool = True) -> dict: ...
        def confirmation_blockers(self, batch_id: str) -> list[str]: ...
        def texts(self, batch_id: str) -> tuple[str, str]: ...

    def workspace_state(self, batch_id):
        value = deepcopy(self._batch(batch_id).get('workspace', {}))
        if value.get('text_ref'):
            value['text'] = self._read(value.pop('text_ref')).decode('utf-8')
        return value

    def save_workspace(self, batch_id, text, *, review_id=None, allow_partial=False):
        from .workflow import digest
        current = self.workspace_state(batch_id)
        if (current.get('text') == text and current.get('review_id') == review_id
                and current.get('allow_partial', False) == allow_partial):
            return
        content = text.encode('utf-8')
        path = f'batches/{batch_id}/workspace-{uuid.uuid4().hex}.txt'
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        batch['workspace'] = dict(text_ref=dict(path=path, sha256=digest(content)),
                                  review_id=review_id, allow_partial=allow_partial)
        if digest(content) != batch['draft']['sha256']:
            batch['current_reading'] = None
            if batch['kind'] == 'pdf':
                batch['pdf']['mapping_valid'] = False
        self._commit(manifest, [(path, content)])

    def backup_manuscript(self, batch_id, text, *, label='編輯稿備份'):
        from .workflow import digest, now
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        identity = uuid.uuid4().hex
        content = text.encode('utf-8')
        ref = dict(id=identity, path=f'batches/{batch_id}/copy-{identity}.txt',
                   sha256=digest(content), created_at=now(), label=label)
        batch.setdefault('draft_copies', []).append(ref)
        self._commit(manifest, [(ref['path'], content)])

    def full_candidate(self, batch_id, review_id):
        review = self._gemini_record(batch_id, review_id, require_candidate=False)
        text = self._read(review['before']).decode('utf-8')
        for part in reversed(review['paragraphs']):
            replacement = part.get('applied_candidate') if part['decision'] == 'rejected' else part['candidate']
            if replacement is not None:
                text = text[:part['start']] + replacement + text[part['end']:]
        return text, review

    def save_reading_manuscript(self, batch_id, text, *, review_id=None, allow_partial=False):
        """Publish the displayed text and its snapshot with one manifest replacement."""
        from .workflow import ProjectError, digest, now
        blockers = self.confirmation_blockers(batch_id)
        if blockers:
            raise ProjectError('來源異常尚未處理，不能儲存為朗讀稿：\n' + '\n'.join(blockers))
        if not text.strip():
            raise ProjectError('文稿為空，請加入內容。')
        if review_id:
            _candidate, review = self.full_candidate(batch_id, review_id)
            if review['status'] != 'completed' and not allow_partial:
                raise ProjectError('尚有未校對範圍。請繼續未完成範圍，或選擇保留未完成處原文。')
        self.texts(batch_id)
        manifest = self.state
        batch = next(b for b in manifest['batches'] if b['id'] == batch_id)
        content = text.encode('utf-8')
        checksum = digest(content)
        files = []
        if checksum != batch['draft']['sha256']:
            batch.setdefault('draft_copies', []).append(dict(
                id=uuid.uuid4().hex, **deepcopy(batch['draft']), created_at=now(), label='儲存前文稿'))
            path = f'batches/{batch_id}/draft-{uuid.uuid4().hex}.txt'
            batch['draft'] = dict(path=path, sha256=checksum)
            batch['revision'] += 1
            files.append((path, content))
            if batch['kind'] == 'pdf':
                batch['pdf']['mapping_valid'] = False
        snapshot = next((s for s in reversed(batch.get('readings', []))
                         if s['sha256'] == checksum and s['revision'] == batch['revision']), None)
        if snapshot is None:
            identity = uuid.uuid4().hex
            snapshot = dict(id=identity, revision=batch['revision'], confirmed_at=now(),
                            path=f'batches/{batch_id}/reading-{identity}.txt', sha256=checksum,
                            review_id=review_id, partial_ai=bool(review_id and allow_partial))
            batch.setdefault('readings', []).append(snapshot)
            files.append((snapshot['path'], content))
        batch['current_reading'] = snapshot['id']
        batch.pop('workspace', None)
        self._commit(manifest, files)
        return deepcopy(snapshot)
