import enum_lib as enumimport sre_compileimport sre_parseimport functoolstry:
    import _locale
except ImportError:
    _locale = None__all__ = ['match', 'fullmatch', 'search', 'sub', 'subn', 'split', 'findall', 'finditer', 'compile', 'purge', 'template', 'escape', 'error', 'Pattern', 'Match', 'A', 'I', 'L', 'M', 'S', 'X', 'U', 'ASCII', 'IGNORECASE', 'LOCALE', 'MULTILINE', 'DOTALL', 'VERBOSE', 'UNICODE']__version__ = '2.2.1'
class RegexFlag(enum.IntFlag):
    ASCII = sre_compile.SRE_FLAG_ASCII
    IGNORECASE = sre_compile.SRE_FLAG_IGNORECASE
    LOCALE = sre_compile.SRE_FLAG_LOCALE
    UNICODE = sre_compile.SRE_FLAG_UNICODE
    MULTILINE = sre_compile.SRE_FLAG_MULTILINE
    DOTALL = sre_compile.SRE_FLAG_DOTALL
    VERBOSE = sre_compile.SRE_FLAG_VERBOSE
    A = ASCII
    I = IGNORECASE
    L = LOCALE
    U = UNICODE
    M = MULTILINE
    S = DOTALL
    X = VERBOSE
    TEMPLATE = sre_compile.SRE_FLAG_TEMPLATE
    T = TEMPLATE
    DEBUG = sre_compile.SRE_FLAG_DEBUG
globals().update(RegexFlag.__members__)error = sre_compile.error
def match(pattern, string, flags=0):
    return _compile(pattern, flags).match(string)

def fullmatch(pattern, string, flags=0):
    return _compile(pattern, flags).fullmatch(string)

def search(pattern, string, flags=0):
    return _compile(pattern, flags).search(string)

def sub(pattern, repl, string, count=0, flags=0):
    return _compile(pattern, flags).sub(repl, string, count)

def subn(pattern, repl, string, count=0, flags=0):
    return _compile(pattern, flags).subn(repl, string, count)

def split(pattern, string, maxsplit=0, flags=0):
    return _compile(pattern, flags).split(string, maxsplit)

def findall(pattern, string, flags=0):
    return _compile(pattern, flags).findall(string)

def finditer(pattern, string, flags=0):
    return _compile(pattern, flags).finditer(string)

def compile(pattern, flags=0):
    return _compile(pattern, flags)

def purge():
    _cache.clear()
    _compile_repl.cache_clear()

def template(pattern, flags=0):
    return _compile(pattern, flags | T)
_special_chars_map = {i: '\\' + chr(i) for i in b'()[]{}?*+-|^$\\.&~# \t\n\r\x0b\x0c'}
def escape(pattern):
    if isinstance(pattern, str):
        return pattern.translate(_special_chars_map)
    else:
        pattern = str(pattern, 'latin1')
        return pattern.translate(_special_chars_map).encode('latin1')
Pattern = type(sre_compile.compile('', 0))Match = type(sre_compile.compile('', 0).match(''))_cache = {}_MAXCACHE = 512
def _compile(pattern, flags):
    if isinstance(flags, RegexFlag):
        flags = flags.value
    try:
        return _cache[(type(pattern), pattern, flags)]
    except KeyError:
        pass
    if isinstance(pattern, Pattern):
        if flags:
            raise ValueError('cannot process flags argument with a compiled pattern')
        return pattern
    if not sre_compile.isstring(pattern):
        raise TypeError('first argument must be string or compiled pattern')
    p = sre_compile.compile(pattern, flags)
    if not flags & DEBUG:
        if len(_cache) >= _MAXCACHE:
            try:
                del _cache[next(iter(_cache))]
            except (StopIteration, RuntimeError, KeyError):
                pass
        _cache[(type(pattern), pattern, flags)] = p
    return p

@functools.lru_cache(_MAXCACHE)
def _compile_repl(repl, pattern):
    return sre_parse.parse_template(repl, pattern)

def _expand(pattern, match, template):
    template = sre_parse.parse_template(template, pattern)
    return sre_parse.expand_template(template, match)

def _subx(pattern, template):
    template = _compile_repl(template, pattern)
    if template[0] or len(template[1]) == 1:
        return template[1][0]

    def filter(match, template=template):
        return sre_parse.expand_template(template, match)

    return filter
import copyreg
def _pickle(p):
    return (_compile, (p.pattern, p.flags))
copyreg.pickle(Pattern, _pickle, _compile)
class Scanner:

    def __init__(self, lexicon, flags=0):
        from sre_constants import BRANCH, SUBPATTERN
        if isinstance(flags, RegexFlag):
            flags = flags.value
        self.lexicon = lexicon
        p = []
        s = sre_parse.Pattern()
        s.flags = flags
        for (phrase, action) in lexicon:
            gid = s.opengroup()
            p.append(sre_parse.SubPattern(s, [(SUBPATTERN, (gid, 0, 0, sre_parse.parse(phrase, flags)))]))
            s.closegroup(gid, p[-1])
        p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
        self.scanner = sre_compile.compile(p)

    def scan(self, string):
        result = []
        append = result.append
        match = self.scanner.scanner(string).match
        i = 0
        while True:
            m = match()
            if not m:
                break
            j = m.end()
            if i == j:
                break
            action = self.lexicon[m.lastindex - 1][1]
            if callable(action):
                self.match = m
                action = action(self, m.group())
            if action is not None:
                append(action)
            i = j
        return (result, string[i:])
