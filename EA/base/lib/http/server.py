__version__ = '0.6'__all__ = ['HTTPServer', 'ThreadingHTTPServer', 'BaseHTTPRequestHandler', 'SimpleHTTPRequestHandler', 'CGIHTTPRequestHandler']import copyimport datetimeimport email.utilsimport htmlimport http.clientimport ioimport mimetypesimport osimport posixpathimport selectimport shutilimport socketimport socketserverimport sysimport timeimport urllib.parsefrom functools import partialfrom http import HTTPStatusDEFAULT_ERROR_MESSAGE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n        "http://www.w3.org/TR/html4/strict.dtd">\n<html>\n    <head>\n        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">\n        <title>Error response</title>\n    </head>\n    <body>\n        <h1>Error response</h1>\n        <p>Error code: %(code)d</p>\n        <p>Message: %(message)s.</p>\n        <p>Error code explanation: %(code)s - %(explain)s.</p>\n    </body>\n</html>\n'DEFAULT_ERROR_CONTENT_TYPE = 'text/html;charset=utf-8'
class HTTPServer(socketserver.TCPServer):
    allow_reuse_address = 1

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        (host, port) = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True

class BaseHTTPRequestHandler(socketserver.StreamRequestHandler):
    sys_version = 'Python/' + sys.version.split()[0]
    server_version = 'BaseHTTP/' + __version__
    error_message_format = DEFAULT_ERROR_MESSAGE
    error_content_type = DEFAULT_ERROR_CONTENT_TYPE
    default_request_version = 'HTTP/0.9'

    def parse_request(self):
        self.command = None
        self.request_version = version = self.default_request_version
        self.close_connection = True
        requestline = str(self.raw_requestline, 'iso-8859-1')
        requestline = requestline.rstrip('\r\n')
        self.requestline = requestline
        words = requestline.split()
        if len(words) == 0:
            return False
        if len(words) >= 3:
            version = words[-1]
            try:
                if not version.startswith('HTTP/'):
                    raise ValueError
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split('.')
                if len(version_number) != 2:
                    raise ValueError
                version_number = (int(version_number[0]), int(version_number[1]))
            except (ValueError, IndexError):
                self.send_error(HTTPStatus.BAD_REQUEST, 'Bad request version (%r)' % version)
                return False
            if self.protocol_version >= 'HTTP/1.1':
                self.close_connection = False
            if version_number >= (1, 1) and version_number >= (2, 0):
                self.send_error(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED, 'Invalid HTTP version (%s)' % base_version_number)
                return False
            self.request_version = version
        if not (2 <= len(words) and len(words) <= 3):
            self.send_error(HTTPStatus.BAD_REQUEST, 'Bad request syntax (%r)' % requestline)
            return False
        (command, path) = words[:2]
        if len(words) == 2:
            self.close_connection = True
            if command != 'GET':
                self.send_error(HTTPStatus.BAD_REQUEST, 'Bad HTTP/0.9 request type (%r)' % command)
                return False
        self.command = command
        self.path = path
        try:
            self.headers = http.client.parse_headers(self.rfile, _class=self.MessageClass)
        except http.client.LineTooLong as err:
            self.send_error(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, 'Line too long', str(err))
            return False
        except http.client.HTTPException as err:
            self.send_error(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, 'Too many headers', str(err))
            return False
        conntype = self.headers.get('Connection', '')
        if conntype.lower() == 'close':
            self.close_connection = True
        elif self.protocol_version >= 'HTTP/1.1':
            self.close_connection = False
        expect = self.headers.get('Expect', '')
        if expect.lower() == '100-continue' and (self.protocol_version >= 'HTTP/1.1' and self.request_version >= 'HTTP/1.1') and not self.handle_expect_100():
            return False
        return True

    def handle_expect_100(self):
        self.send_response_only(HTTPStatus.CONTINUE)
        self.end_headers()
        return True

    def handle_one_request(self):
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(HTTPStatus.NOT_IMPLEMENTED, 'Unsupported method (%r)' % self.command)
                return
            method = getattr(self, mname)
            method()
            self.wfile.flush()
        except socket.timeout as e:
            self.log_error('Request timed out: %r', e)
            self.close_connection = True
            return

    def handle(self):
        self.close_connection = True
        self.handle_one_request()
        while not self.close_connection:
            self.handle_one_request()

    def send_error(self, code, message=None, explain=None):
        try:
            (shortmsg, longmsg) = self.responses[code]
        except KeyError:
            (shortmsg, longmsg) = ('???', '???')
        if message is None:
            message = shortmsg
        if explain is None:
            explain = longmsg
        self.log_error('code %d, message %s', code, message)
        self.send_response(code, message)
        self.send_header('Connection', 'close')
        body = None
        if code >= 200 and code not in (HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT, HTTPStatus.NOT_MODIFIED):
            content = self.error_message_format % {'code': code, 'message': html.escape(message, quote=False), 'explain': html.escape(explain, quote=False)}
            body = content.encode('UTF-8', 'replace')
            self.send_header('Content-Type', self.error_content_type)
            self.send_header('Content-Length', int(len(body)))
        self.end_headers()
        if self.command != 'HEAD' and body:
            self.wfile.write(body)

    def send_response(self, code, message=None):
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())

    def send_response_only(self, code, message=None):
        if self.request_version != 'HTTP/0.9':
            if message is None:
                if code in self.responses:
                    message = self.responses[code][0]
                else:
                    message = ''
            if not hasattr(self, '_headers_buffer'):
                self._headers_buffer = []
            self._headers_buffer.append(('%s %d %s\r\n' % (self.protocol_version, code, message)).encode('latin-1', 'strict'))

    def send_header(self, keyword, value):
        if self.request_version != 'HTTP/0.9':
            if not hasattr(self, '_headers_buffer'):
                self._headers_buffer = []
            self._headers_buffer.append(('%s: %s\r\n' % (keyword, value)).encode('latin-1', 'strict'))
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False

    def end_headers(self):
        if self.request_version != 'HTTP/0.9':
            self._headers_buffer.append(b'\r\n')
            self.flush_headers()

    def flush_headers(self):
        if hasattr(self, '_headers_buffer'):
            self.wfile.write(b''.join(self._headers_buffer))
            self._headers_buffer = []

    def log_request(self, code='-', size='-'):
        if isinstance(code, HTTPStatus):
            code = code.value
        self.log_message('"%s" %s %s', self.requestline, str(code), str(size))

    def log_error(self, format, *args):
        self.log_message(format, *args)

    def log_message(self, format, *args):
        sys.stderr.write('%s - - [%s] %s\n' % (self.address_string(), self.log_date_time_string(), format % args))

    def version_string(self):
        return self.server_version + ' ' + self.sys_version

    def date_time_string(self, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        return email.utils.formatdate(timestamp, usegmt=True)

    def log_date_time_string(self):
        now = time.time()
        (year, month, day, hh, mm, ss, x, y, z) = time.localtime(now)
        s = '%02d/%3s/%04d %02d:%02d:%02d' % (day, self.monthname[month], year, hh, mm, ss)
        return s

    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def address_string(self):
        return self.client_address[0]

    protocol_version = 'HTTP/1.0'
    MessageClass = http.client.HTTPMessage
    responses = {v: (v.phrase, v.description) for v in HTTPStatus.__members__.values()}

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = 'SimpleHTTP/' + __version__

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.getcwd()
        self.directory = directory
        super().__init__(*args, **kwargs)

    def do_GET(self):
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def do_HEAD(self):
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/', parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header('Location', new_url)
                self.end_headers()
                return
            for index in ('index.html', 'index.htm'):
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, 'File not found')
            return
        try:
            fs = os.fstat(f.fileno())
            if 'If-Modified-Since' in self.headers and 'If-None-Match' not in self.headers:
                try:
                    ims = email.utils.parsedate_to_datetime(self.headers['If-Modified-Since'])
                except (TypeError, IndexError, OverflowError, ValueError):
                    pass
                if ims.tzinfo is None:
                    ims = ims.replace(tzinfo=datetime.timezone.utc)
                if ims.tzinfo is datetime.timezone.utc:
                    last_modif = datetime.datetime.fromtimestamp(fs.st_mtime, datetime.timezone.utc)
                    last_modif = last_modif.replace(microsecond=0)
                    if last_modif <= ims:
                        self.send_response(HTTPStatus.NOT_MODIFIED)
                        self.end_headers()
                        f.close()
                        return
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', ctype)
            self.send_header('Content-Length', str(fs[6]))
            self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def list_directory(self, path):
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, 'No permission to list directory')
            return
        list.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path, errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for %s' % displaypath
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" content="text/html; charset=%s">' % enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            if os.path.isdir(fullname):
                displayname = name + '/'
                linkname = name + '/'
            if os.path.islink(fullname):
                displayname = name + '@'
            r.append('<li><a href="%s">%s</a></li>' % (urllib.parse.quote(linkname, errors='surrogatepass'), html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html; charset=%s' % enc)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        return f

    def translate_path(self, path):
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = self.directory
        for word in words:
            if not os.path.dirname(word):
                if word in (os.curdir, os.pardir):
                    pass
                else:
                    path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def copyfile(self, source, outputfile):
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        (base, ext) = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({'': 'application/octet-stream', '.py': 'text/plain', '.c': 'text/plain', '.h': 'text/plain'})

def _url_collapse_path(path):
    (path, _, query) = path.partition('?')
    path = urllib.parse.unquote(path)
    path_parts = path.split('/')
    head_parts = []
    for part in path_parts[:-1]:
        if part == '..':
            head_parts.pop()
        elif part and part != '.':
            head_parts.append(part)
    if path_parts:
        tail_part = path_parts.pop()
        if tail_part:
            if tail_part == '..':
                head_parts.pop()
                tail_part = ''
            elif tail_part == '.':
                tail_part = ''
    else:
        tail_part = ''
    if query:
        tail_part = '?'.join((tail_part, query))
    splitpath = ('/' + '/'.join(head_parts), tail_part)
    collapsed_path = '/'.join(splitpath)
    return collapsed_path
nobody = None
def nobody_uid():
    global nobody
    if nobody:
        return nobody
    try:
        import pwd
    except ImportError:
        return -1
    try:
        nobody = pwd.getpwnam('nobody')[2]
    except KeyError:
        nobody = 1 + max(x[2] for x in pwd.getpwall())
    return nobody

def executable(path):
    return os.access(path, os.X_OK)

class CGIHTTPRequestHandler(SimpleHTTPRequestHandler):
    have_fork = hasattr(os, 'fork')
    rbufsize = 0

    def do_POST(self):
        if self.is_cgi():
            self.run_cgi()
        else:
            self.send_error(HTTPStatus.NOT_IMPLEMENTED, 'Can only POST to CGI scripts')

    def send_head(self):
        if self.is_cgi():
            return self.run_cgi()
        else:
            return SimpleHTTPRequestHandler.send_head(self)

    def is_cgi(self):
        collapsed_path = _url_collapse_path(self.path)
        dir_sep = collapsed_path.find('/', 1)
        head = collapsed_path[:dir_sep]
        tail = collapsed_path[dir_sep + 1:]
        if head in self.cgi_directories:
            self.cgi_info = (head, tail)
            return True
        return False

    cgi_directories = ['/cgi-bin', '/htbin']

    def is_executable(self, path):
        return executable(path)

    def is_python(self, path):
        (head, tail) = os.path.splitext(path)
        return tail.lower() in ('.py', '.pyw')

    def run_cgi(self):
        (dir, rest) = self.cgi_info
        path = dir + '/' + rest
        i = path.find('/', len(dir) + 1)
        while i >= 0:
            nextdir = path[:i]
            nextrest = path[i + 1:]
            scriptdir = self.translate_path(nextdir)
            if os.path.isdir(scriptdir):
                dir = nextdir
                rest = nextrest
                i = path.find('/', len(dir) + 1)
            else:
                break
        (rest, _, query) = rest.partition('?')
        i = rest.find('/')
        if i >= 0:
            script = rest[:i]
            rest = rest[i:]
        else:
            script = rest
            rest = ''
        scriptname = dir + '/' + script
        scriptfile = self.translate_path(scriptname)
        if not os.path.exists(scriptfile):
            self.send_error(HTTPStatus.NOT_FOUND, 'No such CGI script (%r)' % scriptname)
            return
        if not os.path.isfile(scriptfile):
            self.send_error(HTTPStatus.FORBIDDEN, 'CGI script is not a plain file (%r)' % scriptname)
            return
        ispy = self.is_python(scriptname)
        if self.have_fork or ispy or not self.is_executable(scriptfile):
            self.send_error(HTTPStatus.FORBIDDEN, 'CGI script is not executable (%r)' % scriptname)
            return
        env = copy.deepcopy(os.environ)
        env['SERVER_SOFTWARE'] = self.version_string()
        env['SERVER_NAME'] = self.server.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PROTOCOL'] = self.protocol_version
        env['SERVER_PORT'] = str(self.server.server_port)
        env['REQUEST_METHOD'] = self.command
        uqrest = urllib.parse.unquote(rest)
        env['PATH_INFO'] = uqrest
        env['PATH_TRANSLATED'] = self.translate_path(uqrest)
        env['SCRIPT_NAME'] = scriptname
        if query:
            env['QUERY_STRING'] = query
        env['REMOTE_ADDR'] = self.client_address[0]
        authorization = self.headers.get('authorization')
        if authorization:
            authorization = authorization.split()
            if len(authorization) == 2:
                import base64
                import binascii
                env['AUTH_TYPE'] = authorization[0]
                if authorization[0].lower() == 'basic':
                    try:
                        authorization = authorization[1].encode('ascii')
                        authorization = base64.decodebytes(authorization).decode('ascii')
                    except (binascii.Error, UnicodeError):
                        pass
                    authorization = authorization.split(':')
                    if len(authorization) == 2:
                        env['REMOTE_USER'] = authorization[0]
        if self.headers.get('content-type') is None:
            env['CONTENT_TYPE'] = self.headers.get_content_type()
        else:
            env['CONTENT_TYPE'] = self.headers['content-type']
        length = self.headers.get('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        referer = self.headers.get('referer')
        if referer:
            env['HTTP_REFERER'] = referer
        accept = []
        for line in self.headers.getallmatchingheaders('accept'):
            if line[:1] in '\t\n\r ':
                accept.append(line.strip())
            else:
                accept = accept + line[7:].split(',')
        env['HTTP_ACCEPT'] = ','.join(accept)
        ua = self.headers.get('user-agent')
        if ua:
            env['HTTP_USER_AGENT'] = ua
        co = filter(None, self.headers.get_all('cookie', []))
        cookie_str = ', '.join(co)
        if cookie_str:
            env['HTTP_COOKIE'] = cookie_str
        for k in ('QUERY_STRING', 'REMOTE_HOST', 'CONTENT_LENGTH', 'HTTP_USER_AGENT', 'HTTP_COOKIE', 'HTTP_REFERER'):
            env.setdefault(k, '')
        self.send_response(HTTPStatus.OK, 'Script output follows')
        self.flush_headers()
        decoded_query = query.replace('+', ' ')
        if self.have_fork:
            args = [script]
            if '=' not in decoded_query:
                args.append(decoded_query)
            nobody = nobody_uid()
            self.wfile.flush()
            pid = os.fork()
            if pid != 0:
                (pid, sts) = os.waitpid(pid, 0)
                if select.select([self.rfile], [], [], 0)[0]:
                    if not self.rfile.read(1):
                        break
                if sts:
                    self.log_error('CGI script exit status %#x', sts)
                return
            try:
                try:
                    os.setuid(nobody)
                except OSError:
                    pass
                os.dup2(self.rfile.fileno(), 0)
                os.dup2(self.wfile.fileno(), 1)
                os.execve(scriptfile, args, env)
            except:
                self.server.handle_error(self.request, self.client_address)
                os._exit(127)
        else:
            import subprocess
            cmdline = [scriptfile]
            if self.is_python(scriptfile):
                interp = sys.executable
                if interp.lower().endswith('w.exe'):
                    interp = interp[:-5] + interp[-4:]
                cmdline = [interp, '-u'] + cmdline
            if '=' not in query:
                cmdline.append(query)
            self.log_message('command: %s', subprocess.list2cmdline(cmdline))
            try:
                nbytes = int(length)
            except (TypeError, ValueError):
                nbytes = 0
            p = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            if self.command.lower() == 'post' and nbytes > 0:
                data = self.rfile.read(nbytes)
            else:
                data = None
            if select.select([self.rfile._sock], [], [], 0)[0]:
                if not self.rfile._sock.recv(1):
                    break
            (stdout, stderr) = p.communicate(data)
            self.wfile.write(stdout)
            if stderr:
                self.log_error('%s', stderr)
            p.stderr.close()
            p.stdout.close()
            status = p.returncode
            if status:
                self.log_error('CGI script exit status %#x', status)
            else:
                self.log_message('CGI script exited OK')

def test(HandlerClass=BaseHTTPRequestHandler, ServerClass=ThreadingHTTPServer, protocol='HTTP/1.0', port=8000, bind=''):
    server_address = (bind, port)
    HandlerClass.protocol_version = protocol
    with ServerClass(server_address, HandlerClass) as httpd:
        sa = httpd.socket.getsockname()
        serve_message = 'Serving HTTP on {host} port {port} (http://{host}:{port}/) ...'
        print(serve_message.format(host=sa[0], port=sa[1]))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nKeyboard interrupt received, exiting.')
            sys.exit(0)
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cgi', action='store_true', help='Run as CGI Server')
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS', help='Specify alternate bind address [default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(), help='Specify alternative directory [default:current directory]')
    parser.add_argument('port', action='store', default=8000, type=int, nargs='?', help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    if args.cgi:
        handler_class = CGIHTTPRequestHandler
    else:
        handler_class = partial(SimpleHTTPRequestHandler, directory=args.directory)
    test(HandlerClass=handler_class, port=args.port, bind=args.bind)