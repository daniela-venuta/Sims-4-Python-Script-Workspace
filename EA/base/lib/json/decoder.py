import re
    from _json import scanstring as c_scanstring
except ImportError:
    c_scanstring = None
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

def _decode_uXXXX(s, pos):
    esc = s[pos + 1:pos + 5]
    if esc[1] not in 'xX':
        try:
            return int(esc, 16)
        except ValueError:
            pass
    msg = 'Invalid \\uXXXX escape'
    raise JSONDecodeError(msg, s, pos)
