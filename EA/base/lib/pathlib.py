import fnmatchimport functoolsimport ioimport ntpathimport osimport posixpathimport reimport sysfrom _collections_abc import Sequencefrom errno import EINVAL, ENOENT, ENOTDIRfrom operator import attrgetterfrom stat import S_ISDIR, S_ISLNK, S_ISREG, S_ISSOCK, S_ISBLK, S_ISCHR, S_ISFIFOfrom urllib.parse import quote_from_bytes as urlquote_from_bytessupports_symlinks = Trueif os.name == 'nt':
    import nt
    if sys.getwindowsversion()[:2] >= (6, 0):
        from nt import _getfinalpathname
    else:
        supports_symlinks = False
        _getfinalpathname = None
else:
    nt = None__all__ = ['PurePath', 'PurePosixPath', 'PureWindowsPath', 'Path', 'PosixPath', 'WindowsPath']
def _is_wildcard_pattern(pat):
    return '*' in pat or ('?' in pat or '[' in pat)

class _Flavour(object):

    def __init__(self):
        self.join = self.sep.join

    def parse_parts(self, parts):
        parsed = []
        sep = self.sep
        altsep = self.altsep
        drv = root = ''
        it = reversed(parts)
        for part in it:
            if not part:
                pass
            else:
                if altsep:
                    part = part.replace(altsep, sep)
                (drv, root, rel) = self.splitroot(part)
                if sep in rel:
                    for x in reversed(rel.split(sep)):
                        if x and x != '.':
                            parsed.append(sys.intern(x))
                elif rel and rel != '.':
                    parsed.append(sys.intern(rel))
                if not drv:
                    if root:
                        for part in it:
                            if not part:
                                pass
                            else:
                                if altsep:
                                    part = part.replace(altsep, sep)
                                drv = self.splitroot(part)[0]
                                if drv:
                                    break
                        break
                for part in it:
                    if not part:
                        pass
                    else:
                        if altsep:
                            part = part.replace(altsep, sep)
                        drv = self.splitroot(part)[0]
                        if drv:
                            break
                break
        if drv or root:
            parsed.append(drv + root)
        parsed.reverse()
        return (drv, root, parsed)

    def join_parsed_parts(self, drv, root, parts, drv2, root2, parts2):
        if root2:
            if drv2 or drv:
                return (drv, root2, [drv + root2] + parts2[1:])
        elif drv2:
            if drv2 == drv or self.casefold(drv2) == self.casefold(drv):
                return (drv, root, parts + parts2[1:])
        else:
            return (drv, root, parts + parts2)
        return (drv2, root2, parts2)

class _WindowsFlavour(_Flavour):
    sep = '\\'
    altsep = '/'
    has_drv = True
    pathmod = ntpath
    is_supported = os.name == 'nt'
    drive_letters = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    ext_namespace_prefix = '\\\\?\\'
    reserved_names = {'CON', 'PRN', 'AUX', 'NUL'} | {'COM%d' % i for i in range(1, 10)} | {'LPT%d' % i for i in range(1, 10)}

    def splitroot(self, part, sep=sep):
        first = part[0:1]
        second = part[1:2]
        if second == sep and first == sep:
            (prefix, part) = self._split_extended_path(part)
            first = part[0:1]
            second = part[1:2]
        else:
            prefix = ''
        third = part[2:3]
        if second == sep and first == sep and third != sep:
            index = part.find(sep, 2)
            if index != -1:
                index2 = part.find(sep, index + 1)
                if index2 != index + 1:
                    if index2 == -1:
                        index2 = len(part)
                    if prefix:
                        return (prefix + part[1:index2], sep, part[index2 + 1:])
                    return (part[:index2], sep, part[index2 + 1:])
        drv = root = ''
        if first in self.drive_letters:
            drv = part[:2]
            part = part[2:]
            first = third
        if second == ':' and first == sep:
            root = first
            part = part.lstrip(sep)
        return (prefix + drv, root, part)

    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]

    def resolve(self, path, strict=False):
        s = str(path)
        if not s:
            return os.getcwd()
        previous_s = None
        if _getfinalpathname is not None:
            if strict:
                return self._ext_to_normal(_getfinalpathname(s))
            tail_parts = []
            while True:
                try:
                    s = self._ext_to_normal(_getfinalpathname(s))
                except FileNotFoundError:
                    previous_s = s
                    (s, tail) = os.path.split(s)
                    tail_parts.append(tail)
                    if previous_s == s:
                        return path
                return os.path.join(s, reversed(tail_parts))

    def _split_extended_path(self, s, ext_prefix=ext_namespace_prefix):
        prefix = ''
        if s.startswith(ext_prefix):
            prefix = s[:4]
            s = s[4:]
            if s.startswith('UNC\\'):
                prefix += s[:3]
                s = '\\' + s[3:]
        return (prefix, s)

    def _ext_to_normal(self, s):
        return self._split_extended_path(s)[1]

    def is_reserved(self, parts):
        if not parts:
            return False
        if parts[0].startswith('\\\\'):
            return False
        return parts[-1].partition('.')[0].upper() in self.reserved_names

    def make_uri(self, path):
        drive = path.drive
        if len(drive) == 2 and drive[1] == ':':
            rest = path.as_posix()[2:].lstrip('/')
            return 'file:///%s/%s' % (drive, urlquote_from_bytes(rest.encode('utf-8')))
        else:
            return 'file:' + urlquote_from_bytes(path.as_posix().encode('utf-8'))

    def gethomedir(self, username):
        if 'HOME' in os.environ:
            userhome = os.environ['HOME']
        elif 'USERPROFILE' in os.environ:
            userhome = os.environ['USERPROFILE']
        elif 'HOMEPATH' in os.environ:
            try:
                drv = os.environ['HOMEDRIVE']
            except KeyError:
                drv = ''
            userhome = drv + os.environ['HOMEPATH']
        else:
            raise RuntimeError("Can't determine home directory")
        if os.environ['USERNAME'] != username:
            (drv, root, parts) = self.parse_parts((userhome,))
            if parts[-1] != os.environ['USERNAME']:
                raise RuntimeError("Can't determine home directory for %r" % username)
            parts[-1] = username
            if drv or root:
                userhome = drv + root + self.join(parts[1:])
            else:
                userhome = self.join(parts)
        return userhome

class _PosixFlavour(_Flavour):
    sep = '/'
    altsep = ''
    has_drv = False
    pathmod = posixpath
    is_supported = os.name != 'nt'

    def splitroot(self, part, sep=sep):
        if part and part[0] == sep:
            stripped_part = part.lstrip(sep)
            if len(part) - len(stripped_part) == 2:
                return ('', sep*2, stripped_part)
            return ('', sep, stripped_part)
        else:
            return ('', '', part)

    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts

    def resolve(self, path, strict=False):
        sep = self.sep
        accessor = path._accessor
        seen = {}

        def _resolve(path, rest):
            if rest.startswith(sep):
                path = ''
            for name in rest.split(sep):
                if name:
                    if name == '.':
                        pass
                    elif name == '..':
                        (path, _, _) = path.rpartition(sep)
                    else:
                        newpath = path + sep + name
                        if newpath in seen:
                            path = seen[newpath]
                            if path is not None:
                                pass
                            else:
                                raise RuntimeError('Symlink loop from %r' % newpath)
                                try:
                                    target = accessor.readlink(newpath)
                                except OSError as e:
                                    if e.errno != EINVAL and strict:
                                        raise
                                    path = newpath
                                seen[newpath] = None
                                path = _resolve(path, target)
                                seen[newpath] = path
                        try:
                            target = accessor.readlink(newpath)
                        except OSError as e:
                            if e.errno != EINVAL and strict:
                                raise
                            path = newpath
                        seen[newpath] = None
                        path = _resolve(path, target)
                        seen[newpath] = path
            return path

        base = '' if path.is_absolute() else os.getcwd()
        return _resolve(base, str(path)) or sep

    def is_reserved(self, parts):
        return False

    def make_uri(self, path):
        bpath = bytes(path)
        return 'file://' + urlquote_from_bytes(bpath)

    def gethomedir(self, username):
        if not username:
            try:
                return os.environ['HOME']
            except KeyError:
                import pwd
                return pwd.getpwuid(os.getuid()).pw_dir
        else:
            import pwd
            try:
                return pwd.getpwnam(username).pw_dir
            except KeyError:
                raise RuntimeError("Can't determine home directory for %r" % username)
_windows_flavour = _WindowsFlavour()_posix_flavour = _PosixFlavour()
class _Accessor:
    pass

class _NormalAccessor(_Accessor):
    stat = os.stat
    lstat = os.lstat
    open = os.open
    listdir = os.listdir
    scandir = os.scandir
    chmod = os.chmod
    if hasattr(os, 'lchmod'):
        lchmod = os.lchmod
    else:

        def lchmod(self, pathobj, mode):
            raise NotImplementedError('lchmod() not available on this system')

    mkdir = os.mkdir
    unlink = os.unlink
    rmdir = os.rmdir
    rename = os.rename
    replace = os.replace
    if nt:
        if supports_symlinks:
            symlink = os.symlink
        else:

            def symlink(a, b, target_is_directory):
                raise NotImplementedError('symlink() not available on this system')

    else:

        @staticmethod
        def symlink(a, b, target_is_directory):
            return os.symlink(a, b)

    utime = os.utime

    def readlink(self, path):
        return os.readlink(path)
_normal_accessor = _NormalAccessor()
def _make_selector(pattern_parts):
    pat = pattern_parts[0]
    child_parts = pattern_parts[1:]
    if pat == '**':
        cls = _RecursiveWildcardSelector
    elif '**' in pat:
        raise ValueError("Invalid pattern: '**' can only be an entire path component")
    elif _is_wildcard_pattern(pat):
        cls = _WildcardSelector
    else:
        cls = _PreciseSelector
    return cls(pat, child_parts)
if hasattr(functools, 'lru_cache'):
    _make_selector = functools.lru_cache()(_make_selector)
class _Selector:

    def __init__(self, child_parts):
        self.child_parts = child_parts
        if child_parts:
            self.successor = _make_selector(child_parts)
            self.dironly = True
        else:
            self.successor = _TerminatingSelector()
            self.dironly = False

    def select_from(self, parent_path):
        path_cls = type(parent_path)
        is_dir = path_cls.is_dir
        exists = path_cls.exists
        scandir = parent_path._accessor.scandir
        if not is_dir(parent_path):
            return iter([])
        return self._select_from(parent_path, is_dir, exists, scandir)

class _TerminatingSelector:

    def _select_from(self, parent_path, is_dir, exists, scandir):
        yield parent_path

class _PreciseSelector(_Selector):

    def __init__(self, name, child_parts):
        self.name = name
        _Selector.__init__(self, child_parts)

    def _select_from(self, parent_path, is_dir, exists, scandir):
        try:
            path = parent_path._make_child_relpath(self.name)
            if (is_dir if self.dironly else exists)(path):
                for p in self.successor._select_from(path, is_dir, exists, scandir):
                    yield p
        except PermissionError:
            return

class _WildcardSelector(_Selector):

    def __init__(self, pat, child_parts):
        self.pat = re.compile(fnmatch.translate(pat))
        _Selector.__init__(self, child_parts)

    def _select_from(self, parent_path, is_dir, exists, scandir):
        try:
            cf = parent_path._flavour.casefold
            entries = list(scandir(parent_path))
            for entry in entries:
                if not self.dironly or entry.is_dir():
                    name = entry.name
                    casefolded = cf(name)
                    if self.pat.match(casefolded):
                        path = parent_path._make_child_relpath(name)
                        for p in self.successor._select_from(path, is_dir, exists, scandir):
                            yield p
        except PermissionError:
            return

class _RecursiveWildcardSelector(_Selector):

    def __init__(self, pat, child_parts):
        _Selector.__init__(self, child_parts)

    def _iterate_directories(self, parent_path, is_dir, scandir):
        yield parent_path
        try:
            entries = list(scandir(parent_path))
            for entry in entries:
                if entry.is_dir() and not entry.is_symlink():
                    path = parent_path._make_child_relpath(entry.name)
                    for p in self._iterate_directories(path, is_dir, scandir):
                        yield p
        except PermissionError:
            return

    def _select_from(self, parent_path, is_dir, exists, scandir):
        try:
            yielded = set()
            try:
                successor_select = self.successor._select_from
                for starting_point in self._iterate_directories(parent_path, is_dir, scandir):
                    for p in successor_select(starting_point, is_dir, exists, scandir):
                        if p not in yielded:
                            yield p
                            yielded.add(p)
            finally:
                yielded.clear()
        except PermissionError:
            return

class _PathParents(Sequence):
    __slots__ = ('_pathcls', '_drv', '_root', '_parts')

    def __init__(self, path):
        self._pathcls = type(path)
        self._drv = path._drv
        self._root = path._root
        self._parts = path._parts

    def __len__(self):
        if self._drv or self._root:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    def __getitem__(self, idx):
        if idx < 0 or idx >= len(self):
            raise IndexError(idx)
        return self._pathcls._from_parsed_parts(self._drv, self._root, self._parts[:-idx - 1])

    def __repr__(self):
        return '<{}.parents>'.format(self._pathcls.__name__)

class PurePath(object):
    __slots__ = ('_drv', '_root', '_parts', '_str', '_hash', '_pparts', '_cached_cparts')

    def __new__(cls, *args):
        if cls is PurePath:
            cls = PureWindowsPath if os.name == 'nt' else PurePosixPath
        return cls._from_parts(args)

    def __reduce__(self):
        return (self.__class__, tuple(self._parts))

    @classmethod
    def _parse_args(cls, args):
        parts = []
        for a in args:
            if isinstance(a, PurePath):
                parts += a._parts
            else:
                a = os.fspath(a)
                if isinstance(a, str):
                    parts.append(str(a))
                else:
                    raise TypeError('argument should be a str object or an os.PathLike object returning str, not %r' % type(a))
        return cls._flavour.parse_parts(parts)

    @classmethod
    def _from_parts(cls, args, init=True):
        self = object.__new__(cls)
        (drv, root, parts) = self._parse_args(args)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            self._init()
        return self

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, init=True):
        self = object.__new__(cls)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            self._init()
        return self

    @classmethod
    def _format_parsed_parts(cls, drv, root, parts):
        if drv or root:
            return drv + root + cls._flavour.join(parts[1:])
        else:
            return cls._flavour.join(parts)

    def _init(self):
        pass

    def _make_child(self, args):
        (drv, root, parts) = self._parse_args(args)
        (drv, root, parts) = self._flavour.join_parsed_parts(self._drv, self._root, self._parts, drv, root, parts)
        return self._from_parsed_parts(drv, root, parts)

    def __str__(self):
        try:
            return self._str
        except AttributeError:
            self._str = self._format_parsed_parts(self._drv, self._root, self._parts) or '.'
            return self._str

    def __fspath__(self):
        return str(self)

    def as_posix(self):
        f = self._flavour
        return str(self).replace(f.sep, '/')

    def __bytes__(self):
        return os.fsencode(self)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.as_posix())

    def as_uri(self):
        if not self.is_absolute():
            raise ValueError("relative path can't be expressed as a file URI")
        return self._flavour.make_uri(self)

    @property
    def _cparts(self):
        try:
            return self._cached_cparts
        except AttributeError:
            self._cached_cparts = self._flavour.casefold_parts(self._parts)
            return self._cached_cparts

    def __eq__(self, other):
        if not isinstance(other, PurePath):
            return NotImplemented
        return self._cparts == other._cparts and self._flavour is other._flavour

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(tuple(self._cparts))
            return self._hash

    def __lt__(self, other):
        if isinstance(other, PurePath) and self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts < other._cparts

    def __le__(self, other):
        if isinstance(other, PurePath) and self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts <= other._cparts

    def __gt__(self, other):
        if isinstance(other, PurePath) and self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts > other._cparts

    def __ge__(self, other):
        if isinstance(other, PurePath) and self._flavour is not other._flavour:
            return NotImplemented
        return self._cparts >= other._cparts

    drive = property(attrgetter('_drv'), doc='The drive prefix (letter or UNC path), if any.')
    root = property(attrgetter('_root'), doc='The root of the path, if any.')

    @property
    def anchor(self):
        anchor = self._drv + self._root
        return anchor

    @property
    def name(self):
        parts = self._parts
        if len(parts) == 1 if self._drv or self._root else 0:
            return ''
        return parts[-1]

    @property
    def suffix(self):
        name = self.name
        i = name.rfind('.')
        if 0 < i and i < len(name) - 1:
            return name[i:]
        else:
            return ''

    @property
    def suffixes(self):
        name = self.name
        if name.endswith('.'):
            return []
        name = name.lstrip('.')
        return ['.' + suffix for suffix in name.split('.')[1:]]

    @property
    def stem(self):
        name = self.name
        i = name.rfind('.')
        if 0 < i and i < len(name) - 1:
            return name[:i]
        else:
            return name

    def with_name(self, name):
        if not self.name:
            raise ValueError('%r has an empty name' % (self,))
        (drv, root, parts) = self._flavour.parse_parts((name,))
        if name and (name[-1] in [self._flavour.sep, self._flavour.altsep] or (drv or root) or len(parts) != 1):
            raise ValueError('Invalid name %r' % name)
        return self._from_parsed_parts(self._drv, self._root, self._parts[:-1] + [name])

    def with_suffix(self, suffix):
        f = self._flavour
        if f.sep in suffix or f.altsep and f.altsep in suffix:
            raise ValueError('Invalid suffix %r' % suffix)
        if suffix and suffix.startswith('.') and suffix == '.':
            raise ValueError('Invalid suffix %r' % suffix)
        name = self.name
        if not name:
            raise ValueError('%r has an empty name' % (self,))
        old_suffix = self.suffix
        if not old_suffix:
            name = name + suffix
        else:
            name = name[:-len(old_suffix)] + suffix
        return self._from_parsed_parts(self._drv, self._root, self._parts[:-1] + [name])

    def relative_to(self, *other):
        if not other:
            raise TypeError('need at least one argument')
        parts = self._parts
        drv = self._drv
        root = self._root
        if root:
            abs_parts = [drv, root] + parts[1:]
        else:
            abs_parts = parts
        (to_drv, to_root, to_parts) = self._parse_args(other)
        if to_root:
            to_abs_parts = [to_drv, to_root] + to_parts[1:]
        else:
            to_abs_parts = to_parts
        n = len(to_abs_parts)
        cf = self._flavour.casefold_parts
        if n == 0:
            pass
        elif cf(abs_parts[:n]) != cf(to_abs_parts):
            formatted = self._format_parsed_parts(to_drv, to_root, to_parts)
            raise ValueError('{!r} does not start with {!r}'.format(str(self), str(formatted)))
        formatted = self._format_parsed_parts(to_drv, to_root, to_parts)
        raise ValueError('{!r} does not start with {!r}'.format(str(self), str(formatted)))
        return self._from_parsed_parts('', root if n == 1 else '', abs_parts[n:])

    @property
    def parts(self):
        try:
            return self._pparts
        except AttributeError:
            self._pparts = tuple(self._parts)
            return self._pparts

    def joinpath(self, *args):
        return self._make_child(args)

    def __truediv__(self, key):
        return self._make_child((key,))

    def __rtruediv__(self, key):
        return self._from_parts([key] + self._parts)

    @property
    def parent(self):
        drv = self._drv
        root = self._root
        parts = self._parts
        if len(parts) == 1 and (drv or root):
            return self
        return self._from_parsed_parts(drv, root, parts[:-1])

    @property
    def parents(self):
        return _PathParents(self)

    def is_absolute(self):
        if not self._root:
            return False
        return not self._flavour.has_drv or bool(self._drv)

    def is_reserved(self):
        return self._flavour.is_reserved(self._parts)

    def match(self, path_pattern):
        cf = self._flavour.casefold
        path_pattern = cf(path_pattern)
        (drv, root, pat_parts) = self._flavour.parse_parts((path_pattern,))
        if not pat_parts:
            raise ValueError('empty pattern')
        if drv and drv != cf(self._drv):
            return False
        if root and root != cf(self._root):
            return False
        parts = self._cparts
        if drv or root:
            if len(pat_parts) != len(parts):
                return False
            pat_parts = pat_parts[1:]
        elif len(pat_parts) > len(parts):
            return False
        for (part, pat) in zip(reversed(parts), reversed(pat_parts)):
            if not fnmatch.fnmatchcase(part, pat):
                return False
        return True
os.PathLike.register(PurePath)
class PurePosixPath(PurePath):
    _flavour = _posix_flavour
    __slots__ = ()

class PureWindowsPath(PurePath):
    _flavour = _windows_flavour
    __slots__ = ()

class Path(PurePath):
    __slots__ = ('_accessor', '_closed')

    def __new__(cls, *args, **kwargs):
        if cls is Path:
            cls = WindowsPath if os.name == 'nt' else PosixPath
        self = cls._from_parts(args, init=False)
        if not self._flavour.is_supported:
            raise NotImplementedError('cannot instantiate %r on your system' % (cls.__name__,))
        self._init()
        return self

    def _init(self, template=None):
        self._closed = False
        if template is not None:
            self._accessor = template._accessor
        else:
            self._accessor = _normal_accessor

    def _make_child_relpath(self, part):
        parts = self._parts + [part]
        return self._from_parsed_parts(self._drv, self._root, parts)

    def __enter__(self):
        if self._closed:
            self._raise_closed()
        return self

    def __exit__(self, t, v, tb):
        self._closed = True

    def _raise_closed(self):
        raise ValueError('I/O operation on closed path')

    def _opener(self, name, flags, mode=438):
        return self._accessor.open(self, flags, mode)

    def _raw_open(self, flags, mode=511):
        if self._closed:
            self._raise_closed()
        return self._accessor.open(self, flags, mode)

    @classmethod
    def cwd(cls):
        return cls(os.getcwd())

    @classmethod
    def home(cls):
        return cls(cls()._flavour.gethomedir(None))

    def samefile(self, other_path):
        st = self.stat()
        try:
            other_st = other_path.stat()
        except AttributeError:
            other_st = os.stat(other_path)
        return os.path.samestat(st, other_st)

    def iterdir(self):
        if self._closed:
            self._raise_closed()
        for name in self._accessor.listdir(self):
            if name in frozenset({'.', '..'}):
                pass
            else:
                yield self._make_child_relpath(name)
                if self._closed:
                    self._raise_closed()

    def glob(self, pattern):
        if not pattern:
            raise ValueError('Unacceptable pattern: {!r}'.format(pattern))
        pattern = self._flavour.casefold(pattern)
        (drv, root, pattern_parts) = self._flavour.parse_parts((pattern,))
        if drv or root:
            raise NotImplementedError('Non-relative patterns are unsupported')
        selector = _make_selector(tuple(pattern_parts))
        for p in selector.select_from(self):
            yield p

    def rglob(self, pattern):
        pattern = self._flavour.casefold(pattern)
        (drv, root, pattern_parts) = self._flavour.parse_parts((pattern,))
        if drv or root:
            raise NotImplementedError('Non-relative patterns are unsupported')
        selector = _make_selector(('**',) + tuple(pattern_parts))
        for p in selector.select_from(self):
            yield p

    def absolute(self):
        if self._closed:
            self._raise_closed()
        if self.is_absolute():
            return self
        obj = self._from_parts([os.getcwd()] + self._parts, init=False)
        obj._init(template=self)
        return obj

    def resolve(self, strict=False):
        if self._closed:
            self._raise_closed()
        s = self._flavour.resolve(self, strict=strict)
        if s is None:
            self.stat()
            s = str(self.absolute())
        normed = self._flavour.pathmod.normpath(s)
        obj = self._from_parts((normed,), init=False)
        obj._init(template=self)
        return obj

    def stat(self):
        return self._accessor.stat(self)

    def owner(self):
        import pwd
        return pwd.getpwuid(self.stat().st_uid).pw_name

    def group(self):
        import grp
        return grp.getgrgid(self.stat().st_gid).gr_name

    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        if self._closed:
            self._raise_closed()
        return io.open(self, mode, buffering, encoding, errors, newline, opener=self._opener)

    def read_bytes(self):
        with self.open(mode='rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        with self.open(mode='r', encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        view = memoryview(data)
        with self.open(mode='wb') as f:
            return f.write(view)

    def write_text(self, data, encoding=None, errors=None):
        if not isinstance(data, str):
            raise TypeError('data must be str, not %s' % data.__class__.__name__)
        with self.open(mode='w', encoding=encoding, errors=errors) as f:
            return f.write(data)

    def touch(self, mode=438, exist_ok=True):
        if self._closed:
            self._raise_closed()
        if exist_ok:
            try:
                self._accessor.utime(self, None)
            except OSError:
                pass
            return
        flags = os.O_CREAT | os.O_WRONLY
        if not exist_ok:
            flags |= os.O_EXCL
        fd = self._raw_open(flags, mode)
        os.close(fd)

    def mkdir(self, mode=511, parents=False, exist_ok=False):
        if self._closed:
            self._raise_closed()
        try:
            self._accessor.mkdir(self, mode)
        except FileNotFoundError:
            if parents and self.parent == self:
                raise
            self.parent.mkdir(parents=True, exist_ok=True)
            self.mkdir(mode, parents=False, exist_ok=exist_ok)
        except OSError:
            if not (exist_ok and self.is_dir()):
                raise

    def chmod(self, mode):
        if self._closed:
            self._raise_closed()
        self._accessor.chmod(self, mode)

    def lchmod(self, mode):
        if self._closed:
            self._raise_closed()
        self._accessor.lchmod(self, mode)

    def unlink(self):
        if self._closed:
            self._raise_closed()
        self._accessor.unlink(self)

    def rmdir(self):
        if self._closed:
            self._raise_closed()
        self._accessor.rmdir(self)

    def lstat(self):
        if self._closed:
            self._raise_closed()
        return self._accessor.lstat(self)

    def rename(self, target):
        if self._closed:
            self._raise_closed()
        self._accessor.rename(self, target)

    def replace(self, target):
        if self._closed:
            self._raise_closed()
        self._accessor.replace(self, target)

    def symlink_to(self, target, target_is_directory=False):
        if self._closed:
            self._raise_closed()
        self._accessor.symlink(target, self, target_is_directory)

    def exists(self):
        try:
            self.stat()
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False
        return True

    def is_dir(self):
        try:
            return S_ISDIR(self.stat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def is_file(self):
        try:
            return S_ISREG(self.stat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def is_mount(self):
        if not (self.exists() and self.is_dir()):
            return False
        parent = Path(self.parent)
        try:
            parent_dev = parent.stat().st_dev
        except OSError:
            return False
        dev = self.stat().st_dev
        if dev != parent_dev:
            return True
        ino = self.stat().st_ino
        parent_ino = parent.stat().st_ino
        return ino == parent_ino

    def is_symlink(self):
        try:
            return S_ISLNK(self.lstat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def is_block_device(self):
        try:
            return S_ISBLK(self.stat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def is_char_device(self):
        try:
            return S_ISCHR(self.stat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def is_fifo(self):
        try:
            return S_ISFIFO(self.stat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def is_socket(self):
        try:
            return S_ISSOCK(self.stat().st_mode)
        except OSError as e:
            if e.errno not in (ENOENT, ENOTDIR):
                raise
            return False

    def expanduser(self):
        if self._drv or self._root or self._parts and self._parts[0][:1] == '~':
            homedir = self._flavour.gethomedir(self._parts[0][1:])
            return self._from_parts([homedir] + self._parts[1:])
        return self

class PosixPath(Path, PurePosixPath):
    __slots__ = ()

class WindowsPath(Path, PureWindowsPath):
    __slots__ = ()

    def owner(self):
        raise NotImplementedError('Path.owner() is unsupported on this system')

    def group(self):
        raise NotImplementedError('Path.group() is unsupported on this system')

    def is_mount(self):
        raise NotImplementedError('Path.is_mount() is unsupported on this system')
