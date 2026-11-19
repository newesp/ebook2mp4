"""Local request reservations and server cooldowns, shared by all app processes."""
import asyncio
import hashlib
import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from contextvars import ContextVar

from .workflow import ProjectError

request_context = ContextVar('gemini_request_context', default=(None, None))


def stamp_after(seconds):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + seconds))


def scope(value, key):
    return hashlib.sha256((value['provider'] + '\0' + key + '\0' + value['model']).encode()).hexdigest()


@contextmanager
def database():
    from .voice import cache_path
    path = cache_path().parent / 'tts-usage.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    try:
        connection.execute('CREATE TABLE IF NOT EXISTS usage (scope TEXT PRIMARY KEY, next REAL, cooldown REAL, reason TEXT)')
        connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise ProjectError('無法保存服務限速與冷卻記錄，請檢查本機設定資料夾。') from None
    finally:
        connection.close()


def interval(value):
    """Account-specific RPM overrides; one second is only a conservative app default."""
    from .voice import cache_path
    path = cache_path().parent / 'tts-limits.json'
    try:
        limits = json.loads(path.read_bytes()) if path.exists() else {}
        default = 5 if value['provider'] == 'gemini-tts' else 60
        rpm = float(limits.get(value['provider'] + ':' + value['model'], {}).get('requests_per_minute', default))
        if not math.isfinite(rpm) or rpm <= 0:
            raise ValueError()
        return 60 / rpm
    except (OSError, ValueError, TypeError, AttributeError):
        raise ProjectError('tts-limits.json 的 requests_per_minute 必須為正數。') from None


async def before_request(value, key):
    if value['provider'] == 'gemini-tts':
        return await _gemini_before_request(value, key)
    identity, now = scope(value, key), time.time()
    spacing = interval(value)
    with database() as db:
        row = db.execute('SELECT next, cooldown, reason FROM usage WHERE scope=?', (identity,)).fetchone()
        if row and row[1] > now:
            stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row[1]))
            raise ProjectError(f'{row[2]} 冷卻尚未結束；預計 {stamp}（本機時間）後可重試。未送出文字。')
        start = max(now, row[0] if row else now)
        if start - now > 300:
            raise ProjectError('限速佇列等待超過 300 秒，請稍後續作或檢查 tts-limits.json。未送出文字。')
        db.execute('INSERT OR REPLACE INTO usage VALUES (?,?,?,?)', (identity, start + spacing, 0, ''))
    if start > now:
        await asyncio.sleep(start - now)
    # Another request can establish a cooldown while this reservation waits.
    with database() as db:
        row = db.execute('SELECT cooldown, reason FROM usage WHERE scope=?', (identity,)).fetchone()
        if row and row[0] > time.time():
            raise ProjectError(f'{row[1]} 服務仍在冷卻，未送出文字。')


async def _gemini_before_request(value, key):
    identity = scope(value, key)
    configured = interval(value)
    recovery_deadline, waiting = request_context.get()
    deadline = recovery_deadline or time.monotonic() + 1800
    shown = None
    while True:
        now = time.time()
        with database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS gemini_rate (scope TEXT PRIMARY KEY, spacing REAL, limited REAL)')
            row = db.execute('SELECT next, cooldown, reason FROM usage WHERE scope=?', (identity,)).fetchone()
            rate = db.execute('SELECT spacing, limited FROM gemini_rate WHERE scope=?', (identity,)).fetchone()
            db.execute('CREATE TABLE IF NOT EXISTS gemini_block (scope TEXT PRIMARY KEY, category TEXT)')
            blocked = db.execute('SELECT category FROM gemini_block WHERE scope=?', (identity,)).fetchone()
            if row and row[1] > now and (blocked or row[2] and not rate):
                raise ProjectError(f'{row[2]} 冷卻尚未結束；最早 {stamp_after(row[1]-now)}（本機時間）可再嘗試。')
            rate = db.execute('SELECT spacing, limited FROM gemini_rate WHERE scope=?', (identity,)).fetchone()
            spacing = max(configured, rate[0]) if rate and now - rate[1] < 600 else configured
            start = max(now, row[0], row[1]) if row else now
            delay = start - now
            if delay <= 0:
                if time.monotonic() >= deadline:
                    raise ProjectError('連續限流超過恢復上限，已停止自動重試。')
                db.execute('INSERT OR REPLACE INTO usage VALUES (?,?,?,?)',
                           (identity, now + spacing, row[1] if row else 0, row[2] if row else ''))
                return
        if time.monotonic() + delay >= deadline:
            raise ProjectError(f'服務要求長時間冷卻或限速等待超過恢復上限；最早 {stamp_after(delay)}（本機時間）可再嘗試。已停止自動重試。')
        if waiting and (shown is None or abs(start - shown) > 1):
            waiting(delay)
            shown = start
        # Recheck periodically: another process may extend the cooldown.
        await asyncio.sleep(min(delay, 1))


def record_limit(value, key, seconds, reason, *, rate_limited=True, category=None):
    identity = scope(value, key)
    with database() as db:
        row = db.execute('SELECT next, cooldown FROM usage WHERE scope=?', (identity,)).fetchone()
        db.execute('INSERT OR REPLACE INTO usage VALUES (?,?,?,?)',
                   (identity, row[0] if row else 0, max(time.time() + seconds, row[1] if row else 0), reason))
        if value['provider'] == 'gemini-tts' and rate_limited:
            db.execute('CREATE TABLE IF NOT EXISTS gemini_block (scope TEXT PRIMARY KEY, category TEXT)')
            if category in ('daily', 'billing'):
                db.execute('INSERT OR REPLACE INTO gemini_block VALUES (?,?)', (identity, category))
            else:
                db.execute('DELETE FROM gemini_block WHERE scope=?', (identity,))
            now = time.time()
            configured = interval(value)
            db.execute('CREATE TABLE IF NOT EXISTS gemini_rate (scope TEXT PRIMARY KEY, spacing REAL, limited REAL)')
            rate = db.execute('SELECT spacing, limited FROM gemini_rate WHERE scope=?', (identity,)).fetchone()
            current = max(configured, rate[0]) if rate and now - rate[1] < 600 else configured
            spacing = min(max(60, configured), current * 2)
            db.execute('INSERT OR REPLACE INTO gemini_rate VALUES (?,?,?)', (identity, spacing, now))


async def error_reason(response):
    """Classify bounded JSON without storing or displaying raw provider text."""
    data = bytearray()
    async for block in response.content.iter_chunked(4096):
        data.extend(block)
        if len(data) > 65536:
            return '請求過多或配額不足（服務回覆過大，無法判別）'
    try:
        payload = json.loads(data)
    except (ValueError, TypeError):
        return '請求過多或配額不足（服務未提供可辨識原因）'
    text = json.dumps(payload).lower()
    if any(word in text for word in ('perday', 'per_day', 'daily', 'quota_exceeded')):
        return '每日或期間配額已用盡，請檢查服務用量'
    if any(word in text for word in ('billing', 'credit', 'balance', 'spend cap')):
        return '帳務或用量支出限制，請檢查服務帳戶'
    if any(word in text for word in ('perminute', 'per_minute', 'rate_limit', 'concurrency', 'too_many_requests')):
        return '請求頻率或同時請求數超限'
    return '請求過多或配額不足（服務未提供可辨識原因）'


async def gemini_error(response):
    """Return a safe classification and optional google.rpc.RetryInfo delay."""
    data = bytearray()
    async for block in response.content.iter_chunked(4096):
        data.extend(block)
        if len(data) > 65536:
            return 'unknown', 0
    try:
        error = json.loads(data).get('error', {})
        if not isinstance(error, dict):
            return 'unknown', 0
    except (ValueError, TypeError, AttributeError):
        return 'unknown', 0
    fields = [str(error.get('message', ''))]
    retry = 0
    details = error.get('details', [])
    if not isinstance(details, list):
        details = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        kind = str(detail.get('@type', ''))
        if kind.endswith('google.rpc.RetryInfo'):
            match = re.fullmatch(r'(\d+(?:\.\d+)?)s', str(detail.get('retryDelay', '')))
            if match:
                value = float(match.group(1))
                if math.isfinite(value):
                    retry = max(retry, value)
        if kind.endswith('google.rpc.QuotaFailure'):
            violations = detail.get('violations', [])
            if isinstance(violations, list):
                for violation in violations:
                    if isinstance(violation, dict):
                        fields.extend(str(violation.get(name, '')) for name in
                                      ('quotaMetric', 'quotaId', 'description'))
    text = ' '.join(fields).lower()
    if any(word in text for word in ('billing', 'insufficient credit', 'insufficient balance', 'spend cap')):
        return 'billing', retry
    if any(word in text for word in ('perday', 'per_day', 'per day', 'daily')):
        return 'daily', retry
    if any(word in text for word in ('perminute', 'per_minute', 'per minute', 'rate_limit', 'rate limit', 'concurrency')):
        return 'temporary', retry
    return 'unknown', retry
