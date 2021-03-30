import osimport tempfilefrom  import abc as resources_abcfrom contextlib import contextmanager, suppressfrom importlib import import_modulefrom importlib.abc import ResourceLoaderfrom io import BytesIO, TextIOWrapperfrom pathlib import Pathfrom types import ModuleTypefrom typing import Iterable, Iterator, Optional, Set, Unionfrom typing import castfrom typing.io import BinaryIO, TextIOfrom zipimport import ZipImportError__all__ = ['Package', 'Resource', 'contents', 'is_resource', 'open_binary', 'open_text', 'path', 'read_binary', 'read_text']Package = Union[(str, ModuleType)]Resource = Union[(str, os.PathLike)]
def _get_package(package) -> ModuleType:
    if hasattr(package, '__spec__'):
        if package.__spec__.submodule_search_locations is None:
            raise TypeError('{!r} is not a package'.format(package.__spec__.name))
        else:
            return package
    else:
        module = import_module(package)
        if module.__spec__.submodule_search_locations is None:
            raise TypeError('{!r} is not a package'.format(package))
        else:
            return module

def _normalize_path(path) -> str:
    (parent, file_name) = os.path.split(path)
    if parent:
        raise ValueError('{!r} must be only a file name'.format(path))
    else:
        return file_name

def _get_resource_reader(package:ModuleType) -> Optional[resources_abc.ResourceReader]:
    spec = package.__spec__
    if hasattr(spec.loader, 'get_resource_reader'):
        return cast(resources_abc.ResourceReader, spec.loader.get_resource_reader(spec.name))

def _check_location(package):
    if package.__spec__.origin is None or not package.__spec__.has_location:
        raise FileNotFoundError(f'Package has no location {package}')

def open_binary(package:Package, resource:Resource) -> BinaryIO:
    resource = _normalize_path(resource)
    package = _get_package(package)
    reader = _get_resource_reader(package)
    if reader is not None:
        return reader.open_resource(resource)
    _check_location(package)
    absolute_package_path = os.path.abspath(package.__spec__.origin)
    package_path = os.path.dirname(absolute_package_path)
    full_path = os.path.join(package_path, resource)
    try:
        return open(full_path, mode='rb')
    except OSError:
        loader = cast(ResourceLoader, package.__spec__.loader)
        data = None
        if hasattr(package.__spec__.loader, 'get_data'):
            with suppress(OSError):
                data = loader.get_data(full_path)
        if data is None:
            package_name = package.__spec__.name
            message = '{!r} resource not found in {!r}'.format(resource, package_name)
            raise FileNotFoundError(message)
        else:
            return BytesIO(data)

def open_text(package:Package, resource:Resource, encoding:str='utf-8', errors:str='strict') -> TextIO:
    resource = _normalize_path(resource)
    package = _get_package(package)
    reader = _get_resource_reader(package)
    if reader is not None:
        return TextIOWrapper(reader.open_resource(resource), encoding, errors)
    _check_location(package)
    absolute_package_path = os.path.abspath(package.__spec__.origin)
    package_path = os.path.dirname(absolute_package_path)
    full_path = os.path.join(package_path, resource)
    try:
        return open(full_path, mode='r', encoding=encoding, errors=errors)
    except OSError:
        loader = cast(ResourceLoader, package.__spec__.loader)
        data = None
        if hasattr(package.__spec__.loader, 'get_data'):
            with suppress(OSError):
                data = loader.get_data(full_path)
        if data is None:
            package_name = package.__spec__.name
            message = '{!r} resource not found in {!r}'.format(resource, package_name)
            raise FileNotFoundError(message)
        else:
            return TextIOWrapper(BytesIO(data), encoding, errors)

def read_binary(package:Package, resource:Resource) -> bytes:
    resource = _normalize_path(resource)
    package = _get_package(package)
    with open_binary(package, resource) as fp:
        return fp.read()

def read_text(package:Package, resource:Resource, encoding:str='utf-8', errors:str='strict') -> str:
    resource = _normalize_path(resource)
    package = _get_package(package)
    with open_text(package, resource, encoding, errors) as fp:
        return fp.read()

@contextmanager
def path(package:Package, resource:Resource) -> Iterator[Path]:
    resource = _normalize_path(resource)
    package = _get_package(package)
    reader = _get_resource_reader(package)
    if reader is not None:
        try:
            yield Path(reader.resource_path(resource))
            return
        except FileNotFoundError:
            pass
    else:
        _check_location(package)
    package_directory = Path(package.__spec__.origin).parent
    file_path = package_directory/resource
    if file_path.exists():
        yield file_path
    else:
        with open_binary(package, resource) as fp:
            data = fp.read()
        (fd, raw_path) = tempfile.mkstemp()
        try:
            os.write(fd, data)
            os.close(fd)
            yield Path(raw_path)
        finally:
            try:
                os.remove(raw_path)
            except FileNotFoundError:
                pass

def is_resource(package:Package, name:str) -> bool:
    package = _get_package(package)
    _normalize_path(name)
    reader = _get_resource_reader(package)
    if reader is not None:
        return reader.is_resource(name)
    try:
        package_contents = set(contents(package))
    except (NotADirectoryError, FileNotFoundError):
        return False
    if name not in package_contents:
        return False
    path = Path(package.__spec__.origin).parent/name
    return path.is_file()

def contents(package:Package) -> Iterable[str]:
    package = _get_package(package)
    reader = _get_resource_reader(package)
    if reader is not None:
        return reader.contents()
    if package.__spec__.origin is None or not package.__spec__.has_location:
        return ()
    else:
        package_directory = Path(package.__spec__.origin).parent
        return os.listdir(package_directory)

class _ZipImportResourceReader(resources_abc.ResourceReader):

    def __init__(self, zipimporter, fullname):
        self.zipimporter = zipimporter
        self.fullname = fullname

    def open_resource(self, resource):
        fullname_as_path = self.fullname.replace('.', '/')
        path = f'{fullname_as_path}/{resource}'
        try:
            return BytesIO(self.zipimporter.get_data(path))
        except OSError:
            raise FileNotFoundError(path)

    def resource_path(self, resource):
        raise FileNotFoundError

    def is_resource(self, name):
        fullname_as_path = self.fullname.replace('.', '/')
        path = f'{fullname_as_path}/{name}'
        try:
            self.zipimporter.get_data(path)
        except OSError:
            return False
        return True

    def contents(self):
        fullname_path = Path(self.zipimporter.get_filename(self.fullname))
        relative_path = fullname_path.relative_to(self.zipimporter.archive)
        package_path = relative_path.parent
        subdirs_seen = set()
        for filename in self.zipimporter._files:
            try:
                relative = Path(filename).relative_to(package_path)
            except ValueError:
                continue
            parent_name = relative.parent.name
            if len(parent_name) == 0:
                yield relative.name
            elif parent_name not in subdirs_seen:
                subdirs_seen.add(parent_name)
                yield parent_name

def _zipimport_get_resource_reader(zipimporter, fullname):
    try:
        if not zipimporter.is_package(fullname):
            return
    except ZipImportError:
        return
    return _ZipImportResourceReader(zipimporter, fullname)
