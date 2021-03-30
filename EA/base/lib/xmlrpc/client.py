import base64import sysimport timefrom datetime import datetimefrom decimal import Decimalimport http.clientimport urllib.parsefrom xml.parsers import expatimport errnofrom io import BytesIOtry:
    import gzip
except ImportError:
    gzip = None
def escape(s):
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    return s.replace('>', '&gt;')
__version__ = '%d.%d' % sys.version_info[:2]MAXINT = 2147483647MININT = -2147483648PARSE_ERROR = -32700SERVER_ERROR = -32600APPLICATION_ERROR = -32500SYSTEM_ERROR = -32400TRANSPORT_ERROR = -32300NOT_WELLFORMED_ERROR = -32700UNSUPPORTED_ENCODING = -32701INVALID_ENCODING_CHAR = -32702INVALID_XMLRPC = -32600METHOD_NOT_FOUND = -32601INVALID_METHOD_PARAMS = -32602INTERNAL_ERROR = -32603
class Error(Exception):

    def __str__(self):
        return repr(self)

class ProtocolError(Error):

    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
        self.url = url
        self.errcode = errcode
        self.errmsg = errmsg
        self.headers = headers

    def __repr__(self):
        return '<%s for %s: %s %s>' % (self.__class__.__name__, self.url, self.errcode, self.errmsg)

class ResponseError(Error):
    pass

class Fault(Error):

    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString

    def __repr__(self):
        return '<%s %s: %r>' % (self.__class__.__name__, self.faultCode, self.faultString)
boolean = Boolean = bool_day0 = datetime(1, 1, 1)if _day0.strftime('%Y') == '0001':

    def _iso8601_format(value):
        return value.strftime('%Y%m%dT%H:%M:%S')

elif _day0.strftime('%4Y') == '0001':

    def _iso8601_format(value):
        return value.strftime('%4Y%m%dT%H:%M:%S')

else:

    def _iso8601_format(value):
        return value.strftime('%Y%m%dT%H:%M:%S').zfill(17)
del _day0
def _strftime(value):
    if isinstance(value, datetime):
        return _iso8601_format(value)
    if not isinstance(value, (tuple, time.struct_time)):
        if value == 0:
            value = time.time()
        value = time.localtime(value)
    return '%04d%02d%02dT%02d:%02d:%02d' % value[:6]

class DateTime:

    def __init__(self, value=0):
        if isinstance(value, str):
            self.value = value
        else:
            self.value = _strftime(value)

    def make_comparable(self, other):
        if isinstance(other, DateTime):
            s = self.value
            o = other.value
        elif isinstance(other, datetime):
            s = self.value
            o = _iso8601_format(other)
        elif isinstance(other, str):
            s = self.value
            o = other
        elif hasattr(other, 'timetuple'):
            s = self.timetuple()
            o = other.timetuple()
        else:
            if hasattr(other, '__class__'):
                pass
            otype = type(other)
            raise TypeError("Can't compare %s and %s" % (self.__class__.__name__, otype))
        return (s, o)

    def __lt__(self, other):
        (s, o) = self.make_comparable(other)
        return s < o

    def __le__(self, other):
        (s, o) = self.make_comparable(other)
        return s <= o

    def __gt__(self, other):
        (s, o) = self.make_comparable(other)
        return s > o

    def __ge__(self, other):
        (s, o) = self.make_comparable(other)
        return s >= o

    def __eq__(self, other):
        (s, o) = self.make_comparable(other)
        return s == o

    def timetuple(self):
        return time.strptime(self.value, '%Y%m%dT%H:%M:%S')

    def __str__(self):
        return self.value

    def __repr__(self):
        return '<%s %r at %#x>' % (self.__class__.__name__, self.value, id(self))

    def decode(self, data):
        self.value = str(data).strip()

    def encode(self, out):
        out.write('<value><dateTime.iso8601>')
        out.write(self.value)
        out.write('</dateTime.iso8601></value>\n')

def _datetime(data):
    value = DateTime()
    value.decode(data)
    return value

def _datetime_type(data):
    return datetime.strptime(data, '%Y%m%dT%H:%M:%S')

class Binary:

    def __init__(self, data=None):
        if data is None:
            data = b''
        else:
            if not isinstance(data, (bytes, bytearray)):
                raise TypeError('expected bytes or bytearray, not %s' % data.__class__.__name__)
            data = bytes(data)
        self.data = data

    def __str__(self):
        return str(self.data, 'latin-1')

    def __eq__(self, other):
        if isinstance(other, Binary):
            other = other.data
        return self.data == other

    def decode(self, data):
        self.data = base64.decodebytes(data)

    def encode(self, out):
        out.write('<value><base64>\n')
        encoded = base64.encodebytes(self.data)
        out.write(encoded.decode('ascii'))
        out.write('</base64></value>\n')

def _binary(data):
    value = Binary()
    value.decode(data)
    return value
WRAPPERS = (DateTime, Binary)
class ExpatParser:

    def __init__(self, target):
        self._parser = parser = expat.ParserCreate(None, None)
        self._target = target
        parser.StartElementHandler = target.start
        parser.EndElementHandler = target.end
        parser.CharacterDataHandler = target.data
        encoding = None
        target.xml(encoding, None)

    def feed(self, data):
        self._parser.Parse(data, 0)

    def close(self):
        try:
            parser = self._parser
        except AttributeError:
            pass
        del self._target
        del self._parser
        parser.Parse(b'', True)

class Marshaller:

    def __init__(self, encoding=None, allow_none=False):
        self.memo = {}
        self.data = None
        self.encoding = encoding
        self.allow_none = allow_none

    dispatch = {}

    def dumps(self, values):
        out = []
        write = out.append
        dump = self._Marshaller__dump
        if isinstance(values, Fault):
            write('<fault>\n')
            dump({'faultCode': values.faultCode, 'faultString': values.faultString}, write)
            write('</fault>\n')
        else:
            write('<params>\n')
            for v in values:
                write('<param>\n')
                dump(v, write)
                write('</param>\n')
            write('</params>\n')
        result = ''.join(out)
        return result

    def __dump(self, value, write):
        try:
            f = self.dispatch[type(value)]
        except KeyError:
            if not hasattr(value, '__dict__'):
                raise TypeError('cannot marshal %s objects' % type(value))
            for type_ in type(value).__mro__:
                if type_ in self.dispatch.keys():
                    raise TypeError('cannot marshal %s objects' % type(value))
            f = self.dispatch['_arbitrary_instance']
        f(self, value, write)

    def dump_nil(self, value, write):
        if not self.allow_none:
            raise TypeError('cannot marshal None unless allow_none is enabled')
        write('<value><nil/></value>')

    dispatch[type(None)] = dump_nil

    def dump_bool(self, value, write):
        write('<value><boolean>')
        if value:
            pass
        write('0')
        write('</boolean></value>\n')

    dispatch[bool] = dump_bool

    def dump_long(self, value, write):
        if value > MAXINT or value < MININT:
            raise OverflowError('int exceeds XML-RPC limits')
        write('<value><int>')
        write(str(int(value)))
        write('</int></value>\n')

    dispatch[int] = dump_long
    dump_int = dump_long

    def dump_double(self, value, write):
        write('<value><double>')
        write(repr(value))
        write('</double></value>\n')

    dispatch[float] = dump_double

    def dump_unicode(self, value, write, escape=escape):
        write('<value><string>')
        write(escape(value))
        write('</string></value>\n')

    dispatch[str] = dump_unicode

    def dump_bytes(self, value, write):
        write('<value><base64>\n')
        encoded = base64.encodebytes(value)
        write(encoded.decode('ascii'))
        write('</base64></value>\n')

    dispatch[bytes] = dump_bytes
    dispatch[bytearray] = dump_bytes

    def dump_array(self, value, write):
        i = id(value)
        if i in self.memo:
            raise TypeError('cannot marshal recursive sequences')
        self.memo[i] = None
        dump = self._Marshaller__dump
        write('<value><array><data>\n')
        for v in value:
            dump(v, write)
        write('</data></array></value>\n')
        del self.memo[i]

    dispatch[tuple] = dump_array
    dispatch[list] = dump_array

    def dump_struct(self, value, write, escape=escape):
        i = id(value)
        if i in self.memo:
            raise TypeError('cannot marshal recursive dictionaries')
        self.memo[i] = None
        dump = self._Marshaller__dump
        write('<value><struct>\n')
        for (k, v) in value.items():
            write('<member>\n')
            if not isinstance(k, str):
                raise TypeError('dictionary key must be string')
            write('<name>%s</name>\n' % escape(k))
            dump(v, write)
            write('</member>\n')
        write('</struct></value>\n')
        del self.memo[i]

    dispatch[dict] = dump_struct

    def dump_datetime(self, value, write):
        write('<value><dateTime.iso8601>')
        write(_strftime(value))
        write('</dateTime.iso8601></value>\n')

    dispatch[datetime] = dump_datetime

    def dump_instance(self, value, write):
        if value.__class__ in WRAPPERS:
            self.write = write
            value.encode(self)
            del self.write
        else:
            self.dump_struct(value.__dict__, write)

    dispatch[DateTime] = dump_instance
    dispatch[Binary] = dump_instance
    dispatch['_arbitrary_instance'] = dump_instance

class Unmarshaller:

    def __init__(self, use_datetime=False, use_builtin_types=False):
        self._type = None
        self._stack = []
        self._marks = []
        self._data = []
        self._value = False
        self._methodname = None
        self._encoding = 'utf-8'
        self.append = self._stack.append
        self._use_datetime = use_builtin_types or use_datetime
        self._use_bytes = use_builtin_types

    def close(self):
        if self._type is None or self._marks:
            raise ResponseError()
        if self._type == 'fault':
            raise Fault(**self._stack[0])
        return tuple(self._stack)

    def getmethodname(self):
        return self._methodname

    def xml(self, encoding, standalone):
        self._encoding = encoding

    def start(self, tag, attrs):
        if ':' in tag:
            tag = tag.split(':')[-1]
        if tag == 'array' or tag == 'struct':
            self._marks.append(len(self._stack))
        self._data = []
        if self._value and tag not in self.dispatch:
            raise ResponseError('unknown tag %r' % tag)
        self._value = tag == 'value'

    def data(self, text):
        self._data.append(text)

    def end(self, tag):
        try:
            f = self.dispatch[tag]
        except KeyError:
            if ':' not in tag:
                return
            try:
                f = self.dispatch[tag.split(':')[-1]]
            except KeyError:
                return
        return f(self, ''.join(self._data))

    def end_dispatch(self, tag, data):
        try:
            f = self.dispatch[tag]
        except KeyError:
            if ':' not in tag:
                return
            try:
                f = self.dispatch[tag.split(':')[-1]]
            except KeyError:
                return
        return f(self, data)

    dispatch = {}

    def end_nil(self, data):
        self.append(None)
        self._value = 0

    dispatch['nil'] = end_nil

    def end_boolean(self, data):
        if data == '0':
            self.append(False)
        elif data == '1':
            self.append(True)
        else:
            raise TypeError('bad boolean value')
        self._value = 0

    dispatch['boolean'] = end_boolean

    def end_int(self, data):
        self.append(int(data))
        self._value = 0

    dispatch['i1'] = end_int
    dispatch['i2'] = end_int
    dispatch['i4'] = end_int
    dispatch['i8'] = end_int
    dispatch['int'] = end_int
    dispatch['biginteger'] = end_int

    def end_double(self, data):
        self.append(float(data))
        self._value = 0

    dispatch['double'] = end_double
    dispatch['float'] = end_double

    def end_bigdecimal(self, data):
        self.append(Decimal(data))
        self._value = 0

    dispatch['bigdecimal'] = end_bigdecimal

    def end_string(self, data):
        if self._encoding:
            data = data.decode(self._encoding)
        self.append(data)
        self._value = 0

    dispatch['string'] = end_string
    dispatch['name'] = end_string

    def end_array(self, data):
        mark = self._marks.pop()
        self._stack[mark:] = [self._stack[mark:]]
        self._value = 0

    dispatch['array'] = end_array

    def end_struct(self, data):
        mark = self._marks.pop()
        dict = {}
        items = self._stack[mark:]
        for i in range(0, len(items), 2):
            dict[items[i]] = items[i + 1]
        self._stack[mark:] = [dict]
        self._value = 0

    dispatch['struct'] = end_struct

    def end_base64(self, data):
        value = Binary()
        value.decode(data.encode('ascii'))
        if self._use_bytes:
            value = value.data
        self.append(value)
        self._value = 0

    dispatch['base64'] = end_base64

    def end_dateTime(self, data):
        value = DateTime()
        value.decode(data)
        if self._use_datetime:
            value = _datetime_type(data)
        self.append(value)

    dispatch['dateTime.iso8601'] = end_dateTime

    def end_value(self, data):
        if self._value:
            self.end_string(data)

    dispatch['value'] = end_value

    def end_params(self, data):
        self._type = 'params'

    dispatch['params'] = end_params

    def end_fault(self, data):
        self._type = 'fault'

    dispatch['fault'] = end_fault

    def end_methodName(self, data):
        if self._encoding:
            data = data.decode(self._encoding)
        self._methodname = data
        self._type = 'methodName'

    dispatch['methodName'] = end_methodName

class _MultiCallMethod:

    def __init__(self, call_list, name):
        self._MultiCallMethod__call_list = call_list
        self._MultiCallMethod__name = name

    def __getattr__(self, name):
        return _MultiCallMethod(self._MultiCallMethod__call_list, '%s.%s' % (self._MultiCallMethod__name, name))

    def __call__(self, *args):
        self._MultiCallMethod__call_list.append((self._MultiCallMethod__name, args))

class MultiCallIterator:

    def __init__(self, results):
        self.results = results

    def __getitem__(self, i):
        item = self.results[i]
        if type(item) == type({}):
            raise Fault(item['faultCode'], item['faultString'])
        else:
            if type(item) == type([]):
                return item[0]
            raise ValueError('unexpected type in multicall result')

class MultiCall:

    def __init__(self, server):
        self._MultiCall__server = server
        self._MultiCall__call_list = []

    def __repr__(self):
        return '<%s at %#x>' % (self.__class__.__name__, id(self))

    __str__ = __repr__

    def __getattr__(self, name):
        return _MultiCallMethod(self._MultiCall__call_list, name)

    def __call__(self):
        marshalled_list = []
        for (name, args) in self._MultiCall__call_list:
            marshalled_list.append({'methodName': name, 'params': args})
        return MultiCallIterator(self._MultiCall__server.system.multicall(marshalled_list))
FastMarshaller = FastParser = FastUnmarshaller = None
def getparser(use_datetime=False, use_builtin_types=False):
    if FastParser and FastUnmarshaller:
        if use_builtin_types:
            mkdatetime = _datetime_type
            mkbytes = base64.decodebytes
        elif use_datetime:
            mkdatetime = _datetime_type
            mkbytes = _binary
        else:
            mkdatetime = _datetime
            mkbytes = _binary
        target = FastUnmarshaller(True, False, mkbytes, mkdatetime, Fault)
        parser = FastParser(target)
    else:
        target = Unmarshaller(use_datetime=use_datetime, use_builtin_types=use_builtin_types)
        if FastParser:
            parser = FastParser(target)
        else:
            parser = ExpatParser(target)
    return (parser, target)

def dumps(params, methodname=None, methodresponse=None, encoding=None, allow_none=False):
    if isinstance(params, Fault):
        methodresponse = 1
    elif isinstance(params, tuple):
        pass
    if not encoding:
        encoding = 'utf-8'
    if FastMarshaller:
        m = FastMarshaller(encoding)
    else:
        m = Marshaller(encoding, allow_none)
    data = m.dumps(params)
    if encoding != 'utf-8':
        xmlheader = "<?xml version='1.0' encoding='%s'?>\n" % str(encoding)
    else:
        xmlheader = "<?xml version='1.0'?>\n"
    if methodname:
        data = (xmlheader, '<methodCall>\n<methodName>', methodname, '</methodName>\n', data, '</methodCall>\n')
    elif methodresponse:
        data = (xmlheader, '<methodResponse>\n', data, '</methodResponse>\n')
    else:
        return data
    return ''.join(data)

def loads(data, use_datetime=False, use_builtin_types=False):
    (p, u) = getparser(use_datetime=use_datetime, use_builtin_types=use_builtin_types)
    p.feed(data)
    p.close()
    return (u.close(), u.getmethodname())

def gzip_encode(data):
    if not gzip:
        raise NotImplementedError
    f = BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=f, compresslevel=1) as gzf:
        gzf.write(data)
    return f.getvalue()

def gzip_decode(data, max_decode=20971520):
    if not gzip:
        raise NotImplementedError
    with gzip.GzipFile(mode='rb', fileobj=BytesIO(data)) as gzf:
        try:
            if max_decode < 0:
                decoded = gzf.read()
            else:
                decoded = gzf.read(max_decode + 1)
        except OSError:
            raise ValueError('invalid data')
    if max_decode >= 0 and len(decoded) > max_decode:
        raise ValueError('max gzipped payload length exceeded')
    return decoded

class GzipDecodedResponse(gzip.GzipFile if gzip else object):

    def __init__(self, response):
        if not gzip:
            raise NotImplementedError
        self.io = BytesIO(response.read())
        gzip.GzipFile.__init__(self, mode='rb', fileobj=self.io)

    def close(self):
        try:
            gzip.GzipFile.close(self)
        finally:
            self.io.close()

class _Method:

    def __init__(self, send, name):
        self._Method__send = send
        self._Method__name = name

    def __getattr__(self, name):
        return _Method(self._Method__send, '%s.%s' % (self._Method__name, name))

    def __call__(self, *args):
        return self._Method__send(self._Method__name, args)

class Transport:
    user_agent = 'Python-xmlrpc/%s' % __version__
    accept_gzip_encoding = True
    encode_threshold = None

    def __init__(self, use_datetime=False, use_builtin_types=False):
        self._use_datetime = use_datetime
        self._use_builtin_types = use_builtin_types
        self._connection = (None, None)
        self._extra_headers = []

    def request(self, host, handler, request_body, verbose=False):
        for i in (0, 1):
            try:
                return self.single_request(host, handler, request_body, verbose)
            except http.client.RemoteDisconnected:
                if i:
                    raise
            except OSError as e:
                if i or e.errno not in (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE):
                    raise

    def single_request(self, host, handler, request_body, verbose=False):
        try:
            http_conn = self.send_request(host, handler, request_body, verbose)
            resp = http_conn.getresponse()
            if resp.status == 200:
                self.verbose = verbose
                return self.parse_response(resp)
        except Fault:
            raise
        except Exception:
            self.close()
            raise
        if resp.getheader('content-length', ''):
            resp.read()
        raise ProtocolError(host + handler, resp.status, resp.reason, dict(resp.getheaders()))

    def getparser(self):
        return getparser(use_datetime=self._use_datetime, use_builtin_types=self._use_builtin_types)

    def get_host_info(self, host):
        x509 = {}
        if isinstance(host, tuple):
            (host, x509) = host
        (auth, host) = urllib.parse.splituser(host)
        if auth:
            auth = urllib.parse.unquote_to_bytes(auth)
            auth = base64.encodebytes(auth).decode('utf-8')
            auth = ''.join(auth.split())
            extra_headers = [('Authorization', 'Basic ' + auth)]
        else:
            extra_headers = []
        return (host, extra_headers, x509)

    def make_connection(self, host):
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        (chost, self._extra_headers, x509) = self.get_host_info(host)
        self._connection = (host, http.client.HTTPConnection(chost))
        return self._connection[1]

    def close(self):
        (host, connection) = self._connection
        if connection:
            self._connection = (None, None)
            connection.close()

    def send_request(self, host, handler, request_body, debug):
        connection = self.make_connection(host)
        headers = self._extra_headers[:]
        if debug:
            connection.set_debuglevel(1)
        if self.accept_gzip_encoding and gzip:
            connection.putrequest('POST', handler, skip_accept_encoding=True)
            headers.append(('Accept-Encoding', 'gzip'))
        else:
            connection.putrequest('POST', handler)
        headers.append(('Content-Type', 'text/xml'))
        headers.append(('User-Agent', self.user_agent))
        self.send_headers(connection, headers)
        self.send_content(connection, request_body)
        return connection

    def send_headers(self, connection, headers):
        for (key, val) in headers:
            connection.putheader(key, val)

    def send_content(self, connection, request_body):
        if gzip:
            connection.putheader('Content-Encoding', 'gzip')
            request_body = gzip_encode(request_body)
        connection.putheader('Content-Length', str(len(request_body)))
        connection.endheaders(request_body)

    def parse_response(self, response):
        if hasattr(response, 'getheader'):
            if response.getheader('Content-Encoding', '') == 'gzip':
                stream = GzipDecodedResponse(response)
            else:
                stream = response
        else:
            stream = response
        (p, u) = self.getparser()
        while True:
            data = stream.read(1024)
            if not data:
                break
            if self.verbose:
                print('body:', repr(data))
            p.feed(data)
        if stream is not response:
            stream.close()
        p.close()
        return u.close()

class SafeTransport(Transport):

    def __init__(self, use_datetime=False, use_builtin_types=False, *, context=None):
        super().__init__(use_datetime=use_datetime, use_builtin_types=use_builtin_types)
        self.context = context

    def make_connection(self, host):
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        if not hasattr(http.client, 'HTTPSConnection'):
            raise NotImplementedError("your version of http.client doesn't support HTTPS")
        (chost, self._extra_headers, x509) = self.get_host_info(host)
        self._connection = (host, http.client.HTTPSConnection(chost, None, context=self.context, **x509 or {}))
        return self._connection[1]

class ServerProxy:

    def __init__(self, uri, transport=None, encoding=None, verbose=False, allow_none=False, use_datetime=False, use_builtin_types=False, *, context=None):
        (type, uri) = urllib.parse.splittype(uri)
        if type not in ('http', 'https'):
            raise OSError('unsupported XML-RPC protocol')
        (self._ServerProxy__host, self._ServerProxy__handler) = urllib.parse.splithost(uri)
        if not self._ServerProxy__handler:
            self._ServerProxy__handler = '/RPC2'
        if transport is None:
            if type == 'https':
                handler = SafeTransport
                extra_kwargs = {'context': context}
            else:
                handler = Transport
                extra_kwargs = {}
            transport = handler(use_datetime=use_datetime, use_builtin_types=use_builtin_types, **extra_kwargs)
        self._ServerProxy__transport = transport
        self._ServerProxy__encoding = encoding or 'utf-8'
        self._ServerProxy__verbose = verbose
        self._ServerProxy__allow_none = allow_none

    def __close(self):
        self._ServerProxy__transport.close()

    def __request(self, methodname, params):
        request = dumps(params, methodname, encoding=self._ServerProxy__encoding, allow_none=self._ServerProxy__allow_none).encode(self._ServerProxy__encoding, 'xmlcharrefreplace')
        response = self._ServerProxy__transport.request(self._ServerProxy__host, self._ServerProxy__handler, request, verbose=self._ServerProxy__verbose)
        if len(response) == 1:
            response = response[0]
        return response

    def __repr__(self):
        return '<%s for %s%s>' % (self.__class__.__name__, self._ServerProxy__host, self._ServerProxy__handler)

    __str__ = __repr__

    def __getattr__(self, name):
        return _Method(self._ServerProxy__request, name)

    def __call__(self, attr):
        if attr == 'close':
            return self._ServerProxy__close
        if attr == 'transport':
            return self._ServerProxy__transport
        raise AttributeError('Attribute %r not found' % (attr,))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._ServerProxy__close()
Server = ServerProxyif __name__ == '__main__':
    server = ServerProxy('http://localhost:8000')
    try:
        print(server.currentTime.getCurrentTime())
    except Error as v:
        print('ERROR', v)
    multi = MultiCall(server)
    multi.getData()
    multi.pow(2, 9)
    multi.add(1, 2)
    try:
        for response in multi():
            print(response)
    except Error as v:
        print('ERROR', v)