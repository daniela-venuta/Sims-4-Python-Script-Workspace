import osimport abcimport codecsimport errnoimport statimport sysfrom _thread import allocate_lock as Lockif sys.platform in frozenset({'win32', 'cygwin'}):
    from msvcrt import setmode as _setmode
else:
    _setmode = Noneimport iofrom io import __all__, SEEK_SET, SEEK_CUR, SEEK_ENDvalid_seek_flags = {0, 1, 2}if hasattr(os, 'SEEK_HOLE'):
    valid_seek_flags.add(os.SEEK_HOLE)
    valid_seek_flags.add(os.SEEK_DATA)DEFAULT_BUFFER_SIZE = 8192BlockingIOError = BlockingIOError
def open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if not isinstance(file, int):
        file = os.fspath(file)
    if not isinstance(file, (str, bytes, int)):
        raise TypeError('invalid file: %r' % file)
    if not isinstance(mode, str):
        raise TypeError('invalid mode: %r' % mode)
    if not isinstance(buffering, int):
        raise TypeError('invalid buffering: %r' % buffering)
    if encoding is not None and not isinstance(encoding, str):
        raise TypeError('invalid encoding: %r' % encoding)
    if errors is not None and not isinstance(errors, str):
        raise TypeError('invalid errors: %r' % errors)
    modes = set(mode)
    if modes - set('axrwb+tU') or len(mode) > len(modes):
        raise ValueError('invalid mode: %r' % mode)
    creating = 'x' in modes
    reading = 'r' in modes
    writing = 'w' in modes
    appending = 'a' in modes
    updating = '+' in modes
    text = 't' in modes
    binary = 'b' in modes
    if 'U' in modes:
        if creating or (writing or appending) or updating:
            raise ValueError("mode U cannot be combined with 'x', 'w', 'a', or '+'")
        import warnings
        warnings.warn("'U' mode is deprecated", DeprecationWarning, 2)
        reading = True
    if text and binary:
        raise ValueError("can't have text and binary mode at once")
    if creating + reading + writing + appending > 1:
        raise ValueError("can't have read/write/append mode at once")
    if creating or (reading or writing) or not appending:
        raise ValueError('must have exactly one of read/write/append mode')
    if binary and encoding is not None:
        raise ValueError("binary mode doesn't take an encoding argument")
    if binary and errors is not None:
        raise ValueError("binary mode doesn't take an errors argument")
    if binary and newline is not None:
        raise ValueError("binary mode doesn't take a newline argument")
    if creating:
        pass
    if reading:
        pass
    if writing:
        pass
    if appending:
        pass
    if updating:
        pass
    raw = FileIO(file, '' + '' + '' + '' + '', closefd, opener=opener)
    result = raw
    try:
        line_buffering = False
        if raw.isatty():
            buffering = -1
            line_buffering = True
        if (buffering == 1 or buffering < 0) and buffering < 0:
            buffering = DEFAULT_BUFFER_SIZE
            try:
                bs = os.fstat(raw.fileno()).st_blksize
            except (OSError, AttributeError):
                pass
            if bs > 1:
                buffering = bs
        if buffering < 0:
            raise ValueError('invalid buffering size')
        if buffering == 0:
            if binary:
                return result
            raise ValueError("can't have unbuffered text I/O")
        if updating:
            buffer = BufferedRandom(raw, buffering)
        elif creating or writing or appending:
            buffer = BufferedWriter(raw, buffering)
        elif reading:
            buffer = BufferedReader(raw, buffering)
        else:
            raise ValueError('unknown mode: %r' % mode)
        result = buffer
        if binary:
            return result
        text = TextIOWrapper(buffer, encoding, errors, newline, line_buffering)
        result = text
        text.mode = mode
        return result
    except:
        result.close()
        raise

class DocDescriptor:

    def __get__(self, obj, typ):
        return "open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True)\n\n" + open.__doc__

class OpenWrapper:
    __doc__ = DocDescriptor()

    def __new__(cls, *args, **kwargs):
        return open(*args, **kwargs)
try:
    UnsupportedOperation = io.UnsupportedOperation
except AttributeError:

    class UnsupportedOperation(OSError, ValueError):
        pass

class IOBase(metaclass=abc.ABCMeta):

    def _unsupported(self, name):
        raise UnsupportedOperation('%s.%s() not supported' % (self.__class__.__name__, name))

    def seek(self, pos, whence=0):
        self._unsupported('seek')

    def tell(self):
        return self.seek(0, 1)

    def truncate(self, pos=None):
        self._unsupported('truncate')

    def flush(self):
        self._checkClosed()

    _IOBase__closed = False

    def close(self):
        if not self._IOBase__closed:
            try:
                self.flush()
            finally:
                self._IOBase__closed = True

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def seekable(self):
        return False

    def _checkSeekable(self, msg=None):
        if not self.seekable():
            raise UnsupportedOperation('File or stream is not seekable.' if msg is None else msg)

    def readable(self):
        return False

    def _checkReadable(self, msg=None):
        if not self.readable():
            raise UnsupportedOperation('File or stream is not readable.' if msg is None else msg)

    def writable(self):
        return False

    def _checkWritable(self, msg=None):
        if not self.writable():
            raise UnsupportedOperation('File or stream is not writable.' if msg is None else msg)

    @property
    def closed(self):
        return self._IOBase__closed

    def _checkClosed(self, msg=None):
        if self.closed:
            raise ValueError('I/O operation on closed file.' if msg is None else msg)

    def __enter__(self):
        self._checkClosed()
        return self

    def __exit__(self, *args):
        self.close()

    def fileno(self):
        self._unsupported('fileno')

    def isatty(self):
        self._checkClosed()
        return False

    def readline(self, size=-1):
        if hasattr(self, 'peek'):

            def nreadahead():
                readahead = self.peek(1)
                if not readahead:
                    return 1
                n = readahead.find(b'\n') + 1 or len(readahead)
                if size >= 0:
                    n = min(n, size)
                return n

        else:

            def nreadahead():
                return 1

        if size is None:
            size = -1
        else:
            try:
                size_index = size.__index__
            except AttributeError:
                raise TypeError(f'{size} is not an integer')
            size = size_index()
        res = bytearray()
        while True:
            while size < 0 or len(res) < size:
                b = self.read(nreadahead())
                if not b:
                    break
                res += b
                if res.endswith(b'\n'):
                    break
        return bytes(res)

    def __iter__(self):
        self._checkClosed()
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def readlines(self, hint=None):
        if hint is None or hint <= 0:
            return list(self)
        n = 0
        lines = []
        for line in self:
            lines.append(line)
            n += len(line)
            if n >= hint:
                break
        return lines

    def writelines(self, lines):
        self._checkClosed()
        for line in lines:
            self.write(line)
io.IOBase.register(IOBase)
class RawIOBase(IOBase):

    def read(self, size=-1):
        if size is None:
            size = -1
        if size < 0:
            return self.readall()
        b = bytearray(size.__index__())
        n = self.readinto(b)
        if n is None:
            return
        del b[n:]
        return bytes(b)

    def readall(self):
        res = bytearray()
        while True:
            data = self.read(DEFAULT_BUFFER_SIZE)
            if not data:
                break
            res += data
        if res:
            return bytes(res)
        else:
            return data

    def readinto(self, b):
        self._unsupported('readinto')

    def write(self, b):
        self._unsupported('write')
io.RawIOBase.register(RawIOBase)from _io import FileIORawIOBase.register(FileIO)
class BufferedIOBase(IOBase):

    def read(self, size=-1):
        self._unsupported('read')

    def read1(self, size=-1):
        self._unsupported('read1')

    def readinto(self, b):
        return self._readinto(b, read1=False)

    def readinto1(self, b):
        return self._readinto(b, read1=True)

    def _readinto(self, b, read1):
        if not isinstance(b, memoryview):
            b = memoryview(b)
        b = b.cast('B')
        if read1:
            data = self.read1(len(b))
        else:
            data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def write(self, b):
        self._unsupported('write')

    def detach(self):
        self._unsupported('detach')
io.BufferedIOBase.register(BufferedIOBase)
class _BufferedIOMixin(BufferedIOBase):

    def __init__(self, raw):
        self._raw = raw

    def seek(self, pos, whence=0):
        new_position = self.raw.seek(pos, whence)
        if new_position < 0:
            raise OSError('seek() returned an invalid position')
        return new_position

    def tell(self):
        pos = self.raw.tell()
        if pos < 0:
            raise OSError('tell() returned an invalid position')
        return pos

    def truncate(self, pos=None):
        self.flush()
        if pos is None:
            pos = self.tell()
        return self.raw.truncate(pos)

    def flush(self):
        if self.closed:
            raise ValueError('flush on closed file')
        self.raw.flush()

    def close(self):
        if not self.closed:
            try:
                self.flush()
            finally:
                self.raw.close()

    def detach(self):
        if self.raw is None:
            raise ValueError('raw stream already detached')
        self.flush()
        raw = self._raw
        self._raw = None
        return raw

    def seekable(self):
        return self.raw.seekable()

    @property
    def raw(self):
        return self._raw

    @property
    def closed(self):
        return self.raw.closed

    @property
    def name(self):
        return self.raw.name

    @property
    def mode(self):
        return self.raw.mode

    def __getstate__(self):
        raise TypeError("can not serialize a '{0}' object".format(self.__class__.__name__))

    def __repr__(self):
        modname = self.__class__.__module__
        clsname = self.__class__.__qualname__
        try:
            name = self.name
        except Exception:
            return '<{}.{}>'.format(modname, clsname)
        return '<{}.{} name={!r}>'.format(modname, clsname, name)

    def fileno(self):
        return self.raw.fileno()

    def isatty(self):
        return self.raw.isatty()

class BytesIO(BufferedIOBase):

    def __init__(self, initial_bytes=None):
        buf = bytearray()
        if initial_bytes is not None:
            buf += initial_bytes
        self._buffer = buf
        self._pos = 0

    def __getstate__(self):
        if self.closed:
            raise ValueError('__getstate__ on closed file')
        return self.__dict__.copy()

    def getvalue(self):
        if self.closed:
            raise ValueError('getvalue on closed file')
        return bytes(self._buffer)

    def getbuffer(self):
        if self.closed:
            raise ValueError('getbuffer on closed file')
        return memoryview(self._buffer)

    def close(self):
        self._buffer.clear()
        super().close()

    def read(self, size=-1):
        if self.closed:
            raise ValueError('read from closed file')
        if size is None:
            size = -1
        else:
            try:
                size_index = size.__index__
            except AttributeError:
                raise TypeError(f'{size} is not an integer')
            size = size_index()
        if size < 0:
            size = len(self._buffer)
        if len(self._buffer) <= self._pos:
            return b''
        newpos = min(len(self._buffer), self._pos + size)
        b = self._buffer[self._pos:newpos]
        self._pos = newpos
        return bytes(b)

    def read1(self, size=-1):
        return self.read(size)

    def write(self, b):
        if self.closed:
            raise ValueError('write to closed file')
        if isinstance(b, str):
            raise TypeError("can't write str to binary stream")
        with memoryview(b) as view:
            n = view.nbytes
        if n == 0:
            return 0
        pos = self._pos
        if pos > len(self._buffer):
            padding = b'\x00'*(pos - len(self._buffer))
            self._buffer += padding
        self._buffer[pos:pos + n] = b
        self._pos += n
        return n

    def seek(self, pos, whence=0):
        if self.closed:
            raise ValueError('seek on closed file')
        try:
            pos_index = pos.__index__
        except AttributeError:
            raise TypeError(f'{pos} is not an integer')
        pos = pos_index()
        if whence == 0:
            if pos < 0:
                raise ValueError('negative seek position %r' % (pos,))
            self._pos = pos
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError('unsupported whence value')
        return self._pos

    def tell(self):
        if self.closed:
            raise ValueError('tell on closed file')
        return self._pos

    def truncate(self, pos=None):
        if self.closed:
            raise ValueError('truncate on closed file')
        if pos is None:
            pos = self._pos
        else:
            try:
                pos_index = pos.__index__
            except AttributeError:
                raise TypeError(f'{pos} is not an integer')
            pos = pos_index()
            if pos < 0:
                raise ValueError('negative truncate position %r' % (pos,))
        del self._buffer[pos:]
        return pos

    def readable(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        return True

    def writable(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        return True

    def seekable(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        return True

class BufferedReader(_BufferedIOMixin):

    def __init__(self, raw, buffer_size=DEFAULT_BUFFER_SIZE):
        if not raw.readable():
            raise OSError('"raw" argument must be readable.')
        _BufferedIOMixin.__init__(self, raw)
        if buffer_size <= 0:
            raise ValueError('invalid buffer size')
        self.buffer_size = buffer_size
        self._reset_read_buf()
        self._read_lock = Lock()

    def readable(self):
        return self.raw.readable()

    def _reset_read_buf(self):
        self._read_buf = b''
        self._read_pos = 0

    def read(self, size=None):
        if size is not None and size < -1:
            raise ValueError('invalid number of bytes to read')
        with self._read_lock:
            return self._read_unlocked(size)

    def _read_unlocked(self, n=None):
        nodata_val = b''
        empty_values = (b'', None)
        buf = self._read_buf
        pos = self._read_pos
        if n is None or n == -1:
            self._reset_read_buf()
            if hasattr(self.raw, 'readall'):
                chunk = self.raw.readall()
                if chunk is None:
                    return buf[pos:] or None
                return buf[pos:] + chunk
            chunks = [buf[pos:]]
            current_size = 0
            while True:
                chunk = self.raw.read()
                if chunk in empty_values:
                    nodata_val = chunk
                    break
                current_size += len(chunk)
                chunks.append(chunk)
            return b''.join(chunks) or nodata_val
        avail = len(buf) - pos
        if n <= avail:
            self._read_pos += n
            return buf[pos:pos + n]
        else:
            chunks = [buf[pos:]]
            wanted = max(self.buffer_size, n)
            while avail < n:
                chunk = self.raw.read(wanted)
                if chunk in empty_values:
                    nodata_val = chunk
                    break
                avail += len(chunk)
                chunks.append(chunk)
            n = min(n, avail)
            out = b''.join(chunks)
            self._read_buf = out[n:]
            self._read_pos = 0
            if out:
                return out[:n]
        return nodata_val

    def peek(self, size=0):
        with self._read_lock:
            return self._peek_unlocked(size)

    def _peek_unlocked(self, n=0):
        want = min(n, self.buffer_size)
        have = len(self._read_buf) - self._read_pos
        if have < want or have <= 0:
            to_read = self.buffer_size - have
            current = self.raw.read(to_read)
            if current:
                self._read_buf = self._read_buf[self._read_pos:] + current
                self._read_pos = 0
        return self._read_buf[self._read_pos:]

    def read1(self, size=-1):
        if size < 0:
            size = self.buffer_size
        if size == 0:
            return b''
        with self._read_lock:
            self._peek_unlocked(1)
            return self._read_unlocked(min(size, len(self._read_buf) - self._read_pos))

    def _readinto(self, buf, read1):
        if not isinstance(buf, memoryview):
            buf = memoryview(buf)
        if buf.nbytes == 0:
            return 0
        buf = buf.cast('B')
        written = 0
        with self._read_lock:
            while written < len(buf):
                avail = min(len(self._read_buf) - self._read_pos, len(buf))
                if avail:
                    buf[written:written + avail] = self._read_buf[self._read_pos:self._read_pos + avail]
                    self._read_pos += avail
                    written += avail
                    if written == len(buf):
                        break
                if len(buf) - written > self.buffer_size:
                    n = self.raw.readinto(buf[written:])
                    if not n:
                        break
                    written += n
                elif not self._peek_unlocked(1):
                    break
                if read1 and written:
                    break
        return written

    def tell(self):
        return _BufferedIOMixin.tell(self) - len(self._read_buf) + self._read_pos

    def seek(self, pos, whence=0):
        if whence not in valid_seek_flags:
            raise ValueError('invalid whence value')
        with self._read_lock:
            if whence == 1:
                pos -= len(self._read_buf) - self._read_pos
            pos = _BufferedIOMixin.seek(self, pos, whence)
            self._reset_read_buf()
            return pos

class BufferedWriter(_BufferedIOMixin):

    def __init__(self, raw, buffer_size=DEFAULT_BUFFER_SIZE):
        if not raw.writable():
            raise OSError('"raw" argument must be writable.')
        _BufferedIOMixin.__init__(self, raw)
        if buffer_size <= 0:
            raise ValueError('invalid buffer size')
        self.buffer_size = buffer_size
        self._write_buf = bytearray()
        self._write_lock = Lock()

    def writable(self):
        return self.raw.writable()

    def write(self, b):
        if isinstance(b, str):
            raise TypeError("can't write str to binary stream")
        with self._write_lock:
            if self.closed:
                raise ValueError('write to closed file')
            if len(self._write_buf) > self.buffer_size:
                self._flush_unlocked()
            before = len(self._write_buf)
            self._write_buf.extend(b)
            written = len(self._write_buf) - before
            if len(self._write_buf) > self.buffer_size:
                try:
                    self._flush_unlocked()
                except BlockingIOError as e:
                    if len(self._write_buf) > self.buffer_size:
                        overage = len(self._write_buf) - self.buffer_size
                        written -= overage
                        self._write_buf = self._write_buf[:self.buffer_size]
                        raise BlockingIOError(e.errno, e.strerror, written)
            return written

    def truncate(self, pos=None):
        with self._write_lock:
            self._flush_unlocked()
            if pos is None:
                pos = self.raw.tell()
            return self.raw.truncate(pos)

    def flush(self):
        with self._write_lock:
            self._flush_unlocked()

    def _flush_unlocked(self):
        if self.closed:
            raise ValueError('flush on closed file')
        while self._write_buf:
            try:
                n = self.raw.write(self._write_buf)
            except BlockingIOError:
                raise RuntimeError('self.raw should implement RawIOBase: it should not raise BlockingIOError')
            if n is None:
                raise BlockingIOError(errno.EAGAIN, 'write could not complete without blocking', 0)
            if n > len(self._write_buf) or n < 0:
                raise OSError('write() returned incorrect number of bytes')
            del self._write_buf[:n]

    def tell(self):
        return _BufferedIOMixin.tell(self) + len(self._write_buf)

    def seek(self, pos, whence=0):
        if whence not in valid_seek_flags:
            raise ValueError('invalid whence value')
        with self._write_lock:
            self._flush_unlocked()
            return _BufferedIOMixin.seek(self, pos, whence)

    def close(self):
        with self._write_lock:
            if self.raw is None or self.closed:
                return
        try:
            self.flush()
        finally:
            with self._write_lock:
                self.raw.close()

class BufferedRWPair(BufferedIOBase):

    def __init__(self, reader, writer, buffer_size=DEFAULT_BUFFER_SIZE):
        if not reader.readable():
            raise OSError('"reader" argument must be readable.')
        if not writer.writable():
            raise OSError('"writer" argument must be writable.')
        self.reader = BufferedReader(reader, buffer_size)
        self.writer = BufferedWriter(writer, buffer_size)

    def read(self, size=-1):
        if size is None:
            size = -1
        return self.reader.read(size)

    def readinto(self, b):
        return self.reader.readinto(b)

    def write(self, b):
        return self.writer.write(b)

    def peek(self, size=0):
        return self.reader.peek(size)

    def read1(self, size=-1):
        return self.reader.read1(size)

    def readinto1(self, b):
        return self.reader.readinto1(b)

    def readable(self):
        return self.reader.readable()

    def writable(self):
        return self.writer.writable()

    def flush(self):
        return self.writer.flush()

    def close(self):
        try:
            self.writer.close()
        finally:
            self.reader.close()

    def isatty(self):
        return self.reader.isatty() or self.writer.isatty()

    @property
    def closed(self):
        return self.writer.closed

class BufferedRandom(BufferedWriter, BufferedReader):

    def __init__(self, raw, buffer_size=DEFAULT_BUFFER_SIZE):
        raw._checkSeekable()
        BufferedReader.__init__(self, raw, buffer_size)
        BufferedWriter.__init__(self, raw, buffer_size)

    def seek(self, pos, whence=0):
        if whence not in valid_seek_flags:
            raise ValueError('invalid whence value')
        self.flush()
        if self._read_buf:
            with self._read_lock:
                self.raw.seek(self._read_pos - len(self._read_buf), 1)
        pos = self.raw.seek(pos, whence)
        with self._read_lock:
            self._reset_read_buf()
        if pos < 0:
            raise OSError('seek() returned invalid position')
        return pos

    def tell(self):
        if self._write_buf:
            return BufferedWriter.tell(self)
        else:
            return BufferedReader.tell(self)

    def truncate(self, pos=None):
        if pos is None:
            pos = self.tell()
        return BufferedWriter.truncate(self, pos)

    def read(self, size=None):
        if size is None:
            size = -1
        self.flush()
        return BufferedReader.read(self, size)

    def readinto(self, b):
        self.flush()
        return BufferedReader.readinto(self, b)

    def peek(self, size=0):
        self.flush()
        return BufferedReader.peek(self, size)

    def read1(self, size=-1):
        self.flush()
        return BufferedReader.read1(self, size)

    def readinto1(self, b):
        self.flush()
        return BufferedReader.readinto1(self, b)

    def write(self, b):
        if self._read_buf:
            with self._read_lock:
                self.raw.seek(self._read_pos - len(self._read_buf), 1)
                self._reset_read_buf()
        return BufferedWriter.write(self, b)

class FileIO(RawIOBase):
    _fd = -1
    _created = False
    _readable = False
    _writable = False
    _appending = False
    _seekable = None
    _closefd = True

    def __init__(self, file, mode='r', closefd=True, opener=None):
        if self._fd >= 0:
            try:
                if self._closefd:
                    os.close(self._fd)
            finally:
                self._fd = -1
        if isinstance(file, float):
            raise TypeError('integer argument expected, got float')
        if isinstance(file, int):
            fd = file
            if fd < 0:
                raise ValueError('negative file descriptor')
        else:
            fd = -1
        if not isinstance(mode, str):
            raise TypeError('invalid mode: %s' % (mode,))
        if not set(mode) <= set('xrwab+'):
            raise ValueError('invalid mode: %s' % (mode,))
        if sum(c in 'rwax' for c in mode) != 1 or mode.count('+') > 1:
            raise ValueError('Must have exactly one of create/read/write/append mode and at most one plus')
        if 'x' in mode:
            self._created = True
            self._writable = True
            flags = os.O_EXCL | os.O_CREAT
        elif 'r' in mode:
            self._readable = True
            flags = 0
        elif 'w' in mode:
            self._writable = True
            flags = os.O_CREAT | os.O_TRUNC
        elif 'a' in mode:
            self._writable = True
            self._appending = True
            flags = os.O_APPEND | os.O_CREAT
        if '+' in mode:
            self._readable = True
            self._writable = True
        if self._readable and self._writable:
            flags |= os.O_RDWR
        elif self._readable:
            flags |= os.O_RDONLY
        else:
            flags |= os.O_WRONLY
        flags |= getattr(os, 'O_BINARY', 0)
        noinherit_flag = getattr(os, 'O_NOINHERIT', 0) or getattr(os, 'O_CLOEXEC', 0)
        flags |= noinherit_flag
        owned_fd = None
        try:
            if fd < 0:
                if not closefd:
                    raise ValueError('Cannot use closefd=False with file name')
                if opener is None:
                    fd = os.open(file, flags, 438)
                else:
                    fd = opener(file, flags)
                    if not isinstance(fd, int):
                        raise TypeError('expected integer from opener')
                    if fd < 0:
                        raise OSError('Negative file descriptor')
                owned_fd = fd
                if not noinherit_flag:
                    os.set_inheritable(fd, False)
            self._closefd = closefd
            fdfstat = os.fstat(fd)
            try:
                if stat.S_ISDIR(fdfstat.st_mode):
                    raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), file)
            except AttributeError:
                pass
            self._blksize = getattr(fdfstat, 'st_blksize', 0)
            if self._blksize <= 1:
                self._blksize = DEFAULT_BUFFER_SIZE
            if _setmode:
                _setmode(fd, os.O_BINARY)
            self.name = file
            if self._appending:
                os.lseek(fd, 0, SEEK_END)
        except:
            if owned_fd is not None:
                os.close(owned_fd)
            raise
        self._fd = fd

    def __del__(self):
        if self._fd >= 0 and self._closefd and not self.closed:
            import warnings
            warnings.warn('unclosed file %r' % (self,), ResourceWarning, stacklevel=2, source=self)
            self.close()

    def __getstate__(self):
        raise TypeError("cannot serialize '%s' object", self.__class__.__name__)

    def __repr__(self):
        class_name = '%s.%s' % (self.__class__.__module__, self.__class__.__qualname__)
        if self.closed:
            return '<%s [closed]>' % class_name
        try:
            name = self.name
        except AttributeError:
            return '<%s fd=%d mode=%r closefd=%r>' % (class_name, self._fd, self.mode, self._closefd)
        return '<%s name=%r mode=%r closefd=%r>' % (class_name, name, self.mode, self._closefd)

    def _checkReadable(self):
        if not self._readable:
            raise UnsupportedOperation('File not open for reading')

    def _checkWritable(self, msg=None):
        if not self._writable:
            raise UnsupportedOperation('File not open for writing')

    def read(self, size=None):
        self._checkClosed()
        self._checkReadable()
        if size is None or size < 0:
            return self.readall()
        try:
            return os.read(self._fd, size)
        except BlockingIOError:
            return

    def readall(self):
        self._checkClosed()
        self._checkReadable()
        bufsize = DEFAULT_BUFFER_SIZE
        try:
            pos = os.lseek(self._fd, 0, SEEK_CUR)
            end = os.fstat(self._fd).st_size
            if end >= pos:
                bufsize = end - pos + 1
        except OSError:
            pass
        result = bytearray()
        while True:
            if len(result) >= bufsize:
                bufsize = len(result)
                bufsize += max(bufsize, DEFAULT_BUFFER_SIZE)
            n = bufsize - len(result)
            try:
                chunk = os.read(self._fd, n)
            except BlockingIOError:
                if result:
                    break
                return
            if not chunk:
                break
            result += chunk
        return bytes(result)

    def readinto(self, b):
        m = memoryview(b).cast('B')
        data = self.read(len(m))
        n = len(data)
        m[:n] = data
        return n

    def write(self, b):
        self._checkClosed()
        self._checkWritable()
        try:
            return os.write(self._fd, b)
        except BlockingIOError:
            return

    def seek(self, pos, whence=SEEK_SET):
        if isinstance(pos, float):
            raise TypeError('an integer is required')
        self._checkClosed()
        return os.lseek(self._fd, pos, whence)

    def tell(self):
        self._checkClosed()
        return os.lseek(self._fd, 0, SEEK_CUR)

    def truncate(self, size=None):
        self._checkClosed()
        self._checkWritable()
        if size is None:
            size = self.tell()
        os.ftruncate(self._fd, size)
        return size

    def close(self):
        if not self.closed:
            try:
                if self._closefd:
                    os.close(self._fd)
            finally:
                super().close()

    def seekable(self):
        self._checkClosed()
        if self._seekable is None:
            try:
                self.tell()
            except OSError:
                self._seekable = False
            self._seekable = True
        return self._seekable

    def readable(self):
        self._checkClosed()
        return self._readable

    def writable(self):
        self._checkClosed()
        return self._writable

    def fileno(self):
        self._checkClosed()
        return self._fd

    def isatty(self):
        self._checkClosed()
        return os.isatty(self._fd)

    @property
    def closefd(self):
        return self._closefd

    @property
    def mode(self):
        if self._created:
            if self._readable:
                return 'xb+'
            return 'xb'
        elif self._appending:
            if self._readable:
                return 'ab+'
            return 'ab'
        elif self._readable:
            if self._writable:
                return 'rb+'
            return 'rb'
        else:
            return 'wb'

class TextIOBase(IOBase):

    def read(self, size=-1):
        self._unsupported('read')

    def write(self, s):
        self._unsupported('write')

    def truncate(self, pos=None):
        self._unsupported('truncate')

    def readline(self):
        self._unsupported('readline')

    def detach(self):
        self._unsupported('detach')

    @property
    def encoding(self):
        pass

    @property
    def newlines(self):
        pass

    @property
    def errors(self):
        pass
io.TextIOBase.register(TextIOBase)
class IncrementalNewlineDecoder(codecs.IncrementalDecoder):

    def __init__(self, decoder, translate, errors='strict'):
        codecs.IncrementalDecoder.__init__(self, errors=errors)
        self.translate = translate
        self.decoder = decoder
        self.seennl = 0
        self.pendingcr = False

    def decode(self, input, final=False):
        if self.decoder is None:
            output = input
        else:
            output = self.decoder.decode(input, final=final)
        if output or final:
            output = '\r' + output
            self.pendingcr = False
        if not final:
            output = output[:-1]
            self.pendingcr = True
        crlf = output.count('\r\n')
        cr = output.count('\r') - crlf
        lf = output.count('\n') - crlf
        self.seennl |= (self.pendingcr and output.endswith('\r') and lf and self._LF) | (cr and self._CR) | (crlf and self._CRLF)
        if self.translate:
            if crlf:
                output = output.replace('\r\n', '\n')
            if cr:
                output = output.replace('\r', '\n')
        return output

    def getstate(self):
        if self.decoder is None:
            buf = b''
            flag = 0
        else:
            (buf, flag) = self.decoder.getstate()
        flag <<= 1
        if self.pendingcr:
            flag |= 1
        return (buf, flag)

    def setstate(self, state):
        (buf, flag) = state
        self.pendingcr = bool(flag & 1)
        if self.decoder is not None:
            self.decoder.setstate((buf, flag >> 1))

    def reset(self):
        self.seennl = 0
        self.pendingcr = False
        if self.decoder is not None:
            self.decoder.reset()

    _LF = 1
    _CR = 2
    _CRLF = 4

    @property
    def newlines(self):
        return (None, '\n', '\r', ('\r', '\n'), '\r\n', ('\n', '\r\n'), ('\r', '\r\n'), ('\r', '\n', '\r\n'))[self.seennl]

class TextIOWrapper(TextIOBase):
    _CHUNK_SIZE = 2048

    def __init__(self, buffer, encoding=None, errors=None, newline=None, line_buffering=False, write_through=False):
        self._check_newline(newline)
        if encoding is None:
            try:
                encoding = os.device_encoding(buffer.fileno())
            except (AttributeError, UnsupportedOperation):
                pass
            if encoding is None:
                try:
                    import locale
                except ImportError:
                    encoding = 'ascii'
                encoding = locale.getpreferredencoding(False)
        if not isinstance(encoding, str):
            raise ValueError('invalid encoding: %r' % encoding)
        if not codecs.lookup(encoding)._is_text_encoding:
            msg = '%r is not a text encoding; use codecs.open() to handle arbitrary codecs'
            raise LookupError(msg % encoding)
        if errors is None:
            errors = 'strict'
        elif not isinstance(errors, str):
            raise ValueError('invalid errors: %r' % errors)
        self._buffer = buffer
        self._decoded_chars = ''
        self._decoded_chars_used = 0
        self._snapshot = None
        self._seekable = self._telling = self.buffer.seekable()
        self._has_read1 = hasattr(self.buffer, 'read1')
        self._configure(encoding, errors, newline, line_buffering, write_through)

    def _check_newline(self, newline):
        if newline is not None and not isinstance(newline, str):
            raise TypeError('illegal newline type: %r' % (type(newline),))
        if newline not in (None, '', '\n', '\r', '\r\n'):
            raise ValueError('illegal newline value: %r' % (newline,))

    def _configure(self, encoding=None, errors=None, newline=None, line_buffering=False, write_through=False):
        self._encoding = encoding
        self._errors = errors
        self._encoder = None
        self._decoder = None
        self._b2cratio = 0.0
        self._readuniversal = not newline
        self._readtranslate = newline is None
        self._readnl = newline
        self._writetranslate = newline != ''
        self._writenl = newline or os.linesep
        self._line_buffering = line_buffering
        self._write_through = write_through
        if self.writable():
            position = self.buffer.tell()
            if position != 0:
                try:
                    self._get_encoder().setstate(0)
                except LookupError:
                    pass

    def __repr__(self):
        result = '<{}.{}'.format(self.__class__.__module__, self.__class__.__qualname__)
        try:
            name = self.name
        except Exception:
            pass
        result += ' name={0!r}'.format(name)
        try:
            mode = self.mode
        except Exception:
            pass
        result += ' mode={0!r}'.format(mode)
        return result + ' encoding={0!r}>'.format(self.encoding)

    @property
    def encoding(self):
        return self._encoding

    @property
    def errors(self):
        return self._errors

    @property
    def line_buffering(self):
        return self._line_buffering

    @property
    def write_through(self):
        return self._write_through

    @property
    def buffer(self):
        return self._buffer

    def reconfigure(self, *, encoding=None, errors=None, newline=Ellipsis, line_buffering=None, write_through=None):
        if self._decoder is not None and (encoding is not None or errors is not None or newline is not Ellipsis):
            raise UnsupportedOperation('It is not possible to set the encoding or newline of stream after the first read')
        if errors is None:
            if encoding is None:
                errors = self._errors
            else:
                errors = 'strict'
        elif not isinstance(errors, str):
            raise TypeError('invalid errors: %r' % errors)
        if encoding is None:
            encoding = self._encoding
        elif not isinstance(encoding, str):
            raise TypeError('invalid encoding: %r' % encoding)
        if newline is Ellipsis:
            newline = self._readnl
        self._check_newline(newline)
        if line_buffering is None:
            line_buffering = self.line_buffering
        if write_through is None:
            write_through = self.write_through
        self.flush()
        self._configure(encoding, errors, newline, line_buffering, write_through)

    def seekable(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        return self._seekable

    def readable(self):
        return self.buffer.readable()

    def writable(self):
        return self.buffer.writable()

    def flush(self):
        self.buffer.flush()
        self._telling = self._seekable

    def close(self):
        if not self.closed:
            try:
                self.flush()
            finally:
                self.buffer.close()

    @property
    def closed(self):
        return self.buffer.closed

    @property
    def name(self):
        return self.buffer.name

    def fileno(self):
        return self.buffer.fileno()

    def isatty(self):
        return self.buffer.isatty()

    def write(self, s):
        if self.closed:
            raise ValueError('write to closed file')
        if not isinstance(s, str):
            raise TypeError("can't write %s to text stream" % s.__class__.__name__)
        length = len(s)
        if not self._writetranslate:
            pass
        haslf = '\n' in s
        if self._writenl != '\n':
            s = s.replace('\n', self._writenl)
        encoder = haslf and self._writetranslate and self._encoder or self._get_encoder()
        b = encoder.encode(s)
        self.buffer.write(b)
        if self._line_buffering and (haslf or '\r' in s):
            self.flush()
        self._snapshot = None
        if self._decoder:
            self._decoder.reset()
        return length

    def _get_encoder(self):
        make_encoder = codecs.getincrementalencoder(self._encoding)
        self._encoder = make_encoder(self._errors)
        return self._encoder

    def _get_decoder(self):
        make_decoder = codecs.getincrementaldecoder(self._encoding)
        decoder = make_decoder(self._errors)
        if self._readuniversal:
            decoder = IncrementalNewlineDecoder(decoder, self._readtranslate)
        self._decoder = decoder
        return decoder

    def _set_decoded_chars(self, chars):
        self._decoded_chars = chars
        self._decoded_chars_used = 0

    def _get_decoded_chars(self, n=None):
        offset = self._decoded_chars_used
        if n is None:
            chars = self._decoded_chars[offset:]
        else:
            chars = self._decoded_chars[offset:offset + n]
        self._decoded_chars_used += len(chars)
        return chars

    def _rewind_decoded_chars(self, n):
        if self._decoded_chars_used < n:
            raise AssertionError('rewind decoded_chars out of bounds')
        self._decoded_chars_used -= n

    def _read_chunk(self):
        if self._decoder is None:
            raise ValueError('no decoder')
        if self._telling:
            (dec_buffer, dec_flags) = self._decoder.getstate()
        if self._has_read1:
            input_chunk = self.buffer.read1(self._CHUNK_SIZE)
        else:
            input_chunk = self.buffer.read(self._CHUNK_SIZE)
        eof = not input_chunk
        decoded_chars = self._decoder.decode(input_chunk, eof)
        self._set_decoded_chars(decoded_chars)
        if decoded_chars:
            self._b2cratio = len(input_chunk)/len(self._decoded_chars)
        else:
            self._b2cratio = 0.0
        if self._telling:
            self._snapshot = (dec_flags, dec_buffer + input_chunk)
        return not eof

    def _pack_cookie(self, position, dec_flags=0, bytes_to_feed=0, need_eof=0, chars_to_skip=0):
        return position | dec_flags << 64 | bytes_to_feed << 128 | chars_to_skip << 192 | bool(need_eof) << 256

    def _unpack_cookie(self, bigint):
        (rest, position) = divmod(bigint, 18446744073709551616)
        (rest, dec_flags) = divmod(rest, 18446744073709551616)
        (rest, bytes_to_feed) = divmod(rest, 18446744073709551616)
        (need_eof, chars_to_skip) = divmod(rest, 18446744073709551616)
        return (position, dec_flags, bytes_to_feed, need_eof, chars_to_skip)

    def tell(self):
        if not self._seekable:
            raise UnsupportedOperation('underlying stream is not seekable')
        if not self._telling:
            raise OSError('telling position disabled by next() call')
        self.flush()
        position = self.buffer.tell()
        decoder = self._decoder
        if decoder is None or self._snapshot is None:
            if self._decoded_chars:
                raise AssertionError('pending decoded text')
            return position
        (dec_flags, next_input) = self._snapshot
        position -= len(next_input)
        chars_to_skip = self._decoded_chars_used
        if chars_to_skip == 0:
            return self._pack_cookie(position, dec_flags)
        saved_state = decoder.getstate()
        try:
            skip_bytes = int(self._b2cratio*chars_to_skip)
            skip_back = 1
            while skip_bytes > 0:
                decoder.setstate((b'', dec_flags))
                n = len(decoder.decode(next_input[:skip_bytes]))
                if n <= chars_to_skip:
                    (b, d) = decoder.getstate()
                    if not b:
                        dec_flags = d
                        chars_to_skip -= n
                        break
                    skip_bytes -= len(b)
                    skip_back = 1
                else:
                    skip_bytes -= skip_back
                    skip_back = skip_back*2
                    skip_bytes = 0
            skip_bytes = 0
            decoder.setstate((b'', dec_flags))
            start_pos = position + skip_bytes
            start_flags = dec_flags
            if chars_to_skip == 0:
                return self._pack_cookie(start_pos, start_flags)
            bytes_fed = 0
            need_eof = 0
            chars_decoded = 0
            for i in range(skip_bytes, len(next_input)):
                bytes_fed += 1
                chars_decoded += len(decoder.decode(next_input[i:i + 1]))
                (dec_buffer, dec_flags) = decoder.getstate()
                if chars_decoded <= chars_to_skip:
                    start_pos += bytes_fed
                    chars_to_skip -= chars_decoded
                    start_flags = dec_flags
                    bytes_fed = chars_decoded = 0
                if dec_buffer or chars_decoded >= chars_to_skip:
                    break
            chars_decoded += len(decoder.decode(b'', final=True))
            need_eof = 1
            if chars_decoded < chars_to_skip:
                raise OSError("can't reconstruct logical file position")
            return self._pack_cookie(start_pos, start_flags, bytes_fed, need_eof, chars_to_skip)
        finally:
            decoder.setstate(saved_state)

    def truncate(self, pos=None):
        self.flush()
        if pos is None:
            pos = self.tell()
        return self.buffer.truncate(pos)

    def detach(self):
        if self.buffer is None:
            raise ValueError('buffer is already detached')
        self.flush()
        buffer = self._buffer
        self._buffer = None
        return buffer

    def seek(self, cookie, whence=0):

        def _reset_encoder(position):
            try:
                encoder = self._encoder or self._get_encoder()
            except LookupError:
                pass
            if position != 0:
                encoder.setstate(0)
            else:
                encoder.reset()

        if self.closed:
            raise ValueError('tell on closed file')
        if not self._seekable:
            raise UnsupportedOperation('underlying stream is not seekable')
        if whence == 1:
            if cookie != 0:
                raise UnsupportedOperation("can't do nonzero cur-relative seeks")
            whence = 0
            cookie = self.tell()
        if whence == 2:
            if cookie != 0:
                raise UnsupportedOperation("can't do nonzero end-relative seeks")
            self.flush()
            position = self.buffer.seek(0, 2)
            self._set_decoded_chars('')
            self._snapshot = None
            if self._decoder:
                self._decoder.reset()
            _reset_encoder(position)
            return position
        if whence != 0:
            raise ValueError('unsupported whence (%r)' % (whence,))
        if cookie < 0:
            raise ValueError('negative seek position %r' % (cookie,))
        self.flush()
        (start_pos, dec_flags, bytes_to_feed, need_eof, chars_to_skip) = self._unpack_cookie(cookie)
        self.buffer.seek(start_pos)
        self._set_decoded_chars('')
        self._snapshot = None
        if cookie == 0 and self._decoder:
            self._decoder.reset()
        elif self._decoder or dec_flags or chars_to_skip:
            self._decoder = self._decoder or self._get_decoder()
            self._decoder.setstate((b'', dec_flags))
            self._snapshot = (dec_flags, b'')
        if chars_to_skip:
            input_chunk = self.buffer.read(bytes_to_feed)
            self._set_decoded_chars(self._decoder.decode(input_chunk, need_eof))
            self._snapshot = (dec_flags, input_chunk)
            if len(self._decoded_chars) < chars_to_skip:
                raise OSError("can't restore logical file position")
            self._decoded_chars_used = chars_to_skip
        _reset_encoder(cookie)
        return cookie

    def read(self, size=None):
        self._checkReadable()
        if size is None:
            size = -1
        else:
            try:
                size_index = size.__index__
            except AttributeError:
                raise TypeError(f'{size} is not an integer')
            size = size_index()
        decoder = self._decoder or self._get_decoder()
        if size < 0:
            result = self._get_decoded_chars() + decoder.decode(self.buffer.read(), final=True)
            self._set_decoded_chars('')
            self._snapshot = None
            return result
        else:
            eof = False
            result = self._get_decoded_chars(size)
            while len(result) < size and not eof:
                eof = not self._read_chunk()
                result += self._get_decoded_chars(size - len(result))
            return result

    def __next__(self):
        self._telling = False
        line = self.readline()
        if not line:
            self._snapshot = None
            self._telling = self._seekable
            raise StopIteration
        return line

    def readline(self, size=None):
        if self.closed:
            raise ValueError('read from closed file')
        if size is None:
            size = -1
        else:
            try:
                size_index = size.__index__
            except AttributeError:
                raise TypeError(f'{size} is not an integer')
            size = size_index()
        line = self._get_decoded_chars()
        start = 0
        if not self._decoder:
            self._get_decoder()
        pos = endpos = None
        while True:
            if self._readtranslate:
                pos = line.find('\n', start)
                if pos >= 0:
                    endpos = pos + 1
                    break
                else:
                    start = len(line)
            elif self._readuniversal:
                nlpos = line.find('\n', start)
                crpos = line.find('\r', start)
                if crpos == -1:
                    if nlpos == -1:
                        start = len(line)
                    else:
                        endpos = nlpos + 1
                        break
                elif nlpos == -1:
                    endpos = crpos + 1
                    break
                elif nlpos < crpos:
                    endpos = nlpos + 1
                    break
                elif nlpos == crpos + 1:
                    endpos = crpos + 2
                    break
                else:
                    endpos = crpos + 1
                    break
            else:
                pos = line.find(self._readnl)
                if pos >= 0:
                    endpos = pos + len(self._readnl)
                    break
            if len(line) >= size:
                endpos = size
                break
            if size >= 0 and self._read_chunk():
                if self._decoded_chars:
                    break
            if self._decoded_chars:
                line += self._get_decoded_chars()
            else:
                self._set_decoded_chars('')
                self._snapshot = None
                return line
        if endpos > size:
            endpos = size
        self._rewind_decoded_chars(len(line) - endpos)
        return line[:endpos]

    @property
    def newlines(self):
        if self._decoder:
            return self._decoder.newlines

class StringIO(TextIOWrapper):

    def __init__(self, initial_value='', newline='\n'):
        super(StringIO, self).__init__(BytesIO(), encoding='utf-8', errors='surrogatepass', newline=newline)
        if newline is None:
            self._writetranslate = False
        if initial_value is not None:
            if not isinstance(initial_value, str):
                raise TypeError('initial_value must be str or None, not {0}'.format(type(initial_value).__name__))
            self.write(initial_value)
            self.seek(0)

    def getvalue(self):
        self.flush()
        decoder = self._decoder or self._get_decoder()
        old_state = decoder.getstate()
        decoder.reset()
        try:
            return decoder.decode(self.buffer.getvalue(), final=True)
        finally:
            decoder.setstate(old_state)

    def __repr__(self):
        return object.__repr__(self)

    @property
    def errors(self):
        pass

    @property
    def encoding(self):
        pass

    def detach(self):
        self._unsupported('detach')
