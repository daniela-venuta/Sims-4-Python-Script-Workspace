import locale
def _tokenize(plural):
    for mo in re.finditer(_token_pattern, plural):
        kind = mo.lastgroup
        if kind == 'WHITESPACES':
            pass
        else:
            value = mo.group(kind)
            if kind == 'INVALID':
                raise ValueError('invalid token in plural form: %s' % value)
            yield value
    yield ''

def _error(value):
    if value:
        return ValueError('unexpected token in plural form: %s' % value)
    else:
        return ValueError('unexpected end of plural form')
