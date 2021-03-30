import sysimport osfrom collections import namedtuplefrom enum_lib import Enum as _Enum, IntEnum as _IntEnum, IntFlag as _IntFlagimport _sslfrom _ssl import OPENSSL_VERSION_NUMBER, OPENSSL_VERSION_INFO, OPENSSL_VERSIONfrom _ssl import _SSLContext, MemoryBIO, SSLSessionfrom _ssl import SSLError, SSLZeroReturnError, SSLWantReadError, SSLWantWriteError, SSLSyscallError, SSLEOFError, SSLCertVerificationErrorfrom _ssl import txt2obj as _txt2obj, nid2obj as _nid2objfrom _ssl import RAND_status, RAND_add, RAND_bytes, RAND_pseudo_bytestry:
    from _ssl import RAND_egd
except ImportError:
    passfrom _ssl import HAS_SNI, HAS_ECDH, HAS_NPN, HAS_ALPN, HAS_SSLv2, HAS_SSLv3, HAS_TLSv1, HAS_TLSv1_1, HAS_TLSv1_2, HAS_TLSv1_3from _ssl import _DEFAULT_CIPHERS, _OPENSSL_API_VERSION_IntEnum._convert('_SSLMethod', __name__, lambda name: name.startswith('PROTOCOL_') and name != 'PROTOCOL_SSLv23', source=_ssl)_IntFlag._convert('Options', __name__, lambda name: name.startswith('OP_'), source=_ssl)_IntEnum._convert('AlertDescription', __name__, lambda name: name.startswith('ALERT_DESCRIPTION_'), source=_ssl)_IntEnum._convert('SSLErrorNumber', __name__, lambda name: name.startswith('SSL_ERROR_'), source=_ssl)_IntFlag._convert('VerifyFlags', __name__, lambda name: name.startswith('VERIFY_'), source=_ssl)_IntEnum._convert('VerifyMode', __name__, lambda name: name.startswith('CERT_'), source=_ssl)PROTOCOL_SSLv23 = _SSLMethod.PROTOCOL_SSLv23 = _SSLMethod.PROTOCOL_TLS_PROTOCOL_NAMES = {value: name for (name, value) in _SSLMethod.__members__.items()}_SSLv2_IF_EXISTS = getattr(_SSLMethod, 'PROTOCOL_SSLv2', None)
class TLSVersion(_IntEnum):
    MINIMUM_SUPPORTED = _ssl.PROTO_MINIMUM_SUPPORTED
    SSLv3 = _ssl.PROTO_SSLv3
    TLSv1 = _ssl.PROTO_TLSv1
    TLSv1_1 = _ssl.PROTO_TLSv1_1
    TLSv1_2 = _ssl.PROTO_TLSv1_2
    TLSv1_3 = _ssl.PROTO_TLSv1_3
    MAXIMUM_SUPPORTED = _ssl.PROTO_MAXIMUM_SUPPORTED
if sys.platform == 'win32':
    from _ssl import enum_certificates, enum_crlsfrom socket import socket, AF_INET, SOCK_STREAM, create_connectionfrom socket import SOL_SOCKET, SO_TYPEimport socket as _socketimport base64import errnoimport warningssocket_error = OSErrorCHANNEL_BINDING_TYPES = ['tls-unique']HAS_NEVER_CHECK_COMMON_NAME = hasattr(_ssl, 'HOSTFLAG_NEVER_CHECK_SUBJECT')_RESTRICTED_SERVER_CIPHERS = _DEFAULT_CIPHERSCertificateError = SSLCertVerificationError
def _dnsname_match(dn, hostname):
    if not dn:
        return False
    wildcards = dn.count('*')
    if not wildcards:
        return dn.lower() == hostname.lower()
    if wildcards > 1:
        raise CertificateError('too many wildcards in certificate DNS name: {!r}.'.format(dn))
    (dn_leftmost, sep, dn_remainder) = dn.partition('.')
    if '*' in dn_remainder:
        raise CertificateError('wildcard can only be present in the leftmost label: {!r}.'.format(dn))
    if not sep:
        raise CertificateError('sole wildcard without additional labels are not support: {!r}.'.format(dn))
    if dn_leftmost != '*':
        raise CertificateError('partial wildcards in leftmost label are not supported: {!r}.'.format(dn))
    (hostname_leftmost, sep, hostname_remainder) = hostname.partition('.')
    if not (hostname_leftmost and sep):
        return False
    return dn_remainder.lower() == hostname_remainder.lower()

def _inet_paton(ipname):
    if ipname.count('.') == 3:
        try:
            return _socket.inet_aton(ipname)
        except OSError:
            pass
    try:
        return _socket.inet_pton(_socket.AF_INET6, ipname)
    except OSError:
        raise ValueError('{!r} is neither an IPv4 nor an IP6 address.'.format(ipname))
    except AttributeError:
        pass
    raise ValueError('{!r} is not an IPv4 address.'.format(ipname))

def _ipaddress_match(ipname, host_ip):
    ip = _inet_paton(ipname.rstrip())
    return ip == host_ip

def match_hostname(cert, hostname):
    if not cert:
        raise ValueError('empty or no certificate, match_hostname needs a SSL socket or SSL context with either CERT_OPTIONAL or CERT_REQUIRED')
    try:
        host_ip = _inet_paton(hostname)
    except ValueError:
        host_ip = None
    dnsnames = []
    san = cert.get('subjectAltName', ())
    for (key, value) in san:
        if key == 'DNS':
            if host_ip is None and _dnsname_match(value, hostname):
                return
            dnsnames.append(value)
        elif key == 'IP Address':
            if host_ip is not None and _ipaddress_match(value, host_ip):
                return
            dnsnames.append(value)
    if not dnsnames:
        for sub in cert.get('subject', ()):
            for (key, value) in sub:
                if key == 'commonName':
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)
    if len(dnsnames) > 1:
        raise CertificateError("hostname %r doesn't match either of %s" % (hostname, ', '.join(map(repr, dnsnames))))
    elif len(dnsnames) == 1:
        raise CertificateError("hostname %r doesn't match %r" % (hostname, dnsnames[0]))
    else:
        raise CertificateError('no appropriate commonName or subjectAltName fields were found')
DefaultVerifyPaths = namedtuple('DefaultVerifyPaths', 'cafile capath openssl_cafile_env openssl_cafile openssl_capath_env openssl_capath')
def get_default_verify_paths():
    parts = _ssl.get_default_verify_paths()
    cafile = os.environ.get(parts[0], parts[1])
    capath = os.environ.get(parts[2], parts[3])
    return DefaultVerifyPaths(cafile if os.path.isfile(cafile) else None, capath if os.path.isdir(capath) else None, parts)

class _ASN1Object(namedtuple('_ASN1Object', 'nid shortname longname oid')):
    __slots__ = ()

    def __new__(cls, oid):
        return super().__new__(cls, _txt2obj(oid, name=False))

    @classmethod
    def fromnid(cls, nid):
        return super().__new__(cls, _nid2obj(nid))

    @classmethod
    def fromname(cls, name):
        return super().__new__(cls, _txt2obj(name, name=True))

class Purpose(_ASN1Object, _Enum):
    SERVER_AUTH = '1.3.6.1.5.5.7.3.1'
    CLIENT_AUTH = '1.3.6.1.5.5.7.3.2'

class SSLContext(_SSLContext):
    _windows_cert_stores = ('CA', 'ROOT')
    sslsocket_class = None
    sslobject_class = None

    def __new__(cls, protocol=PROTOCOL_TLS, *args, **kwargs):
        self = _SSLContext.__new__(cls, protocol)
        return self

    def _encode_hostname(self, hostname):
        if hostname is None:
            return
        if isinstance(hostname, str):
            return hostname.encode('idna').decode('ascii')
        else:
            return hostname.decode('ascii')

    def wrap_socket(self, sock, server_side=False, do_handshake_on_connect=True, suppress_ragged_eofs=True, server_hostname=None, session=None):
        return self.sslsocket_class._create(sock=sock, server_side=server_side, do_handshake_on_connect=do_handshake_on_connect, suppress_ragged_eofs=suppress_ragged_eofs, server_hostname=server_hostname, context=self, session=session)

    def wrap_bio(self, incoming, outgoing, server_side=False, server_hostname=None, session=None):
        return self.sslobject_class._create(incoming, outgoing, server_side=server_side, server_hostname=self._encode_hostname(server_hostname), session=session, context=self)

    def set_npn_protocols(self, npn_protocols):
        protos = bytearray()
        for protocol in npn_protocols:
            b = bytes(protocol, 'ascii')
            if len(b) == 0 or len(b) > 255:
                raise SSLError('NPN protocols must be 1 to 255 in length')
            protos.append(len(b))
            protos.extend(b)
        self._set_npn_protocols(protos)

    def set_servername_callback(self, server_name_callback):
        if server_name_callback is None:
            self.sni_callback = None
        else:
            if not callable(server_name_callback):
                raise TypeError('not a callable object')

            def shim_cb(sslobj, servername, sslctx):
                servername = self._encode_hostname(servername)
                return server_name_callback(sslobj, servername, sslctx)

            self.sni_callback = shim_cb

    def set_alpn_protocols(self, alpn_protocols):
        protos = bytearray()
        for protocol in alpn_protocols:
            b = bytes(protocol, 'ascii')
            if len(b) == 0 or len(b) > 255:
                raise SSLError('ALPN protocols must be 1 to 255 in length')
            protos.append(len(b))
            protos.extend(b)
        self._set_alpn_protocols(protos)

    def _load_windows_store_certs(self, storename, purpose):
        certs = bytearray()
        try:
            for (cert, encoding, trust) in enum_certificates(storename):
                if not trust is True:
                    if purpose.oid in trust:
                        certs.extend(cert)
                certs.extend(cert)
        except PermissionError:
            warnings.warn('unable to enumerate Windows certificate store')
        if certs:
            self.load_verify_locations(cadata=certs)
        return certs

    def load_default_certs(self, purpose=Purpose.SERVER_AUTH):
        if not isinstance(purpose, _ASN1Object):
            raise TypeError(purpose)
        if sys.platform == 'win32':
            for storename in self._windows_cert_stores:
                self._load_windows_store_certs(storename, purpose)
        self.set_default_verify_paths()

    if hasattr(_SSLContext, 'minimum_version'):

        @property
        def minimum_version(self):
            return TLSVersion(super().minimum_version)

        @minimum_version.setter
        def minimum_version(self, value):
            if value == TLSVersion.SSLv3:
                self.options &= ~Options.OP_NO_SSLv3
            super(SSLContext, SSLContext).minimum_version.__set__(self, value)

        @property
        def maximum_version(self):
            return TLSVersion(super().maximum_version)

        @maximum_version.setter
        def maximum_version(self, value):
            super(SSLContext, SSLContext).maximum_version.__set__(self, value)

    @property
    def options(self):
        return Options(super().options)

    @options.setter
    def options(self, value):
        super(SSLContext, SSLContext).options.__set__(self, value)

    if hasattr(_ssl, 'HOSTFLAG_NEVER_CHECK_SUBJECT'):

        @property
        def hostname_checks_common_name(self):
            ncs = self._host_flags & _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT
            return ncs != _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT

        @hostname_checks_common_name.setter
        def hostname_checks_common_name(self, value):
            if value:
                self._host_flags &= ~_ssl.HOSTFLAG_NEVER_CHECK_SUBJECT
            else:
                self._host_flags |= _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT

    else:

        @property
        def hostname_checks_common_name(self):
            return True

    @property
    def protocol(self):
        return _SSLMethod(super().protocol)

    @property
    def verify_flags(self):
        return VerifyFlags(super().verify_flags)

    @verify_flags.setter
    def verify_flags(self, value):
        super(SSLContext, SSLContext).verify_flags.__set__(self, value)

    @property
    def verify_mode(self):
        value = super().verify_mode
        try:
            return VerifyMode(value)
        except ValueError:
            return value

    @verify_mode.setter
    def verify_mode(self, value):
        super(SSLContext, SSLContext).verify_mode.__set__(self, value)

def create_default_context(purpose=Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
    if not isinstance(purpose, _ASN1Object):
        raise TypeError(purpose)
    context = SSLContext(PROTOCOL_TLS)
    if purpose == Purpose.SERVER_AUTH:
        context.verify_mode = CERT_REQUIRED
        context.check_hostname = True
    if cafile or capath or cadata:
        context.load_verify_locations(cafile, capath, cadata)
    elif context.verify_mode != CERT_NONE:
        context.load_default_certs(purpose)
    return context

def _create_unverified_context(protocol=PROTOCOL_TLS, *, cert_reqs=CERT_NONE, check_hostname=False, purpose=Purpose.SERVER_AUTH, certfile=None, keyfile=None, cafile=None, capath=None, cadata=None):
    if not isinstance(purpose, _ASN1Object):
        raise TypeError(purpose)
    context = SSLContext(protocol)
    if not check_hostname:
        context.check_hostname = False
    if cert_reqs is not None:
        context.verify_mode = cert_reqs
    if check_hostname:
        context.check_hostname = True
    if keyfile and not certfile:
        raise ValueError('certfile must be specified')
    if certfile or keyfile:
        context.load_cert_chain(certfile, keyfile)
    if cafile or capath or cadata:
        context.load_verify_locations(cafile, capath, cadata)
    elif context.verify_mode != CERT_NONE:
        context.load_default_certs(purpose)
    return context
_create_default_https_context = create_default_context_create_stdlib_context = _create_unverified_context
class SSLObject:

    def __init__(self, *args, **kwargs):
        raise TypeError(f'{self.__class__.__name__} does not have a public constructor. Instances are returned by SSLContext.wrap_bio().')

    @classmethod
    def _create(cls, incoming, outgoing, server_side=False, server_hostname=None, session=None, context=None):
        self = cls.__new__(cls)
        sslobj = context._wrap_bio(incoming, outgoing, server_side=server_side, server_hostname=server_hostname, owner=self, session=session)
        self._sslobj = sslobj
        return self

    @property
    def context(self):
        return self._sslobj.context

    @context.setter
    def context(self, ctx):
        self._sslobj.context = ctx

    @property
    def session(self):
        return self._sslobj.session

    @session.setter
    def session(self, session):
        self._sslobj.session = session

    @property
    def session_reused(self):
        return self._sslobj.session_reused

    @property
    def server_side(self):
        return self._sslobj.server_side

    @property
    def server_hostname(self):
        return self._sslobj.server_hostname

    def read(self, len=1024, buffer=None):
        if buffer is not None:
            v = self._sslobj.read(len, buffer)
        else:
            v = self._sslobj.read(len)
        return v

    def write(self, data):
        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):
        return self._sslobj.getpeercert(binary_form)

    def selected_npn_protocol(self):
        if _ssl.HAS_NPN:
            return self._sslobj.selected_npn_protocol()

    def selected_alpn_protocol(self):
        if _ssl.HAS_ALPN:
            return self._sslobj.selected_alpn_protocol()

    def cipher(self):
        return self._sslobj.cipher()

    def shared_ciphers(self):
        return self._sslobj.shared_ciphers()

    def compression(self):
        return self._sslobj.compression()

    def pending(self):
        return self._sslobj.pending()

    def do_handshake(self):
        self._sslobj.do_handshake()

    def unwrap(self):
        return self._sslobj.shutdown()

    def get_channel_binding(self, cb_type='tls-unique'):
        return self._sslobj.get_channel_binding(cb_type)

    def version(self):
        return self._sslobj.version()

class SSLSocket(socket):

    def __init__(self, *args, **kwargs):
        raise TypeError(f'{self.__class__.__name__} does not have a public constructor. Instances are returned by SSLContext.wrap_socket().')

    @classmethod
    def _create(cls, sock, server_side=False, do_handshake_on_connect=True, suppress_ragged_eofs=True, server_hostname=None, context=None, session=None):
        if sock.getsockopt(SOL_SOCKET, SO_TYPE) != SOCK_STREAM:
            raise NotImplementedError('only stream sockets are supported')
        if server_side:
            if server_hostname:
                raise ValueError('server_hostname can only be specified in client mode')
            if session is not None:
                raise ValueError('session can only be specified in client mode')
        if context.check_hostname and not server_hostname:
            raise ValueError('check_hostname requires server_hostname')
        kwargs = dict(family=sock.family, type=sock.type, proto=sock.proto, fileno=sock.fileno())
        self = cls.__new__(cls, **kwargs)
        super(SSLSocket, self).__init__(**kwargs)
        self.settimeout(sock.gettimeout())
        sock.detach()
        self._context = context
        self._session = session
        self._closed = False
        self._sslobj = None
        self.server_side = server_side
        self.server_hostname = context._encode_hostname(server_hostname)
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        try:
            self.getpeername()
        except OSError as e:
            if e.errno != errno.ENOTCONN:
                raise
            connected = False
        connected = True
        self._connected = connected
        if connected:
            try:
                self._sslobj = self._context._wrap_socket(self, server_side, self.server_hostname, owner=self, session=self._session)
                if do_handshake_on_connect:
                    timeout = self.gettimeout()
                    if timeout == 0.0:
                        raise ValueError('do_handshake_on_connect should not be specified for non-blocking sockets')
                    self.do_handshake()
            except (OSError, ValueError):
                self.close()
                raise
        return self

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, ctx):
        self._context = ctx
        self._sslobj.context = ctx

    @property
    def session(self):
        if self._sslobj is not None:
            return self._sslobj.session

    @session.setter
    def session(self, session):
        self._session = session
        if self._sslobj is not None:
            self._sslobj.session = session

    @property
    def session_reused(self):
        if self._sslobj is not None:
            return self._sslobj.session_reused

    def dup(self):
        raise NotImplemented("Can't dup() %s instances" % self.__class__.__name__)

    def _checkClosed(self, msg=None):
        pass

    def _check_connected(self):
        if not self._connected:
            self.getpeername()

    def read(self, len=1024, buffer=None):
        self._checkClosed()
        if self._sslobj is None:
            raise ValueError('Read on closed or unwrapped SSL socket.')
        try:
            if buffer is not None:
                return self._sslobj.read(len, buffer)
            return self._sslobj.read(len)
        except SSLError as x:
            if self.suppress_ragged_eofs:
                if buffer is not None:
                    return 0
                return b''
            raise

    def write(self, data):
        self._checkClosed()
        if self._sslobj is None:
            raise ValueError('Write on closed or unwrapped SSL socket.')
        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):
        self._checkClosed()
        self._check_connected()
        return self._sslobj.getpeercert(binary_form)

    def selected_npn_protocol(self):
        self._checkClosed()
        if self._sslobj is None or not _ssl.HAS_NPN:
            return
        else:
            return self._sslobj.selected_npn_protocol()

    def selected_alpn_protocol(self):
        self._checkClosed()
        if self._sslobj is None or not _ssl.HAS_ALPN:
            return
        else:
            return self._sslobj.selected_alpn_protocol()

    def cipher(self):
        self._checkClosed()
        if self._sslobj is None:
            return
        else:
            return self._sslobj.cipher()

    def shared_ciphers(self):
        self._checkClosed()
        if self._sslobj is None:
            return
        else:
            return self._sslobj.shared_ciphers()

    def compression(self):
        self._checkClosed()
        if self._sslobj is None:
            return
        else:
            return self._sslobj.compression()

    def send(self, data, flags=0):
        self._checkClosed()
        if self._sslobj is not None:
            if flags != 0:
                raise ValueError('non-zero flags not allowed in calls to send() on %s' % self.__class__)
            return self._sslobj.write(data)
        else:
            return super().send(data, flags)

    def sendto(self, data, flags_or_addr, addr=None):
        self._checkClosed()
        if self._sslobj is not None:
            raise ValueError('sendto not allowed on instances of %s' % self.__class__)
        elif addr is None:
            return super().sendto(data, flags_or_addr)
        else:
            return super().sendto(data, flags_or_addr, addr)

    def sendmsg(self, *args, **kwargs):
        raise NotImplementedError('sendmsg not allowed on instances of %s' % self.__class__)

    def sendall(self, data, flags=0):
        self._checkClosed()
        if self._sslobj is not None:
            if flags != 0:
                raise ValueError('non-zero flags not allowed in calls to sendall() on %s' % self.__class__)
            count = 0
            with memoryview(data) as view, view.cast('B') as byte_view:
                amount = len(byte_view)
                while count < amount:
                    v = self.send(byte_view[count:])
                    count += v
        else:
            return super().sendall(data, flags)

    def sendfile(self, file, offset=0, count=None):
        if self._sslobj is not None:
            return self._sendfile_use_send(file, offset, count)
        else:
            return super().sendfile(file, offset, count)

    def recv(self, buflen=1024, flags=0):
        self._checkClosed()
        if self._sslobj is not None:
            if flags != 0:
                raise ValueError('non-zero flags not allowed in calls to recv() on %s' % self.__class__)
            return self.read(buflen)
        else:
            return super().recv(buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if buffer and nbytes is None:
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj is not None:
            if flags != 0:
                raise ValueError('non-zero flags not allowed in calls to recv_into() on %s' % self.__class__)
            return self.read(nbytes, buffer)
        else:
            return super().recv_into(buffer, nbytes, flags)

    def recvfrom(self, buflen=1024, flags=0):
        self._checkClosed()
        if self._sslobj is not None:
            raise ValueError('recvfrom not allowed on instances of %s' % self.__class__)
        else:
            return super().recvfrom(buflen, flags)

    def recvfrom_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if self._sslobj is not None:
            raise ValueError('recvfrom_into not allowed on instances of %s' % self.__class__)
        else:
            return super().recvfrom_into(buffer, nbytes, flags)

    def recvmsg(self, *args, **kwargs):
        raise NotImplementedError('recvmsg not allowed on instances of %s' % self.__class__)

    def recvmsg_into(self, *args, **kwargs):
        raise NotImplementedError('recvmsg_into not allowed on instances of %s' % self.__class__)

    def pending(self):
        self._checkClosed()
        if self._sslobj is not None:
            return self._sslobj.pending()
        else:
            return 0

    def shutdown(self, how):
        self._checkClosed()
        self._sslobj = None
        super().shutdown(how)

    def unwrap(self):
        if self._sslobj:
            s = self._sslobj.shutdown()
            self._sslobj = None
            return s
        raise ValueError('No SSL wrapper around ' + str(self))

    def _real_close(self):
        self._sslobj = None
        super()._real_close()

    def do_handshake(self, block=False):
        self._check_connected()
        timeout = self.gettimeout()
        try:
            if timeout == 0.0 and block:
                self.settimeout(None)
            self._sslobj.do_handshake()
        finally:
            self.settimeout(timeout)

    def _real_connect(self, addr, connect_ex):
        if self.server_side:
            raise ValueError("can't connect in server-side mode")
        if self._connected or self._sslobj is not None:
            raise ValueError('attempt to connect already-connected SSLSocket!')
        self._sslobj = self.context._wrap_socket(self, False, self.server_hostname, owner=self, session=self._session)
        try:
            if connect_ex:
                rc = super().connect_ex(addr)
            else:
                rc = None
                super().connect(addr)
            if not rc:
                self._connected = True
                if self.do_handshake_on_connect:
                    self.do_handshake()
            return rc
        except (OSError, ValueError):
            self._sslobj = None
            raise

    def connect(self, addr):
        self._real_connect(addr, False)

    def connect_ex(self, addr):
        return self._real_connect(addr, True)

    def accept(self):
        (newsock, addr) = super().accept()
        newsock = self.context.wrap_socket(newsock, do_handshake_on_connect=self.do_handshake_on_connect, suppress_ragged_eofs=self.suppress_ragged_eofs, server_side=True)
        return (newsock, addr)

    def get_channel_binding(self, cb_type='tls-unique'):
        if self._sslobj is not None:
            return self._sslobj.get_channel_binding(cb_type)
        else:
            if cb_type not in CHANNEL_BINDING_TYPES:
                raise ValueError('{0} channel binding type not implemented'.format(cb_type))
            return

    def version(self):
        if self._sslobj is not None:
            return self._sslobj.version()
        else:
            return
SSLContext.sslsocket_class = SSLSocketSSLContext.sslobject_class = SSLObject
def wrap_socket(sock, keyfile=None, certfile=None, server_side=False, cert_reqs=CERT_NONE, ssl_version=PROTOCOL_TLS, ca_certs=None, do_handshake_on_connect=True, suppress_ragged_eofs=True, ciphers=None):
    if server_side and not certfile:
        raise ValueError('certfile must be specified for server-side operations')
    if keyfile and not certfile:
        raise ValueError('certfile must be specified')
    context = SSLContext(ssl_version)
    context.verify_mode = cert_reqs
    if ca_certs:
        context.load_verify_locations(ca_certs)
    if certfile:
        context.load_cert_chain(certfile, keyfile)
    if ciphers:
        context.set_ciphers(ciphers)
    return context.wrap_socket(sock=sock, server_side=server_side, do_handshake_on_connect=do_handshake_on_connect, suppress_ragged_eofs=suppress_ragged_eofs)

def cert_time_to_seconds(cert_time):
    from time import strptime
    from calendar import timegm
    months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    time_format = ' %d %H:%M:%S %Y GMT'
    try:
        month_number = months.index(cert_time[:3].title()) + 1
    except ValueError:
        raise ValueError('time data %r does not match format "%%b%s"' % (cert_time, time_format))
    tt = strptime(cert_time[3:], time_format)
    return timegm((tt[0], month_number) + tt[2:6])
PEM_HEADER = '-----BEGIN CERTIFICATE-----'PEM_FOOTER = '-----END CERTIFICATE-----'
def DER_cert_to_PEM_cert(der_cert_bytes):
    f = str(base64.standard_b64encode(der_cert_bytes), 'ASCII', 'strict')
    ss = [PEM_HEADER]
    ss += [f[i:i + 64] for i in range(0, len(f), 64)]
    ss.append(PEM_FOOTER + '\n')
    return '\n'.join(ss)

def PEM_cert_to_DER_cert(pem_cert_string):
    if not pem_cert_string.startswith(PEM_HEADER):
        raise ValueError('Invalid PEM encoding; must start with %s' % PEM_HEADER)
    if not pem_cert_string.strip().endswith(PEM_FOOTER):
        raise ValueError('Invalid PEM encoding; must end with %s' % PEM_FOOTER)
    d = pem_cert_string.strip()[len(PEM_HEADER):-len(PEM_FOOTER)]
    return base64.decodebytes(d.encode('ASCII', 'strict'))

def get_server_certificate(addr, ssl_version=PROTOCOL_TLS, ca_certs=None):
    (host, port) = addr
    if ca_certs is not None:
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    context = _create_stdlib_context(ssl_version, cert_reqs=cert_reqs, cafile=ca_certs)
    with create_connection(addr) as sock, context.wrap_socket(sock) as sslsock:
        dercert = sslsock.getpeercert(True)
    return DER_cert_to_PEM_cert(dercert)

def get_protocol_name(protocol_code):
    return _PROTOCOL_NAMES.get(protocol_code, '<unknown>')
