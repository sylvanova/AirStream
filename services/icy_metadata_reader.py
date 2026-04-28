"""ICY/Shoutcast in-stream metadata parser.

This module contains only the byte-level parsing logic. The Qt-thread
worker that drives it is added in a separate task and lives in the
same file (we'll grow it in place).

ICY format reminder:
  - Server response includes header `icy-metaint: <N>`.
  - Stream alternates: N audio bytes, 1 length byte, length*16 metadata bytes, N audio bytes, ...
  - Metadata payload is text like:  StreamTitle='Artist - Title';StreamUrl='...';
"""

from __future__ import annotations

import re
from typing import BinaryIO, Iterator

# Match StreamTitle='...' up to the next ';'.
_TITLE_RE = re.compile(r"StreamTitle='([^;]*)';")


def parse_stream_title(metadata_text: str) -> str:
    """Extract the StreamTitle value from a decoded metadata payload."""
    m = _TITLE_RE.search(metadata_text)
    if not m:
        return ""
    return m.group(1).strip()


def decode_metadata_block(block: bytes) -> str:
    """Decode a length-prefixed metadata block to its StreamTitle.

    The block starts with a single byte whose value is the metadata
    length in 16-byte units. Returns "" when the block is empty or the
    block contains no StreamTitle.
    """
    if not block:
        return ""
    length_units = block[0]
    if length_units == 0:
        return ""
    payload = block[1 : 1 + length_units * 16].rstrip(b"\x00")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("latin-1", errors="replace")
    return parse_stream_title(text)


def iter_titles(stream: BinaryIO, metaint: int) -> Iterator[str]:
    """Yield StreamTitle strings as they arrive on an ICY-enabled stream.

    The caller is responsible for opening the connection with
    `Icy-MetaData: 1` and reading `icy-metaint` from the headers.

    Yields empty strings for empty metadata blocks (so callers can
    deduplicate using a single 'last seen' variable). Stops iterating
    when the stream is closed or truncated mid-block.
    """
    while True:
        # Discard the audio chunk; we don't decode audio here.
        audio = _read_exact(stream, metaint)
        if audio is None:
            return

        length_byte = stream.read(1)
        if not length_byte:
            return
        length_units = length_byte[0]
        if length_units == 0:
            yield ""
            continue

        meta_bytes = _read_exact(stream, length_units * 16)
        if meta_bytes is None:
            return

        yield decode_metadata_block(length_byte + meta_bytes)


def _read_exact(stream: BinaryIO, n: int) -> bytes | None:
    """Read exactly n bytes, returning None on EOF / truncation."""
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
