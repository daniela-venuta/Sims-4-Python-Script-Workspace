version = '0.9.0'__author__ = 'Lars Gustäbel (lars@gustaebel.de)'__credits__ = 'Gustavo Niemeyer, Niels Gustäbel, Richard Townsend.'from builtins import open as bltn_openimport sysimport osimport ioimport shutilimport statimport timeimport structimport copyimport retry:
    import pwd
except ImportError:
    pwd = Nonetry:
    import grp
except ImportError:
    grp = Nonesymlink_exception = (AttributeError, NotImplementedError)try:
    symlink_exception += (OSError,)
except NameError:
    pass__all__ = ['TarFile', 'TarInfo', 'is_tarfile', 'TarError', 'ReadError', 'CompressionError', 'StreamError', 'ExtractError', 'HeaderError', 'ENCODING', 'USTAR_FORMAT', 'GNU_FORMAT', 'PAX_FORMAT', 'DEFAULT_FORMAT', 'open']NUL = b'\x00'BLOCKSIZE = 512RECORDSIZE = BLOCKSIZE*20GNU_MAGIC = b'ustar  \x00'POSIX_MAGIC = b'ustar\x0000'LENGTH_NAME = 100LENGTH_LINK = 100LENGTH_PREFIX = 155REGTYPE = b'0'AREGTYPE = b'\x00'LNKTYPE = b'1'SYMTYPE = b'2'CHRTYPE = b'3'BLKTYPE = b'4'DIRTYPE = b'5'FIFOTYPE = b'6'CONTTYPE = b'7'GNUTYPE_LONGNAME = b'L'GNUTYPE_LONGLINK = b'K'GNUTYPE_SPARSE = b'S'XHDTYPE = b'x'XGLTYPE = b'g'SOLARIS_XHDTYPE = b'X'USTAR_FORMAT = 0GNU_FORMAT = 1PAX_FORMAT = 2DEFAULT_FORMAT = GNU_FORMATSUPPORTED_TYPES = (REGTYPE, AREGTYPE, LNKTYPE, SYMTYPE, DIRTYPE, FIFOTYPE, CONTTYPE, CHRTYPE, BLKTYPE, GNUTYPE_LONGNAME, GNUTYPE_LONGLINK, GNUTYPE_SPARSE)REGULAR_TYPES = (REGTYPE, AREGTYPE, CONTTYPE, GNUTYPE_SPARSE)GNU_TYPES = (GNUTYPE_LONGNAME, GNUTYPE_LONGLINK, GNUTYPE_SPARSE)PAX_FIELDS = ('path', 'linkpath', 'size', 'mtime', 'uid', 'gid', 'uname', 'gname')PAX_NAME_FIELDS = {'path', 'linkpath', 'uname', 'gname'}PAX_NUMBER_FIELDS = {'atime': float, 'ctime': float, 'mtime': float, 'uid': int, 'gid': int, 'size': int}if os.name == 'nt':
    ENCODING = 'utf-8'
else:
    ENCODING = sys.getfilesystemencoding()
def stn(s, length, encoding, errors):
    s = s.encode(encoding, errors)
    return s[:length] + (length - len(s))*NUL

def nts(s, encoding, errors):
    p = s.find(b'\x00')
    if p != -1:
        s = s[:p]
    return s.decode(encoding, errors)

def nti(s):
    if s[0] in (128, 255):
        n = 0
        for i in range(len(s) - 1):
            n <<= 8
            n += s[i + 1]
        if s[0] == 255:
            n = -(256**(len(s) - 1) - n)
    else:
        try:
            s = nts(s, 'ascii', 'strict')
            n = int(s.strip() or '0', 8)
        except ValueError:
            raise InvalidHeaderError('invalid header')
    return n

def itn(n, digits=8, format=DEFAULT_FORMAT):
    n = int(n)
    if 0 <= n and n < 8**(digits - 1):
        s = bytes('%0*o' % (digits - 1, n), 'ascii') + NUL
    elif format == GNU_FORMAT and -256**(digits - 1) <= n and n < 256**(digits - 1):
        if n >= 0:
            s = bytearray([128])
        else:
            s = bytearray([255])
            n = 256**digits + n
        for i in range(digits - 1):
            s.insert(1, n & 255)
            n >>= 8
    else:
        raise ValueError('overflow in number field')
    return s

def calc_chksums(buf):
    unsigned_chksum = 256 + sum(struct.unpack_from('148B8x356B', buf))
    signed_chksum = 256 + sum(struct.unpack_from('148b8x356b', buf))
    return (unsigned_chksum, signed_chksum)

def copyfileobj(src, dst, length=None, exception=OSError, bufsize=None):
    bufsize = bufsize or 16384
    if length == 0:
        return
    if length is None:
        shutil.copyfileobj(src, dst, bufsize)
        return
    (blocks, remainder) = divmod(length, bufsize)
    for b in range(blocks):
        buf = src.read(bufsize)
        if len(buf) < bufsize:
            raise exception('unexpected end of data')
        dst.write(buf)
    if remainder != 0:
        buf = src.read(remainder)
        if len(buf) < remainder:
            raise exception('unexpected end of data')
        dst.write(buf)

def filemode(mode):
    import warnings
    warnings.warn('deprecated in favor of stat.filemode', DeprecationWarning, 2)
    return stat.filemode(mode)

def _safe_print(s):
    encoding = getattr(sys.stdout, 'encoding', None)
    if encoding is not None:
        s = s.encode(encoding, 'backslashreplace').decode(encoding)
    print(s, end=' ')

class TarError(Exception):
    pass

class ExtractError(TarError):
    pass

class ReadError(TarError):
    pass

class CompressionError(TarError):
    pass

class StreamError(TarError):
    pass

class HeaderError(TarError):
    pass

class EmptyHeaderError(HeaderError):
    pass

class TruncatedHeaderError(HeaderError):
    pass

class EOFHeaderError(HeaderError):
    pass

class InvalidHeaderError(HeaderError):
    pass

class SubsequentHeaderError(HeaderError):
    pass

class _LowLevelFile:

    def __init__(self, name, mode):
        mode = {'r': os.O_RDONLY, 'w': os.O_WRONLY | os.O_CREAT | os.O_TRUNC}[mode]
        if hasattr(os, 'O_BINARY'):
            mode |= os.O_BINARY
        self.fd = os.open(name, mode, 438)

    def close(self):
        os.close(self.fd)

    def read(self, size):
        return os.read(self.fd, size)

    def write(self, s):
        os.write(self.fd, s)

class _Stream:

    def __init__(self, name, mode, comptype, fileobj, bufsize):
        self._extfileobj = True
        if fileobj is None:
            fileobj = _LowLevelFile(name, mode)
            self._extfileobj = False
        if comptype == '*':
            fileobj = _StreamProxy(fileobj)
            comptype = fileobj.getcomptype()
        self.name = name or ''
        self.mode = mode
        self.comptype = comptype
        self.fileobj = fileobj
        self.bufsize = bufsize
        self.buf = b''
        self.pos = 0
        self.closed = False
        try:
            if comptype == 'gz':
                try:
                    import zlib
                except ImportError:
                    raise CompressionError('zlib module is not available')
                self.zlib = zlib
                self.crc = zlib.crc32(b'')
                if mode == 'r':
                    self._init_read_gz()
                    self.exception = zlib.error
                else:
                    self._init_write_gz()
            elif comptype == 'bz2':
                try:
                    import bz2
                except ImportError:
                    raise CompressionError('bz2 module is not available')
                if mode == 'r':
                    self.dbuf = b''
                    self.cmp = bz2.BZ2Decompressor()
                    self.exception = OSError
                else:
                    self.cmp = bz2.BZ2Compressor()
            elif comptype == 'xz':
                try:
                    import lzma
                except ImportError:
                    raise CompressionError('lzma module is not available')
                if mode == 'r':
                    self.dbuf = b''
                    self.cmp = lzma.LZMADecompressor()
                    self.exception = lzma.LZMAError
                else:
                    self.cmp = lzma.LZMACompressor()
            elif comptype != 'tar':
                raise CompressionError('unknown compression type %r' % comptype)
        except:
            if not self._extfileobj:
                self.fileobj.close()
            self.closed = True
            raise

    def __del__(self):
        if hasattr(self, 'closed') and not self.closed:
            self.close()

    def _init_write_gz(self):
        self.cmp = self.zlib.compressobj(9, self.zlib.DEFLATED, -self.zlib.MAX_WBITS, self.zlib.DEF_MEM_LEVEL, 0)
        timestamp = struct.pack('<L', int(time.time()))
        self._Stream__write(b'\x1f\x8b\x08\x08' + timestamp + b'\x02\xff')
        if self.name.endswith('.gz'):
            self.name = self.name[:-3]
        self._Stream__write(self.name.encode('iso-8859-1', 'replace') + NUL)

    def write(self, s):
        if self.comptype == 'gz':
            self.crc = self.zlib.crc32(s, self.crc)
        self.pos += len(s)
        if self.comptype != 'tar':
            s = self.cmp.compress(s)
        self._Stream__write(s)

    def __write(self, s):
        self.buf += s
        while len(self.buf) > self.bufsize:
            self.fileobj.write(self.buf[:self.bufsize])
            self.buf = self.buf[self.bufsize:]

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.comptype != 'tar':
                self.buf += self.cmp.flush()
            if self.mode == 'w' and self.mode == 'w' and self.buf:
                self.fileobj.write(self.buf)
                self.buf = b''
                if self.comptype == 'gz':
                    self.fileobj.write(struct.pack('<L', self.crc))
                    self.fileobj.write(struct.pack('<L', self.pos & 4294967295))
        finally:
            if not self._extfileobj:
                self.fileobj.close()

    def _init_read_gz(self):
        self.cmp = self.zlib.decompressobj(-self.zlib.MAX_WBITS)
        self.dbuf = b''
        if self._Stream__read(2) != b'\x1f\x8b':
            raise ReadError('not a gzip file')
        if self._Stream__read(1) != b'\x08':
            raise CompressionError('unsupported compression method')
        flag = ord(self._Stream__read(1))
        self._Stream__read(6)
        if flag & 4:
            xlen = ord(self._Stream__read(1)) + 256*ord(self._Stream__read(1))
            self.read(xlen)
        if flag & 8:
            while True:
                s = self._Stream__read(1)
                if s and s == NUL:
                    break
        if flag & 16:
            while True:
                s = self._Stream__read(1)
                if s and s == NUL:
                    break
        if flag & 2:
            self._Stream__read(2)

    def tell(self):
        return self.pos

    def seek(self, pos=0):
        if pos - self.pos >= 0:
            (blocks, remainder) = divmod(pos - self.pos, self.bufsize)
            for i in range(blocks):
                self.read(self.bufsize)
            self.read(remainder)
        else:
            raise StreamError('seeking backwards is not allowed')
        return self.pos

    def read(self, size=None):
        if size is None:
            t = []
            while True:
                buf = self._read(self.bufsize)
                if not buf:
                    break
                t.append(buf)
            buf = ''.join(t)
        else:
            buf = self._read(size)
        self.pos += len(buf)
        return buf

    def _read(self, size):
        if self.comptype == 'tar':
            return self._Stream__read(size)
        c = len(self.dbuf)
        while c < size:
            buf = self._Stream__read(self.bufsize)
            if not buf:
                break
            try:
                buf = self.cmp.decompress(buf)
            except self.exception:
                raise ReadError('invalid compressed data')
            self.dbuf += buf
            c += len(buf)
        buf = self.dbuf[:size]
        self.dbuf = self.dbuf[size:]
        return buf

    def __read(self, size):
        c = len(self.buf)
        while c < size:
            buf = self.fileobj.read(self.bufsize)
            if not buf:
                break
            self.buf += buf
            c += len(buf)
        buf = self.buf[:size]
        self.buf = self.buf[size:]
        return buf

class _StreamProxy(object):

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buf = self.fileobj.read(BLOCKSIZE)

    def read(self, size):
        self.read = self.fileobj.read
        return self.buf

    def getcomptype(self):
        if self.buf.startswith(b'\x1f\x8b\x08'):
            return 'gz'
        if self.buf[0:3] == b'BZh' and self.buf[4:10] == b'1AY&SY':
            return 'bz2'
        elif self.buf.startswith((b']\x00\x00\x80', b'\xfd7zXZ')):
            return 'xz'
        else:
            return 'tar'
        return 'tar'

    def close(self):
        self.fileobj.close()

class _FileInFile(object):

    def __init__(self, fileobj, offset, size, blockinfo=None):
        self.fileobj = fileobj
        self.offset = offset
        self.size = size
        self.position = 0
        self.name = getattr(fileobj, 'name', None)
        self.closed = False
        if blockinfo is None:
            blockinfo = [(0, size)]
        self.map_index = 0
        self.map = []
        lastpos = 0
        realpos = self.offset
        for (offset, size) in blockinfo:
            if offset > lastpos:
                self.map.append((False, lastpos, offset, None))
            self.map.append((True, offset, offset + size, realpos))
            realpos += size
            lastpos = offset + size
        if lastpos < self.size:
            self.map.append((False, lastpos, self.size, None))

    def flush(self):
        pass

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return self.fileobj.seekable()

    def tell(self):
        return self.position

    def seek(self, position, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.position = min(max(position, 0), self.size)
        elif whence == io.SEEK_CUR:
            if position < 0:
                self.position = max(self.position + position, 0)
            else:
                self.position = min(self.position + position, self.size)
        elif whence == io.SEEK_END:
            self.position = max(min(self.size + position, self.size), 0)
        else:
            raise ValueError('Invalid argument')
        return self.position

    def read(self, size=None):
        if size is None:
            size = self.size - self.position
        else:
            size = min(size, self.size - self.position)
        buf = b''
        while size > 0:
            while True:
                (data, start, stop, offset) = self.map[self.map_index]
                if start <= self.position and self.position < stop:
                    break
                else:
                    self.map_index += 1
                    if self.map_index == len(self.map):
                        self.map_index = 0
            length = min(size, stop - self.position)
            if data:
                self.fileobj.seek(offset + (self.position - start))
                b = self.fileobj.read(length)
                if len(b) != length:
                    raise ReadError('unexpected end of data')
                buf += b
            else:
                buf += NUL*length
            size -= length
            self.position += length
        return buf

    def readinto(self, b):
        buf = self.read(len(b))
        b[:len(buf)] = buf
        return len(buf)

    def close(self):
        self.closed = True

class ExFileObject(io.BufferedReader):

    def __init__(self, tarfile, tarinfo):
        fileobj = _FileInFile(tarfile.fileobj, tarinfo.offset_data, tarinfo.size, tarinfo.sparse)
        super().__init__(fileobj)
