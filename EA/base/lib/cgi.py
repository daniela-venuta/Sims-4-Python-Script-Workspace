__version__ = '2.6'from io import StringIO, BytesIO, TextIOWrapperfrom collections.abc import Mappingimport sysimport osimport urllib.parsefrom email.parser import FeedParserfrom email.message import Messagefrom warnings import warnimport htmlimport localeimport tempfile__all__ = ['MiniFieldStorage', 'FieldStorage', 'parse', 'parse_qs', 'parse_qsl', 'parse_multipart', 'parse_header', 'test', 'print_exception', 'print_environ', 'print_form', 'print_directory', 'print_arguments', 'print_environ_usage', 'escape']logfile = ''logfp = None
def initlog(*allargs):
    global logfp, log
    if not logfp:
        try:
            logfp = open(logfile, 'a')
        except OSError:
            pass
    if not (logfile and logfp):
        log = nolog
    else:
        log = dolog
    log(*allargs)

def dolog(fmt, *args):
    logfp.write(fmt % args + '\n')

def nolog(*allargs):
    pass

def closelog():
    global logfile, logfp, log
    logfile = ''
    if logfp:
        logfp.close()
        logfp = None
    log = initlog
log = initlogmaxlen = 0
def parse(fp=None, environ=os.environ, keep_blank_values=0, strict_parsing=0):
    if fp is None:
        fp = sys.stdin
    if hasattr(fp, 'encoding'):
        encoding = fp.encoding
    else:
        encoding = 'latin-1'
    if isinstance(fp, TextIOWrapper):
        fp = fp.buffer
    if 'REQUEST_METHOD' not in environ:
        environ['REQUEST_METHOD'] = 'GET'
    if environ['REQUEST_METHOD'] == 'POST':
        (ctype, pdict) = parse_header(environ['CONTENT_TYPE'])
        if ctype == 'multipart/form-data':
            return parse_multipart(fp, pdict)
        if ctype == 'application/x-www-form-urlencoded':
            clength = int(environ['CONTENT_LENGTH'])
            if maxlen and clength > maxlen:
                raise ValueError('Maximum content length exceeded')
            qs = fp.read(clength).decode(encoding)
        else:
            qs = ''
        if 'QUERY_STRING' in environ:
            if qs:
                qs = qs + '&'
            qs = qs + environ['QUERY_STRING']
        elif sys.argv[1:]:
            if qs:
                qs = qs + '&'
            qs = qs + sys.argv[1]
        environ['QUERY_STRING'] = qs
    elif 'QUERY_STRING' in environ:
        qs = environ['QUERY_STRING']
    else:
        if sys.argv[1:]:
            qs = sys.argv[1]
        else:
            qs = ''
        environ['QUERY_STRING'] = qs
    return urllib.parse.parse_qs(qs, keep_blank_values, strict_parsing, encoding=encoding)

def parse_qs(qs, keep_blank_values=0, strict_parsing=0):
    warn('cgi.parse_qs is deprecated, use urllib.parse.parse_qs instead', DeprecationWarning, 2)
    return urllib.parse.parse_qs(qs, keep_blank_values, strict_parsing)

def parse_qsl(qs, keep_blank_values=0, strict_parsing=0):
    warn('cgi.parse_qsl is deprecated, use urllib.parse.parse_qsl instead', DeprecationWarning, 2)
    return urllib.parse.parse_qsl(qs, keep_blank_values, strict_parsing)

def parse_multipart(fp, pdict, encoding='utf-8', errors='replace'):
    boundary = pdict['boundary'].decode('ascii')
    ctype = 'multipart/form-data; boundary={}'.format(boundary)
    headers = Message()
    headers.set_type(ctype)
    headers['Content-Length'] = pdict['CONTENT-LENGTH']
    fs = FieldStorage(fp, headers=headers, encoding=encoding, errors=errors, environ={'REQUEST_METHOD': 'POST'})
    return {k: fs.getlist(k) for k in fs}

def _parseparam(s):
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]
