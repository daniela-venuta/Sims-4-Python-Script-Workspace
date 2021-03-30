curdir = '.'pardir = '..'extsep = '.'sep = '\\'pathsep = ';'altsep = '/'defpath = '.;C:\\bin'devnull = 'nul'import osimport sysimport statimport genericpathfrom genericpath import *__all__ = ['normcase', 'isabs', 'join', 'splitdrive', 'split', 'splitext', 'basename', 'dirname', 'commonprefix', 'getsize', 'getmtime', 'getatime', 'getctime', 'islink', 'exists', 'lexists', 'isdir', 'isfile', 'ismount', 'expanduser', 'expandvars', 'normpath', 'abspath', 'curdir', 'pardir', 'sep', 'pathsep', 'defpath', 'altsep', 'extsep', 'devnull', 'realpath', 'supports_unicode_filenames', 'relpath', 'samefile', 'sameopenfile', 'samestat', 'commonpath']
def _get_bothseps(path):
    if isinstance(path, bytes):
        return b'\\/'
    else:
        return '\\/'

def normcase(s):
    s = os.fspath(s)
    try:
        if isinstance(s, bytes):
            return s.replace(b'/', b'\\').lower()
        return s.replace('/', '\\').lower()
    except (TypeError, AttributeError):
        if not isinstance(s, (bytes, str)):
            raise TypeError('normcase() argument must be str or bytes, not %r' % s.__class__.__name__) from None
        raise

def isabs(s):
    s = os.fspath(s)
    s = splitdrive(s)[1]
    return len(s) > 0 and s[0] in _get_bothseps(s)

def join(path, *paths):
    path = os.fspath(path)
    if isinstance(path, bytes):
        sep = b'\\'
        seps = b'\\/'
        colon = b':'
    else:
        sep = '\\'
        seps = '\\/'
        colon = ':'
    try:
        if not paths:
            path[:0] + sep
        (result_drive, result_path) = splitdrive(path)
        for p in map(os.fspath, paths):
            (p_drive, p_path) = splitdrive(p)
            if p_path and p_path[0] in seps:
                if not (p_drive or result_drive):
                    result_drive = p_drive
                result_path = p_path
            elif p_drive != result_drive:
                if p_drive.lower() != result_drive.lower():
                    result_drive = p_drive
                    result_path = p_path
                else:
                    result_drive = p_drive
                    if result_path[-1] not in seps:
                        result_path = result_path + sep
                    result_path = result_path + p_path
            if result_path[-1] not in seps:
                result_path = result_path + sep
            result_path = result_path + p_path
        if result_path and (result_path[0] not in seps and result_drive) and result_drive[-1:] != colon:
            return result_drive + sep + result_path
        return result_drive + result_path
    except (TypeError, AttributeError, BytesWarning):
        genericpath._check_arg_types('join', path, paths)
        raise

def splitdrive(p):
    p = os.fspath(p)
    if len(p) >= 2:
        if isinstance(p, bytes):
            sep = b'\\'
            altsep = b'/'
            colon = b':'
        else:
            sep = '\\'
            altsep = '/'
            colon = ':'
        normp = p.replace(altsep, sep)
        if normp[0:2] == sep*2 and normp[2:3] != sep:
            index = normp.find(sep, 2)
            if index == -1:
                return (p[:0], p)
            index2 = normp.find(sep, index + 1)
            if index2 == index + 1:
                return (p[:0], p)
            if index2 == -1:
                index2 = len(p)
            return (p[:index2], p[index2:])
        if normp[1:2] == colon:
            return (p[:2], p[2:])
    return (p[:0], p)

def split(p):
    p = os.fspath(p)
    seps = _get_bothseps(p)
    (d, p) = splitdrive(p)
    i = len(p)
    while i and p[i - 1] not in seps:
        i -= 1
    head = p[:i]
    tail = p[i:]
    head = head.rstrip(seps) or head
    return (d + head, tail)

def splitext(p):
    p = os.fspath(p)
    if isinstance(p, bytes):
        return genericpath._splitext(p, b'\\', b'/', b'.')
    else:
        return genericpath._splitext(p, '\\', '/', '.')
splitext.__doc__ = genericpath._splitext.__doc__
def basename(p):
    return split(p)[1]

def dirname(p):
    return split(p)[0]

def islink(path):
    try:
        st = os.lstat(path)
    except (OSError, AttributeError):
        return False
    return stat.S_ISLNK(st.st_mode)

def lexists(path):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return True
try:
    from nt import _getvolumepathname
except ImportError:
    _getvolumepathname = None
def ismount(path):
    path = os.fspath(path)
    seps = _get_bothseps(path)
    path = abspath(path)
    (root, rest) = splitdrive(path)
    if root and root[0] in seps:
        return not rest or rest in seps
    if rest in seps:
        return True
    elif _getvolumepathname:
        return path.rstrip(seps) == _getvolumepathname(path).rstrip(seps)
    else:
        return False
    return False

def expanduser(path):
    path = os.fspath(path)
    if isinstance(path, bytes):
        tilde = b'~'
    else:
        tilde = '~'
    if not path.startswith(tilde):
        return path
    i = 1
    n = len(path)
    while i < n and path[i] not in _get_bothseps(path):
        i += 1
    if 'HOME' in os.environ:
        userhome = os.environ['HOME']
    elif 'USERPROFILE' in os.environ:
        userhome = os.environ['USERPROFILE']
    else:
        if 'HOMEPATH' not in os.environ:
            return path
        try:
            drive = os.environ['HOMEDRIVE']
        except KeyError:
            drive = ''
        userhome = join(drive, os.environ['HOMEPATH'])
    if isinstance(path, bytes):
        userhome = os.fsencode(userhome)
    if i != 1:
        userhome = join(dirname(userhome), path[1:i])
    return userhome + path[i:]

def expandvars(path):
    path = os.fspath(path)
    if isinstance(path, bytes):
        if b'$' not in path and b'%' not in path:
            return path
        import string
        varchars = bytes(string.ascii_letters + string.digits + '_-', 'ascii')
        quote = b"'"
        percent = b'%'
        brace = b'{'
        rbrace = b'}'
        dollar = b'$'
        environ = getattr(os, 'environb', None)
    else:
        if '$' not in path and '%' not in path:
            return path
        import string
        varchars = string.ascii_letters + string.digits + '_-'
        quote = "'"
        percent = '%'
        brace = '{'
        rbrace = '}'
        dollar = '$'
        environ = os.environ
    res = path[:0]
    index = 0
    pathlen = len(path)
    while index < pathlen:
        c = path[index:index + 1]
        if c == quote:
            path = path[index + 1:]
            pathlen = len(path)
            try:
                index = path.index(c)
                res += c + path[:index + 1]
            except ValueError:
                res += c + path
                index = pathlen - 1
        elif c == percent:
            if path[index + 1:index + 2] == percent:
                res += c
                index += 1
            else:
                path = path[index + 1:]
                pathlen = len(path)
                try:
                    index = path.index(percent)
                except ValueError:
                    res += percent + path
                    index = pathlen - 1
                var = path[:index]
                try:
                    if environ is None:
                        value = os.fsencode(os.environ[os.fsdecode(var)])
                    else:
                        value = environ[var]
                except KeyError:
                    value = percent + var + percent
                res += value
        elif c == dollar:
            if path[index + 1:index + 2] == dollar:
                res += c
                index += 1
            elif path[index + 1:index + 2] == brace:
                path = path[index + 2:]
                pathlen = len(path)
                try:
                    index = path.index(rbrace)
                except ValueError:
                    res += dollar + brace + path
                    index = pathlen - 1
                var = path[:index]
                try:
                    if environ is None:
                        value = os.fsencode(os.environ[os.fsdecode(var)])
                    else:
                        value = environ[var]
                except KeyError:
                    value = dollar + brace + var + rbrace
                res += value
            else:
                var = path[:0]
                index += 1
                c = path[index:index + 1]
                while c and c in varchars:
                    var += c
                    index += 1
                    c = path[index:index + 1]
                try:
                    if environ is None:
                        value = os.fsencode(os.environ[os.fsdecode(var)])
                    else:
                        value = environ[var]
                except KeyError:
                    value = dollar + var
                res += value
                if c:
                    index -= 1
        else:
            res += c
        index += 1
    return res

def normpath(path):
    path = os.fspath(path)
    if isinstance(path, bytes):
        sep = b'\\'
        altsep = b'/'
        curdir = b'.'
        pardir = b'..'
        special_prefixes = (b'\\\\.\\', b'\\\\?\\')
    else:
        sep = '\\'
        altsep = '/'
        curdir = '.'
        pardir = '..'
        special_prefixes = ('\\\\.\\', '\\\\?\\')
    if path.startswith(special_prefixes):
        return path
    path = path.replace(altsep, sep)
    (prefix, path) = splitdrive(path)
    if path.startswith(sep):
        prefix += sep
        path = path.lstrip(sep)
    comps = path.split(sep)
    i = 0
    if i < len(comps):
        if comps[i] and comps[i] == curdir:
            del comps[i]
        elif comps[i] == pardir:
            if i > 0 and comps[i - 1] != pardir:
                del comps[i - 1:i + 1]
                i -= 1
            elif i == 0 and prefix.endswith(sep):
                del comps[i]
            else:
                i += 1
        else:
            i += 1
    if prefix or not comps:
        comps.append(curdir)
    return prefix + sep.join(comps)
try:
    from nt import _getfullpathname
except ImportError:

    def abspath(path):
        path = os.fspath(path)
        if not isabs(path):
            if isinstance(path, bytes):
                cwd = os.getcwdb()
            else:
                cwd = os.getcwd()
            path = join(cwd, path)
        return normpath(path)

def abspath(path):
    if path:
        path = os.fspath(path)
        try:
            path = _getfullpathname(path)
        except OSError:
            pass
    elif isinstance(path, bytes):
        path = os.getcwdb()
    else:
        path = os.getcwd()
    return normpath(path)
realpath = abspathsupports_unicode_filenames = hasattr(sys, 'getwindowsversion') and sys.getwindowsversion()[3] >= 2
def relpath(path, start=None):
    path = os.fspath(path)
    if isinstance(path, bytes):
        sep = b'\\'
        curdir = b'.'
        pardir = b'..'
    else:
        sep = '\\'
        curdir = '.'
        pardir = '..'
    if start is None:
        start = curdir
    if not path:
        raise ValueError('no path specified')
    start = os.fspath(start)
    try:
        start_abs = abspath(normpath(start))
        path_abs = abspath(normpath(path))
        (start_drive, start_rest) = splitdrive(start_abs)
        (path_drive, path_rest) = splitdrive(path_abs)
        if normcase(start_drive) != normcase(path_drive):
            raise ValueError('path is on mount %r, start on mount %r' % (path_drive, start_drive))
        start_list = [x for x in start_rest.split(sep) if x]
        path_list = [x for x in path_rest.split(sep) if x]
        i = 0
        for (e1, e2) in zip(start_list, path_list):
            if normcase(e1) != normcase(e2):
                break
            i += 1
        rel_list = [pardir]*(len(start_list) - i) + path_list[i:]
        if not rel_list:
            return curdir
        return join(*rel_list)
    except (TypeError, ValueError, AttributeError, BytesWarning, DeprecationWarning):
        genericpath._check_arg_types('relpath', path, start)
        raise

def commonpath(paths):
    if not paths:
        raise ValueError('commonpath() arg is an empty sequence')
    paths = tuple(map(os.fspath, paths))
    if isinstance(paths[0], bytes):
        sep = b'\\'
        altsep = b'/'
        curdir = b'.'
    else:
        sep = '\\'
        altsep = '/'
        curdir = '.'
    try:
        drivesplits = [splitdrive(p.replace(altsep, sep).lower()) for p in paths]
        split_paths = [p.split(sep) for (d, p) in drivesplits]
        try:
            (isabs,) = set(p[:1] == sep for (d, p) in drivesplits)
        except ValueError:
            raise ValueError("Can't mix absolute and relative paths") from None
        if len(set(d for (d, p) in drivesplits)) != 1:
            raise ValueError("Paths don't have the same drive")
        (drive, path) = splitdrive(paths[0].replace(altsep, sep))
        common = path.split(sep)
        common = [c for c in common if c and c != curdir]
        split_paths = [[c for c in s if c and c != curdir] for s in split_paths]
        s1 = min(split_paths)
        s2 = max(split_paths)
        for (i, c) in enumerate(s1):
            if c != s2[i]:
                common = common[:i]
                break
        common = common[:len(s1)]
        prefix = drive + sep if isabs else drive
        return prefix + sep.join(common)
    except (TypeError, AttributeError):
        genericpath._check_arg_types(('commonpath',), paths)
        raise
try:
    if sys.getwindowsversion()[:2] >= (6, 0):
        from nt import _getfinalpathname
    else:
        raise ImportError
except (AttributeError, ImportError):

    def _getfinalpathname(f):
        return normcase(abspath(f))
try:
    from nt import _isdir as isdir
except ImportError:
    pass