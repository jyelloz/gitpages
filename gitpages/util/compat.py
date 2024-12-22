_ENCODING = 'utf-8'


def _text_to_bytes(text: str) -> bytes:
    return text.encode(_ENCODING)


def _bytes_to_text(bytestring: bytes) -> str:
    return bytestring.decode(_ENCODING)


def utcnow():
    from datetime import datetime, UTC
    return datetime.now(UTC)
