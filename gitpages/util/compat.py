_ENCODING = 'utf-8'


def _text_to_bytes(text):
    return text.encode('utf-8')


def _bytes_to_text(bytestring):
    return bytestring.decode('utf-8')
