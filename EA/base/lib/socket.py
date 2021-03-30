import _socketfrom _socket import *import osimport sysimport ioimport selectorsfrom enum_lib import IntEnum, IntFlagtry:
    import errno
except ImportError:
    errno = NoneEBADF = getattr(errno, 'EBADF', 9)EAGAIN = getattr(errno, 'EAGAIN', 11)EWOULDBLOCK = getattr(errno, 'EWOULDBLOCK', 11)__all__ = ['fromfd', 'getfqdn', 'create_connection', 'AddressFamily', 'SocketKind']__all__.extend(os._get_exports_list(_socket))IntEnum._convert('AddressFamily', __name__, lambda C: C.isupper() and C.startswith('AF_'))IntEnum._convert('SocketKind', __name__, lambda C: C.isupper() and C.startswith('SOCK_'))IntFlag._convert('MsgFlag', __name__, lambda C: C.isupper() and C.startswith('MSG_'))IntFlag._convert('AddressInfo', __name__, lambda C: C.isupper() and C.startswith('AI_'))_LOCALHOST = '127.0.0.1'_LOCALHOST_V6 = '::1'
def _intenum_converter(value, enum_klass):
    try:
        return enum_klass(value)
    except ValueError:
        return value
_realsocket = socketif sys.platform.lower().startswith('win'):
    errorTab = {}
    errorTab[10004] = 'The operation was interrupted.'
    errorTab[10009] = 'A bad file handle was passed.'
    errorTab[10013] = 'Permission denied.'
    errorTab[10014] = 'A fault occurred on the network??'
    errorTab[10022] = 'An invalid operation was attempted.'
    errorTab[10035] = 'The socket operation would block'
    errorTab[10036] = 'A blocking operation is already in progress.'
    errorTab[10048] = 'The network address is in use.'
    errorTab[10054] = 'The connection has been reset.'
    errorTab[10058] = 'The network has been shut down.'
    errorTab[10060] = 'The operation timed out.'
    errorTab[10061] = 'Connection refused.'
    errorTab[10063] = 'The name is too long.'
    errorTab[10064] = 'The host is down.'
    errorTab[10065] = 'The host is unreachable.'
    __all__.append('errorTab')
class _GiveupOnSendfile(Exception):
    pass

class socket(_socket.socket):
    __slots__ = ['__weakref__', '_io_refs', '_closed']

    def __init__(self, family=-1, type=-1, proto=-1, fileno=None):
        if fileno is None:
            if family == -1:
                family = AF_INET
            if type == -1:
                type = SOCK_STREAM
            if proto == -1:
                proto = 0
        _socket.socket.__init__(self, family, type, proto, fileno)
        self._io_refs = 0
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self._closed:
            self.close()

    def __repr__(self):
        closed = getattr(self, '_closed', False)
        s = '<%s.%s%s fd=%i, family=%s, type=%s, proto=%i' % (self.__class__.__module__, self.__class__.__qualname__, ' [closed]' if closed else '', self.fileno(), self.family, self.type, self.proto)
        if not closed:
            try:
                laddr = self.getsockname()
                if laddr:
                    s += ', laddr=%s' % str(laddr)
            except error:
                pass
            try:
                raddr = self.getpeername()
                if raddr:
                    s += ', raddr=%s' % str(raddr)
            except error:
                pass
        s += '>'
        return s

    def __getstate__(self):
        raise TypeError('Cannot serialize socket object')

    def dup(self):
        fd = dup(self.fileno())
        sock = self.__class__(self.family, self.type, self.proto, fileno=fd)
        sock.settimeout(self.gettimeout())
        return sock

    def accept(self):
        (fd, addr) = self._accept()
        sock = socket(self.family, self.type, self.proto, fileno=fd)
        if getdefaulttimeout() is None and self.gettimeout():
            sock.setblocking(True)
        return (sock, addr)

    def makefile(self, mode='r', buffering=None, *, encoding=None, errors=None, newline=None):
        if not set(mode) <= {'r', 'w', 'b'}:
            raise ValueError('invalid mode %r (only r, w, b allowed)' % (mode,))
        writing = 'w' in mode
        reading = 'r' in mode or not writing
        binary = 'b' in mode
        rawmode = ''
        if reading:
            rawmode += 'r'
        if writing:
            rawmode += 'w'
        raw = SocketIO(self, rawmode)
        self._io_refs += 1
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError('unbuffered streams must be binary')
            return raw
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode
        return text

    if hasattr(os, 'sendfile'):

        def _sendfile_use_sendfile(self, file, offset=0, count=None):
            self._check_sendfile_params(file, offset, count)
            sockno = self.fileno()
            try:
                fileno = file.fileno()
            except (AttributeError, io.UnsupportedOperation) as err:
                raise _GiveupOnSendfile(err)
            try:
                fsize = os.fstat(fileno).st_size
            except OSError as err:
                raise _GiveupOnSendfile(err)
            if not fsize:
                return 0
            blocksize = fsize if not count else count
            timeout = self.gettimeout()
            if timeout == 0:
                raise ValueError('non-blocking sockets are not supported')
            if hasattr(selectors, 'PollSelector'):
                selector = selectors.PollSelector()
            else:
                selector = selectors.SelectSelector()
            selector.register(sockno, selectors.EVENT_WRITE)
            total_sent = 0
            selector_select = selector.select
            os_sendfile = os.sendfile
            try:
                while True:
                    if timeout and not selector_select(timeout):
                        raise _socket.timeout('timed out')
                    if count:
                        blocksize = count - total_sent
                        if blocksize <= 0:
                            break
                    try:
                        sent = os_sendfile(sockno, fileno, offset, blocksize)
                    except BlockingIOError:
                        if not timeout:
                            selector_select()
                        continue
                    except OSError as err:
                        if total_sent == 0:
                            raise _GiveupOnSendfile(err)
                        raise err from None
                    if sent == 0:
                        break
                    offset += sent
                    total_sent += sent
                return total_sent
            finally:
                if total_sent > 0 and hasattr(file, 'seek'):
                    file.seek(offset)

    else:

        def _sendfile_use_sendfile(self, file, offset=0, count=None):
            raise _GiveupOnSendfile('os.sendfile() not available on this platform')

    def _sendfile_use_send(self, file, offset=0, count=None):
        self._check_sendfile_params(file, offset, count)
        if self.gettimeout() == 0:
            raise ValueError('non-blocking sockets are not supported')
        if offset:
            file.seek(offset)
        blocksize = min(count, 8192) if count else 8192
        total_sent = 0
        file_read = file.read
        sock_send = self.send
        try:
            while True:
                if count:
                    blocksize = min(count - total_sent, blocksize)
                    if blocksize <= 0:
                        break
                data = memoryview(file_read(blocksize))
                if not data:
                    break
                while True:
                    try:
                        sent = sock_send(data)
                    except BlockingIOError:
                        continue
                    total_sent += sent
                    if sent < len(data):
                        data = data[sent:]
                    else:
                        break
            return total_sent
        finally:
            if total_sent > 0 and hasattr(file, 'seek'):
                file.seek(offset + total_sent)

    def _check_sendfile_params(self, file, offset, count):
        if 'b' not in getattr(file, 'mode', 'b'):
            raise ValueError('file should be opened in binary mode')
        if not self.type & SOCK_STREAM:
            raise ValueError('only SOCK_STREAM type sockets are supported')
        if count is not None:
            if not isinstance(count, int):
                raise TypeError('count must be a positive integer (got {!r})'.format(count))
            if count <= 0:
                raise ValueError('count must be a positive integer (got {!r})'.format(count))

    def sendfile(self, file, offset=0, count=None):
        try:
            return self._sendfile_use_sendfile(file, offset, count)
        except _GiveupOnSendfile:
            return self._sendfile_use_send(file, offset, count)

    def _decref_socketios(self):
        if self._io_refs > 0:
            self._io_refs -= 1
        if self._closed:
            self.close()

    def _real_close(self, _ss=_socket.socket):
        _ss.close(self)

    def close(self):
        self._closed = True
        if self._io_refs <= 0:
            self._real_close()

    def detach(self):
        self._closed = True
        return super().detach()

    @property
    def family(self):
        return _intenum_converter(super().family, AddressFamily)

    @property
    def type(self):
        return _intenum_converter(super().type, SocketKind)

    if os.name == 'nt':

        def get_inheritable(self):
            return os.get_handle_inheritable(self.fileno())

        def set_inheritable(self, inheritable):
            os.set_handle_inheritable(self.fileno(), inheritable)

    else:

        def get_inheritable(self):
            return os.get_inheritable(self.fileno())

        def set_inheritable(self, inheritable):
            os.set_inheritable(self.fileno(), inheritable)

    get_inheritable.__doc__ = 'Get the inheritable flag of the socket'
    set_inheritable.__doc__ = 'Set the inheritable flag of the socket'

def fromfd(fd, family, type, proto=0):
    nfd = dup(fd)
    return socket(family, type, proto, nfd)
if hasattr(_socket.socket, 'share'):

    def fromshare(info):
        return socket(0, 0, 0, info)

    __all__.append('fromshare')if hasattr(_socket, 'socketpair'):

    def socketpair(family=None, type=SOCK_STREAM, proto=0):
        if family is None:
            try:
                family = AF_UNIX
            except NameError:
                family = AF_INET
        (a, b) = _socket.socketpair(family, type, proto)
        a = socket(family, type, proto, a.detach())
        b = socket(family, type, proto, b.detach())
        return (a, b)

else:

    def socketpair(family=AF_INET, type=SOCK_STREAM, proto=0):
        if family == AF_INET:
            host = _LOCALHOST
        elif family == AF_INET6:
            host = _LOCALHOST_V6
        else:
            raise ValueError('Only AF_INET and AF_INET6 socket address families are supported')
        if type != SOCK_STREAM:
            raise ValueError('Only SOCK_STREAM socket type is supported')
        if proto != 0:
            raise ValueError('Only protocol zero is supported')
        lsock = socket(family, type, proto)
        try:
            lsock.bind((host, 0))
            lsock.listen()
            (addr, port) = lsock.getsockname()[:2]
            csock = socket(family, type, proto)
            try:
                csock.setblocking(False)
                try:
                    csock.connect((addr, port))
                except (BlockingIOError, InterruptedError):
                    pass
                csock.setblocking(True)
                (ssock, _) = lsock.accept()
            except:
                csock.close()
                raise
        finally:
            lsock.close()
        return (ssock, csock)

    __all__.append('socketpair')socketpair.__doc__ = 'socketpair([family[, type[, proto]]]) -> (socket object, socket object)\nCreate a pair of socket objects from the sockets returned by the platform\nsocketpair() function.\nThe arguments are the same as for socket() except the default family is AF_UNIX\nif defined on the platform; otherwise, the default is AF_INET.\n'_blocking_errnos = {EAGAIN, EWOULDBLOCK}
class SocketIO(io.RawIOBase):

    def __init__(self, sock, mode):
        if mode not in ('r', 'w', 'rw', 'rb', 'wb', 'rwb'):
            raise ValueError('invalid mode: %r' % mode)
        io.RawIOBase.__init__(self)
        self._sock = sock
        if 'b' not in mode:
            mode += 'b'
        self._mode = mode
        self._reading = 'r' in mode
        self._writing = 'w' in mode
        self._timeout_occurred = False

    def readinto(self, b):
        self._checkClosed()
        self._checkReadable()
        if self._timeout_occurred:
            raise OSError('cannot read from timed out object')
        while True:
            try:
                return self._sock.recv_into(b)
            except timeout:
                self._timeout_occurred = True
                raise
            except error as e:
                if e.args[0] in _blocking_errnos:
                    return
                raise

    def write(self, b):
        self._checkClosed()
        self._checkWritable()
        try:
            return self._sock.send(b)
        except error as e:
            if e.args[0] in _blocking_errnos:
                return
            raise

    def readable(self):
        if self.closed:
            raise ValueError('I/O operation on closed socket.')
        return self._reading

    def writable(self):
        if self.closed:
            raise ValueError('I/O operation on closed socket.')
        return self._writing

    def seekable(self):
        if self.closed:
            raise ValueError('I/O operation on closed socket.')
        return super().seekable()

    def fileno(self):
        self._checkClosed()
        return self._sock.fileno()

    @property
    def name(self):
        if not self.closed:
            return self.fileno()
        else:
            return -1

    @property
    def mode(self):
        return self._mode

    def close(self):
        if self.closed:
            return
        io.RawIOBase.close(self)
        self._sock._decref_socketios()
        self._sock = None

def getfqdn(name=''):
    name = name.strip()
    if name and name == '0.0.0.0':
        name = gethostname()
    try:
        (hostname, aliases, ipaddrs) = gethostbyaddr(name)
    except error:
        pass
    aliases.insert(0, hostname)
    for name in aliases:
        if '.' in name:
            break
    name = hostname
    return name
_GLOBAL_DEFAULT_TIMEOUT = object()
def create_connection(address, timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    (host, port) = address
    err = None
    for res in getaddrinfo(host, port, 0, SOCK_STREAM):
        (af, socktype, proto, canonname, sa) = res
        sock = None
        try:
            sock = socket(af, socktype, proto)
            if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            err = None
            return sock
        except error as _:
            err = _
            if sock is not None:
                sock.close()
    if err is not None:
        raise err
    else:
        raise error('getaddrinfo returns an empty list')

def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    addrlist = []
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
        (af, socktype, proto, canonname, sa) = res
        addrlist.append((_intenum_converter(af, AddressFamily), _intenum_converter(socktype, SocketKind), proto, canonname, sa))
    return addrlist
