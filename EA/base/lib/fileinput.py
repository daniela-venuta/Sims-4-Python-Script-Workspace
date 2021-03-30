import sysimport os__all__ = ['input', 'close', 'nextfile', 'filename', 'lineno', 'filelineno', 'fileno', 'isfirstline', 'isstdin', 'FileInput', 'hook_compressed', 'hook_encoded']_state = None
def input(files=None, inplace=False, backup='', bufsize=0, mode='r', openhook=None):
    global _state
    if _state and _state._file:
        raise RuntimeError('input() already active')
    _state = FileInput(files, inplace, backup, bufsize, mode, openhook)
    return _state

def close():
    global _state
    state = _state
    _state = None
    if state:
        state.close()

def nextfile():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.nextfile()

def filename():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.filename()

def lineno():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.lineno()

def filelineno():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.filelineno()

def fileno():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.fileno()

def isfirstline():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.isfirstline()

def isstdin():
    if not _state:
        raise RuntimeError('no active input()')
    return _state.isstdin()

class FileInput:

    def __init__(self, files=None, inplace=False, backup='', bufsize=0, mode='r', openhook=None):
        if isinstance(files, str):
            files = (files,)
        elif isinstance(files, os.PathLike):
            files = (os.fspath(files),)
        else:
            if files is None:
                files = sys.argv[1:]
            if not files:
                files = ('-',)
            else:
                files = tuple(files)
        self._files = files
        self._inplace = inplace
        self._backup = backup
        if bufsize:
            import warnings
            warnings.warn('bufsize is deprecated and ignored', DeprecationWarning, stacklevel=2)
        self._savestdout = None
        self._output = None
        self._filename = None
        self._startlineno = 0
        self._filelineno = 0
        self._file = None
        self._isstdin = False
        self._backupfilename = None
        if mode not in ('r', 'rU', 'U', 'rb'):
            raise ValueError("FileInput opening mode must be one of 'r', 'rU', 'U' and 'rb'")
        if 'U' in mode:
            import warnings
            warnings.warn("'U' mode is deprecated", DeprecationWarning, 2)
        self._mode = mode
        if openhook:
            if inplace:
                raise ValueError('FileInput cannot use an opening hook in inplace mode')
            if not callable(openhook):
                raise ValueError('FileInput openhook must be callable')
        self._openhook = openhook

    def __del__(self):
        self.close()

    def close(self):
        try:
            self.nextfile()
        finally:
            self._files = ()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            line = self._readline()
            if line:
                self._filelineno += 1
                return line
            if not self._file:
                raise StopIteration
            self.nextfile()

    def __getitem__(self, i):
        if i != self.lineno():
            raise RuntimeError('accessing lines out of order')
        try:
            return self.__next__()
        except StopIteration:
            raise IndexError('end of input reached')

    def nextfile(self):
        savestdout = self._savestdout
        self._savestdout = None
        if savestdout:
            sys.stdout = savestdout
        output = self._output
        self._output = None
        try:
            if output:
                output.close()
        finally:
            file = self._file
            self._file = None
            try:
                del self._readline
            except AttributeError:
                pass
            try:
                if file and not self._isstdin:
                    file.close()
            finally:
                backupfilename = self._backupfilename
                self._backupfilename = None
                if not self._backup:
                    try:
                        os.unlink(backupfilename)
                    except OSError:
                        pass
                self._isstdin = False

    def readline(self):
        while True:
            line = self._readline()
            if line:
                self._filelineno += 1
                return line
            if not self._file:
                return line
            self.nextfile()

    def _readline(self):
        if not self._files:
            if 'b' in self._mode:
                return b''
            return ''
        self._filename = self._files[0]
        self._files = self._files[1:]
        self._startlineno = self.lineno()
        self._filelineno = 0
        self._file = None
        self._isstdin = False
        self._backupfilename = 0
        if self._filename == '-':
            self._filename = '<stdin>'
            if 'b' in self._mode:
                self._file = getattr(sys.stdin, 'buffer', sys.stdin)
            else:
                self._file = sys.stdin
            self._isstdin = True
        elif self._inplace:
            self._backupfilename = os.fspath(self._filename) + (self._backup or '.bak')
            try:
                os.unlink(self._backupfilename)
            except OSError:
                pass
            os.rename(self._filename, self._backupfilename)
            self._file = open(self._backupfilename, self._mode)
            try:
                perm = os.fstat(self._file.fileno()).st_mode
            except OSError:
                self._output = open(self._filename, 'w')
            mode = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            if hasattr(os, 'O_BINARY'):
                mode |= os.O_BINARY
            fd = os.open(self._filename, mode, perm)
            self._output = os.fdopen(fd, 'w')
            try:
                if hasattr(os, 'chmod'):
                    os.chmod(self._filename, perm)
            except OSError:
                pass
            self._savestdout = sys.stdout
            sys.stdout = self._output
        elif self._openhook:
            self._file = self._openhook(self._filename, self._mode)
        else:
            self._file = open(self._filename, self._mode)
        self._readline = self._file.readline
        return self._readline()

    def filename(self):
        return self._filename

    def lineno(self):
        return self._startlineno + self._filelineno

    def filelineno(self):
        return self._filelineno

    def fileno(self):
        if self._file:
            try:
                return self._file.fileno()
            except ValueError:
                return -1
        else:
            return -1

    def isfirstline(self):
        return self._filelineno == 1

    def isstdin(self):
        return self._isstdin

def hook_compressed(filename, mode):
    ext = os.path.splitext(filename)[1]
    if ext == '.gz':
        import gzip
        return gzip.open(filename, mode)
    if ext == '.bz2':
        import bz2
        return bz2.BZ2File(filename, mode)
    else:
        return open(filename, mode)

def hook_encoded(encoding, errors=None):

    def openhook(filename, mode):
        return open(filename, mode, encoding=encoding, errors=errors)

    return openhook

def _test():
    import getopt
    inplace = False
    backup = False
    (opts, args) = getopt.getopt(sys.argv[1:], 'ib:')
    for (o, a) in opts:
        if o == '-i':
            inplace = True
        if o == '-b':
            backup = a
    for line in input(args, inplace=inplace, backup=backup):
        if line[-1:] == '\n':
            line = line[:-1]
        if line[-1:] == '\r':
            line = line[:-1]
        if isfirstline():
            pass
        print('%d: %s[%d]%s %s' % (lineno(), filename(), filelineno(), '', line))
    print('%d: %s[%d]' % (lineno(), filename(), filelineno()))
if __name__ == '__main__':
    _test()