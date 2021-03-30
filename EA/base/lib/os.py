import abcimport sysimport stat as st_names = sys.builtin_module_names__all__ = ['altsep', 'curdir', 'pardir', 'sep', 'pathsep', 'linesep', 'defpath', 'name', 'path', 'devnull', 'SEEK_SET', 'SEEK_CUR', 'SEEK_END', 'fsencode', 'fsdecode', 'get_exec_path', 'fdopen', 'popen', 'extsep']
def _exists(name):
    return name in globals()

def _get_exports_list(module):
    try:
        return list(module.__all__)
    except AttributeError:
        return [n for n in dir(module) if n[0] != '_']
if 'posix' in _names:
    name = 'posix'
    linesep = '\n'
    from posix import *
    try:
        from posix import _exit
        __all__.append('_exit')
    except ImportError:
        pass
    import posixpath as path
    try:
        from posix import _have_functions
    except ImportError:
        pass
    import posix
    __all__.extend(_get_exports_list(posix))
    del posix
elif 'nt' in _names:
    name = 'nt'
    linesep = '\r\n'
    from nt import *
    try:
        from nt import _exit
        __all__.append('_exit')
    except ImportError:
        pass
    import ntpath as path
    import nt
    __all__.extend(_get_exports_list(nt))
    del nt
    try:
        from nt import _have_functions
    except ImportError:
        pass
else:
    raise ImportError('no os specific module found')sys.modules['os.path'] = pathfrom os.path import curdir, pardir, sep, pathsep, defpath, extsep, altsep, devnulldel _namesif _exists('_have_functions'):
    _globals = globals()

    def _add(str, fn):
        if fn in _globals and str in _have_functions:
            _set.add(_globals[fn])

    _set = set()
    _add('HAVE_FACCESSAT', 'access')
    _add('HAVE_FCHMODAT', 'chmod')
    _add('HAVE_FCHOWNAT', 'chown')
    _add('HAVE_FSTATAT', 'stat')
    _add('HAVE_FUTIMESAT', 'utime')
    _add('HAVE_LINKAT', 'link')
    _add('HAVE_MKDIRAT', 'mkdir')
    _add('HAVE_MKFIFOAT', 'mkfifo')
    _add('HAVE_MKNODAT', 'mknod')
    _add('HAVE_OPENAT', 'open')
    _add('HAVE_READLINKAT', 'readlink')
    _add('HAVE_RENAMEAT', 'rename')
    _add('HAVE_SYMLINKAT', 'symlink')
    _add('HAVE_UNLINKAT', 'unlink')
    _add('HAVE_UNLINKAT', 'rmdir')
    _add('HAVE_UTIMENSAT', 'utime')
    supports_dir_fd = _set
    _set = set()
    _add('HAVE_FACCESSAT', 'access')
    supports_effective_ids = _set
    _set = set()
    _add('HAVE_FCHDIR', 'chdir')
    _add('HAVE_FCHMOD', 'chmod')
    _add('HAVE_FCHOWN', 'chown')
    _add('HAVE_FDOPENDIR', 'listdir')
    _add('HAVE_FDOPENDIR', 'scandir')
    _add('HAVE_FEXECVE', 'execve')
    _set.add(stat)
    _add('HAVE_FTRUNCATE', 'truncate')
    _add('HAVE_FUTIMENS', 'utime')
    _add('HAVE_FUTIMES', 'utime')
    _add('HAVE_FPATHCONF', 'pathconf')
    if _exists('statvfs') and _exists('fstatvfs'):
        _add('HAVE_FSTATVFS', 'statvfs')
    supports_fd = _set
    _set = set()
    _add('HAVE_FACCESSAT', 'access')
    _add('HAVE_FCHOWNAT', 'chown')
    _add('HAVE_FSTATAT', 'stat')
    _add('HAVE_LCHFLAGS', 'chflags')
    _add('HAVE_LCHMOD', 'chmod')
    if _exists('lchown'):
        _add('HAVE_LCHOWN', 'chown')
    _add('HAVE_LINKAT', 'link')
    _add('HAVE_LUTIMES', 'utime')
    _add('HAVE_LSTAT', 'stat')
    _add('HAVE_FSTATAT', 'stat')
    _add('HAVE_UTIMENSAT', 'utime')
    _add('MS_WINDOWS', 'stat')
    supports_follow_symlinks = _set
    del _set
    del _have_functions
    del _globals
    del _addSEEK_SET = 0SEEK_CUR = 1SEEK_END = 2
def makedirs(name, mode=511, exist_ok=False):
    (head, tail) = path.split(name)
    if not tail:
        (head, tail) = path.split(head)
    if head and tail and not path.exists(head):
        try:
            makedirs(head, exist_ok=exist_ok)
        except FileExistsError:
            pass
        cdir = curdir
        if isinstance(tail, bytes):
            cdir = bytes(curdir, 'ASCII')
        if tail == cdir:
            return
    try:
        mkdir(name, mode)
    except OSError:
        if not (exist_ok and path.isdir(name)):
            raise

def removedirs(name):
    rmdir(name)
    (head, tail) = path.split(name)
    if not tail:
        (head, tail) = path.split(head)
    while head and tail:
        try:
            rmdir(head)
        except OSError:
            break
        (head, tail) = path.split(head)

def renames(old, new):
    (head, tail) = path.split(new)
    if head and tail and not path.exists(head):
        makedirs(head)
    rename(old, new)
    (head, tail) = path.split(old)
    if tail:
        try:
            removedirs(head)
        except OSError:
            pass
__all__.extend(['makedirs', 'removedirs', 'renames'])
def walk(top, topdown=True, onerror=None, followlinks=False):
    top = fspath(top)
    dirs = []
    nondirs = []
    walk_dirs = []
    try:
        scandir_it = scandir(top)
    except OSError as error:
        if onerror is not None:
            onerror(error)
        return
    with scandir_it:
        while True:
            try:
                try:
                    entry = next(scandir_it)
                except StopIteration:
                    break
            except OSError as error:
                if onerror is not None:
                    onerror(error)
                return
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            if is_dir:
                dirs.append(entry.name)
            else:
                nondirs.append(entry.name)
            if followlinks:
                walk_into = True
            else:
                try:
                    is_symlink = entry.is_symlink()
                except OSError:
                    is_symlink = False
                walk_into = not is_symlink
            if topdown or is_dir and walk_into:
                walk_dirs.append(entry.path)
    if topdown:
        yield (top, dirs, nondirs)
        islink = path.islink
        join = path.join
        for dirname in dirs:
            new_path = join(top, dirname)
            if followlinks or not islink(new_path):
                yield from walk(new_path, topdown, onerror, followlinks)
    else:
        for new_path in walk_dirs:
            yield from walk(new_path, topdown, onerror, followlinks)
        yield (top, dirs, nondirs)
__all__.append('walk')if {open, stat} <= supports_dir_fd and {scandir, stat} <= supports_fd:

    def fwalk(top='.', topdown=True, onerror=None, *, follow_symlinks=False, dir_fd=None):
        if not (isinstance(top, int) and hasattr(top, '__index__')):
            top = fspath(top)
        if not follow_symlinks:
            orig_st = stat(top, follow_symlinks=False, dir_fd=dir_fd)
        topfd = open(top, O_RDONLY, dir_fd=dir_fd)
        try:
            if follow_symlinks or st.S_ISDIR(orig_st.st_mode) and path.samestat(orig_st, stat(topfd)):
                yield from _fwalk(topfd, top, isinstance(top, bytes), topdown, onerror, follow_symlinks)
        finally:
            close(topfd)

    def _fwalk(topfd, toppath, isbytes, topdown, onerror, follow_symlinks):
        scandir_it = scandir(topfd)
        dirs = []
        nondirs = []
        entries = None if topdown or follow_symlinks else []
        for entry in scandir_it:
            name = entry.name
            name = fsencode(name)
            try:
                if entry.is_dir():
                    dirs.append(name)
                    if entries is not None:
                        entries.append(entry)
                else:
                    nondirs.append(name)
            except OSError:
                try:
                    if entry.is_symlink():
                        nondirs.append(name)
                except OSError:
                    pass
        if topdown:
            yield (toppath, dirs, nondirs, topfd)
        for name in dirs if entries is None else zip(dirs, entries):
            try:
                if topdown:
                    orig_st = stat(name, dir_fd=topfd, follow_symlinks=False)
                else:
                    (name, entry) = name
                    orig_st = entry.stat(follow_symlinks=False)
                dirfd = open(name, O_RDONLY, dir_fd=topfd)
            except OSError as err:
                if onerror is not None:
                    onerror(err)
                continue
            try:
                if follow_symlinks or path.samestat(orig_st, stat(dirfd)):
                    dirpath = path.join(toppath, name)
                    yield from _fwalk(dirfd, dirpath, isbytes, topdown, onerror, follow_symlinks)
            finally:
                close(dirfd)
        if not topdown:
            yield (toppath, dirs, nondirs, topfd)

    __all__.append('fwalk')try:
    environ
except NameError:
    environ = {}
def execl(file, *args):
    execv(file, args)

def execle(file, *args):
    env = args[-1]
    execve(file, args[:-1], env)

def execlp(file, *args):
    execvp(file, args)

def execlpe(file, *args):
    env = args[-1]
    execvpe(file, args[:-1], env)

def execvp(file, args):
    _execvpe(file, args)

def execvpe(file, args, env):
    _execvpe(file, args, env)
__all__.extend(['execl', 'execle', 'execlp', 'execlpe', 'execvp', 'execvpe'])
def _execvpe(file, args, env=None):
    if env is not None:
        exec_func = execve
        argrest = (args, env)
    else:
        exec_func = execv
        argrest = (args,)
        env = environ
    if path.dirname(file):
        exec_func(file, argrest)
        return
    saved_exc = None
    path_list = get_exec_path(env)
    if name != 'nt':
        file = fsencode(file)
        path_list = map(fsencode, path_list)
    for dir in path_list:
        fullname = path.join(dir, file)
        try:
            exec_func(fullname, argrest)
        except (FileNotFoundError, NotADirectoryError) as e:
            last_exc = e
        except OSError as e:
            last_exc = e
            if saved_exc is None:
                saved_exc = e
    if saved_exc is not None:
        raise saved_exc
    raise last_exc

def get_exec_path(env=None):
    import warnings
    if env is None:
        env = environ
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', BytesWarning)
        try:
            path_list = env.get('PATH')
        except TypeError:
            path_list = None
        if supports_bytes_environ:
            try:
                path_listb = env[b'PATH']
            except (KeyError, TypeError):
                pass
            if path_list is not None:
                raise ValueError("env cannot contain 'PATH' and b'PATH' keys")
            path_list = path_listb
            if isinstance(path_list, bytes):
                path_list = fsdecode(path_list)
    if path_list is None:
        path_list = defpath
    return path_list.split(pathsep)
from _collections_abc import MutableMapping
class _Environ(MutableMapping):

    def __init__(self, data, encodekey, decodekey, encodevalue, decodevalue, putenv, unsetenv):
        self.encodekey = encodekey
        self.decodekey = decodekey
        self.encodevalue = encodevalue
        self.decodevalue = decodevalue
        self.putenv = putenv
        self.unsetenv = unsetenv
        self._data = data

    def __getitem__(self, key):
        try:
            value = self._data[self.encodekey(key)]
        except KeyError:
            raise KeyError(key) from None
        return self.decodevalue(value)

    def __setitem__(self, key, value):
        key = self.encodekey(key)
        value = self.encodevalue(value)
        self.putenv(key, value)
        self._data[key] = value

    def __delitem__(self, key):
        encodedkey = self.encodekey(key)
        self.unsetenv(encodedkey)
        try:
            del self._data[encodedkey]
        except KeyError:
            raise KeyError(key) from None

    def __iter__(self):
        keys = list(self._data)
        for key in keys:
            yield self.decodekey(key)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return 'environ({{{}}})'.format(', '.join('{!r}: {!r}'.format(self.decodekey(key), self.decodevalue(value)) for (key, value) in self._data.items()))

    def copy(self):
        return dict(self)

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
        return self[key]
try:
    _putenv = putenv
except NameError:
    _putenv = lambda key, value: Noneif 'putenv' not in __all__:
    __all__.append('putenv')try:
    _unsetenv = unsetenv
except NameError:
    _unsetenv = lambda key: _putenv(key, '')if 'unsetenv' not in __all__:
    __all__.append('unsetenv')
def _createenviron():
    if name == 'nt':

        def check_str(value):
            if not isinstance(value, str):
                raise TypeError('str expected, not %s' % type(value).__name__)
            return value

        encode = check_str
        decode = str

        def encodekey(key):
            return encode(key).upper()

        data = {}
        for (key, value) in environ.items():
            data[encodekey(key)] = value
    else:
        encoding = sys.getfilesystemencoding()

        def encode(value):
            if not isinstance(value, str):
                raise TypeError('str expected, not %s' % type(value).__name__)
            return value.encode(encoding, 'surrogateescape')

        def decode(value):
            return value.decode(encoding, 'surrogateescape')

        encodekey = encode
        data = environ
    return _Environ(data, encodekey, decode, encode, decode, _putenv, _unsetenv)
environ = _createenviron()del _createenviron
def getenv(key, default=None):
    return environ.get(key, default)
supports_bytes_environ = name != 'nt'__all__.extend(('getenv', 'supports_bytes_environ'))if supports_bytes_environ:

    def _check_bytes(value):
        if not isinstance(value, bytes):
            raise TypeError('bytes expected, not %s' % type(value).__name__)
        return value

    environb = _Environ(environ._data, _check_bytes, bytes, _check_bytes, bytes, _putenv, _unsetenv)
    del _check_bytes

    def getenvb(key, default=None):
        return environb.get(key, default)

    __all__.extend(('environb', 'getenvb'))
def _fscodec():
    encoding = sys.getfilesystemencoding()
    errors = sys.getfilesystemencodeerrors()

    def fsencode(filename):
        filename = fspath(filename)
        if isinstance(filename, str):
            return filename.encode(encoding, errors)
        else:
            return filename

    def fsdecode(filename):
        filename = fspath(filename)
        if isinstance(filename, bytes):
            return filename.decode(encoding, errors)
        else:
            return filename

    return (fsencode, fsdecode)
(fsencode, fsdecode) = _fscodec()del _fscodecif _exists('fork') and (_exists('spawnv') or _exists('execv')):
    P_WAIT = 0
    P_NOWAIT = P_NOWAITO = 1
    __all__.extend(['P_WAIT', 'P_NOWAIT', 'P_NOWAITO'])

    def _spawnvef(mode, file, args, env, func):
        if not isinstance(args, (tuple, list)):
            raise TypeError('argv must be a tuple or a list')
        if not (args and args[0]):
            raise ValueError('argv first element cannot be empty')
        pid = fork()
        if not pid:
            try:
                if env is None:
                    func(file, args)
                else:
                    func(file, args, env)
            except:
                _exit(127)
        else:
            if mode == P_NOWAIT:
                return pid
            while True:
                (wpid, sts) = waitpid(pid, 0)
                if WIFSTOPPED(sts):
                    pass
                else:
                    if WIFSIGNALED(sts):
                        return -WTERMSIG(sts)
                    if WIFEXITED(sts):
                        return WEXITSTATUS(sts)
                    raise OSError('Not stopped, signaled or exited???')

    def spawnv(mode, file, args):
        return _spawnvef(mode, file, args, None, execv)

    def spawnve(mode, file, args, env):
        return _spawnvef(mode, file, args, env, execve)

    def spawnvp(mode, file, args):
        return _spawnvef(mode, file, args, None, execvp)

    def spawnvpe(mode, file, args, env):
        return _spawnvef(mode, file, args, env, execvpe)

    __all__.extend(['spawnv', 'spawnve', 'spawnvp', 'spawnvpe'])if _exists('spawnv'):

    def spawnl(mode, file, *args):
        return spawnv(mode, file, args)

    def spawnle(mode, file, *args):
        env = args[-1]
        return spawnve(mode, file, args[:-1], env)

    __all__.extend(['spawnl', 'spawnle'])if _exists('spawnvp'):

    def spawnlp(mode, file, *args):
        return spawnvp(mode, file, args)

    def spawnlpe(mode, file, *args):
        env = args[-1]
        return spawnvpe(mode, file, args[:-1], env)

    __all__.extend(['spawnlp', 'spawnlpe'])
def popen(cmd, mode='r', buffering=-1):
    if not isinstance(cmd, str):
        raise TypeError('invalid cmd type (%s, expected string)' % type(cmd))
    if mode not in ('r', 'w'):
        raise ValueError('invalid mode %r' % mode)
    if buffering == 0 or buffering is None:
        raise ValueError('popen() does not support unbuffered streams')
    import subprocess
    import io
    if mode == 'r':
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, bufsize=buffering)
        return _wrap_close(io.TextIOWrapper(proc.stdout), proc)
    else:
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, bufsize=buffering)
        return _wrap_close(io.TextIOWrapper(proc.stdin), proc)

class _wrap_close:

    def __init__(self, stream, proc):
        self._stream = stream
        self._proc = proc

    def close(self):
        self._stream.close()
        returncode = self._proc.wait()
        if returncode == 0:
            return
        if name == 'nt':
            return returncode
        else:
            return returncode << 8

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __iter__(self):
        return iter(self._stream)

def fdopen(fd, *args, **kwargs):
    if not isinstance(fd, int):
        raise TypeError('invalid fd type (%s, expected integer)' % type(fd))
    import io
    return io.open(fd, *args, **kwargs)

def _fspath(path):
    if isinstance(path, (str, bytes)):
        return path
    path_type = type(path)
    try:
        path_repr = path_type.__fspath__(path)
    except AttributeError:
        if hasattr(path_type, '__fspath__'):
            raise
        else:
            raise TypeError('expected str, bytes or os.PathLike object, not ' + path_type.__name__)
    if isinstance(path_repr, (str, bytes)):
        return path_repr
    raise TypeError('expected {}.__fspath__() to return str or bytes, not {}'.format(path_type.__name__, type(path_repr).__name__))
if not _exists('fspath'):
    fspath = _fspath
    fspath.__name__ = 'fspath'
class PathLike(abc.ABC):

    @abc.abstractmethod
    def __fspath__(self):
        raise NotImplementedError

    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, '__fspath__')
