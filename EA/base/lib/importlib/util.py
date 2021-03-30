from  import abcfrom _bootstrap import module_from_specfrom _bootstrap import _resolve_namefrom _bootstrap import spec_from_loaderfrom _bootstrap import _find_specfrom _bootstrap_external import MAGIC_NUMBERfrom _bootstrap_external import _RAW_MAGIC_NUMBERfrom _bootstrap_external import cache_from_sourcefrom _bootstrap_external import decode_sourcefrom _bootstrap_external import source_from_cachefrom _bootstrap_external import spec_from_file_locationfrom contextlib import contextmanagerimport _impimport functoolsimport sysimport typesimport warnings
def source_hash(source_bytes):
    return _imp.source_hash(_RAW_MAGIC_NUMBER, source_bytes)

def resolve_name(name, package):
    if not name.startswith('.'):
        return name
    if not package:
        raise ValueError(f'no package specified for {repr(name)} (required for relative module names)')
    level = 0
    for character in name:
        if character != '.':
            break
        level += 1
    return _resolve_name(name[level:], package, level)

def _find_spec_from_path(name, path=None):
    if name not in sys.modules:
        return _find_spec(name, path)
    module = sys.modules[name]
    if module is None:
        return
    else:
        try:
            spec = module.__spec__
        except AttributeError:
            raise ValueError('{}.__spec__ is not set'.format(name)) from None
        if spec is None:
            raise ValueError('{}.__spec__ is None'.format(name))
        return spec

def find_spec(name, package=None):
    fullname = resolve_name(name, package) if name.startswith('.') else name
    if fullname not in sys.modules:
        parent_name = fullname.rpartition('.')[0]
        if parent_name:
            parent = __import__(parent_name, fromlist=['__path__'])
            try:
                parent_path = parent.__path__
            except AttributeError as e:
                raise ModuleNotFoundError(f'__path__ attribute not found on {parent_name} while trying to find {fullname}', name=fullname) from e
        else:
            parent_path = None
        return _find_spec(fullname, parent_path)
    module = sys.modules[fullname]
    if module is None:
        return
    else:
        try:
            spec = module.__spec__
        except AttributeError:
            raise ValueError('{}.__spec__ is not set'.format(name)) from None
        if spec is None:
            raise ValueError('{}.__spec__ is None'.format(name))
        return spec

@contextmanager
def _module_to_load(name):
    is_reload = name in sys.modules
    module = sys.modules.get(name)
    module = type(sys)(name)
    module.__initializing__ = True
    sys.modules[name] = module
    try:
        yield module
    except Exception:
        if not is_reload:
            try:
                del sys.modules[name]
            except KeyError:
                pass
    finally:
        module.__initializing__ = False

def set_package(fxn):

    @functools.wraps(fxn)
    def set_package_wrapper(*args, **kwargs):
        warnings.warn('The import system now takes care of this automatically.', DeprecationWarning, stacklevel=2)
        module = fxn(*args, **kwargs)
        if getattr(module, '__package__', None) is None:
            module.__package__ = module.__name__
            if not hasattr(module, '__path__'):
                module.__package__ = module.__package__.rpartition('.')[0]
        return module

    return set_package_wrapper

def set_loader(fxn):

    @functools.wraps(fxn)
    def set_loader_wrapper(self, *args, **kwargs):
        warnings.warn('The import system now takes care of this automatically.', DeprecationWarning, stacklevel=2)
        module = fxn(self, *args, **kwargs)
        if getattr(module, '__loader__', None) is None:
            module.__loader__ = self
        return module

    return set_loader_wrapper

def module_for_loader(fxn):
    warnings.warn('The import system now takes care of this automatically.', DeprecationWarning, stacklevel=2)

    @functools.wraps(fxn)
    def module_for_loader_wrapper(self, fullname, *args, **kwargs):
        with _module_to_load(fullname) as module:
            module.__loader__ = self
            try:
                is_package = self.is_package(fullname)
            except (ImportError, AttributeError):
                pass
            if is_package:
                module.__package__ = fullname
            else:
                module.__package__ = fullname.rpartition('.')[0]
            return fxn(self, module, *args, **kwargs)

    return module_for_loader_wrapper

class _LazyModule(types.ModuleType):

    def __getattribute__(self, attr):
        self.__class__ = types.ModuleType
        original_name = self.__spec__.name
        attrs_then = self.__spec__.loader_state['__dict__']
        original_type = self.__spec__.loader_state['__class__']
        attrs_now = self.__dict__
        attrs_updated = {}
        for (key, value) in attrs_now.items():
            if key not in attrs_then:
                attrs_updated[key] = value
            elif id(attrs_now[key]) != id(attrs_then[key]):
                attrs_updated[key] = value
        self.__spec__.loader.exec_module(self)
        if original_name in sys.modules and id(self) != id(sys.modules[original_name]):
            raise ValueError(f'module object for {original_name} substituted in sys.modules during a lazy load')
        self.__dict__.update(attrs_updated)
        return getattr(self, attr)

    def __delattr__(self, attr):
        self.__getattribute__(attr)
        delattr(self, attr)

class LazyLoader(abc.Loader):

    @staticmethod
    def __check_eager_loader(loader):
        if not hasattr(loader, 'exec_module'):
            raise TypeError('loader must define exec_module()')

    @classmethod
    def factory(cls, loader):
        cls._LazyLoader__check_eager_loader(loader)
        return lambda *args, **kwargs: cls(loader(*args, **kwargs))

    def __init__(self, loader):
        self._LazyLoader__check_eager_loader(loader)
        self.loader = loader

    def create_module(self, spec):
        return self.loader.create_module(spec)

    def exec_module(self, module):
        module.__spec__.loader = self.loader
        module.__loader__ = self.loader
        loader_state = {}
        loader_state['__dict__'] = module.__dict__.copy()
        loader_state['__class__'] = module.__class__
        module.__spec__.loader_state = loader_state
        module.__class__ = _LazyModule
