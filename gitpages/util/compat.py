_ENCODING = 'utf-8'


def _text_to_bytes(text: str) -> bytearray:
    return text.encode(_ENCODING)


def _bytes_to_text(bytestring: bytearray) -> str:
    return bytestring.decode(_ENCODING)
