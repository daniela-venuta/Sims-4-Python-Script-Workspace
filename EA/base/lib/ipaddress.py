__version__ = '1.0'import functoolsIPV4LENGTH = 32IPV6LENGTH = 128
class AddressValueError(ValueError):
    pass

class NetmaskValueError(ValueError):
    pass

def ip_address(address):
    try:
        return IPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError('%r does not appear to be an IPv4 or IPv6 address' % address)

def ip_network(address, strict=True):
    try:
        return IPv4Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError('%r does not appear to be an IPv4 or IPv6 network' % address)

def ip_interface(address):
    try:
        return IPv4Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError('%r does not appear to be an IPv4 or IPv6 interface' % address)

def v4_int_to_packed(address):
    try:
        return address.to_bytes(4, 'big')
    except OverflowError:
        raise ValueError('Address negative or too large for IPv4')

def v6_int_to_packed(address):
    try:
        return address.to_bytes(16, 'big')
    except OverflowError:
        raise ValueError('Address negative or too large for IPv6')

def _split_optional_netmask(address):
    addr = str(address).split('/')
    if len(addr) > 2:
        raise AddressValueError("Only one '/' permitted in %r" % address)
    return addr

def _find_address_range(addresses):
    it = iter(addresses)
    first = last = next(it)
    for ip in it:
        yield (first, last)
        first = ip
        last = ip
    yield (first, last)

def _count_righthand_zero_bits(number, bits):
    if number == 0:
        return bits
    return min(bits, (~number & number - 1).bit_length())

def summarize_address_range(first, last):
    if not (isinstance(first, _BaseAddress) and isinstance(last, _BaseAddress)):
        raise TypeError('first and last must be IP addresses, not networks')
    if first.version != last.version:
        raise TypeError('%s and %s are not of the same version' % (first, last))
    if first > last:
        raise ValueError('last IP address must be greater than first')
    if first.version == 4:
        ip = IPv4Network
    elif first.version == 6:
        ip = IPv6Network
    else:
        raise ValueError('unknown IP version')
    ip_bits = first._max_prefixlen
    first_int = first._ip
    last_int = last._ip
    while first_int <= last_int:
        nbits = min(_count_righthand_zero_bits(first_int, ip_bits), (last_int - first_int + 1).bit_length() - 1)
        net = ip((first_int, ip_bits - nbits))
        yield net
        first_int += 1 << nbits
        if first_int - 1 == ip._ALL_ONES:
            break

def _collapse_addresses_internal(addresses):
    to_merge = list(addresses)
    subnets = {}
    while to_merge:
        net = to_merge.pop()
        supernet = net.supernet()
        existing = subnets.get(supernet)
        if existing is None:
            subnets[supernet] = net
        elif existing != net:
            del subnets[supernet]
            to_merge.append(supernet)
    last = None
    for net in sorted(subnets.values()):
        if not last is not None or last.broadcast_address >= net.broadcast_address:
            pass
        else:
            yield net
            last = net

def collapse_addresses(addresses):
    addrs = []
    ips = []
    nets = []
    for ip in addresses:
        if isinstance(ip, _BaseAddress):
            if ips and ips[-1]._version != ip._version:
                raise TypeError('%s and %s are not of the same version' % (ip, ips[-1]))
            ips.append(ip)
        elif ip._prefixlen == ip._max_prefixlen:
            if ips and ips[-1]._version != ip._version:
                raise TypeError('%s and %s are not of the same version' % (ip, ips[-1]))
            try:
                ips.append(ip.ip)
            except AttributeError:
                ips.append(ip.network_address)
        else:
            if nets and nets[-1]._version != ip._version:
                raise TypeError('%s and %s are not of the same version' % (ip, nets[-1]))
            nets.append(ip)
    ips = sorted(set(ips))
    if ips:
        for (first, last) in _find_address_range(ips):
            addrs.extend(summarize_address_range(first, last))
    return _collapse_addresses_internal(addrs + nets)

def get_mixed_type_key(obj):
    if isinstance(obj, _BaseNetwork):
        return obj._get_networks_key()
    elif isinstance(obj, _BaseAddress):
        return obj._get_address_key()
    return NotImplemented

class _IPAddressBase:
    __slots__ = ()

    @property
    def exploded(self):
        return self._explode_shorthand_ip_string()

    @property
    def compressed(self):
        return str(self)

    @property
    def reverse_pointer(self):
        return self._reverse_pointer()

    @property
    def version(self):
        msg = '%200s has no version specified' % (type(self),)
        raise NotImplementedError(msg)

    def _check_int_address(self, address):
        if address < 0:
            msg = '%d (< 0) is not permitted as an IPv%d address'
            raise AddressValueError(msg % (address, self._version))
        if address > self._ALL_ONES:
            msg = '%d (>= 2**%d) is not permitted as an IPv%d address'
            raise AddressValueError(msg % (address, self._max_prefixlen, self._version))

    def _check_packed_address(self, address, expected_len):
        address_len = len(address)
        if address_len != expected_len:
            msg = '%r (len %d != %d) is not permitted as an IPv%d address'
            raise AddressValueError(msg % (address, address_len, expected_len, self._version))

    @classmethod
    def _ip_int_from_prefix(cls, prefixlen):
        return cls._ALL_ONES ^ cls._ALL_ONES >> prefixlen

    @classmethod
    def _prefix_from_ip_int(cls, ip_int):
        trailing_zeroes = _count_righthand_zero_bits(ip_int, cls._max_prefixlen)
        prefixlen = cls._max_prefixlen - trailing_zeroes
        leading_ones = ip_int >> trailing_zeroes
        all_ones = (1 << prefixlen) - 1
        if leading_ones != all_ones:
            byteslen = cls._max_prefixlen//8
            details = ip_int.to_bytes(byteslen, 'big')
            msg = 'Netmask pattern %r mixes zeroes & ones'
            raise ValueError(msg % details)
        return prefixlen

    @classmethod
    def _report_invalid_netmask(cls, netmask_str):
        msg = '%r is not a valid netmask' % netmask_str
        raise NetmaskValueError(msg) from None

    @classmethod
    def _prefix_from_prefix_string(cls, prefixlen_str):
        if not _BaseV4._DECIMAL_DIGITS.issuperset(prefixlen_str):
            cls._report_invalid_netmask(prefixlen_str)
        try:
            prefixlen = int(prefixlen_str)
        except ValueError:
            cls._report_invalid_netmask(prefixlen_str)
        if not (0 <= prefixlen and prefixlen <= cls._max_prefixlen):
            cls._report_invalid_netmask(prefixlen_str)
        return prefixlen

    @classmethod
    def _prefix_from_ip_string(cls, ip_str):
        try:
            ip_int = cls._ip_int_from_string(ip_str)
        except AddressValueError:
            cls._report_invalid_netmask(ip_str)
        try:
            return cls._prefix_from_ip_int(ip_int)
        except ValueError:
            pass
        ip_int ^= cls._ALL_ONES
        try:
            return cls._prefix_from_ip_int(ip_int)
        except ValueError:
            cls._report_invalid_netmask(ip_str)

    def __reduce__(self):
        return (self.__class__, (str(self),))

@functools.total_ordering
class _BaseAddress(_IPAddressBase):
    __slots__ = ()

    def __int__(self):
        return self._ip

    def __eq__(self, other):
        try:
            return self._ip == other._ip and self._version == other._version
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        if not isinstance(other, _BaseAddress):
            return NotImplemented
        else:
            if self._version != other._version:
                raise TypeError('%s and %s are not of the same version' % (self, other))
            if self._ip != other._ip:
                return self._ip < other._ip
        return False

    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__(int(self) + other)

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__(int(self) - other)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return str(self._string_from_ip_int(self._ip))

    def __hash__(self):
        return hash(hex(int(self._ip)))

    def _get_address_key(self):
        return (self._version, self)

    def __reduce__(self):
        return (self.__class__, (self._ip,))

@functools.total_ordering
class _BaseNetwork(_IPAddressBase):

    def __init__(self, address):
        self._cache = {}

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return '%s/%d' % (self.network_address, self.prefixlen)

    def hosts(self):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range(network + 1, broadcast):
            yield self._address_class(x)

    def __iter__(self):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range(network, broadcast + 1):
            yield self._address_class(x)

    def __getitem__(self, n):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        if n >= 0:
            if network + n > broadcast:
                raise IndexError('address out of range')
            return self._address_class(network + n)
        else:
            n += 1
            if broadcast + n < network:
                raise IndexError('address out of range')
            return self._address_class(broadcast + n)

    def __lt__(self, other):
        if not isinstance(other, _BaseNetwork):
            return NotImplemented
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same version' % (self, other))
        if self.network_address != other.network_address:
            return self.network_address < other.network_address
        elif self.netmask != other.netmask:
            return self.netmask < other.netmask
        return False

    def __eq__(self, other):
        try:
            return self._version == other._version and (self.network_address == other.network_address and int(self.netmask) == int(other.netmask))
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash(int(self.network_address) ^ int(self.netmask))

    def __contains__(self, other):
        if self._version != other._version:
            return False
        if isinstance(other, _BaseNetwork):
            return False
        return int(self.network_address) <= int(other._ip) <= int(self.broadcast_address)

    def overlaps(self, other):
        return self.network_address in other or (self.broadcast_address in other or (other.network_address in self or other.broadcast_address in self))

    @property
    def broadcast_address(self):
        x = self._cache.get('broadcast_address')
        if x is None:
            x = self._address_class(int(self.network_address) | int(self.hostmask))
            self._cache['broadcast_address'] = x
        return x

    @property
    def hostmask(self):
        x = self._cache.get('hostmask')
        if x is None:
            x = self._address_class(int(self.netmask) ^ self._ALL_ONES)
            self._cache['hostmask'] = x
        return x

    @property
    def with_prefixlen(self):
        return '%s/%d' % (self.network_address, self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self.network_address, self.netmask)

    @property
    def with_hostmask(self):
        return '%s/%s' % (self.network_address, self.hostmask)

    @property
    def num_addresses(self):
        return int(self.broadcast_address) - int(self.network_address) + 1

    @property
    def _address_class(self):
        msg = '%200s has no associated address class' % (type(self),)
        raise NotImplementedError(msg)

    @property
    def prefixlen(self):
        return self._prefixlen

    def address_exclude(self, other):
        if not self._version == other._version:
            raise TypeError('%s and %s are not of the same version' % (self, other))
        if not isinstance(other, _BaseNetwork):
            raise TypeError('%s is not a network object' % other)
        if not other.subnet_of(self):
            raise ValueError('%s not contained in %s' % (other, self))
        if other == self:
            return
        other = other.__class__('%s/%s' % (other.network_address, other.prefixlen))
        (s1, s2) = self.subnets()
        if other.subnet_of(s1):
            yield s2
            (s1, s2) = s1.subnets()
        elif other.subnet_of(s2):
            yield s1
            (s1, s2) = s2.subnets()
        else:
            raise AssertionError('Error performing exclusion: s1: %s s2: %s other: %s' % (s1, s2, other))
        if s1 != other and s2 != other and s1 == other:
            yield s2
        elif s2 == other:
            yield s1
        else:
            raise AssertionError('Error performing exclusion: s1: %s s2: %s other: %s' % (s1, s2, other))

    def compare_networks(self, other):
        if self._version != other._version:
            raise TypeError('%s and %s are not of the same type' % (self, other))
        if self.network_address < other.network_address:
            return -1
        if self.network_address > other.network_address:
            return 1
        if self.netmask < other.netmask:
            return -1
        elif self.netmask > other.netmask:
            return 1
        return 0

    def _get_networks_key(self):
        return (self._version, self.network_address, self.netmask)

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        if self._prefixlen == self._max_prefixlen:
            yield self
            return
        if new_prefix < self._prefixlen:
            raise ValueError('new prefix must be longer')
        if prefixlen_diff != 1:
            raise ValueError('cannot set prefixlen_diff and new_prefix')
        prefixlen_diff = new_prefix - self._prefixlen
        if new_prefix is not None and prefixlen_diff < 0:
            raise ValueError('prefix length diff must be > 0')
        new_prefixlen = self._prefixlen + prefixlen_diff
        if new_prefixlen > self._max_prefixlen:
            raise ValueError('prefix length diff %d is invalid for netblock %s' % (new_prefixlen, self))
        start = int(self.network_address)
        end = int(self.broadcast_address) + 1
        step = int(self.hostmask) + 1 >> prefixlen_diff
        for new_addr in range(start, end, step):
            current = self.__class__((new_addr, new_prefixlen))
            yield current

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        if self._prefixlen == 0:
            return self
        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError('new prefix must be shorter')
            if prefixlen_diff != 1:
                raise ValueError('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff = self._prefixlen - new_prefix
        new_prefixlen = self.prefixlen - prefixlen_diff
        if new_prefixlen < 0:
            raise ValueError('current prefixlen is %d, cannot have a prefixlen_diff of %d' % (self.prefixlen, prefixlen_diff))
        return self.__class__((int(self.network_address) & int(self.netmask) << prefixlen_diff, new_prefixlen))

    @property
    def is_multicast(self):
        return self.network_address.is_multicast and self.broadcast_address.is_multicast

    @staticmethod
    def _is_subnet_of(a, b):
        try:
            if a._version != b._version:
                raise TypeError(f'{a} and {b} are not of the same version')
            return b.network_address <= a.network_address and b.broadcast_address >= a.broadcast_address
        except AttributeError:
            raise TypeError(f'Unable to test subnet containment between {a} and {b}')

    def subnet_of(self, other):
        return self._is_subnet_of(self, other)

    def supernet_of(self, other):
        return self._is_subnet_of(other, self)

    @property
    def is_reserved(self):
        return self.network_address.is_reserved and self.broadcast_address.is_reserved

    @property
    def is_link_local(self):
        return self.network_address.is_link_local and self.broadcast_address.is_link_local

    @property
    def is_private(self):
        return self.network_address.is_private and self.broadcast_address.is_private

    @property
    def is_global(self):
        return not self.is_private

    @property
    def is_unspecified(self):
        return self.network_address.is_unspecified and self.broadcast_address.is_unspecified

    @property
    def is_loopback(self):
        return self.network_address.is_loopback and self.broadcast_address.is_loopback

class _BaseV4:
    __slots__ = ()
    _version = 4
    _ALL_ONES = 2**IPV4LENGTH - 1
    _DECIMAL_DIGITS = frozenset('0123456789')
    _valid_mask_octets = frozenset({255, 254, 252, 248, 240, 224, 192, 128, 0})
    _max_prefixlen = IPV4LENGTH
    _netmask_cache = {}

    def _explode_shorthand_ip_string(self):
        return str(self)

    @classmethod
    def _make_netmask(cls, arg):
        if arg not in cls._netmask_cache:
            if isinstance(arg, int):
                prefixlen = arg
            else:
                try:
                    prefixlen = cls._prefix_from_prefix_string(arg)
                except NetmaskValueError:
                    prefixlen = cls._prefix_from_ip_string(arg)
            netmask = IPv4Address(cls._ip_int_from_prefix(prefixlen))
            cls._netmask_cache[arg] = (netmask, prefixlen)
        return cls._netmask_cache[arg]

    @classmethod
    def _ip_int_from_string(cls, ip_str):
        if not ip_str:
            raise AddressValueError('Address cannot be empty')
        octets = ip_str.split('.')
        if len(octets) != 4:
            raise AddressValueError('Expected 4 octets in %r' % ip_str)
        try:
            return int.from_bytes(map(cls._parse_octet, octets), 'big')
        except ValueError as exc:
            raise AddressValueError('%s in %r' % (exc, ip_str)) from None

    @classmethod
    def _parse_octet(cls, octet_str):
        if not octet_str:
            raise ValueError('Empty octet not permitted')
        if not cls._DECIMAL_DIGITS.issuperset(octet_str):
            msg = 'Only decimal digits permitted in %r'
            raise ValueError(msg % octet_str)
        if len(octet_str) > 3:
            msg = 'At most 3 characters permitted in %r'
            raise ValueError(msg % octet_str)
        octet_int = int(octet_str, 10)
        if octet_int > 7 and octet_str[0] == '0':
            msg = 'Ambiguous (octal/decimal) value in %r not permitted'
            raise ValueError(msg % octet_str)
        if octet_int > 255:
            raise ValueError('Octet %d (> 255) not permitted' % octet_int)
        return octet_int

    @classmethod
    def _string_from_ip_int(cls, ip_int):
        return '.'.join(map(str, ip_int.to_bytes(4, 'big')))

    def _is_valid_netmask(self, netmask):
        mask = netmask.split('.')
        if len(mask) == 4:
            try:
                for x in mask:
                    if int(x) not in self._valid_mask_octets:
                        return False
            except ValueError:
                return False
            for (idx, y) in enumerate(mask):
                if idx > 0 and y > mask[idx - 1]:
                    return False
            return True
        try:
            netmask = int(netmask)
        except ValueError:
            return False
        return 0 <= netmask <= self._max_prefixlen

    def _is_hostmask(self, ip_str):
        bits = ip_str.split('.')
        try:
            parts = [x for x in map(int, bits) if x in self._valid_mask_octets]
        except ValueError:
            return False
        if len(parts) != len(bits):
            return False
        elif parts[0] < parts[-1]:
            return True
        return False

    def _reverse_pointer(self):
        reverse_octets = str(self).split('.')[::-1]
        return '.'.join(reverse_octets) + '.in-addr.arpa'

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def version(self):
        return self._version

class IPv4Address(_BaseV4, _BaseAddress):
    __slots__ = ('_ip', '__weakref__')

    def __init__(self, address):
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            return
        if isinstance(address, bytes):
            self._check_packed_address(address, 4)
            self._ip = int.from_bytes(address, 'big')
            return
        addr_str = str(address)
        if '/' in addr_str:
            raise AddressValueError("Unexpected '/' in %r" % address)
        self._ip = self._ip_int_from_string(addr_str)

    @property
    def packed(self):
        return v4_int_to_packed(self._ip)

    @property
    def is_reserved(self):
        return self in self._constants._reserved_network

    @property
    @functools.lru_cache()
    def is_private(self):
        return any(self in net for net in self._constants._private_networks)

    @property
    @functools.lru_cache()
    def is_global(self):
        return self not in self._constants._public_network and not self.is_private

    @property
    def is_multicast(self):
        return self in self._constants._multicast_network

    @property
    def is_unspecified(self):
        return self == self._constants._unspecified_address

    @property
    def is_loopback(self):
        return self in self._constants._loopback_network

    @property
    def is_link_local(self):
        return self in self._constants._linklocal_network

class IPv4Interface(IPv4Address):

    def __init__(self, address):
        if isinstance(address, (bytes, int)):
            IPv4Address.__init__(self, address)
            self.network = IPv4Network(self._ip)
            self._prefixlen = self._max_prefixlen
            return
        if isinstance(address, tuple):
            IPv4Address.__init__(self, address[0])
            if len(address) > 1:
                self._prefixlen = int(address[1])
            else:
                self._prefixlen = self._max_prefixlen
            self.network = IPv4Network(address, strict=False)
            self.netmask = self.network.netmask
            self.hostmask = self.network.hostmask
            return
        addr = _split_optional_netmask(address)
        IPv4Address.__init__(self, addr[0])
        self.network = IPv4Network(address, strict=False)
        self._prefixlen = self.network._prefixlen
        self.netmask = self.network.netmask
        self.hostmask = self.network.hostmask

    def __str__(self):
        return '%s/%d' % (self._string_from_ip_int(self._ip), self.network.prefixlen)

    def __eq__(self, other):
        address_equal = IPv4Address.__eq__(self, other)
        if address_equal and address_equal is NotImplemented:
            return address_equal
        try:
            return self.network == other.network
        except AttributeError:
            return False

    def __lt__(self, other):
        address_less = IPv4Address.__lt__(self, other)
        if address_less is NotImplemented:
            return NotImplemented
        try:
            return self.network < other.network or self.network == other.network and address_less
        except AttributeError:
            return False

    def __hash__(self):
        return self._ip ^ self._prefixlen ^ int(self.network.network_address)

    __reduce__ = _IPAddressBase.__reduce__

    @property
    def ip(self):
        return IPv4Address(self._ip)

    @property
    def with_prefixlen(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip), self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip), self.netmask)

    @property
    def with_hostmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip), self.hostmask)

class IPv4Network(_BaseV4, _BaseNetwork):
    _address_class = IPv4Address

    def __init__(self, address, strict=True):
        _BaseNetwork.__init__(self, address)
        if isinstance(address, (int, bytes)):
            addr = address
            mask = self._max_prefixlen
        elif isinstance(address, tuple):
            addr = address[0]
            mask = address[1] if len(address) > 1 else self._max_prefixlen
        else:
            args = _split_optional_netmask(address)
            addr = self._ip_int_from_string(args[0])
            mask = args[1] if len(args) == 2 else self._max_prefixlen
        self.network_address = IPv4Address(addr)
        (self.netmask, self._prefixlen) = self._make_netmask(mask)
        packed = int(self.network_address)
        if packed & int(self.netmask) != packed:
            if strict:
                raise ValueError('%s has host bits set' % self)
            else:
                self.network_address = IPv4Address(packed & int(self.netmask))
        if self._prefixlen == self._max_prefixlen - 1:
            self.hosts = self.__iter__

    @property
    @functools.lru_cache()
    def is_global(self):
        return not (self.network_address in IPv4Network('100.64.0.0/10') and self.broadcast_address in IPv4Network('100.64.0.0/10')) and not self.is_private

class _IPv4Constants:
    _linklocal_network = IPv4Network('169.254.0.0/16')
    _loopback_network = IPv4Network('127.0.0.0/8')
    _multicast_network = IPv4Network('224.0.0.0/4')
    _public_network = IPv4Network('100.64.0.0/10')
    _private_networks = [IPv4Network('0.0.0.0/8'), IPv4Network('10.0.0.0/8'), IPv4Network('127.0.0.0/8'), IPv4Network('169.254.0.0/16'), IPv4Network('172.16.0.0/12'), IPv4Network('192.0.0.0/29'), IPv4Network('192.0.0.170/31'), IPv4Network('192.0.2.0/24'), IPv4Network('192.168.0.0/16'), IPv4Network('198.18.0.0/15'), IPv4Network('198.51.100.0/24'), IPv4Network('203.0.113.0/24'), IPv4Network('240.0.0.0/4'), IPv4Network('255.255.255.255/32')]
    _reserved_network = IPv4Network('240.0.0.0/4')
    _unspecified_address = IPv4Address('0.0.0.0')
IPv4Address._constants = _IPv4Constants
class _BaseV6:
    __slots__ = ()
    _version = 6
    _ALL_ONES = 2**IPV6LENGTH - 1
    _HEXTET_COUNT = 8
    _HEX_DIGITS = frozenset('0123456789ABCDEFabcdef')
    _max_prefixlen = IPV6LENGTH
    _netmask_cache = {}

    @classmethod
    def _make_netmask(cls, arg):
        if arg not in cls._netmask_cache:
            if isinstance(arg, int):
                prefixlen = arg
            else:
                prefixlen = cls._prefix_from_prefix_string(arg)
            netmask = IPv6Address(cls._ip_int_from_prefix(prefixlen))
            cls._netmask_cache[arg] = (netmask, prefixlen)
        return cls._netmask_cache[arg]

    @classmethod
    def _ip_int_from_string(cls, ip_str):
        if not ip_str:
            raise AddressValueError('Address cannot be empty')
        parts = ip_str.split(':')
        _min_parts = 3
        if len(parts) < _min_parts:
            msg = 'At least %d parts expected in %r' % (_min_parts, ip_str)
            raise AddressValueError(msg)
        if '.' in parts[-1]:
            try:
                ipv4_int = IPv4Address(parts.pop())._ip
            except AddressValueError as exc:
                raise AddressValueError('%s in %r' % (exc, ip_str)) from None
            parts.append('%x' % (ipv4_int >> 16 & 65535))
            parts.append('%x' % (ipv4_int & 65535))
        _max_parts = cls._HEXTET_COUNT + 1
        if len(parts) > _max_parts:
            msg = 'At most %d colons permitted in %r' % (_max_parts - 1, ip_str)
            raise AddressValueError(msg)
        skip_index = None
        for i in range(1, len(parts) - 1):
            if not parts[i]:
                if skip_index is not None:
                    msg = "At most one '::' permitted in %r" % ip_str
                    raise AddressValueError(msg)
                skip_index = i
        if skip_index is not None:
            parts_hi = skip_index
            parts_lo = len(parts) - skip_index - 1
            if not parts[0]:
                parts_hi -= 1
                if parts_hi:
                    msg = "Leading ':' only permitted as part of '::' in %r"
                    raise AddressValueError(msg % ip_str)
            if not parts[-1]:
                parts_lo -= 1
                if parts_lo:
                    msg = "Trailing ':' only permitted as part of '::' in %r"
                    raise AddressValueError(msg % ip_str)
            parts_skipped = cls._HEXTET_COUNT - (parts_hi + parts_lo)
            if parts_skipped < 1:
                msg = "Expected at most %d other parts with '::' in %r"
                raise AddressValueError(msg % (cls._HEXTET_COUNT - 1, ip_str))
        else:
            if len(parts) != cls._HEXTET_COUNT:
                msg = "Exactly %d parts expected without '::' in %r"
                raise AddressValueError(msg % (cls._HEXTET_COUNT, ip_str))
            if not parts[0]:
                msg = "Leading ':' only permitted as part of '::' in %r"
                raise AddressValueError(msg % ip_str)
            if not parts[-1]:
                msg = "Trailing ':' only permitted as part of '::' in %r"
                raise AddressValueError(msg % ip_str)
            parts_hi = len(parts)
            parts_lo = 0
            parts_skipped = 0
        try:
            ip_int = 0
            for i in range(parts_hi):
                ip_int <<= 16
                ip_int |= cls._parse_hextet(parts[i])
            ip_int <<= 16*parts_skipped
            for i in range(-parts_lo, 0):
                ip_int <<= 16
                ip_int |= cls._parse_hextet(parts[i])
            return ip_int
        except ValueError as exc:
            raise AddressValueError('%s in %r' % (exc, ip_str)) from None

    @classmethod
    def _parse_hextet(cls, hextet_str):
        if not cls._HEX_DIGITS.issuperset(hextet_str):
            raise ValueError('Only hex digits permitted in %r' % hextet_str)
        if len(hextet_str) > 4:
            msg = 'At most 4 characters permitted in %r'
            raise ValueError(msg % hextet_str)
        return int(hextet_str, 16)

    @classmethod
    def _compress_hextets(cls, hextets):
        best_doublecolon_start = -1
        best_doublecolon_len = 0
        doublecolon_start = -1
        doublecolon_len = 0
        for (index, hextet) in enumerate(hextets):
            if hextet == '0':
                doublecolon_len += 1
                if doublecolon_start == -1:
                    doublecolon_start = index
                if doublecolon_len > best_doublecolon_len:
                    best_doublecolon_len = doublecolon_len
                    best_doublecolon_start = doublecolon_start
                    doublecolon_len = 0
                    doublecolon_start = -1
            else:
                doublecolon_len = 0
                doublecolon_start = -1
        if best_doublecolon_len > 1:
            best_doublecolon_end = best_doublecolon_start + best_doublecolon_len
            if best_doublecolon_end == len(hextets):
                hextets += ['']
            hextets[best_doublecolon_start:best_doublecolon_end] = ['']
            if best_doublecolon_start == 0:
                hextets = [''] + hextets
        return hextets

    @classmethod
    def _string_from_ip_int(cls, ip_int=None):
        if ip_int is None:
            ip_int = int(cls._ip)
        if ip_int > cls._ALL_ONES:
            raise ValueError('IPv6 address is too large')
        hex_str = '%032x' % ip_int
        hextets = ['%x' % int(hex_str[x:x + 4], 16) for x in range(0, 32, 4)]
        hextets = cls._compress_hextets(hextets)
        return ':'.join(hextets)

    def _explode_shorthand_ip_string(self):
        if isinstance(self, IPv6Network):
            ip_str = str(self.network_address)
        elif isinstance(self, IPv6Interface):
            ip_str = str(self.ip)
        else:
            ip_str = str(self)
        ip_int = self._ip_int_from_string(ip_str)
        hex_str = '%032x' % ip_int
        parts = [hex_str[x:x + 4] for x in range(0, 32, 4)]
        if isinstance(self, (_BaseNetwork, IPv6Interface)):
            return '%s/%d' % (':'.join(parts), self._prefixlen)
        return ':'.join(parts)

    def _reverse_pointer(self):
        reverse_chars = self.exploded[::-1].replace(':', '')
        return '.'.join(reverse_chars) + '.ip6.arpa'

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def version(self):
        return self._version

class IPv6Address(_BaseV6, _BaseAddress):
    __slots__ = ('_ip', '__weakref__')

    def __init__(self, address):
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            return
        if isinstance(address, bytes):
            self._check_packed_address(address, 16)
            self._ip = int.from_bytes(address, 'big')
            return
        addr_str = str(address)
        if '/' in addr_str:
            raise AddressValueError("Unexpected '/' in %r" % address)
        self._ip = self._ip_int_from_string(addr_str)

    @property
    def packed(self):
        return v6_int_to_packed(self._ip)

    @property
    def is_multicast(self):
        return self in self._constants._multicast_network

    @property
    def is_reserved(self):
        return any(self in x for x in self._constants._reserved_networks)

    @property
    def is_link_local(self):
        return self in self._constants._linklocal_network

    @property
    def is_site_local(self):
        return self in self._constants._sitelocal_network

    @property
    @functools.lru_cache()
    def is_private(self):
        return any(self in net for net in self._constants._private_networks)

    @property
    def is_global(self):
        return not self.is_private

    @property
    def is_unspecified(self):
        return self._ip == 0

    @property
    def is_loopback(self):
        return self._ip == 1

    @property
    def ipv4_mapped(self):
        if self._ip >> 32 != 65535:
            return
        return IPv4Address(self._ip & 4294967295)

    @property
    def teredo(self):
        if self._ip >> 96 != 536936448:
            return
        return (IPv4Address(self._ip >> 64 & 4294967295), IPv4Address(~self._ip & 4294967295))

    @property
    def sixtofour(self):
        if self._ip >> 112 != 8194:
            return
        return IPv4Address(self._ip >> 80 & 4294967295)

class IPv6Interface(IPv6Address):

    def __init__(self, address):
        if isinstance(address, (bytes, int)):
            IPv6Address.__init__(self, address)
            self.network = IPv6Network(self._ip)
            self._prefixlen = self._max_prefixlen
            return
        if isinstance(address, tuple):
            IPv6Address.__init__(self, address[0])
            if len(address) > 1:
                self._prefixlen = int(address[1])
            else:
                self._prefixlen = self._max_prefixlen
            self.network = IPv6Network(address, strict=False)
            self.netmask = self.network.netmask
            self.hostmask = self.network.hostmask
            return
        addr = _split_optional_netmask(address)
        IPv6Address.__init__(self, addr[0])
        self.network = IPv6Network(address, strict=False)
        self.netmask = self.network.netmask
        self._prefixlen = self.network._prefixlen
        self.hostmask = self.network.hostmask

    def __str__(self):
        return '%s/%d' % (self._string_from_ip_int(self._ip), self.network.prefixlen)

    def __eq__(self, other):
        address_equal = IPv6Address.__eq__(self, other)
        if address_equal and address_equal is NotImplemented:
            return address_equal
        try:
            return self.network == other.network
        except AttributeError:
            return False

    def __lt__(self, other):
        address_less = IPv6Address.__lt__(self, other)
        if address_less is NotImplemented:
            return NotImplemented
        try:
            return self.network < other.network or self.network == other.network and address_less
        except AttributeError:
            return False

    def __hash__(self):
        return self._ip ^ self._prefixlen ^ int(self.network.network_address)

    __reduce__ = _IPAddressBase.__reduce__

    @property
    def ip(self):
        return IPv6Address(self._ip)

    @property
    def with_prefixlen(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip), self._prefixlen)

    @property
    def with_netmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip), self.netmask)

    @property
    def with_hostmask(self):
        return '%s/%s' % (self._string_from_ip_int(self._ip), self.hostmask)

    @property
    def is_unspecified(self):
        return self._ip == 0 and self.network.is_unspecified

    @property
    def is_loopback(self):
        return self._ip == 1 and self.network.is_loopback

class IPv6Network(_BaseV6, _BaseNetwork):
    _address_class = IPv6Address

    def __init__(self, address, strict=True):
        _BaseNetwork.__init__(self, address)
        if isinstance(address, (int, bytes)):
            addr = address
            mask = self._max_prefixlen
        elif isinstance(address, tuple):
            addr = address[0]
            mask = address[1] if len(address) > 1 else self._max_prefixlen
        else:
            args = _split_optional_netmask(address)
            addr = self._ip_int_from_string(args[0])
            mask = args[1] if len(args) == 2 else self._max_prefixlen
        self.network_address = IPv6Address(addr)
        (self.netmask, self._prefixlen) = self._make_netmask(mask)
        packed = int(self.network_address)
        if packed & int(self.netmask) != packed:
            if strict:
                raise ValueError('%s has host bits set' % self)
            else:
                self.network_address = IPv6Address(packed & int(self.netmask))
        if self._prefixlen == self._max_prefixlen - 1:
            self.hosts = self.__iter__

    def hosts(self):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range(network + 1, broadcast + 1):
            yield self._address_class(x)

    @property
    def is_site_local(self):
        return self.network_address.is_site_local and self.broadcast_address.is_site_local

class _IPv6Constants:
    _linklocal_network = IPv6Network('fe80::/10')
    _multicast_network = IPv6Network('ff00::/8')
    _private_networks = [IPv6Network('::1/128'), IPv6Network('::/128'), IPv6Network('::ffff:0:0/96'), IPv6Network('100::/64'), IPv6Network('2001::/23'), IPv6Network('2001:2::/48'), IPv6Network('2001:db8::/32'), IPv6Network('2001:10::/28'), IPv6Network('fc00::/7'), IPv6Network('fe80::/10')]
    _reserved_networks = [IPv6Network('::/8'), IPv6Network('100::/8'), IPv6Network('200::/7'), IPv6Network('400::/6'), IPv6Network('800::/5'), IPv6Network('1000::/4'), IPv6Network('4000::/3'), IPv6Network('6000::/3'), IPv6Network('8000::/3'), IPv6Network('A000::/3'), IPv6Network('C000::/3'), IPv6Network('E000::/4'), IPv6Network('F000::/5'), IPv6Network('F800::/6'), IPv6Network('FE00::/9')]
    _sitelocal_network = IPv6Network('fec0::/10')
IPv6Address._constants = _IPv6Constants