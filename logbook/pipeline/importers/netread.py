"""Read an HTTP response with a hard wall-clock limit.

urlopen(timeout=...) only limits each single socket read, so a server that keeps
trickling a few bytes (a busy Overpass mirror, a slow news site) can hold a request
open for hours - and with it the whole background update, so new layovers never
reached the diary. read() gives up once the whole download takes longer than `deadline`.
"""
import time


def read(r, deadline=90, limit=None):
    """Body of response `r`, at most `limit` bytes; TimeoutError after `deadline` seconds."""
    end = time.time() + deadline
    parts, got = [], 0
    while limit is None or got < limit:
        chunk = r.read(65536 if limit is None else min(65536, limit - got))
        if not chunk:
            break
        parts.append(chunk)
        got += len(chunk)
        if time.time() > end:
            raise TimeoutError(f'download took longer than {deadline}s: {getattr(r, "url", "")}')
    return b''.join(parts)
