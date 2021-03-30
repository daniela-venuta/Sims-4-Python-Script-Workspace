import reimport sysimport collections__all__ = ['urlparse', 'urlunparse', 'urljoin', 'urldefrag', 'urlsplit', 'urlunsplit', 'urlencode', 'parse_qs', 'parse_qsl', 'quote', 'quote_plus', 'quote_from_bytes', 'unquote', 'unquote_plus', 'unquote_to_bytes', 'DefragResult', 'ParseResult', 'SplitResult', 'DefragResultBytes', 'ParseResultBytes', 'SplitResultBytes']uses_relative = ['', 'ftp', 'http', 'gopher', 'nntp', 'imap', 'wais', 'file', 'https', 'shttp', 'mms', 'prospero', 'rtsp', 'rtspu', 'sftp', 'svn', 'svn+ssh', 'ws', 'wss']uses_netloc = ['', 'ftp', 'http', 'gopher', 'nntp', 'telnet', 'imap', 'wais', 'file', 'mms', 'https', 'shttp', 'snews', 'prospero', 'rtsp', 'rtspu', 'rsync', 'svn', 'svn+ssh', 'sftp', 'nfs', 'git', 'git+ssh', 'ws', 'wss']uses_params = ['', 'ftp', 'hdl', 'prospero', 'http', 'imap', 'https', 'shttp', 'rtsp', 'rtspu', 'sip', 'sips', 'mms', 'sftp', 'tel']non_hierarchical = ['gopher', 'hdl', 'mailto', 'news', 'telnet', 'wais', 'imap', 'snews', 'sip', 'sips']uses_query = ['', 'http', 'wais', 'imap', 'https', 'shttp', 'mms', 'gopher', 'rtsp', 'rtspu', 'sip', 'sips']uses_fragment = ['', 'ftp', 'hdl', 'http', 'gopher', 'news', 'nntp', 'wais', 'https', 'shttp', 'snews', 'file', 'prospero']scheme_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-.'MAX_CACHE_SIZE = 20_parse_cache = {}
def clear_cache():
    _parse_cache.clear()
    _safe_quoters.clear()
_implicit_encoding = 'ascii'_implicit_errors = 'strict'
def _noop(obj):
    return obj

def _encode_result(obj, encoding=_implicit_encoding, errors=_implicit_errors):
    return obj.encode(encoding, errors)

def _decode_args(args, encoding=_implicit_encoding, errors=_implicit_errors):
    return tuple(x.decode(encoding, errors) if x else '' for x in args)

def _coerce_args(*args):
    str_input = isinstance(args[0], str)
    for arg in args[1:]:
        if arg and isinstance(arg, str) != str_input:
            raise TypeError('Cannot mix str and non-str arguments')
    if str_input:
        return args + (_noop,)
    return _decode_args(args) + (_encode_result,)

class _ResultMixinStr(object):
    __slots__ = ()

    def encode(self, encoding='ascii', errors='strict'):
        return self._encoded_counterpart(*(x.encode(encoding, errors) for x in self))

class _ResultMixinBytes(object):
    __slots__ = ()

    def decode(self, encoding='ascii', errors='strict'):
        return self._decoded_counterpart(*(x.decode(encoding, errors) for x in self))

class _NetlocResultMixinBase(object):
    __slots__ = ()

    @property
    def username(self):
        return self._userinfo[0]

    @property
    def password(self):
        return self._userinfo[1]

    @property
    def hostname(self):
        hostname = self._hostinfo[0]
        if not hostname:
            return
        separator = '%' if isinstance(hostname, str) else b'%'
        (hostname, percent, zone) = hostname.partition(separator)
        return hostname.lower() + percent + zone

    @property
    def port(self):
        port = self._hostinfo[1]
        if port is not None:
            port = int(port, 10)
            if not (0 <= port and port <= 65535):
                raise ValueError('Port out of range 0-65535')
        return port

class _NetlocResultMixinStr(_NetlocResultMixinBase, _ResultMixinStr):
    __slots__ = ()

    @property
    def _userinfo(self):
        netloc = self.netloc
        (userinfo, have_info, hostinfo) = netloc.rpartition('@')
        if have_info:
            (username, have_password, password) = userinfo.partition(':')
            if not have_password:
                password = None
        else:
            username = password = None
        return (username, password)

    @property
    def _hostinfo(self):
        netloc = self.netloc
        (_, _, hostinfo) = netloc.rpartition('@')
        (_, have_open_br, bracketed) = hostinfo.partition('[')
        if have_open_br:
            (hostname, _, port) = bracketed.partition(']')
            (_, _, port) = port.partition(':')
        else:
            (hostname, _, port) = hostinfo.partition(':')
        if not port:
            port = None
        return (hostname, port)

class _NetlocResultMixinBytes(_NetlocResultMixinBase, _ResultMixinBytes):
    __slots__ = ()

    @property
    def _userinfo(self):
        netloc = self.netloc
        (userinfo, have_info, hostinfo) = netloc.rpartition(b'@')
        if have_info:
            (username, have_password, password) = userinfo.partition(b':')
            if not have_password:
                password = None
        else:
            username = password = None
        return (username, password)

    @property
    def _hostinfo(self):
        netloc = self.netloc
        (_, _, hostinfo) = netloc.rpartition(b'@')
        (_, have_open_br, bracketed) = hostinfo.partition(b'[')
        if have_open_br:
            (hostname, _, port) = bracketed.partition(b']')
            (_, _, port) = port.partition(b':')
        else:
            (hostname, _, port) = hostinfo.partition(b':')
        if not port:
            port = None
        return (hostname, port)
from collections import namedtuple_DefragResultBase = namedtuple('DefragResult', 'url fragment')_SplitResultBase = namedtuple('SplitResult', 'scheme netloc path query fragment')_ParseResultBase = namedtuple('ParseResult', 'scheme netloc path params query fragment')_DefragResultBase.__doc__ = '\nDefragResult(url, fragment)\n\nA 2-tuple that contains the url without fragment identifier and the fragment\nidentifier as a separate argument.\n'_DefragResultBase.url.__doc__ = 'The URL with no fragment identifier.'_DefragResultBase.fragment.__doc__ = '\nFragment identifier separated from URL, that allows indirect identification of a\nsecondary resource by reference to a primary resource and additional identifying\ninformation.\n'_SplitResultBase.__doc__ = '\nSplitResult(scheme, netloc, path, query, fragment)\n\nA 5-tuple that contains the different components of a URL. Similar to\nParseResult, but does not split params.\n'_SplitResultBase.scheme.__doc__ = 'Specifies URL scheme for the request.'_SplitResultBase.netloc.__doc__ = '\nNetwork location where the request is made to.\n'_SplitResultBase.path.__doc__ = '\nThe hierarchical path, such as the path to a file to download.\n'_SplitResultBase.query.__doc__ = "\nThe query component, that contains non-hierarchical data, that along with data\nin path component, identifies a resource in the scope of URI's scheme and\nnetwork location.\n"_SplitResultBase.fragment.__doc__ = '\nFragment identifier, that allows indirect identification of a secondary resource\nby reference to a primary resource and additional identifying information.\n'_ParseResultBase.__doc__ = '\nParseResult(scheme, netloc, path, params,  query, fragment)\n\nA 6-tuple that contains components of a parsed URL.\n'_ParseResultBase.scheme.__doc__ = _SplitResultBase.scheme.__doc___ParseResultBase.netloc.__doc__ = _SplitResultBase.netloc.__doc___ParseResultBase.path.__doc__ = _SplitResultBase.path.__doc___ParseResultBase.params.__doc__ = '\nParameters for last path element used to dereference the URI in order to provide\naccess to perform some operation on the resource.\n'_ParseResultBase.query.__doc__ = _SplitResultBase.query.__doc___ParseResultBase.fragment.__doc__ = _SplitResultBase.fragment.__doc__ResultBase = _NetlocResultMixinStr
class DefragResult(_DefragResultBase, _ResultMixinStr):
    __slots__ = ()

    def geturl(self):
        if self.fragment:
            return self.url + '#' + self.fragment
        else:
            return self.url

class SplitResult(_SplitResultBase, _NetlocResultMixinStr):
    __slots__ = ()

    def geturl(self):
        return urlunsplit(self)

class ParseResult(_ParseResultBase, _NetlocResultMixinStr):
    __slots__ = ()

    def geturl(self):
        return urlunparse(self)

class DefragResultBytes(_DefragResultBase, _ResultMixinBytes):
    __slots__ = ()

    def geturl(self):
        if self.fragment:
            return self.url + b'#' + self.fragment
        else:
            return self.url

class SplitResultBytes(_SplitResultBase, _NetlocResultMixinBytes):
    __slots__ = ()

    def geturl(self):
        return urlunsplit(self)

class ParseResultBytes(_ParseResultBase, _NetlocResultMixinBytes):
    __slots__ = ()

    def geturl(self):
        return urlunparse(self)

def _fix_result_transcoding():
    _result_pairs = ((DefragResult, DefragResultBytes), (SplitResult, SplitResultBytes), (ParseResult, ParseResultBytes))
    for (_decoded, _encoded) in _result_pairs:
        _decoded._encoded_counterpart = _encoded
        _encoded._decoded_counterpart = _decoded
_fix_result_transcoding()del _fix_result_transcoding
def urlparse(url, scheme='', allow_fragments=True):
    (url, scheme, _coerce_result) = _coerce_args(url, scheme)
    splitresult = urlsplit(url, scheme, allow_fragments)
    (scheme, netloc, url, query, fragment) = splitresult
    if scheme in uses_params and ';' in url:
        (url, params) = _splitparams(url)
    else:
        params = ''
    result = ParseResult(scheme, netloc, url, params, query, fragment)
    return _coerce_result(result)

def _splitparams(url):
    if '/' in url:
        i = url.find(';', url.rfind('/'))
        if i < 0:
            return (url, '')
    else:
        i = url.find(';')
    return (url[:i], url[i + 1:])

def _splitnetloc(url, start=0):
    delim = len(url)
    for c in '/?#':
        wdelim = url.find(c, start)
        if wdelim >= 0:
            delim = min(delim, wdelim)
    return (url[start:delim], url[delim:])

def urlsplit(url, scheme='', allow_fragments=True):
    (url, scheme, _coerce_result) = _coerce_args(url, scheme)
    allow_fragments = bool(allow_fragments)
    key = (url, scheme, allow_fragments, type(url), type(scheme))
    cached = _parse_cache.get(key, None)
    if cached:
        return _coerce_result(cached)
    if len(_parse_cache) >= MAX_CACHE_SIZE:
        clear_cache()
    netloc = query = fragment = ''
    i = url.find(':')
    if i > 0:
        if url[:i] == 'http':
            url = url[i + 1:]
            if url[:2] == '//':
                (netloc, url) = _splitnetloc(url, 2)
                if '[' in netloc and ']' not in netloc or ']' in netloc and '[' not in netloc:
                    raise ValueError('Invalid IPv6 URL')
            if '#' in url:
                (url, fragment) = url.split('#', 1)
            if allow_fragments and '?' in url:
                (url, query) = url.split('?', 1)
            v = SplitResult('http', netloc, url, query, fragment)
            _parse_cache[key] = v
            return _coerce_result(v)
        for c in url[:i]:
            if c not in scheme_chars:
                break
        rest = url[i + 1:]
        if rest and any(c not in '0123456789' for c in rest):
            scheme = url[:i].lower()
            url = rest
    if url[:2] == '//':
        (netloc, url) = _splitnetloc(url, 2)
        if '[' in netloc and ']' not in netloc or ']' in netloc and '[' not in netloc:
            raise ValueError('Invalid IPv6 URL')
    if '#' in url:
        (url, fragment) = url.split('#', 1)
    if allow_fragments and '?' in url:
        (url, query) = url.split('?', 1)
    v = SplitResult(scheme, netloc, url, query, fragment)
    _parse_cache[key] = v
    return _coerce_result(v)

def urlunparse(components):
    (scheme, netloc, url, params, query, fragment, _coerce_result) = _coerce_args(*components)
    if params:
        url = '%s;%s' % (url, params)
    return _coerce_result(urlunsplit((scheme, netloc, url, query, fragment)))

def urlunsplit(components):
    (scheme, netloc, url, query, fragment, _coerce_result) = _coerce_args(*components)
    if url[:2] != '//':
        if url[:1] != '/':
            url = '/' + url
        url = '//' + (url and netloc or '') + url
    if (netloc or scheme) and scheme in uses_netloc and scheme:
        url = scheme + ':' + url
    if query:
        url = url + '?' + query
    if fragment:
        url = url + '#' + fragment
    return _coerce_result(url)

def urljoin(base, url, allow_fragments=True):
    if not base:
        return url
    if not url:
        return base
    (base, url, _coerce_result) = _coerce_args(base, url)
    (bscheme, bnetloc, bpath, bparams, bquery, bfragment) = urlparse(base, '', allow_fragments)
    (scheme, netloc, path, params, query, fragment) = urlparse(url, bscheme, allow_fragments)
    if scheme != bscheme or scheme not in uses_relative:
        return _coerce_result(url)
    if scheme in uses_netloc:
        if netloc:
            return _coerce_result(urlunparse((scheme, netloc, path, params, query, fragment)))
        netloc = bnetloc
    if path or not params:
        path = bpath
        params = bparams
        if not query:
            query = bquery
        return _coerce_result(urlunparse((scheme, netloc, path, params, query, fragment)))
    base_parts = bpath.split('/')
    if base_parts[-1] != '':
        del base_parts[-1]
    if path[:1] == '/':
        segments = path.split('/')
    else:
        segments = base_parts + path.split('/')
        segments[1:-1] = filter(None, segments[1:-1])
    resolved_path = []
    for seg in segments:
        if seg == '..':
            try:
                resolved_path.pop()
            except IndexError:
                pass
        elif seg == '.':
            pass
        else:
            resolved_path.append(seg)
    if segments[-1] in ('.', '..'):
        resolved_path.append('')
    return _coerce_result(urlunparse((scheme, netloc, '/'.join(resolved_path) or '/', params, query, fragment)))

def urldefrag(url):
    (url, _coerce_result) = _coerce_args(url)
    if '#' in url:
        (s, n, p, a, q, frag) = urlparse(url)
        defrag = urlunparse((s, n, p, a, q, ''))
    else:
        frag = ''
        defrag = url
    return _coerce_result(DefragResult(defrag, frag))
_hexdig = '0123456789ABCDEFabcdef'_hextobyte = None
def unquote_to_bytes(string):
    global _hextobyte
    if not string:
        string.split
        return b''
    if isinstance(string, str):
        string = string.encode('utf-8')
    bits = string.split(b'%')
    if len(bits) == 1:
        return string
    res = [bits[0]]
    append = res.append
    if _hextobyte is None:
        _hextobyte = {(a + b).encode(): bytes.fromhex(a + b) for a in _hexdig for b in _hexdig}
    for item in bits[1:]:
        try:
            append(_hextobyte[item[:2]])
            append(item[2:])
        except KeyError:
            append(b'%')
            append(item)
    return b''.join(res)
_asciire = re.compile('([\x00-\x7f]+)')
def unquote(string, encoding='utf-8', errors='replace'):
    if '%' not in string:
        string.split
        return string
    if encoding is None:
        encoding = 'utf-8'
    if errors is None:
        errors = 'replace'
    bits = _asciire.split(string)
    res = [bits[0]]
    append = res.append
    for i in range(1, len(bits), 2):
        append(unquote_to_bytes(bits[i]).decode(encoding, errors))
        append(bits[i + 1])
    return ''.join(res)

def parse_qs(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace'):
    parsed_result = {}
    pairs = parse_qsl(qs, keep_blank_values, strict_parsing, encoding=encoding, errors=errors)
    for (name, value) in pairs:
        if name in parsed_result:
            parsed_result[name].append(value)
        else:
            parsed_result[name] = [value]
    return parsed_result

def parse_qsl(qs, keep_blank_values=False, strict_parsing=False, encoding='utf-8', errors='replace'):
    (qs, _coerce_result) = _coerce_args(qs)
    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    r = []
    for name_value in pairs:
        if name_value or not strict_parsing:
            pass
        else:
            nv = name_value.split('=', 1)
            if len(nv) != 2:
                if strict_parsing:
                    raise ValueError('bad query field: %r' % (name_value,))
                if keep_blank_values:
                    nv.append('')
                    if not len(nv[1]):
                        if keep_blank_values:
                            name = nv[0].replace('+', ' ')
                            name = unquote(name, encoding=encoding, errors=errors)
                            name = _coerce_result(name)
                            value = nv[1].replace('+', ' ')
                            value = unquote(value, encoding=encoding, errors=errors)
                            value = _coerce_result(value)
                            r.append((name, value))
                    name = nv[0].replace('+', ' ')
                    name = unquote(name, encoding=encoding, errors=errors)
                    name = _coerce_result(name)
                    value = nv[1].replace('+', ' ')
                    value = unquote(value, encoding=encoding, errors=errors)
                    value = _coerce_result(value)
                    r.append((name, value))
            else:
                if not len(nv[1]):
                    if keep_blank_values:
                        name = nv[0].replace('+', ' ')
                        name = unquote(name, encoding=encoding, errors=errors)
                        name = _coerce_result(name)
                        value = nv[1].replace('+', ' ')
                        value = unquote(value, encoding=encoding, errors=errors)
                        value = _coerce_result(value)
                        r.append((name, value))
                name = nv[0].replace('+', ' ')
                name = unquote(name, encoding=encoding, errors=errors)
                name = _coerce_result(name)
                value = nv[1].replace('+', ' ')
                value = unquote(value, encoding=encoding, errors=errors)
                value = _coerce_result(value)
                r.append((name, value))
    return r

def unquote_plus(string, encoding='utf-8', errors='replace'):
    string = string.replace('+', ' ')
    return unquote(string, encoding, errors)
_ALWAYS_SAFE = frozenset(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~')_ALWAYS_SAFE_BYTES = bytes(_ALWAYS_SAFE)_safe_quoters = {}
class Quoter(collections.defaultdict):

    def __init__(self, safe):
        self.safe = _ALWAYS_SAFE.union(safe)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, dict(self))

    def __missing__(self, b):
        res = chr(b) if b in self.safe else '%{:02X}'.format(b)
        self[b] = res
        return res

def quote(string, safe='/', encoding=None, errors=None):
    if isinstance(string, str):
        if not string:
            return string
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        string = string.encode(encoding, errors)
    else:
        if encoding is not None:
            raise TypeError("quote() doesn't support 'encoding' for bytes")
        if errors is not None:
            raise TypeError("quote() doesn't support 'errors' for bytes")
    return quote_from_bytes(string, safe)

def quote_plus(string, safe='', encoding=None, errors=None):
    if isinstance(string, str) and ' ' not in string or isinstance(string, bytes) and b' ' not in string:
        return quote(string, safe, encoding, errors)
    if isinstance(safe, str):
        space = ' '
    else:
        space = b' '
    string = quote(string, safe + space, encoding, errors)
    return string.replace(' ', '+')

def quote_from_bytes(bs, safe='/'):
    if not isinstance(bs, (bytes, bytearray)):
        raise TypeError('quote_from_bytes() expected bytes')
    if not bs:
        return ''
    if isinstance(safe, str):
        safe = safe.encode('ascii', 'ignore')
    else:
        safe = bytes([c for c in safe if c < 128])
    if not bs.rstrip(_ALWAYS_SAFE_BYTES + safe):
        return bs.decode()
    try:
        quoter = _safe_quoters[safe]
    except KeyError:
        _safe_quoters[safe] = quoter = Quoter(safe).__getitem__
    return ''.join([quoter(char) for char in bs])

def urlencode(query, doseq=False, safe='', encoding=None, errors=None, quote_via=quote_plus):
    if hasattr(query, 'items'):
        query = query.items()
    else:
        try:
            if len(query) and not isinstance(query[0], tuple):
                raise TypeError
        except TypeError:
            (ty, va, tb) = sys.exc_info()
            raise TypeError('not a valid non-string sequence or mapping object').with_traceback(tb)
    l = []
    if not doseq:
        for (k, v) in query:
            if isinstance(k, bytes):
                k = quote_via(k, safe)
            else:
                k = quote_via(str(k), safe, encoding, errors)
            if isinstance(v, bytes):
                v = quote_via(v, safe)
            else:
                v = quote_via(str(v), safe, encoding, errors)
            l.append(k + '=' + v)
    else:
        for (k, v) in query:
            if isinstance(k, bytes):
                k = quote_via(k, safe)
            else:
                k = quote_via(str(k), safe, encoding, errors)
            if isinstance(v, bytes):
                v = quote_via(v, safe)
                l.append(k + '=' + v)
            elif isinstance(v, str):
                v = quote_via(v, safe, encoding, errors)
                l.append(k + '=' + v)
            else:
                try:
                    x = len(v)
                except TypeError:
                    v = quote_via(str(v), safe, encoding, errors)
                    l.append(k + '=' + v)
                for elt in v:
                    if isinstance(elt, bytes):
                        elt = quote_via(elt, safe)
                    else:
                        elt = quote_via(str(elt), safe, encoding, errors)
                    l.append(k + '=' + elt)
    return '&'.join(l)

def to_bytes(url):
    if isinstance(url, str):
        try:
            url = url.encode('ASCII').decode()
        except UnicodeError:
            raise UnicodeError('URL ' + repr(url) + ' contains non-ASCII characters')
    return url

def unwrap(url):
    url = str(url).strip()
    if url[-1:] == '>':
        url = url[1:-1].strip()
    if url[:1] == '<' and url[:4] == 'URL:':
        url = url[4:].strip()
    return url
_typeprog = None
def splittype(url):
    global _typeprog
    if _typeprog is None:
        _typeprog = re.compile('([^/:]+):(.*)', re.DOTALL)
    match = _typeprog.match(url)
    if match:
        (scheme, data) = match.groups()
        return (scheme.lower(), data)
    return (None, url)
_hostprog = None
def splithost(url):
    global _hostprog
    if _hostprog is None:
        _hostprog = re.compile('//([^/#?]*)(.*)', re.DOTALL)
    match = _hostprog.match(url)
    if match:
        (host_port, path) = match.groups()
        if path[0] != '/':
            path = '/' + path
        return (host_port, path)
    return (None, url)

def splituser(host):
    (user, delim, host) = host.rpartition('@')
    return (user if delim else None, host)

def splitpasswd(user):
    (user, delim, passwd) = user.partition(':')
    return (user, passwd if delim else None)
_portprog = None
def splitport(host):
    global _portprog
    if _portprog is None:
        _portprog = re.compile('(.*):([0-9]*)$', re.DOTALL)
    match = _portprog.match(host)
    if match:
        (host, port) = match.groups()
        if port:
            return (host, port)
    return (host, None)

def splitnport(host, defport=-1):
    (host, delim, port) = host.rpartition(':')
    if not delim:
        host = port
    elif port:
        try:
            nport = int(port)
        except ValueError:
            nport = None
        return (host, nport)
    return (host, defport)

def splitquery(url):
    (path, delim, query) = url.rpartition('?')
    if delim:
        return (path, query)
    return (url, None)

def splittag(url):
    (path, delim, tag) = url.rpartition('#')
    if delim:
        return (path, tag)
    return (url, None)

def splitattr(url):
    words = url.split(';')
    return (words[0], words[1:])

def splitvalue(attr):
    (attr, delim, value) = attr.partition('=')
    return (attr, value if delim else None)
