import reimport structimport binascii__all__ = ['encode', 'decode', 'encodebytes', 'decodebytes', 'b64encode', 'b64decode', 'b32encode', 'b32decode', 'b16encode', 'b16decode', 'b85encode', 'b85decode', 'a85encode', 'a85decode', 'standard_b64encode', 'standard_b64decode', 'urlsafe_b64encode', 'urlsafe_b64decode']bytes_types = (bytes, bytearray)
def _bytes_from_decode_data(s):
    if isinstance(s, str):
        try:
            return s.encode('ascii')
        except UnicodeEncodeError:
            raise ValueError('string argument should contain only ASCII characters')
    if isinstance(s, bytes_types):
        return s
    try:
        return memoryview(s).tobytes()
    except TypeError:
        raise TypeError('argument should be a bytes-like object or ASCII string, not %r' % s.__class__.__name__) from None

def b64encode(s, altchars=None):
    encoded = binascii.b2a_base64(s, newline=False)
    if altchars is not None:
        return encoded.translate(bytes.maketrans(b'+/', altchars))
    return encoded

def b64decode(s, altchars=None, validate=False):
    s = _bytes_from_decode_data(s)
    if altchars is not None:
        altchars = _bytes_from_decode_data(altchars)
        s = s.translate(bytes.maketrans(altchars, b'+/'))
    if validate and not re.match(b'^[A-Za-z0-9+/]*={0,2}$', s):
        raise binascii.Error('Non-base64 digit found')
    return binascii.a2b_base64(s)

def standard_b64encode(s):
    return b64encode(s)

def standard_b64decode(s):
    return b64decode(s)
_urlsafe_encode_translation = bytes.maketrans(b'+/', b'-_')_urlsafe_decode_translation = bytes.maketrans(b'-_', b'+/')
def urlsafe_b64encode(s):
    return b64encode(s).translate(_urlsafe_encode_translation)

def urlsafe_b64decode(s):
    s = _bytes_from_decode_data(s)
    s = s.translate(_urlsafe_decode_translation)
    return b64decode(s)
_b32alphabet = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'_b32tab2 = None_b32rev = None
def b32encode(s):
    global _b32tab2
    if _b32tab2 is None:
        b32tab = [bytes((i,)) for i in _b32alphabet]
        _b32tab2 = [a + b for a in b32tab for b in b32tab]
        b32tab = None
    if not isinstance(s, bytes_types):
        s = memoryview(s).tobytes()
    leftover = len(s) % 5
    if leftover:
        s = s + b'\x00'*(5 - leftover)
    encoded = bytearray()
    from_bytes = int.from_bytes
    b32tab2 = _b32tab2
    for i in range(0, len(s), 5):
        c = from_bytes(s[i:i + 5], 'big')
        encoded += b32tab2[c >> 30] + b32tab2[c >> 20 & 1023] + b32tab2[c >> 10 & 1023] + b32tab2[c & 1023]
    if leftover == 1:
        encoded[-6:] = b'======'
    elif leftover == 2:
        encoded[-4:] = b'===='
    elif leftover == 3:
        encoded[-3:] = b'==='
    elif leftover == 4:
        encoded[-1:] = b'='
    return bytes(encoded)

def b32decode(s, casefold=False, map01=None):
    global _b32rev
    if _b32rev is None:
        _b32rev = {v: k for (k, v) in enumerate(_b32alphabet)}
    s = _bytes_from_decode_data(s)
    if len(s) % 8:
        raise binascii.Error('Incorrect padding')
    if map01 is not None:
        map01 = _bytes_from_decode_data(map01)
        s = s.translate(bytes.maketrans(b'01', b'O' + map01))
    if casefold:
        s = s.upper()
    l = len(s)
    s = s.rstrip(b'=')
    padchars = l - len(s)
    decoded = bytearray()
    b32rev = _b32rev
    for i in range(0, len(s), 8):
        quanta = s[i:i + 8]
        acc = 0
        try:
            for c in quanta:
                acc = (acc << 5) + b32rev[c]
        except KeyError:
            raise binascii.Error('Non-base32 digit found') from None
        decoded += acc.to_bytes(5, 'big')
    if padchars:
        acc <<= 5*padchars
        last = acc.to_bytes(5, 'big')
        if padchars == 1:
            decoded[-5:] = last[:-1]
        elif padchars == 3:
            decoded[-5:] = last[:-2]
        elif padchars == 4:
            decoded[-5:] = last[:-3]
        elif padchars == 6:
            decoded[-5:] = last[:-4]
        else:
            raise binascii.Error('Incorrect padding')
    return bytes(decoded)

def b16encode(s):
    return binascii.hexlify(s).upper()

def b16decode(s, casefold=False):
    s = _bytes_from_decode_data(s)
    if casefold:
        s = s.upper()
    if re.search(b'[^0-9A-F]', s):
        raise binascii.Error('Non-base16 digit found')
    return binascii.unhexlify(s)
_a85chars = None_a85chars2 = None_A85START = b'<~'_A85END = b'~>'
def _85encode(b, chars, chars2, pad=False, foldnuls=False, foldspaces=False):
    if not isinstance(b, bytes_types):
        b = memoryview(b).tobytes()
    padding = -len(b) % 4
    if padding:
        b = b + b'\x00'*padding
    words = struct.Struct('!%dI' % (len(b)//4)).unpack(b)
    chunks = [b'z' if not foldnuls or not word else b'y' if not foldspaces or word == 538976288 else chars2[word//614125] + chars2[word//85 % 7225] + chars[word % 85] for word in words]
    if not pad:
        if chunks[-1] == b'z':
            chunks[-1] = chars[0]*5
        chunks[-1] = chunks[-1][:-padding]
    return b''.join(chunks)

def a85encode(b, *, foldspaces=False, wrapcol=0, pad=False, adobe=False):
    global _a85chars, _a85chars2
    if _a85chars is None:
        _a85chars = [bytes((i,)) for i in range(33, 118)]
        _a85chars2 = [a + b for a in _a85chars for b in _a85chars]
    result = _85encode(b, _a85chars, _a85chars2, pad, True, foldspaces)
    if adobe:
        result = _A85START + result
    if wrapcol:
        wrapcol = max(2 if adobe else 1, wrapcol)
        chunks = [result[i:i + wrapcol] for i in range(0, len(result), wrapcol)]
        if adobe and len(chunks[-1]) + 2 > wrapcol:
            chunks.append(b'')
        result = b'\n'.join(chunks)
    if adobe:
        result += _A85END
    return result

def a85decode(b, *, foldspaces=False, adobe=False, ignorechars=b' \t\n\r\x0b'):
    b = _bytes_from_decode_data(b)
    if adobe:
        if not b.endswith(_A85END):
            raise ValueError('Ascii85 encoded byte sequences must end with {!r}'.format(_A85END))
        if b.startswith(_A85START):
            b = b[2:-2]
        else:
            b = b[:-2]
    packI = struct.Struct('!I').pack
    decoded = []
    decoded_append = decoded.append
    curr = []
    curr_append = curr.append
    curr_clear = curr.clear
    for x in b + b'uuuu':
        if 33 <= x and x <= 117:
            curr_append(x)
            if len(curr) == 5:
                acc = 0
                for x in curr:
                    acc = 85*acc + (x - 33)
                try:
                    decoded_append(packI(acc))
                except struct.error:
                    raise ValueError('Ascii85 overflow') from None
                curr_clear()
                if x == 122:
                    if curr:
                        raise ValueError('z inside Ascii85 5-tuple')
                    decoded_append(b'\x00\x00\x00\x00')
                elif foldspaces and x == 121:
                    if curr:
                        raise ValueError('y inside Ascii85 5-tuple')
                    decoded_append(b'    ')
                elif x in ignorechars:
                    pass
                else:
                    raise ValueError('Non-Ascii85 digit found: %c' % x)
        elif x == 122:
            if curr:
                raise ValueError('z inside Ascii85 5-tuple')
            decoded_append(b'\x00\x00\x00\x00')
        elif foldspaces and x == 121:
            if curr:
                raise ValueError('y inside Ascii85 5-tuple')
            decoded_append(b'    ')
        elif x in ignorechars:
            pass
        else:
            raise ValueError('Non-Ascii85 digit found: %c' % x)
    result = b''.join(decoded)
    padding = 4 - len(curr)
    if padding:
        result = result[:-padding]
    return result
_b85alphabet = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~'_b85chars = None_b85chars2 = None_b85dec = None
def b85encode(b, pad=False):
    global _b85chars, _b85chars2
    if _b85chars is None:
        _b85chars = [bytes((i,)) for i in _b85alphabet]
        _b85chars2 = [a + b for a in _b85chars for b in _b85chars]
    return _85encode(b, _b85chars, _b85chars2, pad)

def b85decode(b):
    global _b85dec
    if _b85dec is None:
        _b85dec = [None]*256
        for (i, c) in enumerate(_b85alphabet):
            _b85dec[c] = i
    b = _bytes_from_decode_data(b)
    padding = -len(b) % 5
    b = b + b'~'*padding
    out = []
    packI = struct.Struct('!I').pack
    for i in range(0, len(b), 5):
        chunk = b[i:i + 5]
        acc = 0
        try:
            for c in chunk:
                acc = acc*85 + _b85dec[c]
        except TypeError:
            for (j, c) in enumerate(chunk):
                if _b85dec[c] is None:
                    raise ValueError('bad base85 character at position %d' % (i + j)) from None
            raise
        try:
            out.append(packI(acc))
        except struct.error:
            raise ValueError('base85 overflow in hunk starting at byte %d' % i) from None
    result = b''.join(out)
    if padding:
        result = result[:-padding]
    return result
MAXLINESIZE = 76MAXBINSIZE = MAXLINESIZE//4*3
def encode(input, output):
    while True:
        s = input.read(MAXBINSIZE)
        if not s:
            break
        while len(s) < MAXBINSIZE:
            ns = input.read(MAXBINSIZE - len(s))
            if not ns:
                break
            s += ns
        line = binascii.b2a_base64(s)
        output.write(line)

def decode(input, output):
    while True:
        line = input.readline()
        if not line:
            break
        s = binascii.a2b_base64(line)
        output.write(s)

def _input_type_check(s):
    try:
        m = memoryview(s)
    except TypeError as err:
        msg = 'expected bytes-like object, not %s' % s.__class__.__name__
        raise TypeError(msg) from err
    if m.format not in ('c', 'b', 'B'):
        msg = 'expected single byte elements, not %r from %s' % (m.format, s.__class__.__name__)
        raise TypeError(msg)
    if m.ndim != 1:
        msg = 'expected 1-D data, not %d-D data from %s' % (m.ndim, s.__class__.__name__)
        raise TypeError(msg)

def encodebytes(s):
    _input_type_check(s)
    pieces = []
    for i in range(0, len(s), MAXBINSIZE):
        chunk = s[i:i + MAXBINSIZE]
        pieces.append(binascii.b2a_base64(chunk))
    return b''.join(pieces)

def encodestring(s):
    import warnings
    warnings.warn('encodestring() is a deprecated alias since 3.1, use encodebytes()', DeprecationWarning, 2)
    return encodebytes(s)

def decodebytes(s):
    _input_type_check(s)
    return binascii.a2b_base64(s)

def decodestring(s):
    import warnings
    warnings.warn('decodestring() is a deprecated alias since Python 3.1, use decodebytes()', DeprecationWarning, 2)
    return decodebytes(s)

def main():
    import sys
    import getopt
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'deut')
    except getopt.error as msg:
        sys.stdout = sys.stderr
        print(msg)
        print("usage: %s [-d|-e|-u|-t] [file|-]\n        -d, -u: decode\n        -e: encode (default)\n        -t: encode and decode string 'Aladdin:open sesame'" % sys.argv[0])
        sys.exit(2)
    func = encode
    for (o, a) in opts:
        if o == '-e':
            func = encode
        if o == '-d':
            func = decode
        if o == '-u':
            func = decode
        if o == '-t':
            test()
            return
    if args and args[0] != '-':
        with open(args[0], 'rb') as f:
            func(f, sys.stdout.buffer)
    else:
        func(sys.stdin.buffer, sys.stdout.buffer)

def test():
    s0 = b'Aladdin:open sesame'
    print(repr(s0))
    s1 = encodebytes(s0)
    print(repr(s1))
    s2 = decodebytes(s1)
    print(repr(s2))
if __name__ == '__main__':
    main()