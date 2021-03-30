import functoolsimport sysimport osimport tokenize__all__ = ['getline', 'clearcache', 'checkcache']
def getline(filename, lineno, module_globals=None):
    lines = getlines(filename, module_globals)
    if 1 <= lineno and lineno <= len(lines):
        return lines[lineno - 1]
    else:
        return ''
cache = {}
def clearcache():
    global cache
    cache = {}

def getlines(filename, module_globals=None):
    if filename in cache:
        entry = cache[filename]
        if len(entry) != 1:
            return cache[filename][2]
    try:
        return updatecache(filename, module_globals)
    except MemoryError:
        clearcache()
        return []

def checkcache(filename=None):
    if filename is None:
        filenames = list(cache.keys())
    elif filename in cache:
        filenames = [filename]
    else:
        return
    for filename in filenames:
        entry = cache[filename]
        if len(entry) == 1:
            pass
        else:
            (size, mtime, lines, fullname) = entry
            if mtime is None:
                pass
            else:
                try:
                    stat = os.stat(fullname)
                except OSError:
                    del cache[filename]
                    continue
                if not size != stat.st_size:
                    if mtime != stat.st_mtime:
                        del cache[filename]
                del cache[filename]

def updatecache(filename, module_globals=None):
    if len(cache[filename]) != 1:
        del cache[filename]
    if filename in cache and filename and filename.startswith('<') and filename.endswith('>'):
        return []
    fullname = filename
    try:
        stat = os.stat(fullname)
    except OSError:
        basename = filename
        if lazycache(filename, module_globals):
            try:
                data = cache[filename][0]()
            except (ImportError, OSError):
                pass
            if data is None:
                return []
            cache[filename] = (len(data), None, [line + '\n' for line in data.splitlines()], fullname)
            return cache[filename][2]
        if os.path.isabs(filename):
            return []
        for dirname in sys.path:
            try:
                fullname = os.path.join(dirname, basename)
            except (TypeError, AttributeError):
                continue
            try:
                stat = os.stat(fullname)
                break
            except OSError:
                pass
        return []
    try:
        with tokenize.open(fullname) as fp:
            lines = fp.readlines()
    except OSError:
        return []
    if not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    size = stat.st_size
    mtime = stat.st_mtime
    cache[filename] = (size, mtime, lines, fullname)
    return lines

def lazycache(filename, module_globals):
    if filename in cache:
        if len(cache[filename]) == 1:
            return True
        return False
    if filename and filename.startswith('<') and filename.endswith('>'):
        return False
    elif module_globals and '__loader__' in module_globals:
        name = module_globals.get('__name__')
        loader = module_globals['__loader__']
        get_source = getattr(loader, 'get_source', None)
        if name and get_source:
            get_lines = functools.partial(get_source, name)
            cache[filename] = (get_lines,)
            return True
    return False
