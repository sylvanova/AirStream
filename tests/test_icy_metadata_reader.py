import io

from services.icy_metadata_reader import (
    decode_metadata_block,
    parse_stream_title,
    iter_titles,
)


def _build_metadata_block(payload: bytes) -> bytes:
    """Encode a payload the way ICY does: 1 length byte (in 16-byte units), then padded payload."""
    length_units = (len(payload) + 15) // 16
    padded = payload.ljust(length_units * 16, b"\x00")
    return bytes([length_units]) + padded


def test_parse_stream_title_basic():
    assert parse_stream_title("StreamTitle='Tycho - A Walk';StreamUrl='';") == "Tycho - A Walk"


def test_parse_stream_title_no_title_returns_empty():
    assert parse_stream_title("StreamUrl='https://example.com';") == ""


def test_parse_stream_title_with_quotes_inside():
    # ICY uses single-quoted values; embedded quotes are rare but we accept the first ';' terminator.
    assert (
        parse_stream_title("StreamTitle='Hello, world';StreamUrl='';")
        == "Hello, world"
    )


def test_decode_metadata_block_utf8():
    raw = _build_metadata_block("StreamTitle='Björk - All Is Full of Love';".encode("utf-8"))
    assert decode_metadata_block(raw) == "Björk - All Is Full of Love"


def test_decode_metadata_block_latin1_fallback():
    # \xe9 is é in latin-1 but invalid UTF-8 on its own.
    raw = _build_metadata_block(b"StreamTitle='Caf\xe9 del Mar';")
    assert decode_metadata_block(raw) == "Café del Mar"


def test_decode_metadata_block_empty_length_byte():
    # Length byte 0 means no metadata in this interval.
    raw = b"\x00"
    assert decode_metadata_block(raw) == ""


def test_iter_titles_skips_audio_and_extracts_titles():
    metaint = 4
    audio_chunk = b"AAAA"
    block_one = _build_metadata_block(b"StreamTitle='Song A';")
    block_two_empty = b"\x00"
    block_three = _build_metadata_block(b"StreamTitle='Song B';")
    payload = audio_chunk + block_one + audio_chunk + block_two_empty + audio_chunk + block_three
    stream = io.BytesIO(payload)

    titles = list(iter_titles(stream, metaint=metaint))

    assert titles == ["Song A", "", "Song B"]


def test_iter_titles_handles_truncated_stream():
    # When the stream ends mid-block, iter_titles just stops cleanly.
    metaint = 4
    payload = b"AAAA" + b"\x02StreamTitle"  # length says 32 bytes, only 11 follow
    stream = io.BytesIO(payload)

    # No exception, no spurious yield.
    assert list(iter_titles(stream, metaint=metaint)) == []
