_ENCODING = 'utf-8'


def _text_to_bytes(text):
    return text.encode(_ENCODING)


def _bytes_to_text(bytestring):
    return bytestring.decode(_ENCODING)
