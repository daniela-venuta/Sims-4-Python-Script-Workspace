__all__ = ['CHECK_NONE', 'CHECK_CRC32', 'CHECK_CRC64', 'CHECK_SHA256', 'CHECK_ID_MAX', 'CHECK_UNKNOWN', 'FILTER_LZMA1', 'FILTER_LZMA2', 'FILTER_DELTA', 'FILTER_X86', 'FILTER_IA64', 'FILTER_ARM', 'FILTER_ARMTHUMB', 'FILTER_POWERPC', 'FILTER_SPARC', 'FORMAT_AUTO', 'FORMAT_XZ', 'FORMAT_ALONE', 'FORMAT_RAW', 'MF_HC3', 'MF_HC4', 'MF_BT2', 'MF_BT3', 'MF_BT4', 'MODE_FAST', 'MODE_NORMAL', 'PRESET_DEFAULT', 'PRESET_EXTREME', 'LZMACompressor', 'LZMADecompressor', 'LZMAFile', 'LZMAError', 'open', 'compress', 'decompress', 'is_check_supported']import builtinsimport ioimport osfrom _lzma import *from _lzma import _encode_filter_properties, _decode_filter_propertiesimport _compression_MODE_CLOSED = 0_MODE_READ = 1_MODE_WRITE = 3
class LZMAFile(_compression.BaseStream):

    def __init__(self, filename=None, mode='r', *, format=None, check=-1, preset=None, filters=None):
        self._fp = None
        self._closefp = False
        self._mode = _MODE_CLOSED
        if mode in ('r', 'rb'):
            if check != -1:
                raise ValueError('Cannot specify an integrity check when opening a file for reading')
            if preset is not None:
                raise ValueError('Cannot specify a preset compression level when opening a file for reading')
            if format is None:
                format = FORMAT_AUTO
            mode_code = _MODE_READ
        elif mode in ('w', 'wb', 'a', 'ab', 'x', 'xb'):
            if format is None:
                format = FORMAT_XZ
            mode_code = _MODE_WRITE
            self._compressor = LZMACompressor(format=format, check=check, preset=preset, filters=filters)
            self._pos = 0
        else:
            raise ValueError('Invalid mode: {!r}'.format(mode))
        if isinstance(filename, (str, bytes, os.PathLike)):
            if 'b' not in mode:
                mode += 'b'
            self._fp = builtins.open(filename, mode)
            self._closefp = True
            self._mode = mode_code
        elif hasattr(filename, 'read') or hasattr(filename, 'write'):
            self._fp = filename
            self._mode = mode_code
        else:
            raise TypeError('filename must be a str, bytes, file or PathLike object')
        if self._mode == _MODE_READ:
            raw = _compression.DecompressReader(self._fp, LZMADecompressor, trailing_error=LZMAError, format=format, filters=filters)
            self._buffer = io.BufferedReader(raw)

    def close(self):
        if self._mode == _MODE_CLOSED:
            return
        try:
            if self._mode == _MODE_READ:
                self._buffer.close()
                self._buffer = None
            elif self._mode == _MODE_WRITE:
                self._fp.write(self._compressor.flush())
                self._compressor = None
        finally:
            try:
                if self._closefp:
                    self._fp.close()
            finally:
                self._fp = None
                self._closefp = False
                self._mode = _MODE_CLOSED

    @property
    def closed(self):
        return self._mode == _MODE_CLOSED

    def fileno(self):
        self._check_not_closed()
        return self._fp.fileno()

    def seekable(self):
        return self.readable() and self._buffer.seekable()

    def readable(self):
        self._check_not_closed()
        return self._mode == _MODE_READ

    def writable(self):
        self._check_not_closed()
        return self._mode == _MODE_WRITE

    def peek(self, size=-1):
        self._check_can_read()
        return self._buffer.peek(size)

    def read(self, size=-1):
        self._check_can_read()
        return self._buffer.read(size)

    def read1(self, size=-1):
        self._check_can_read()
        if size < 0:
            size = io.DEFAULT_BUFFER_SIZE
        return self._buffer.read1(size)

    def readline(self, size=-1):
        self._check_can_read()
        return self._buffer.readline(size)

    def write(self, data):
        self._check_can_write()
        compressed = self._compressor.compress(data)
        self._fp.write(compressed)
        self._pos += len(data)
        return len(data)

    def seek(self, offset, whence=io.SEEK_SET):
        self._check_can_seek()
        return self._buffer.seek(offset, whence)

    def tell(self):
        self._check_not_closed()
        if self._mode == _MODE_READ:
            return self._buffer.tell()
        return self._pos

def open(filename, mode='rb', *, format=None, check=-1, preset=None, filters=None, encoding=None, errors=None, newline=None):
    if 't' in mode:
        if 'b' in mode:
            raise ValueError('Invalid mode: %r' % (mode,))
    else:
        if encoding is not None:
            raise ValueError("Argument 'encoding' not supported in binary mode")
        if errors is not None:
            raise ValueError("Argument 'errors' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")
    lz_mode = mode.replace('t', '')
    binary_file = LZMAFile(filename, lz_mode, format=format, check=check, preset=preset, filters=filters)
    if 't' in mode:
        return io.TextIOWrapper(binary_file, encoding, errors, newline)
    else:
        return binary_file

def compress(data, format=FORMAT_XZ, check=-1, preset=None, filters=None):
    comp = LZMACompressor(format, check, preset, filters)
    return comp.compress(data) + comp.flush()

def decompress(data, format=FORMAT_AUTO, memlimit=None, filters=None):
    results = []
    while True:
        decomp = LZMADecompressor(format, memlimit, filters)
        try:
            res = decomp.decompress(data)
        except LZMAError:
            if results:
                break
            else:
                raise
        results.append(res)
        if not decomp.eof:
            raise LZMAError('Compressed data ended before the end-of-stream marker was reached')
        data = decomp.unused_data
        if not data:
            break
    return b''.join(results)
