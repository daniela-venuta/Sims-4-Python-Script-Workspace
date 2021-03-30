import base64import bisectimport emailimport hashlibimport http.clientimport ioimport osimport posixpathimport reimport socketimport stringimport sysimport timeimport tempfileimport contextlibimport warningsfrom urllib.error import URLError, HTTPError, ContentTooShortErrorfrom urllib.parse import urlparse, urlsplit, urljoin, unwrap, quote, unquote, splittype, splithost, splitport, splituser, splitpasswd, splitattr, splitquery, splitvalue, splittag, to_bytes, unquote_to_bytes, urlunparsefrom urllib.response import addinfourl, addclosehooktry:
    import ssl
except ImportError:
    _have_ssl = False_have_ssl = True__all__ = ['Request', 'OpenerDirector', 'BaseHandler', 'HTTPDefaultErrorHandler', 'HTTPRedirectHandler', 'HTTPCookieProcessor', 'ProxyHandler', 'HTTPPasswordMgr', 'HTTPPasswordMgrWithDefaultRealm', 'HTTPPasswordMgrWithPriorAuth', 'AbstractBasicAuthHandler', 'HTTPBasicAuthHandler', 'ProxyBasicAuthHandler', 'AbstractDigestAuthHandler', 'HTTPDigestAuthHandler', 'ProxyDigestAuthHandler', 'HTTPHandler', 'FileHandler', 'FTPHandler', 'CacheFTPHandler', 'DataHandler', 'UnknownHandler', 'HTTPErrorProcessor', 'urlopen', 'install_opener', 'build_opener', 'pathname2url', 'url2pathname', 'getproxies', 'urlretrieve', 'urlcleanup', 'URLopener', 'FancyURLopener']__version__ = '%d.%d' % sys.version_info[:2]_opener = None
def urlopen(url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, *, cafile=None, capath=None, cadefault=False, context=None):
    global _opener
    if cafile or capath or cadefault:
        import warnings
        warnings.warn('cafile, cpath and cadefault are deprecated, use a custom context instead.', DeprecationWarning, 2)
        if context is not None:
            raise ValueError("You can't pass both context and any of cafile, capath, and cadefault")
        if not _have_ssl:
            raise ValueError('SSL support not available')
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile, capath=capath)
        https_handler = HTTPSHandler(context=context)
        opener = build_opener(https_handler)
    elif context:
        https_handler = HTTPSHandler(context=context)
        opener = build_opener(https_handler)
    elif _opener is None:
        _opener = opener = build_opener()
    else:
        opener = _opener
    return opener.open(url, data, timeout)

def install_opener(opener):
    global _opener
    _opener = opener
_url_tempfiles = []
def urlretrieve(url, filename=None, reporthook=None, data=None):
    (url_type, path) = splittype(url)
    with contextlib.closing(urlopen(url, data)) as fp:
        headers = fp.info()
        if url_type == 'file' and not filename:
            return (os.path.normpath(path), headers)
        if filename:
            tfp = open(filename, 'wb')
        else:
            tfp = tempfile.NamedTemporaryFile(delete=False)
            filename = tfp.name
            _url_tempfiles.append(filename)
        with tfp:
            result = (filename, headers)
            bs = 8192
            size = -1
            read = 0
            blocknum = 0
            if 'content-length' in headers:
                size = int(headers['Content-Length'])
            if reporthook:
                reporthook(blocknum, bs, size)
            while True:
                block = fp.read(bs)
                if not block:
                    break
                read += len(block)
                tfp.write(block)
                blocknum += 1
                if reporthook:
                    reporthook(blocknum, bs, size)
    if size >= 0 and read < size:
        raise ContentTooShortError('retrieval incomplete: got only %i out of %i bytes' % (read, size), result)
    return result

def urlcleanup():
    global _opener
    for temp_file in _url_tempfiles:
        try:
            os.unlink(temp_file)
        except OSError:
            pass
    del _url_tempfiles[:]
    if _opener:
        _opener = None
_cut_port_re = re.compile(':\\d+$', re.ASCII)
def request_host(request):
    url = request.full_url
    host = urlparse(url)[1]
    if host == '':
        host = request.get_header('Host', '')
    host = _cut_port_re.sub('', host, 1)
    return host.lower()

class Request:

    def __init__(self, url, data=None, headers={}, origin_req_host=None, unverifiable=False, method=None):
        self.full_url = url
        self.headers = {}
        self.unredirected_hdrs = {}
        self._data = None
        self.data = data
        self._tunnel_host = None
        for (key, value) in headers.items():
            self.add_header(key, value)
        if origin_req_host is None:
            origin_req_host = request_host(self)
        self.origin_req_host = origin_req_host
        self.unverifiable = unverifiable
        if method:
            self.method = method

    @property
    def full_url(self):
        if self.fragment:
            return '{}#{}'.format(self._full_url, self.fragment)
        return self._full_url

    @full_url.setter
    def full_url(self, url):
        self._full_url = unwrap(url)
        (self._full_url, self.fragment) = splittag(self._full_url)
        self._parse()

    @full_url.deleter
    def full_url(self):
        self._full_url = None
        self.fragment = None
        self.selector = ''

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        if data != self._data:
            self._data = data
            if self.has_header('Content-length'):
                self.remove_header('Content-length')

    @data.deleter
    def data(self):
        self.data = None

    def _parse(self):
        (self.type, rest) = splittype(self._full_url)
        if self.type is None:
            raise ValueError('unknown url type: %r' % self.full_url)
        (self.host, self.selector) = splithost(rest)
        if self.host:
            self.host = unquote(self.host)

    def get_method(self):
        default_method = 'POST' if self.data is not None else 'GET'
        return getattr(self, 'method', default_method)

    def get_full_url(self):
        return self.full_url

    def set_proxy(self, host, type):
        if self.type == 'https' and not self._tunnel_host:
            self._tunnel_host = self.host
        else:
            self.type = type
            self.selector = self.full_url
        self.host = host

    def has_proxy(self):
        return self.selector == self.full_url

    def add_header(self, key, val):
        self.headers[key.capitalize()] = val

    def add_unredirected_header(self, key, val):
        self.unredirected_hdrs[key.capitalize()] = val

    def has_header(self, header_name):
        return header_name in self.headers or header_name in self.unredirected_hdrs

    def get_header(self, header_name, default=None):
        return self.headers.get(header_name, self.unredirected_hdrs.get(header_name, default))

    def remove_header(self, header_name):
        self.headers.pop(header_name, None)
        self.unredirected_hdrs.pop(header_name, None)

    def header_items(self):
        hdrs = self.unredirected_hdrs.copy()
        hdrs.update(self.headers)
        return list(hdrs.items())

class OpenerDirector:

    def __init__(self):
        client_version = 'Python-urllib/%s' % __version__
        self.addheaders = [('User-agent', client_version)]
        self.handlers = []
        self.handle_open = {}
        self.handle_error = {}
        self.process_response = {}
        self.process_request = {}

    def add_handler(self, handler):
        if not hasattr(handler, 'add_parent'):
            raise TypeError('expected BaseHandler instance, got %r' % type(handler))
        added = False
        for meth in dir(handler):
            if meth in ('redirect_request', 'do_open', 'proxy_open'):
                pass
            else:
                i = meth.find('_')
                protocol = meth[:i]
                condition = meth[i + 1:]
                if condition.startswith('error'):
                    j = condition.find('_') + i + 1
                    kind = meth[j + 1:]
                    try:
                        kind = int(kind)
                    except ValueError:
                        pass
                    lookup = self.handle_error.get(protocol, {})
                    self.handle_error[protocol] = lookup
                elif condition == 'open':
                    kind = protocol
                    lookup = self.handle_open
                elif condition == 'response':
                    kind = protocol
                    lookup = self.process_response
                elif condition == 'request':
                    kind = protocol
                    lookup = self.process_request
                    handlers = lookup.setdefault(kind, [])
                    if handlers:
                        bisect.insort(handlers, handler)
                    else:
                        handlers.append(handler)
                    added = True
                handlers = lookup.setdefault(kind, [])
                if handlers:
                    bisect.insort(handlers, handler)
                else:
                    handlers.append(handler)
                added = True
        if added:
            bisect.insort(self.handlers, handler)
            handler.add_parent(self)

    def close(self):
        pass

    def _call_chain(self, chain, kind, meth_name, *args):
        handlers = chain.get(kind, ())
        for handler in handlers:
            func = getattr(handler, meth_name)
            result = func(*args)
            if result is not None:
                return result

    def open(self, fullurl, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        if isinstance(fullurl, str):
            req = Request(fullurl, data)
        else:
            req = fullurl
            if data is not None:
                req.data = data
        req.timeout = timeout
        protocol = req.type
        meth_name = protocol + '_request'
        for processor in self.process_request.get(protocol, []):
            meth = getattr(processor, meth_name)
            req = meth(req)
        response = self._open(req, data)
        meth_name = protocol + '_response'
        for processor in self.process_response.get(protocol, []):
            meth = getattr(processor, meth_name)
            response = meth(req, response)
        return response

    def _open(self, req, data=None):
        result = self._call_chain(self.handle_open, 'default', 'default_open', req)
        if result:
            return result
        protocol = req.type
        result = self._call_chain(self.handle_open, protocol, protocol + '_open', req)
        if result:
            return result
        return self._call_chain(self.handle_open, 'unknown', 'unknown_open', req)

    def error(self, proto, *args):
        if proto in ('http', 'https'):
            dict = self.handle_error['http']
            proto = args[2]
            meth_name = 'http_error_%s' % proto
            http_err = 1
            orig_args = args
        else:
            dict = self.handle_error
            meth_name = proto + '_error'
            http_err = 0
        args = (dict, proto, meth_name) + args
        result = self._call_chain(*args)
        if result:
            return result
        elif http_err:
            args = (dict, 'default', 'http_error_default') + orig_args
            return self._call_chain(*args)

def build_opener(*handlers):
    opener = OpenerDirector()
    default_classes = [ProxyHandler, UnknownHandler, HTTPHandler, HTTPDefaultErrorHandler, HTTPRedirectHandler, FTPHandler, FileHandler, HTTPErrorProcessor, DataHandler]
    if hasattr(http.client, 'HTTPSConnection'):
        default_classes.append(HTTPSHandler)
    skip = set()
    for klass in default_classes:
        for check in handlers:
            if isinstance(check, type):
                if issubclass(check, klass):
                    skip.add(klass)
                    if isinstance(check, klass):
                        skip.add(klass)
            elif isinstance(check, klass):
                skip.add(klass)
    for klass in skip:
        default_classes.remove(klass)
    for klass in default_classes:
        opener.add_handler(klass())
    for h in handlers:
        if isinstance(h, type):
            h = h()
        opener.add_handler(h)
    return opener

class BaseHandler:
    handler_order = 500

    def add_parent(self, parent):
        self.parent = parent

    def close(self):
        pass

    def __lt__(self, other):
        if not hasattr(other, 'handler_order'):
            return True
        return self.handler_order < other.handler_order
