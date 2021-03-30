from  import _bootstrapfrom  import _bootstrap_externalfrom  import machinerytry:
    import _frozen_importlib
except ImportError as exc:
    if exc.name != '_frozen_importlib':
        raise
    _frozen_importlib = Nonetry:
    import _frozen_importlib_external
except ImportError as exc:
    _frozen_importlib_external = _bootstrap_externalimport abcimport warnings
def _register(abstract_cls, *classes):
    for cls in classes:
        abstract_cls.register(cls)
        if _frozen_importlib is not None:
            try:
                frozen_cls = getattr(_frozen_importlib, cls.__name__)
            except AttributeError:
                frozen_cls = getattr(_frozen_importlib_external, cls.__name__)
            abstract_cls.register(frozen_cls)

class Finder(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def find_module(self, fullname, path=None):
        pass

class MetaPathFinder(Finder):

    def find_module(self, fullname, path):
        warnings.warn('MetaPathFinder.find_module() is deprecated since Python 3.4 in favor of MetaPathFinder.find_spec()(available since 3.4)', DeprecationWarning, stacklevel=2)
        if not hasattr(self, 'find_spec'):
            return
        else:
            found = self.find_spec(fullname, path)
            if found is not None:
                return found.loader

    def invalidate_caches(self):
        pass
_register(MetaPathFinder, machinery.BuiltinImporter, machinery.FrozenImporter, machinery.PathFinder)
class PathEntryFinder(Finder):

    def find_loader(self, fullname):
        warnings.warn('PathEntryFinder.find_loader() is deprecated since Python 3.4 in favor of PathEntryFinder.find_spec() (available since 3.4)', DeprecationWarning, stacklevel=2)
        if not hasattr(self, 'find_spec'):
            return (None, [])
        found = self.find_spec(fullname)
        if found is not None:
            if not found.submodule_search_locations:
                portions = []
            else:
                portions = found.submodule_search_locations
            return (found.loader, portions)
        else:
            return (None, [])

    find_module = _bootstrap_external._find_module_shim

    def invalidate_caches(self):
        pass
_register(PathEntryFinder, machinery.FileFinder)
class Loader(metaclass=abc.ABCMeta):

    def create_module(self, spec):
        pass

    def load_module(self, fullname):
        if not hasattr(self, 'exec_module'):
            raise ImportError
        return _bootstrap._load_module_shim(self, fullname)

    def module_repr(self, module):
        raise NotImplementedError

class ResourceLoader(Loader):

    @abc.abstractmethod
    def get_data(self, path):
        raise OSError

class InspectLoader(Loader):

    def is_package(self, fullname):
        raise ImportError

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return
        return self.source_to_code(source)

    @abc.abstractmethod
    def get_source(self, fullname):
        raise ImportError

    @staticmethod
    def source_to_code(data, path='<string>'):
        return compile(data, path, 'exec', dont_inherit=True)

    exec_module = _bootstrap_external._LoaderBasics.exec_module
    load_module = _bootstrap_external._LoaderBasics.load_module
_register(InspectLoader, machinery.BuiltinImporter, machinery.FrozenImporter)
class ExecutionLoader(InspectLoader):

    @abc.abstractmethod
    def get_filename(self, fullname):
        raise ImportError

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return
        try:
            path = self.get_filename(fullname)
        except ImportError:
            return self.source_to_code(source)
        return self.source_to_code(source, path)
_register(ExecutionLoader, machinery.ExtensionFileLoader)
class FileLoader(_bootstrap_external.FileLoader, ResourceLoader, ExecutionLoader):
    pass
_register(FileLoader, machinery.SourceFileLoader, machinery.SourcelessFileLoader)
class SourceLoader(_bootstrap_external.SourceLoader, ResourceLoader, ExecutionLoader):

    def path_mtime(self, path):
        if self.path_stats.__func__ is SourceLoader.path_stats:
            raise OSError
        return int(self.path_stats(path)['mtime'])

    def path_stats(self, path):
        if self.path_mtime.__func__ is SourceLoader.path_mtime:
            raise OSError
        return {'mtime': self.path_mtime(path)}

    def set_data(self, path, data):
        pass
_register(SourceLoader, machinery.SourceFileLoader)
class ResourceReader(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def open_resource(self, resource):
        raise FileNotFoundError

    @abc.abstractmethod
    def resource_path(self, resource):
        raise FileNotFoundError

    @abc.abstractmethod
    def is_resource(self, name):
        raise FileNotFoundError

    @abc.abstractmethod
    def contents(self):
        return []
_register(ResourceReader, machinery.SourceFileLoader)