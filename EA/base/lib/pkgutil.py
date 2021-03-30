from collections import namedtuplefrom functools import singledispatch as simplegenericimport importlibimport importlib.utilimport importlib.machineryimport osimport os.pathimport sysfrom types import ModuleTypeimport warnings__all__ = ['get_importer', 'iter_importers', 'get_loader', 'find_loader', 'walk_packages', 'iter_modules', 'get_data', 'ImpImporter', 'ImpLoader', 'read_code', 'extend_path', 'ModuleInfo']ModuleInfo = namedtuple('ModuleInfo', 'module_finder name ispkg')ModuleInfo.__doc__ = 'A namedtuple with minimal info about a module.'
def _get_spec(finder, name):
    try:
        find_spec = finder.find_spec
    except AttributeError:
        loader = finder.find_module(name)
        if loader is None:
            return
        return importlib.util.spec_from_loader(name, loader)
    return find_spec(name)

def read_code(stream):
    import marshal
    magic = stream.read(4)
    if magic != importlib.util.MAGIC_NUMBER:
        return
    stream.read(12)
    return marshal.load(stream)

def walk_packages(path=None, prefix='', onerror=None):

    def seen(p, m={}):
        if p in m:
            return True
        m[p] = True

    for info in iter_modules(path, prefix):
        yield info
        if info.ispkg:
            try:
                __import__(info.name)
            except ImportError:
                if onerror is not None:
                    onerror(info.name)
            except Exception:
                if onerror is not None:
                    onerror(info.name)
                else:
                    raise
            path = getattr(sys.modules[info.name], '__path__', None) or []
            path = [p for p in path if not seen(p)]
            yield from walk_packages(path, info.name + '.', onerror)

def iter_modules(path=None, prefix=''):
    if path is None:
        importers = iter_importers()
    elif isinstance(path, str):
        raise ValueError('path must be None or list of paths to look for modules in')
    else:
        importers = map(get_importer, path)
    yielded = {}
    for i in importers:
        for (name, ispkg) in iter_importer_modules(i, prefix):
            if name not in yielded:
                yielded[name] = 1
                yield ModuleInfo(i, name, ispkg)

@simplegeneric
def iter_importer_modules(importer, prefix=''):
    if not hasattr(importer, 'iter_modules'):
        return []
    return importer.iter_modules(prefix)

def _iter_file_finder_modules(importer, prefix=''):
    if importer.path is None or not os.path.isdir(importer.path):
        return
    yielded = {}
    import inspect
    try:
        filenames = os.listdir(importer.path)
    except OSError:
        filenames = []
    filenames.sort()
    for fn in filenames:
        modname = inspect.getmodulename(fn)
        if not modname == '__init__':
            if modname in yielded:
                pass
            else:
                path = os.path.join(importer.path, fn)
                ispkg = False
                if modname or not os.path.isdir(path) or '.' not in fn:
                    modname = fn
                    try:
                        dircontents = os.listdir(path)
                    except OSError:
                        dircontents = []
                    for fn in dircontents:
                        subname = inspect.getmodulename(fn)
                        if subname == '__init__':
                            ispkg = True
                            break
                elif modname and '.' not in modname:
                    yielded[modname] = 1
                    yield (prefix + modname, ispkg)
iter_importer_modules.register(importlib.machinery.FileFinder, _iter_file_finder_modules)
def _import_imp():
    global imp
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        imp = importlib.import_module('imp')

class ImpImporter:

    def __init__(self, path=None):
        warnings.warn("This emulation is deprecated, use 'importlib' instead", DeprecationWarning)
        _import_imp()
        self.path = path

    def find_module(self, fullname, path=None):
        subname = fullname.split('.')[-1]
        if subname != fullname and self.path is None:
            return
        if self.path is None:
            path = None
        else:
            path = [os.path.realpath(self.path)]
        try:
            (file, filename, etc) = imp.find_module(subname, path)
        except ImportError:
            return
        return ImpLoader(fullname, file, filename, etc)

    def iter_modules(self, prefix=''):
        if self.path is None or not os.path.isdir(self.path):
            return
        yielded = {}
        import inspect
        try:
            filenames = os.listdir(self.path)
        except OSError:
            filenames = []
        filenames.sort()
        for fn in filenames:
            modname = inspect.getmodulename(fn)
            if not modname == '__init__':
                if modname in yielded:
                    pass
                else:
                    path = os.path.join(self.path, fn)
                    ispkg = False
                    if modname or not os.path.isdir(path) or '.' not in fn:
                        modname = fn
                        try:
                            dircontents = os.listdir(path)
                        except OSError:
                            dircontents = []
                        for fn in dircontents:
                            subname = inspect.getmodulename(fn)
                            if subname == '__init__':
                                ispkg = True
                                break
                    elif modname and '.' not in modname:
                        yielded[modname] = 1
                        yield (prefix + modname, ispkg)

class ImpLoader:
    code = source = None

    def __init__(self, fullname, file, filename, etc):
        warnings.warn("This emulation is deprecated, use 'importlib' instead", DeprecationWarning)
        _import_imp()
        self.file = file
        self.filename = filename
        self.fullname = fullname
        self.etc = etc

    def load_module(self, fullname):
        self._reopen()
        try:
            mod = imp.load_module(fullname, self.file, self.filename, self.etc)
        finally:
            if self.file:
                self.file.close()
        return mod

    def get_data(self, pathname):
        with open(pathname, 'rb') as file:
            return file.read()

    def _reopen(self):
        if self.file.closed:
            mod_type = self.etc[2]
            if mod_type == imp.PY_SOURCE:
                self.file = open(self.filename, 'r')
            elif mod_type in (imp.PY_COMPILED, imp.C_EXTENSION):
                self.file = open(self.filename, 'rb')

    def _fix_name(self, fullname):
        if fullname is None:
            fullname = self.fullname
        elif fullname != self.fullname:
            raise ImportError('Loader for module %s cannot handle module %s' % (self.fullname, fullname))
        return fullname

    def is_package(self, fullname):
        fullname = self._fix_name(fullname)
        return self.etc[2] == imp.PKG_DIRECTORY

    def get_code(self, fullname=None):
        fullname = self._fix_name(fullname)
        if self.code is None:
            mod_type = self.etc[2]
            if mod_type == imp.PY_SOURCE:
                source = self.get_source(fullname)
                self.code = compile(source, self.filename, 'exec')
            elif mod_type == imp.PY_COMPILED:
                self._reopen()
                try:
                    self.code = read_code(self.file)
                finally:
                    self.file.close()
            elif mod_type == imp.PKG_DIRECTORY:
                self.code = self._get_delegate().get_code()
        return self.code

    def get_source(self, fullname=None):
        fullname = self._fix_name(fullname)
        if self.source is None:
            mod_type = self.etc[2]
            if mod_type == imp.PY_SOURCE:
                self._reopen()
                try:
                    self.source = self.file.read()
                finally:
                    self.file.close()
            elif mod_type == imp.PY_COMPILED:
                if os.path.exists(self.filename[:-1]):
                    with open(self.filename[:-1], 'r') as f:
                        self.source = f.read()
            elif mod_type == imp.PKG_DIRECTORY:
                self.source = self._get_delegate().get_source()
        return self.source

    def _get_delegate(self):
        finder = ImpImporter(self.filename)
        spec = _get_spec(finder, '__init__')
        return spec.loader

    def get_filename(self, fullname=None):
        fullname = self._fix_name(fullname)
        mod_type = self.etc[2]
        if mod_type == imp.PKG_DIRECTORY:
            return self._get_delegate().get_filename()
        elif mod_type in (imp.PY_SOURCE, imp.PY_COMPILED, imp.C_EXTENSION):
            return self.filename
try:
    import zipimport
    from zipimport import zipimporter

    def iter_zipimport_modules(importer, prefix=''):
        dirlist = sorted(zipimport._zip_directory_cache[importer.archive])
        _prefix = importer.prefix
        plen = len(_prefix)
        yielded = {}
        import inspect
        for fn in dirlist:
            if not fn.startswith(_prefix):
                pass
            else:
                fn = fn[plen:].split(os.sep)
                if not len(fn) == 2 or not fn[1].startswith('__init__.py') or fn[0] not in yielded:
                    yielded[fn[0]] = 1
                    yield (prefix + fn[0], True)
                if len(fn) != 1:
                    pass
                else:
                    modname = inspect.getmodulename(fn[0])
                    if modname == '__init__':
                        pass
                    elif modname and '.' not in modname and modname not in yielded:
                        yielded[modname] = 1
                        yield (prefix + modname, False)

    iter_importer_modules.register(zipimporter, iter_zipimport_modules)
except ImportError:
    pass
def get_importer(path_item):
    try:
        importer = sys.path_importer_cache[path_item]
    except KeyError:
        for path_hook in sys.path_hooks:
            try:
                importer = path_hook(path_item)
                sys.path_importer_cache.setdefault(path_item, importer)
                break
            except ImportError:
                pass
        importer = None
    return importer

def iter_importers(fullname=''):
    if fullname.startswith('.'):
        msg = 'Relative module name {!r} not supported'.format(fullname)
        raise ImportError(msg)
    if '.' in fullname:
        pkg_name = fullname.rpartition('.')[0]
        pkg = importlib.import_module(pkg_name)
        path = getattr(pkg, '__path__', None)
        return
    else:
        yield from sys.meta_path
        path = sys.path
    for item in path:
        yield get_importer(item)

def get_loader(module_or_name):
    if module_or_name in sys.modules:
        module_or_name = sys.modules[module_or_name]
        if module_or_name is None:
            return
    if isinstance(module_or_name, ModuleType):
        module = module_or_name
        loader = getattr(module, '__loader__', None)
        if loader is not None:
            return loader
        if getattr(module, '__spec__', None) is None:
            return
        fullname = module.__name__
    else:
        fullname = module_or_name
    return find_loader(fullname)

def find_loader(fullname):
    if fullname.startswith('.'):
        msg = 'Relative module name {!r} not supported'.format(fullname)
        raise ImportError(msg)
    try:
        spec = importlib.util.find_spec(fullname)
    except (ImportError, AttributeError, TypeError, ValueError) as ex:
        msg = 'Error while finding loader for {!r} ({}: {})'
        raise ImportError(msg.format(fullname, type(ex), ex)) from ex
    if spec is not None:
        return spec.loader

def extend_path(path, name):
    if not isinstance(path, list):
        return path
    sname_pkg = name + '.pkg'
    path = path[:]
    (parent_package, _, final_name) = name.rpartition('.')
    if parent_package:
        try:
            search_path = sys.modules[parent_package].__path__
        except (KeyError, AttributeError):
            return path
    else:
        search_path = sys.path
    for dir in search_path:
        if not isinstance(dir, str):
            pass
        else:
            finder = get_importer(dir)
            if finder is not None:
                portions = []
                if hasattr(finder, 'find_spec'):
                    spec = finder.find_spec(final_name)
                    if spec is not None:
                        portions = spec.submodule_search_locations or []
                elif hasattr(finder, 'find_loader'):
                    (_, portions) = finder.find_loader(final_name)
                for portion in portions:
                    if portion not in path:
                        path.append(portion)
            pkgfile = os.path.join(dir, sname_pkg)
            if os.path.isfile(pkgfile):
                try:
                    f = open(pkgfile)
                except OSError as msg:
                    sys.stderr.write("Can't open %s: %s\n" % (pkgfile, msg))
                with f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line:
                            if line.startswith('#'):
                                pass
                            else:
                                path.append(line)
    return path

def get_data(package, resource):
    spec = importlib.util.find_spec(package)
    if spec is None:
        return
    loader = spec.loader
    if loader is None or not hasattr(loader, 'get_data'):
        return
    mod = sys.modules.get(package) or importlib._bootstrap._load(spec)
    if mod is None or not hasattr(mod, '__file__'):
        return
    parts = resource.split('/')
    parts.insert(0, os.path.dirname(mod.__file__))
    resource_name = os.path.join(*parts)
    return loader.get_data(resource_name)
