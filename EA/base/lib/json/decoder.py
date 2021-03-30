import refrom json import scannertry:
    from _json import scanstring as c_scanstring
except ImportError:
    c_scanstring = None__all__ = ['JSONDecoder', 'JSONDecodeError']FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALLNaN = float('nan')PosInf = float('inf')NegInf = float('-inf')
class JSONDecodeError(ValueError):

    def __init__(self, msg, doc, pos):
        lineno = doc.count('\n', 0, pos) + 1
        colno = pos - doc.rfind('\n', 0, pos)
        errmsg = '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
        ValueError.__init__(self, errmsg)
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = lineno
        self.colno = colno

    def __reduce__(self):
        return (self.__class__, (self.msg, self.doc, self.pos))
_CONSTANTS = {'-Infinity': NegInf, 'Infinity': PosInf, 'NaN': NaN}STRINGCHUNK = re.compile('(.*?)(["\\\\\\x00-\\x1f])', FLAGS)BACKSLASH = {'"': '"', '\\': '\\', '/': '/', 'b': '\x08', 'f': '\x0c', 'n': '\n', 'r': '\r', 't': '\t'}
def _decode_uXXXX(s, pos):
    esc = s[pos + 1:pos + 5]
    if esc[1] not in 'xX':
        try:
            return int(esc, 16)
        except ValueError:
            pass
    msg = 'Invalid \\uXXXX escape'
    raise JSONDecodeError(msg, s, pos)
