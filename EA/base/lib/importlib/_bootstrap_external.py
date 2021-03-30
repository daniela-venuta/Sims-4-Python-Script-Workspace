_CASE_INSENSITIVE_PLATFORMS_STR_KEY = ('win',)_CASE_INSENSITIVE_PLATFORMS_BYTES_KEY = ('cygwin', 'darwin')_CASE_INSENSITIVE_PLATFORMS = _CASE_INSENSITIVE_PLATFORMS_BYTES_KEY + _CASE_INSENSITIVE_PLATFORMS_STR_KEY
def _make_relax_case():
    if sys.platform.startswith(_CASE_INSENSITIVE_PLATFORMS):
        if sys.platform.startswith(_CASE_INSENSITIVE_PLATFORMS_STR_KEY):
            key = 'PYTHONCASEOK'
        else:
            key = b'PYTHONCASEOK'

        def _relax_case():
            return key in _os.environ

    else:

        def _relax_case():
            return False

    return _relax_case

def _w_long(x):
    return (int(x) & 4294967295).to_bytes(4, 'little')

def _r_long(int_bytes):
    return int.from_bytes(int_bytes, 'little')

def _path_join(*path_parts):
    return path_sep.join([part.rstrip(path_separators) for part in path_parts if part])

def _path_split(path):
    if len(path_separators) == 1:
        (front, _, tail) = path.rpartition(path_sep)
        return (front, tail)
    for x in reversed(path):
        if x in path_separators:
            (front, tail) = path.rsplit(x, maxsplit=1)
            return (front, tail)
    return ('', path)

def _path_stat(path):
    return _os.stat(path)

def _path_is_mode_type(path, mode):
    try:
        stat_info = _path_stat(path)
    except OSError:
        return False
    return stat_info.st_mode & 61440 == mode

def _path_isfile(path):
    return _path_is_mode_type(path, 32768)

def _path_isdir(path):
    if not path:
        path = _os.getcwd()
    return _path_is_mode_type(path, 16384)

def _write_atomic(path, data, mode=438):
    path_tmp = '{}.{}'.format(path, id(path))
    fd = _os.open(path_tmp, _os.O_EXCL | _os.O_CREAT | _os.O_WRONLY, mode & 438)
    try:
        with _io.FileIO(fd, 'wb') as file:
            file.write(data)
        _os.replace(path_tmp, path)
    except OSError:
        try:
            _os.unlink(path_tmp)
        except OSError:
            pass
        raise
_code_type = type(_write_atomic.__code__)MAGIC_NUMBER = 3394.to_bytes(2, 'little') + b'\r\n'_RAW_MAGIC_NUMBER = int.from_bytes(MAGIC_NUMBER, 'little')_PYCACHE = '__pycache__'_OPT = 'opt-'SOURCE_SUFFIXES = ['.py']BYTECODE_SUFFIXES = ['.pyc']DEBUG_BYTECODE_SUFFIXES = OPTIMIZED_BYTECODE_SUFFIXES = BYTECODE_SUFFIXES
def cache_from_source(path, debug_override=None, *, optimization=None):
    if debug_override is not None:
        _warnings.warn("the debug_override parameter is deprecated; use 'optimization' instead", DeprecationWarning)
        if optimization is not None:
            message = 'debug_override or optimization must be set to None'
            raise TypeError(message)
        optimization = '' if debug_override else 1
    path = _os.fspath(path)
    (head, tail) = _path_split(path)
    (base, sep, rest) = tail.rpartition('.')
    tag = sys.implementation.cache_tag
    if tag is None:
        raise NotImplementedError('sys.implementation.cache_tag is None')
    almost_filename = ''.join([base if base else rest, sep, tag])
    if optimization is None:
        if sys.flags.optimize == 0:
            optimization = ''
        else:
            optimization = sys.flags.optimize
    optimization = str(optimization)
    if optimization != '':
        if not optimization.isalnum():
            raise ValueError('{!r} is not alphanumeric'.format(optimization))
        almost_filename = '{}.{}{}'.format(almost_filename, _OPT, optimization)
    return _path_join(head, _PYCACHE, almost_filename + BYTECODE_SUFFIXES[0])

def source_from_cache(path):
    if sys.implementation.cache_tag is None:
        raise NotImplementedError('sys.implementation.cache_tag is None')
    path = _os.fspath(path)
    (head, pycache_filename) = _path_split(path)
    (head, pycache) = _path_split(head)
    if pycache != _PYCACHE:
        raise ValueError('{} not bottom-level directory in {!r}'.format(_PYCACHE, path))
    dot_count = pycache_filename.count('.')
    if dot_count not in frozenset({2, 3}):
        raise ValueError('expected only 2 or 3 dots in {!r}'.format(pycache_filename))
    elif dot_count == 3:
        optimization = pycache_filename.rsplit('.', 2)[-2]
        if not optimization.startswith(_OPT):
            raise ValueError('optimization portion of filename does not start with {!r}'.format(_OPT))
        opt_level = optimization[len(_OPT):]
        if not opt_level.isalnum():
            raise ValueError('optimization level {!r} is not an alphanumeric value'.format(optimization))
    base_filename = pycache_filename.partition('.')[0]
    return _path_join(head, base_filename + SOURCE_SUFFIXES[0])

def _get_sourcefile(bytecode_path):
    if len(bytecode_path) == 0:
        return
    (rest, _, extension) = bytecode_path.rpartition('.')
    if rest and extension.lower()[-3:-1] != 'py':
        return bytecode_path
    else:
        try:
            source_path = source_from_cache(bytecode_path)
        except (NotImplementedError, ValueError):
            source_path = bytecode_path[:-1]
        if _path_isfile(source_path):
            return source_path
    return bytecode_path

def _get_cached(filename):
    if filename.endswith(tuple(SOURCE_SUFFIXES)):
        try:
            return cache_from_source(filename)
        except NotImplementedError:
            pass
    elif filename.endswith(tuple(BYTECODE_SUFFIXES)):
        return filename
    else:
        return

def _calc_mode(path):
    try:
        mode = _path_stat(path).st_mode
    except OSError:
        mode = 438
    mode |= 128
    return mode

def _check_name(method):

    def _check_name_wrapper(self, name=None, *args, **kwargs):
        if name is None:
            name = self.name
        elif self.name != name:
            raise ImportError('loader for %s cannot handle %s' % (self.name, name), name=name)
        return method(self, name, *args, **kwargs)

    try:
        _wrap = _bootstrap._wrap
    except NameError:

        def _wrap(new, old):
            for replace in ('__module__', '__name__', '__qualname__', '__doc__'):
                if hasattr(old, replace):
                    setattr(new, replace, getattr(old, replace))
            new.__dict__.update(old.__dict__)

    _wrap(_check_name_wrapper, method)
    return _check_name_wrapper

def _find_module_shim(self, fullname):
    (loader, portions) = self.find_loader(fullname)
    if loader is None and len(portions):
        msg = 'Not importing directory {}: missing __init__'
        _warnings.warn(msg.format(portions[0]), ImportWarning)
    return loader

def _classify_pyc(data, name, exc_details):
    magic = data[:4]
    if magic != MAGIC_NUMBER:
        message = f'bad magic number in {name}: {magic}'
        _bootstrap._verbose_message('{}', message)
        raise ImportError(message, **exc_details)
    if len(data) < 16:
        message = f'reached EOF while reading pyc header of {name}'
        _bootstrap._verbose_message('{}', message)
        raise EOFError(message)
    flags = _r_long(data[4:8])
    if flags & -4:
        message = f'invalid flags {flags} in {name}'
        raise ImportError(message, **exc_details)
    return flags

def _validate_timestamp_pyc(data, source_mtime, source_size, name, exc_details):
    if _r_long(data[8:12]) != source_mtime & 4294967295:
        message = f'bytecode is stale for {name}'
        _bootstrap._verbose_message('{}', message)
        raise ImportError(message, **exc_details)
    if source_size is not None and _r_long(data[12:16]) != source_size & 4294967295:
        raise ImportError(f'bytecode is stale for {name}', **exc_details)

def _validate_hash_pyc(data, source_hash, name, exc_details):
    if data[8:16] != source_hash:
        raise ImportError(f'hash in bytecode doesn't match hash of source {name}', **exc_details)

def _compile_bytecode(data, name=None, bytecode_path=None, source_path=None):
    code = marshal.loads(data)
    if isinstance(code, _code_type):
        _bootstrap._verbose_message('code object from {!r}', bytecode_path)
        if source_path is not None:
            _imp._fix_co_filename(code, source_path)
        return code
    raise ImportError('Non-code object in {!r}'.format(bytecode_path), name=name, path=bytecode_path)

def _code_to_timestamp_pyc(code, mtime=0, source_size=0):
    data = bytearray(MAGIC_NUMBER)
    data.extend(_w_long(0))
    data.extend(_w_long(mtime))
    data.extend(_w_long(source_size))
    data.extend(marshal.dumps(code))
    return data

def _code_to_hash_pyc(code, source_hash, checked=True):
    data = bytearray(MAGIC_NUMBER)
    flags = 1 | checked << 1
    data.extend(_w_long(flags))
    data.extend(source_hash)
    data.extend(marshal.dumps(code))
    return data

def decode_source(source_bytes):
    import tokenize
    source_bytes_readline = _io.BytesIO(source_bytes).readline
    encoding = tokenize.detect_encoding(source_bytes_readline)
    newline_decoder = _io.IncrementalNewlineDecoder(None, True)
    return newline_decoder.decode(source_bytes.decode(encoding[0]))
_POPULATE = object()
def spec_from_file_location(name, location=None, *, loader=None, submodule_search_locations=_POPULATE):
    if location is None:
        location = '<unknown>'
        if hasattr(loader, 'get_filename'):
            try:
                location = loader.get_filename(name)
            except ImportError:
                pass
    else:
        location = _os.fspath(location)
    spec = _bootstrap.ModuleSpec(name, loader, origin=location)
    spec._set_fileattr = True
    if loader is None:
        for (loader_class, suffixes) in _get_supported_file_loaders():
            if location.endswith(tuple(suffixes)):
                loader = loader_class(name, location)
                spec.loader = loader
                break
        return
    if submodule_search_locations is _POPULATE:
        if hasattr(loader, 'is_package'):
            try:
                is_package = loader.is_package(name)
            except ImportError:
                pass
            if is_package:
                spec.submodule_search_locations = []
    else:
        spec.submodule_search_locations = submodule_search_locations
    if spec.submodule_search_locations == [] and location:
        dirname = _path_split(location)[0]
        spec.submodule_search_locations.append(dirname)
    return spec

class _LoaderBasics:

    def is_package(self, fullname):
        filename = _path_split(self.get_filename(fullname))[1]
        filename_base = filename.rsplit('.', 1)[0]
        tail_name = fullname.rpartition('.')[2]
        return filename_base == '__init__' and tail_name != '__init__'

    def create_module(self, spec):
        pass

    def exec_module(self, module):
        code = self.get_code(module.__name__)
        if code is None:
            raise ImportError('cannot load module {!r} when get_code() returns None'.format(module.__name__))
        _bootstrap._call_with_frames_removed(exec, code, module.__dict__)

    def load_module(self, fullname):
        return _bootstrap._load_module_shim(self, fullname)

class SourceLoader(_LoaderBasics):

    def path_mtime(self, path):
        raise OSError

    def path_stats(self, path):
        return {'mtime': self.path_mtime(path)}

    def _cache_bytecode(self, source_path, cache_path, data):
        return self.set_data(cache_path, data)

    def set_data(self, path, data):
        pass

    def get_source(self, fullname):
        path = self.get_filename(fullname)
        try:
            source_bytes = self.get_data(path)
        except OSError as exc:
            raise ImportError('source not available through get_data()', name=fullname) from exc
        return decode_source(source_bytes)

    def source_to_code(self, data, path, *, _optimize=-1):
        return _bootstrap._call_with_frames_removed(compile, data, path, 'exec', dont_inherit=True, optimize=_optimize)

    def get_code(self, fullname):
        source_path = self.get_filename(fullname)
        source_mtime = None
        source_bytes = None
        source_hash = None
        hash_based = False
        check_source = True
        try:
            bytecode_path = cache_from_source(source_path)
        except NotImplementedError:
            bytecode_path = None
        try:
            st = self.path_stats(source_path)
        except OSError:
            pass
        source_mtime = int(st['mtime'])
        try:
            data = self.get_data(bytecode_path)
        except OSError:
            pass
        exc_details = {'name': fullname, 'path': bytecode_path}
        try:
            flags = _classify_pyc(data, fullname, exc_details)
            bytes_data = memoryview(data)[16:]
            hash_based = flags & 1 != 0
            if hash_based:
                check_source = flags & 2 != 0
                if _imp.check_hash_based_pycs != 'never' and (check_source or _imp.check_hash_based_pycs == 'always'):
                    source_bytes = self.get_data(source_path)
                    source_hash = _imp.source_hash(_RAW_MAGIC_NUMBER, source_bytes)
                    _validate_hash_pyc(data, source_hash, fullname, exc_details)
            else:
                _validate_timestamp_pyc(data, source_mtime, st['size'], fullname, exc_details)
        except (ImportError, EOFError):
            pass
        _bootstrap._verbose_message('{} matches {}', bytecode_path, source_path)
        return _compile_bytecode(bytes_data, name=fullname, bytecode_path=bytecode_path, source_path=source_path)
        if source_bytes is None:
            source_bytes = self.get_data(source_path)
        code_object = self.source_to_code(source_bytes, source_path)
        _bootstrap._verbose_message('code object from {}', source_path)
        if source_mtime is not None:
            if hash_based:
                if source_hash is None:
                    source_hash = _imp.source_hash(source_bytes)
                data = _code_to_hash_pyc(code_object, source_hash, check_source)
            else:
                data = _code_to_timestamp_pyc(code_object, source_mtime, len(source_bytes))
            try:
                self._cache_bytecode(source_path, bytecode_path, data)
                _bootstrap._verbose_message('wrote {!r}', bytecode_path)
            except NotImplementedError:
                pass
        return code_object

class FileLoader:

    def __init__(self, fullname, path):
        self.name = fullname
        self.path = path

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.name) ^ hash(self.path)

    @_check_name
    def load_module(self, fullname):
        return super(FileLoader, self).load_module(fullname)

    @_check_name
    def get_filename(self, fullname):
        return self.path

    def get_data(self, path):
        with _io.FileIO(path, 'r') as file:
            return file.read()

    @_check_name
    def get_resource_reader(self, module):
        if self.is_package(module):
            return self

    def open_resource(self, resource):
        path = _path_join(_path_split(self.path)[0], resource)
        return _io.FileIO(path, 'r')

    def resource_path(self, resource):
        if not self.is_resource(resource):
            raise FileNotFoundError
        path = _path_join(_path_split(self.path)[0], resource)
        return path

    def is_resource(self, name):
        if path_sep in name:
            return False
        path = _path_join(_path_split(self.path)[0], name)
        return _path_isfile(path)

    def contents(self):
        return iter(_os.listdir(_path_split(self.path)[0]))

class SourceFileLoader(FileLoader, SourceLoader):

    def path_stats(self, path):
        st = _path_stat(path)
        return {'mtime': st.st_mtime, 'size': st.st_size}

    def _cache_bytecode(self, source_path, bytecode_path, data):
        mode = _calc_mode(source_path)
        return self.set_data(bytecode_path, data, _mode=mode)

    def set_data(self, path, data, *, _mode=438):
        (parent, filename) = _path_split(path)
        path_parts = []
        while parent and not _path_isdir(parent):
            (parent, part) = _path_split(parent)
            path_parts.append(part)
        for part in reversed(path_parts):
            parent = _path_join(parent, part)
            try:
                _os.mkdir(parent)
            except FileExistsError:
                continue
            except OSError as exc:
                _bootstrap._verbose_message('could not create {!r}: {!r}', parent, exc)
                return
        try:
            _write_atomic(path, data, _mode)
            _bootstrap._verbose_message('created {!r}', path)
        except OSError as exc:
            _bootstrap._verbose_message('could not create {!r}: {!r}', path, exc)

class SourcelessFileLoader(FileLoader, _LoaderBasics):

    def get_code(self, fullname):
        path = self.get_filename(fullname)
        data = self.get_data(path)
        exc_details = {'name': fullname, 'path': path}
        _classify_pyc(data, fullname, exc_details)
        return _compile_bytecode(memoryview(data)[16:], name=fullname, bytecode_path=path)

    def get_source(self, fullname):
        pass
EXTENSION_SUFFIXES = []
class ExtensionFileLoader(FileLoader, _LoaderBasics):

    def __init__(self, name, path):
        self.name = name
        self.path = path

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.name) ^ hash(self.path)

    def create_module(self, spec):
        module = _bootstrap._call_with_frames_removed(_imp.create_dynamic, spec)
        _bootstrap._verbose_message('extension module {!r} loaded from {!r}', spec.name, self.path)
        return module

    def exec_module(self, module):
        _bootstrap._call_with_frames_removed(_imp.exec_dynamic, module)
        _bootstrap._verbose_message('extension module {!r} executed from {!r}', self.name, self.path)

    def is_package(self, fullname):
        file_name = _path_split(self.path)[1]
        return any(file_name == '__init__' + suffix for suffix in EXTENSION_SUFFIXES)

    def get_code(self, fullname):
        pass

    def get_source(self, fullname):
        pass

    @_check_name
    def get_filename(self, fullname):
        return self.path

class _NamespacePath:

    def __init__(self, name, path, path_finder):
        self._name = name
        self._path = path
        self._last_parent_path = tuple(self._get_parent_path())
        self._path_finder = path_finder

    def _find_parent_path_names(self):
        (parent, dot, me) = self._name.rpartition('.')
        if dot == '':
            return ('sys', 'path')
        return (parent, '__path__')

    def _get_parent_path(self):
        (parent_module_name, path_attr_name) = self._find_parent_path_names()
        return getattr(sys.modules[parent_module_name], path_attr_name)

    def _recalculate(self):
        parent_path = tuple(self._get_parent_path())
        if parent_path != self._last_parent_path:
            spec = self._path_finder(self._name, parent_path)
            if spec.submodule_search_locations:
                self._path = spec.submodule_search_locations
            self._last_parent_path = parent_path
        return self._path

    def __iter__(self):
        return iter(self._recalculate())

    def __setitem__(self, index, path):
        self._path[index] = path

    def __len__(self):
        return len(self._recalculate())

    def __repr__(self):
        return '_NamespacePath({!r})'.format(self._path)

    def __contains__(self, item):
        return item in self._recalculate()

    def append(self, item):
        self._path.append(item)

class _NamespaceLoader:

    def __init__(self, name, path, path_finder):
        self._path = _NamespacePath(name, path, path_finder)

    @classmethod
    def module_repr(cls, module):
        return '<module {!r} (namespace)>'.format(module.__name__)

    def is_package(self, fullname):
        return True

    def get_source(self, fullname):
        return ''

    def get_code(self, fullname):
        return compile('', '<string>', 'exec', dont_inherit=True)

    def create_module(self, spec):
        pass

    def exec_module(self, module):
        pass

    def load_module(self, fullname):
        _bootstrap._verbose_message('namespace module loaded with path {!r}', self._path)
        return _bootstrap._load_module_shim(self, fullname)

class PathFinder:

    @classmethod
    def invalidate_caches(cls):
        for (name, finder) in list(sys.path_importer_cache.items()):
            if finder is None:
                del sys.path_importer_cache[name]
            elif hasattr(finder, 'invalidate_caches'):
                finder.invalidate_caches()

    @classmethod
    def _path_hooks(cls, path):
        if sys.path_hooks is not None and not sys.path_hooks:
            _warnings.warn('sys.path_hooks is empty', ImportWarning)
        for hook in sys.path_hooks:
            try:
                return hook(path)
            except ImportError:
                continue
        return

    @classmethod
    def _path_importer_cache(cls, path):
        if path == '':
            try:
                path = _os.getcwd()
            except FileNotFoundError:
                return
        try:
            finder = sys.path_importer_cache[path]
        except KeyError:
            finder = cls._path_hooks(path)
            sys.path_importer_cache[path] = finder
        return finder

    @classmethod
    def _legacy_get_spec(cls, fullname, finder):
        if hasattr(finder, 'find_loader'):
            (loader, portions) = finder.find_loader(fullname)
        else:
            loader = finder.find_module(fullname)
            portions = []
        if loader is not None:
            return _bootstrap.spec_from_loader(fullname, loader)
        spec = _bootstrap.ModuleSpec(fullname, None)
        spec.submodule_search_locations = portions
        return spec

    @classmethod
    def _get_spec(cls, fullname, path, target=None):
        namespace_path = []
        for entry in path:
            if not isinstance(entry, (str, bytes)):
                pass
            else:
                finder = cls._path_importer_cache(entry)
                if finder is not None:
                    if hasattr(finder, 'find_spec'):
                        spec = finder.find_spec(fullname, target)
                    else:
                        spec = cls._legacy_get_spec(fullname, finder)
                    if spec is None:
                        pass
                    elif spec.loader is not None:
                        return spec
                    else:
                        portions = spec.submodule_search_locations
                        if portions is None:
                            raise ImportError('spec missing loader')
                        namespace_path.extend(portions)
                        spec = _bootstrap.ModuleSpec(fullname, None)
                        spec.submodule_search_locations = namespace_path
                        return spec
        spec = _bootstrap.ModuleSpec(fullname, None)
        spec.submodule_search_locations = namespace_path
        return spec

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if path is None:
            path = sys.path
        spec = cls._get_spec(fullname, path, target)
        if spec is None:
            return
        elif spec.loader is None:
            namespace_path = spec.submodule_search_locations
            if namespace_path:
                spec.origin = None
                spec.submodule_search_locations = _NamespacePath(fullname, namespace_path, cls._get_spec)
                return spec
            return
        else:
            return spec
        return

    @classmethod
    def find_module(cls, fullname, path=None):
        spec = cls.find_spec(fullname, path)
        if spec is None:
            return
        return spec.loader

class FileFinder:

    def __init__(self, path, *loader_details):
        loaders = []
        for (loader, suffixes) in loader_details:
            loaders.extend((suffix, loader) for suffix in suffixes)
        self._loaders = loaders
        self.path = path or '.'
        self._path_mtime = -1
        self._path_cache = set()
        self._relaxed_path_cache = set()

    def invalidate_caches(self):
        self._path_mtime = -1

    find_module = _find_module_shim

    def find_loader(self, fullname):
        spec = self.find_spec(fullname)
        if spec is None:
            return (None, [])
        return (spec.loader, spec.submodule_search_locations or [])

    def _get_spec(self, loader_class, fullname, path, smsl, target):
        loader = loader_class(fullname, path)
        return spec_from_file_location(fullname, path, loader=loader, submodule_search_locations=smsl)

    def find_spec(self, fullname, target=None):
        is_namespace = False
        tail_module = fullname.rpartition('.')[2]
        try:
            mtime = _path_stat(self.path or _os.getcwd()).st_mtime
        except OSError:
            mtime = -1
        if mtime != self._path_mtime:
            self._fill_cache()
            self._path_mtime = mtime
        if _relax_case():
            cache = self._relaxed_path_cache
            cache_module = tail_module.lower()
        else:
            cache = self._path_cache
            cache_module = tail_module
        if cache_module in cache:
            base_path = _path_join(self.path, tail_module)
            for (suffix, loader_class) in self._loaders:
                init_filename = '__init__' + suffix
                full_path = _path_join(base_path, init_filename)
                if _path_isfile(full_path):
                    return self._get_spec(loader_class, fullname, full_path, [base_path], target)
            is_namespace = _path_isdir(base_path)
        for (suffix, loader_class) in self._loaders:
            full_path = _path_join(self.path, tail_module + suffix)
            _bootstrap._verbose_message('trying {}', full_path, verbosity=2)
            if cache_module + suffix in cache and _path_isfile(full_path):
                return self._get_spec(loader_class, fullname, full_path, None, target)
        if is_namespace:
            _bootstrap._verbose_message('possible namespace for {}', base_path)
            spec = _bootstrap.ModuleSpec(fullname, None)
            spec.submodule_search_locations = [base_path]
            return spec

    def _fill_cache(self):
        path = self.path
        try:
            contents = _os.listdir(path or _os.getcwd())
        except (FileNotFoundError, PermissionError, NotADirectoryError):
            contents = []
        if not sys.platform.startswith('win'):
            self._path_cache = set(contents)
        else:
            lower_suffix_contents = set()
            for item in contents:
                (name, dot, suffix) = item.partition('.')
                if dot:
                    new_name = '{}.{}'.format(name, suffix.lower())
                else:
                    new_name = name
                lower_suffix_contents.add(new_name)
            self._path_cache = lower_suffix_contents
        if sys.platform.startswith(_CASE_INSENSITIVE_PLATFORMS):
            self._relaxed_path_cache = {fn.lower() for fn in contents}

    @classmethod
    def path_hook(cls, *loader_details):

        def path_hook_for_FileFinder(path):
            if not _path_isdir(path):
                raise ImportError('only directories are supported', path=path)
            return cls(path, loader_details)

        return path_hook_for_FileFinder

    def __repr__(self):
        return 'FileFinder({!r})'.format(self.path)

def _fix_up_module(ns, name, pathname, cpathname=None):
    loader = ns.get('__loader__')
    spec = ns.get('__spec__')
    if not loader:
        if spec:
            loader = spec.loader
        elif pathname == cpathname:
            loader = SourcelessFileLoader(name, pathname)
        else:
            loader = SourceFileLoader(name, pathname)
    if not spec:
        spec = spec_from_file_location(name, pathname, loader=loader)
    try:
        ns['__spec__'] = spec
        ns['__loader__'] = loader
        ns['__file__'] = pathname
        ns['__cached__'] = cpathname
    except Exception:
        pass

def _get_supported_file_loaders():
    extensions = (ExtensionFileLoader, _imp.extension_suffixes())
    source = (SourceFileLoader, SOURCE_SUFFIXES)
    bytecode = (SourcelessFileLoader, BYTECODE_SUFFIXES)
    return [extensions, source, bytecode]

def _setup(_bootstrap_module):
    global _bootstrap, sys, _imp
    _bootstrap = _bootstrap_module
    sys = _bootstrap.sys
    _imp = _bootstrap._imp
    self_module = sys.modules[__name__]
    for builtin_name in ('_io', '_warnings', 'builtins', 'marshal'):
        if builtin_name not in sys.modules:
            builtin_module = _bootstrap._builtin_from_name(builtin_name)
        else:
            builtin_module = sys.modules[builtin_name]
        setattr(self_module, builtin_name, builtin_module)
    os_details = (('posix', ['/']), ('nt', ['\\', '/']))
    for (builtin_os, path_separators) in os_details:
        path_sep = path_separators[0]
        if builtin_os in sys.modules:
            os_module = sys.modules[builtin_os]
            break
        else:
            try:
                os_module = _bootstrap._builtin_from_name(builtin_os)
                break
            except ImportError:
                continue
    raise ImportError('importlib requires posix or nt')
    setattr(self_module, '_os', os_module)
    setattr(self_module, 'path_sep', path_sep)
    setattr(self_module, 'path_separators', ''.join(path_separators))
    thread_module = _bootstrap._builtin_from_name('_thread')
    setattr(self_module, '_thread', thread_module)
    weakref_module = _bootstrap._builtin_from_name('_weakref')
    setattr(self_module, '_weakref', weakref_module)
    setattr(self_module, '_relax_case', _make_relax_case())
    EXTENSION_SUFFIXES.extend(_imp.extension_suffixes())
    if builtin_os == 'nt':
        SOURCE_SUFFIXES.append('.pyw')

def _install(_bootstrap_module):
    _setup(_bootstrap_module)
    supported_loaders = _get_supported_file_loaders()
    sys.path_hooks.extend([FileFinder.path_hook(*supported_loaders)])
    sys.meta_path.append(PathFinder)
