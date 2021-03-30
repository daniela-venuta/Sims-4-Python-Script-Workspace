import osimport sysfrom enum_lib import Enum__author__ = 'Ka-Ping Yee <ping@zesty.ca>'(RESERVED_NCS, RFC_4122, RESERVED_MICROSOFT, RESERVED_FUTURE) = ['reserved for NCS compatibility', 'specified in RFC 4122', 'reserved for Microsoft compatibility', 'reserved for future definition']int_ = intbytes_ = bytes
class SafeUUID(Enum):
    safe = 0
    unsafe = -1
    unknown = None

class UUID:

    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None, version=None, *, is_safe=SafeUUID.unknown):
        if [hex, bytes, bytes_le, fields, int].count(None) != 4:
            raise TypeError('one of the hex, bytes, bytes_le, fields, or int arguments must be given')
        if hex is not None:
            hex = hex.replace('urn:', '').replace('uuid:', '')
            hex = hex.strip('{}').replace('-', '')
            if len(hex) != 32:
                raise ValueError('badly formed hexadecimal UUID string')
            int = int_(hex, 16)
        if bytes_le is not None:
            if len(bytes_le) != 16:
                raise ValueError('bytes_le is not a 16-char string')
            bytes = bytes_le[3::-1] + bytes_le[5:3:-1] + bytes_le[7:5:-1] + bytes_le[8:]
        if bytes is not None:
            if len(bytes) != 16:
                raise ValueError('bytes is not a 16-char string')
            int = int_.from_bytes(bytes, byteorder='big')
        if fields is not None:
            if len(fields) != 6:
                raise ValueError('fields is not a 6-tuple')
            (time_low, time_mid, time_hi_version, clock_seq_hi_variant, clock_seq_low, node) = fields
            if not (0 <= time_low and time_low < 4294967296):
                raise ValueError('field 1 out of range (need a 32-bit value)')
            if not (0 <= time_mid and time_mid < 65536):
                raise ValueError('field 2 out of range (need a 16-bit value)')
            if not (0 <= time_hi_version and time_hi_version < 65536):
                raise ValueError('field 3 out of range (need a 16-bit value)')
            if not (0 <= clock_seq_hi_variant and clock_seq_hi_variant < 256):
                raise ValueError('field 4 out of range (need an 8-bit value)')
            if not (0 <= clock_seq_low and clock_seq_low < 256):
                raise ValueError('field 5 out of range (need an 8-bit value)')
            if not (0 <= node and node < 281474976710656):
                raise ValueError('field 6 out of range (need a 48-bit value)')
            clock_seq = clock_seq_hi_variant << 8 | clock_seq_low
            int = time_low << 96 | time_mid << 80 | time_hi_version << 64 | clock_seq << 48 | node
        if not (int is not None and 0 <= int and int < 1 << 128):
            raise ValueError('int is out of range (need a 128-bit value)')
        if version is not None:
            if not (1 <= version and version <= 5):
                raise ValueError('illegal version number')
            int &= -13835058055282163713
            int |= 9223372036854775808
            int &= -1133367955888714851287041
            int |= version << 76
        self.__dict__['int'] = int
        self.__dict__['is_safe'] = is_safe

    def __eq__(self, other):
        if isinstance(other, UUID):
            return self.int == other.int
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, UUID):
            return self.int < other.int
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, UUID):
            return self.int > other.int
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, UUID):
            return self.int <= other.int
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, UUID):
            return self.int >= other.int
        return NotImplemented

    def __hash__(self):
        return hash(self.int)

    def __int__(self):
        return self.int

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __setattr__(self, name, value):
        raise TypeError('UUID objects are immutable')

    def __str__(self):
        hex = '%032x' % self.int
        return '%s-%s-%s-%s-%s' % (hex[:8], hex[8:12], hex[12:16], hex[16:20], hex[20:])

    @property
    def bytes(self):
        return self.int.to_bytes(16, 'big')

    @property
    def bytes_le(self):
        bytes = self.bytes
        return bytes[3::-1] + bytes[5:3:-1] + bytes[7:5:-1] + bytes[8:]

    @property
    def fields(self):
        return (self.time_low, self.time_mid, self.time_hi_version, self.clock_seq_hi_variant, self.clock_seq_low, self.node)

    @property
    def time_low(self):
        return self.int >> 96

    @property
    def time_mid(self):
        return self.int >> 80 & 65535

    @property
    def time_hi_version(self):
        return self.int >> 64 & 65535

    @property
    def clock_seq_hi_variant(self):
        return self.int >> 56 & 255

    @property
    def clock_seq_low(self):
        return self.int >> 48 & 255

    @property
    def time(self):
        return (self.time_hi_version & 4095) << 48 | self.time_mid << 32 | self.time_low

    @property
    def clock_seq(self):
        return (self.clock_seq_hi_variant & 63) << 8 | self.clock_seq_low

    @property
    def node(self):
        return self.int & 281474976710655

    @property
    def hex(self):
        return '%032x' % self.int

    @property
    def urn(self):
        return 'urn:uuid:' + str(self)

    @property
    def variant(self):
        if not self.int & 9223372036854775808:
            return RESERVED_NCS
        if not self.int & 4611686018427387904:
            return RFC_4122
        elif not self.int & 2305843009213693952:
            return RESERVED_MICROSOFT
        else:
            return RESERVED_FUTURE
        return RESERVED_FUTURE

    @property
    def version(self):
        if self.variant == RFC_4122:
            return int(self.int >> 76 & 15)

def _popen(command, *args):
    import os
    import shutil
    import subprocess
    executable = shutil.which(command)
    if executable is None:
        path = os.pathsep.join(('/sbin', '/usr/sbin'))
        executable = shutil.which(command, path=path)
        if executable is None:
            return
    env = dict(os.environ)
    env['LC_ALL'] = 'C'
    proc = subprocess.Popen((executable,) + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
    return proc

def _is_universal(mac):
    return not mac & 2199023255552

def _find_mac(command, args, hw_identifiers, get_index):
    first_local_mac = None
    try:
        proc = _popen(command, args.split())
        if not proc:
            return
        with proc:
            for line in proc.stdout:
                words = line.lower().rstrip().split()
                for i in range(len(words)):
                    if words[i] in hw_identifiers:
                        try:
                            word = words[get_index(i)]
                            mac = int(word.replace(b':', b''), 16)
                            if _is_universal(mac):
                                return mac
                            first_local_mac = first_local_mac or mac
                        except (ValueError, IndexError):
                            pass
    except OSError:
        pass
    return first_local_mac or None

def _ifconfig_getnode():
    keywords = (b'hwaddr', b'ether', b'address:', b'lladdr')
    for args in ('', '-a', '-av'):
        mac = _find_mac('ifconfig', args, keywords, lambda i: i + 1)
        if mac:
            return mac
        return

def _ip_getnode():
    mac = _find_mac('ip', 'link', [b'link/ether'], lambda i: i + 1)
    if mac:
        return mac

def _arp_getnode():
    import os
    import socket
    try:
        ip_addr = socket.gethostbyname(socket.gethostname())
    except OSError:
        return
    mac = _find_mac('arp', '-an', [os.fsencode(ip_addr)], lambda i: -1)
    if mac:
        return mac
    mac = _find_mac('arp', '-an', [os.fsencode(ip_addr)], lambda i: i + 1)
    if mac:
        return mac
    else:
        mac = _find_mac('arp', '-an', [os.fsencode('(%s)' % ip_addr)], lambda i: i + 2)
        if mac:
            return mac

def _lanscan_getnode():
    return _find_mac('lanscan', '-ai', [b'lan0'], lambda i: 0)

def _netstat_getnode():
    first_local_mac = None
    try:
        proc = _popen('netstat', '-ia')
        if not proc:
            return
        with proc:
            words = proc.stdout.readline().rstrip().split()
            try:
                i = words.index(b'Address')
            except ValueError:
                return
            for line in proc.stdout:
                try:
                    words = line.rstrip().split()
                    word = words[i]
                    mac = int(word.replace(b':', b''), 16)
                    if _is_universal(mac):
                        return mac
                    first_local_mac = first_local_mac or mac
                except (ValueError, IndexError):
                    pass
    except OSError:
        pass
    return first_local_mac or None

def _ipconfig_getnode():
    import os
    import re
    import subprocess
    first_local_mac = None
    dirs = ['', 'c:\\windows\\system32', 'c:\\winnt\\system32']
    try:
        import ctypes
        buffer = ctypes.create_string_buffer(300)
        ctypes.windll.kernel32.GetSystemDirectoryA(buffer, 300)
        dirs.insert(0, buffer.value.decode('mbcs'))
    except:
        pass
    for dir in dirs:
        try:
            proc = subprocess.Popen([os.path.join(dir, 'ipconfig'), '/all'], stdout=subprocess.PIPE, encoding='oem')
        except OSError:
            continue
        with proc:
            for line in proc.stdout:
                value = line.split(':')[-1].strip().lower()
                if re.fullmatch('(?:[0-9a-f][0-9a-f]-){5}[0-9a-f][0-9a-f]', value):
                    mac = int(value.replace('-', ''), 16)
                    if _is_universal(mac):
                        return mac
                    first_local_mac = first_local_mac or mac
    return first_local_mac or None

def _netbios_getnode():
    import win32wnet
    import netbios
    first_local_mac = None
    ncb = netbios.NCB()
    ncb.Command = netbios.NCBENUM
    ncb.Buffer = adapters = netbios.LANA_ENUM()
    adapters._pack()
    if win32wnet.Netbios(ncb) != 0:
        return
    adapters._unpack()
    for i in range(adapters.length):
        ncb.Reset()
        ncb.Command = netbios.NCBRESET
        ncb.Lana_num = ord(adapters.lana[i])
        if win32wnet.Netbios(ncb) != 0:
            pass
        else:
            ncb.Reset()
            ncb.Command = netbios.NCBASTAT
            ncb.Lana_num = ord(adapters.lana[i])
            ncb.Callname = '*'.ljust(16)
            ncb.Buffer = status = netbios.ADAPTER_STATUS()
            if win32wnet.Netbios(ncb) != 0:
                pass
            else:
                status._unpack()
                bytes = status.adapter_address[:6]
                if len(bytes) != 6:
                    pass
                else:
                    mac = int.from_bytes(bytes, 'big')
                    if _is_universal(mac):
                        return mac
                    first_local_mac = first_local_mac or mac
    return first_local_mac or None
_generate_time_safe = _UuidCreate = None_has_uuid_generate_time_safe = Nonetry:
    import _uuid
except ImportError:
    _uuid = None
def _load_system_functions():
    global _has_uuid_generate_time_safe, _generate_time_safe, _UuidCreate
    if _has_uuid_generate_time_safe is not None:
        return
    _has_uuid_generate_time_safe = False
    if sys.platform == 'darwin' and int(os.uname().release.split('.')[0]) < 9:
        pass
    elif _uuid is not None:
        _generate_time_safe = _uuid.generate_time_safe
        _has_uuid_generate_time_safe = _uuid.has_uuid_generate_time_safe
        return
    try:
        import ctypes
        import ctypes.util
        _libnames = ['uuid']
        if not sys.platform.startswith('win'):
            _libnames.append('c')
        for libname in _libnames:
            try:
                lib = ctypes.CDLL(ctypes.util.find_library(libname))
            except Exception:
                continue
            if hasattr(lib, 'uuid_generate_time_safe'):
                _uuid_generate_time_safe = lib.uuid_generate_time_safe

                def _generate_time_safe():
                    _buffer = ctypes.create_string_buffer(16)
                    res = _uuid_generate_time_safe(_buffer)
                    return (bytes(_buffer.raw), res)

                _has_uuid_generate_time_safe = True
                break
            elif hasattr(lib, 'uuid_generate_time'):
                _uuid_generate_time = lib.uuid_generate_time
                _uuid_generate_time.restype = None

                def _generate_time_safe():
                    _buffer = ctypes.create_string_buffer(16)
                    _uuid_generate_time(_buffer)
                    return (bytes(_buffer.raw), None)

                break
        try:
            lib = ctypes.windll.rpcrt4
        except:
            lib = None
        _UuidCreate = getattr(lib, 'UuidCreateSequential', getattr(lib, 'UuidCreate', None))
    except Exception as exc:
        import warnings
        warnings.warn(f'Could not find fallback ctypes uuid functions: {exc}', ImportWarning)

def _unix_getnode():
    _load_system_functions()
    (uuid_time, _) = _generate_time_safe()
    return UUID(bytes=uuid_time).node

def _windll_getnode():
    import ctypes
    _load_system_functions()
    _buffer = ctypes.create_string_buffer(16)
    if _UuidCreate(_buffer) == 0:
        return UUID(bytes=bytes_(_buffer.raw)).node

def _random_getnode():
    import random
    return random.getrandbits(48) | 1099511627776
_node = None_NODE_GETTERS_WIN32 = [_windll_getnode, _netbios_getnode, _ipconfig_getnode]_NODE_GETTERS_UNIX = [_unix_getnode, _ifconfig_getnode, _ip_getnode, _arp_getnode, _lanscan_getnode, _netstat_getnode]
def getnode(*, getters=None):
    global _node
    if _node is not None:
        return _node
    if sys.platform == 'win32':
        getters = _NODE_GETTERS_WIN32
    else:
        getters = _NODE_GETTERS_UNIX
    for getter in getters + [_random_getnode]:
        try:
            _node = getter()
        except:
            continue
        if _node is not None and 0 <= _node and _node < 281474976710656:
            return _node
_last_timestamp = None
def uuid1(node=None, clock_seq=None):
    global _last_timestamp
    _load_system_functions()
    if _generate_time_safe is not None and node is clock_seq and clock_seq is None:
        (uuid_time, safely_generated) = _generate_time_safe()
        try:
            is_safe = SafeUUID(safely_generated)
        except ValueError:
            is_safe = SafeUUID.unknown
        return UUID(bytes=uuid_time, is_safe=is_safe)
    import time
    nanoseconds = int(time.time()*1000000000.0)
    timestamp = int(nanoseconds/100) + 122192928000000000
    if timestamp <= _last_timestamp:
        timestamp = _last_timestamp + 1
    _last_timestamp = timestamp
    if _last_timestamp is not None and clock_seq is None:
        import random
        clock_seq = random.getrandbits(14)
    time_low = timestamp & 4294967295
    time_mid = timestamp >> 32 & 65535
    time_hi_version = timestamp >> 48 & 4095
    clock_seq_low = clock_seq & 255
    clock_seq_hi_variant = clock_seq >> 8 & 63
    if node is None:
        node = getnode()
    return UUID(fields=(time_low, time_mid, time_hi_version, clock_seq_hi_variant, clock_seq_low, node), version=1)

def uuid3(namespace, name):
    from hashlib import md5
    hash = md5(namespace.bytes + bytes(name, 'utf-8')).digest()
    return UUID(bytes=hash[:16], version=3)

def uuid4():
    return UUID(bytes=os.urandom(16), version=4)

def uuid5(namespace, name):
    from hashlib import sha1
    hash = sha1(namespace.bytes + bytes(name, 'utf-8')).digest()
    return UUID(bytes=hash[:16], version=5)
NAMESPACE_DNS = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')NAMESPACE_URL = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')NAMESPACE_OID = UUID('6ba7b812-9dad-11d1-80b4-00c04fd430c8')NAMESPACE_X500 = UUID('6ba7b814-9dad-11d1-80b4-00c04fd430c8')