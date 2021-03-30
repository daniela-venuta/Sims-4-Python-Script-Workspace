from _imp import lock_held, acquire_lock, release_lock, get_frozen_object, is_frozen_package, init_frozen, is_builtin, is_frozen, _fix_co_filenametry:
    from _imp import create_dynamic
except ImportError:
    create_dynamic = Nonefrom importlib._bootstrap import _ERR_MSG, _exec, _load, _builtin_from_namefrom importlib._bootstrap_external import SourcelessFileLoaderfrom importlib import machineryfrom importlib import utilimport importlibimport osimport sysimport tokenizeimport typesimport warningswarnings.warn("the imp module is deprecated in favour of importlib; see the module's documentation for alternative uses", DeprecationWarning, stacklevel=2)SEARCH_ERROR = 0PY_SOURCE = 1PY_COMPILED = 2C_EXTENSION = 3PY_RESOURCE = 4PKG_DIRECTORY = 5C_BUILTIN = 6PY_FROZEN = 7PY_CODERESOURCE = 8IMP_HOOK = 9
def new_module(name):
    return types.ModuleType(name)

def get_magic():
    return util.MAGIC_NUMBER

def get_tag():
    return sys.implementation.cache_tag

def cache_from_source(path, debug_override=None):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return util.cache_from_source(path, debug_override)

def source_from_cache(path):
    return util.source_from_cache(path)

def get_suffixes():
    extensions = [(s, 'rb', C_EXTENSION) for s in machinery.EXTENSION_SUFFIXES]
    source = [(s, 'r', PY_SOURCE) for s in machinery.SOURCE_SUFFIXES]
    bytecode = [(s, 'rb', PY_COMPILED) for s in machinery.BYTECODE_SUFFIXES]
    return extensions + source + bytecode

class NullImporter:

    def __init__(self, path):
        if path == '':
            raise ImportError('empty pathname', path='')
        elif os.path.isdir(path):
            raise ImportError('existing directory', path=path)

    def find_module(self, fullname):
        pass

class _HackedGetData:

    def __init__(self, fullname, path, file=None):
        super().__init__(fullname, path)
        self.file = file

    def get_data(self, path):
        if self.file and path == self.path:
            if not self.file.closed:
                file = self.file
            else:
                self.file = file = open(self.path, 'r')
            with file:
                return file.read()
        else:
            return super().get_data(path)

class _LoadSourceCompatibility(_HackedGetData, machinery.SourceFileLoader):
    pass

def load_source(name, pathname, file=None):
    loader = _LoadSourceCompatibility(name, pathname, file)
    spec = util.spec_from_file_location(name, pathname, loader=loader)
    if name in sys.modules:
        module = _exec(spec, sys.modules[name])
    else:
        module = _load(spec)
    module.__loader__ = machinery.SourceFileLoader(name, pathname)
    module.__spec__.loader = module.__loader__
    return module

class _LoadCompiledCompatibility(_HackedGetData, SourcelessFileLoader):
    pass

def load_compiled(name, pathname, file=None):
    loader = _LoadCompiledCompatibility(name, pathname, file)
    spec = util.spec_from_file_location(name, pathname, loader=loader)
    if name in sys.modules:
        module = _exec(spec, sys.modules[name])
    else:
        module = _load(spec)
    module.__loader__ = SourcelessFileLoader(name, pathname)
    module.__spec__.loader = module.__loader__
    return module

def load_package(name, path):
    if os.path.isdir(path):
        extensions = machinery.SOURCE_SUFFIXES[:] + machinery.BYTECODE_SUFFIXES[:]
        for extension in extensions:
            init_path = os.path.join(path, '__init__' + extension)
            if os.path.exists(init_path):
                path = init_path
                break
        raise ValueError('{!r} is not a package'.format(path))
    spec = util.spec_from_file_location(name, path, submodule_search_locations=[])
    if name in sys.modules:
        return _exec(spec, sys.modules[name])
    else:
        return _load(spec)

def load_module(name, file, filename, details):
    (suffix, mode, type_) = details
    if mode and mode.startswith(('r', 'U')) and '+' in mode:
        raise ValueError('invalid file open mode {!r}'.format(mode))
    elif file is None and type_ in {PY_SOURCE, PY_COMPILED}:
        msg = 'file object required for import (type code {})'.format(type_)
        raise ValueError(msg)
    else:
        if type_ == PY_SOURCE:
            return load_source(name, filename, file)
        if type_ == PY_COMPILED:
            return load_compiled(name, filename, file)
        if type_ == C_EXTENSION and load_dynamic is not None:
            if file is None:
                with open(filename, 'rb') as opened_file:
                    return load_dynamic(name, filename, opened_file)
            else:
                return load_dynamic(name, filename, file)
        else:
            if type_ == PKG_DIRECTORY:
                return load_package(name, filename)
            if type_ == C_BUILTIN:
                return init_builtin(name)
            if type_ == PY_FROZEN:
                return init_frozen(name)
            msg = "Don't know how to import {} (type code {})".format(name, type_)
            raise ImportError(msg, name=name)

def find_module(name, path=None):
    if not isinstance(name, str):
        raise TypeError("'name' must be a str, not {}".format(type(name)))
    elif not isinstance(path, (type(None), list)):
        raise RuntimeError("'path' must be None or a list, not {}".format(type(path)))
    if path is None:
        if is_builtin(name):
            return (None, None, ('', '', C_BUILTIN))
        if is_frozen(name):
            return (None, None, ('', '', PY_FROZEN))
        path = sys.path
    for entry in path:
        package_directory = os.path.join(entry, name)
        for suffix in ['.py', machinery.BYTECODE_SUFFIXES[0]]:
            package_file_name = '__init__' + suffix
            file_path = os.path.join(package_directory, package_file_name)
            if os.path.isfile(file_path):
                return (None, package_directory, ('', '', PKG_DIRECTORY))
        for (suffix, mode, type_) in get_suffixes():
            file_name = name + suffix
            file_path = os.path.join(entry, file_name)
            if os.path.isfile(file_path):
                break
        break
    raise ImportError(_ERR_MSG.format(name), name=name)
    encoding = None
    if 'b' not in mode:
        with open(file_path, 'rb') as file:
            encoding = tokenize.detect_encoding(file.readline)[0]
    file = open(file_path, mode, encoding=encoding)
    return (file, file_path, (suffix, mode, type_))

def reload(module):
    return importlib.reload(module)

def init_builtin(name):
    try:
        return _builtin_from_name(name)
    except ImportError:
        return
if create_dynamic:

    def load_dynamic(name, path, file=None):
        import importlib.machinery
        loader = importlib.machinery.ExtensionFileLoader(name, path)
        spec = importlib.machinery.ModuleSpec(name=name, loader=loader, origin=path)
        return _load(spec)

else:
    load_dynamic = None