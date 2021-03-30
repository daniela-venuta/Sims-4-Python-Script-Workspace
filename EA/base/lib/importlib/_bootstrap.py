_bootstrap_external = None
def _wrap(new, old):
    for replace in ('__module__', '__name__', '__qualname__', '__doc__'):
        if hasattr(old, replace):
            setattr(new, replace, getattr(old, replace))
    new.__dict__.update(old.__dict__)

def _new_module(name):
    return type(sys)(name)
_module_locks = {}_blocking_on = {}
class _DeadlockError(RuntimeError):
    pass

class _ModuleLock:

    def __init__(self, name):
        self.lock = _thread.allocate_lock()
        self.wakeup = _thread.allocate_lock()
        self.name = name
        self.owner = None
        self.count = 0
        self.waiters = 0

    def has_deadlock(self):
        me = _thread.get_ident()
        tid = self.owner
        while True:
            lock = _blocking_on.get(tid)
            if lock is None:
                return False
            tid = lock.owner
            if tid == me:
                return True

    def acquire(self):
        tid = _thread.get_ident()
        _blocking_on[tid] = self
        try:
            while True:
                with self.lock:
                    if self.count == 0 or self.owner == tid:
                        self.owner = tid
                        self.count += 1
                        return True
                    if self.has_deadlock():
                        raise _DeadlockError('deadlock detected by %r' % self)
                    if self.wakeup.acquire(False):
                        self.waiters += 1
                self.wakeup.acquire()
                self.wakeup.release()
        finally:
            del _blocking_on[tid]

    def release(self):
        tid = _thread.get_ident()
        with self.lock:
            if self.owner != tid:
                raise RuntimeError('cannot release un-acquired lock')
            self.count -= 1
            if self.count == 0:
                self.owner = None
                if self.waiters:
                    self.waiters -= 1
                    self.wakeup.release()

    def __repr__(self):
        return '_ModuleLock({!r}) at {}'.format(self.name, id(self))

class _DummyModuleLock:

    def __init__(self, name):
        self.name = name
        self.count = 0

    def acquire(self):
        self.count += 1
        return True

    def release(self):
        if self.count == 0:
            raise RuntimeError('cannot release un-acquired lock')
        self.count -= 1

    def __repr__(self):
        return '_DummyModuleLock({!r}) at {}'.format(self.name, id(self))

class _ModuleLockManager:

    def __init__(self, name):
        self._name = name
        self._lock = None

    def __enter__(self):
        self._lock = _get_module_lock(self._name)
        self._lock.acquire()

    def __exit__(self, *args, **kwargs):
        self._lock.release()

def _get_module_lock(name):
    _imp.acquire_lock()
    try:
        try:
            lock = _module_locks[name]()
        except KeyError:
            lock = None
        if lock is None:
            if _thread is None:
                lock = _DummyModuleLock(name)
            else:
                lock = _ModuleLock(name)

            def cb(ref, name=name):
                _imp.acquire_lock()
                try:
                    if _module_locks.get(name) is ref:
                        del _module_locks[name]
                finally:
                    _imp.release_lock()

            _module_locks[name] = _weakref.ref(lock, cb)
    finally:
        _imp.release_lock()
    return lock

def _lock_unlock_module(name):
    lock = _get_module_lock(name)
    try:
        lock.acquire()
    except _DeadlockError:
        pass
    lock.release()

def _call_with_frames_removed(f, *args, **kwds):
    return f(*args, **kwds)

def _verbose_message(message, *args, verbosity=1):
    if sys.flags.verbose >= verbosity:
        if not message.startswith(('#', 'import ')):
            message = '# ' + message
        print(message.format(*args), file=sys.stderr)

def _requires_builtin(fxn):

    def _requires_builtin_wrapper(self, fullname):
        if fullname not in sys.builtin_module_names:
            raise ImportError('{!r} is not a built-in module'.format(fullname), name=fullname)
        return fxn(self, fullname)

    _wrap(_requires_builtin_wrapper, fxn)
    return _requires_builtin_wrapper

def _requires_frozen(fxn):

    def _requires_frozen_wrapper(self, fullname):
        if not _imp.is_frozen(fullname):
            raise ImportError('{!r} is not a frozen module'.format(fullname), name=fullname)
        return fxn(self, fullname)

    _wrap(_requires_frozen_wrapper, fxn)
    return _requires_frozen_wrapper

def _load_module_shim(self, fullname):
    spec = spec_from_loader(fullname, self)
    if fullname in sys.modules:
        module = sys.modules[fullname]
        _exec(spec, module)
        return sys.modules[fullname]
    else:
        return _load(spec)

def _module_repr(module):
    loader = getattr(module, '__loader__', None)
    if hasattr(loader, 'module_repr'):
        try:
            return loader.module_repr(module)
        except Exception:
            pass
    try:
        spec = module.__spec__
    except AttributeError:
        pass
    if spec is not None:
        return _module_repr_from_spec(spec)
    try:
        name = module.__name__
    except AttributeError:
        name = '?'
    try:
        filename = module.__file__
    except AttributeError:
        if loader is None:
            return '<module {!r}>'.format(name)
        return '<module {!r} ({!r})>'.format(name, loader)
    return '<module {!r} from {!r}>'.format(name, filename)

class _installed_safely:

    def __init__(self, module):
        self._module = module
        self._spec = module.__spec__

    def __enter__(self):
        self._spec._initializing = True
        sys.modules[self._spec.name] = self._module

    def __exit__(self, *args):
        try:
            spec = self._spec
            if any(arg is not None for arg in args):
                try:
                    del sys.modules[spec.name]
                except KeyError:
                    pass
            else:
                _verbose_message('import {!r} # {!r}', spec.name, spec.loader)
        finally:
            self._spec._initializing = False

class ModuleSpec:

    def __init__(self, name, loader, *, origin=None, loader_state=None, is_package=None):
        self.name = name
        self.loader = loader
        self.origin = origin
        self.loader_state = loader_state
        self.submodule_search_locations = [] if is_package else None
        self._set_fileattr = False
        self._cached = None

    def __repr__(self):
        args = ['name={!r}'.format(self.name), 'loader={!r}'.format(self.loader)]
        if self.origin is not None:
            args.append('origin={!r}'.format(self.origin))
        if self.submodule_search_locations is not None:
            args.append('submodule_search_locations={}'.format(self.submodule_search_locations))
        return '{}({})'.format(self.__class__.__name__, ', '.join(args))

    def __eq__(self, other):
        smsl = self.submodule_search_locations
        try:
            return self.name == other.name and (self.loader == other.loader and (self.origin == other.origin and (smsl == other.submodule_search_locations and (self.cached == other.cached and self.has_location == other.has_location))))
        except AttributeError:
            return False

    @property
    def cached(self):
        if self._set_fileattr:
            if _bootstrap_external is None:
                raise NotImplementedError
            self._cached = _bootstrap_external._get_cached(self.origin)
        return self._cached

    @cached.setter
    def cached(self, cached):
        self._cached = cached

    @property
    def parent(self):
        if self.submodule_search_locations is None:
            return self.name.rpartition('.')[0]
        else:
            return self.name

    @property
    def has_location(self):
        return self._set_fileattr

    @has_location.setter
    def has_location(self, value):
        self._set_fileattr = bool(value)

def spec_from_loader(name, loader, *, origin=None, is_package=None):
    if hasattr(loader, 'get_filename'):
        if _bootstrap_external is None:
            raise NotImplementedError
        spec_from_file_location = _bootstrap_external.spec_from_file_location
        if is_package is None:
            return spec_from_file_location(name, loader=loader)
        search = [] if is_package else None
        return spec_from_file_location(name, loader=loader, submodule_search_locations=search)
    if is_package is None:
        if hasattr(loader, 'is_package'):
            try:
                is_package = loader.is_package(name)
            except ImportError:
                is_package = None
        else:
            is_package = False
    return ModuleSpec(name, loader, origin=origin, is_package=is_package)

def _spec_from_module(module, loader=None, origin=None):
    try:
        spec = module.__spec__
    except AttributeError:
        pass
    if spec is not None:
        return spec
    name = module.__name__
    if loader is None:
        try:
            loader = module.__loader__
        except AttributeError:
            pass
    try:
        location = module.__file__
    except AttributeError:
        location = None
    if origin is None:
        if location is None:
            try:
                origin = loader._ORIGIN
            except AttributeError:
                origin = None
        else:
            origin = location
    try:
        cached = module.__cached__
    except AttributeError:
        cached = None
    try:
        submodule_search_locations = list(module.__path__)
    except AttributeError:
        submodule_search_locations = None
    spec = ModuleSpec(name, loader, origin=origin)
    spec._set_fileattr = False if location is None else True
    spec.cached = cached
    spec.submodule_search_locations = submodule_search_locations
    return spec

def _init_module_attrs(spec, module, *, override=False):
    if override or getattr(module, '__name__', None) is None:
        try:
            module.__name__ = spec.name
        except AttributeError:
            pass
    if override or getattr(module, '__loader__', None) is None:
        loader = spec.loader
        if spec.submodule_search_locations is not None:
            if _bootstrap_external is None:
                raise NotImplementedError
            _NamespaceLoader = _bootstrap_external._NamespaceLoader
            loader = _NamespaceLoader.__new__(_NamespaceLoader)
            loader._path = spec.submodule_search_locations
            spec.loader = loader
            module.__file__ = None
        try:
            module.__loader__ = loader
        except AttributeError:
            pass
    if override or getattr(module, '__package__', None) is None:
        try:
            module.__package__ = spec.parent
        except AttributeError:
            pass
    try:
        module.__spec__ = spec
    except AttributeError:
        pass
    if spec.submodule_search_locations is not None:
        try:
            module.__path__ = spec.submodule_search_locations
        except AttributeError:
            pass
    if (override or getattr(module, '__path__', None) is None) and spec.has_location:
        if override or getattr(module, '__file__', None) is None:
            try:
                module.__file__ = spec.origin
            except AttributeError:
                pass
        if spec.cached is not None:
            try:
                module.__cached__ = spec.cached
            except AttributeError:
                pass
    return module

def module_from_spec(spec):
    module = None
    if hasattr(spec.loader, 'create_module'):
        module = spec.loader.create_module(spec)
    elif hasattr(spec.loader, 'exec_module'):
        raise ImportError('loaders that define exec_module() must also define create_module()')
    if module is None:
        module = _new_module(spec.name)
    _init_module_attrs(spec, module)
    return module

def _module_repr_from_spec(spec):
    name = '?' if spec.name is None else spec.name
    if spec.origin is None:
        if spec.loader is None:
            return '<module {!r}>'.format(name)
        return '<module {!r} ({!r})>'.format(name, spec.loader)
    elif spec.has_location:
        return '<module {!r} from {!r}>'.format(name, spec.origin)
    else:
        return '<module {!r} ({})>'.format(spec.name, spec.origin)

def _exec(spec, module):
    name = spec.name
    with _ModuleLockManager(name):
        if sys.modules.get(name) is not module:
            msg = 'module {!r} not in sys.modules'.format(name)
            raise ImportError(msg, name=name)
        if spec.loader is None:
            if spec.submodule_search_locations is None:
                raise ImportError('missing loader', name=spec.name)
            _init_module_attrs(spec, module, override=True)
            return module
        _init_module_attrs(spec, module, override=True)
        if not hasattr(spec.loader, 'exec_module'):
            spec.loader.load_module(name)
        else:
            spec.loader.exec_module(module)
    return sys.modules[name]

def _load_backward_compatible(spec):
    spec.loader.load_module(spec.name)
    module = sys.modules[spec.name]
    if getattr(module, '__loader__', None) is None:
        try:
            module.__loader__ = spec.loader
        except AttributeError:
            pass
    if getattr(module, '__package__', None) is None:
        try:
            module.__package__ = module.__name__
            if not hasattr(module, '__path__'):
                module.__package__ = spec.name.rpartition('.')[0]
        except AttributeError:
            pass
    if getattr(module, '__spec__', None) is None:
        try:
            module.__spec__ = spec
        except AttributeError:
            pass
    return module

def _load_unlocked(spec):
    if spec.loader is not None and not hasattr(spec.loader, 'exec_module'):
        return _load_backward_compatible(spec)
    module = module_from_spec(spec)
    with _installed_safely(module):
        if spec.loader is None:
            if spec.submodule_search_locations is None:
                raise ImportError('missing loader', name=spec.name)
        else:
            spec.loader.exec_module(module)
    return sys.modules[spec.name]

def _load(spec):
    with _ModuleLockManager(spec.name):
        return _load_unlocked(spec)

class BuiltinImporter:

    @staticmethod
    def module_repr(module):
        return '<module {!r} (built-in)>'.format(module.__name__)

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if path is not None:
            return
        elif _imp.is_builtin(fullname):
            return spec_from_loader(fullname, cls, origin='built-in')
        else:
            return
        return

    @classmethod
    def find_module(cls, fullname, path=None):
        spec = cls.find_spec(fullname, path)
        if spec is not None:
            return spec.loader

    @classmethod
    def create_module(self, spec):
        if spec.name not in sys.builtin_module_names:
            raise ImportError('{!r} is not a built-in module'.format(spec.name), name=spec.name)
        return _call_with_frames_removed(_imp.create_builtin, spec)

    @classmethod
    def exec_module(self, module):
        _call_with_frames_removed(_imp.exec_builtin, module)

    @classmethod
    @_requires_builtin
    def get_code(cls, fullname):
        pass

    @classmethod
    @_requires_builtin
    def get_source(cls, fullname):
        pass

    @classmethod
    @_requires_builtin
    def is_package(cls, fullname):
        return False

    load_module = classmethod(_load_module_shim)

class FrozenImporter:

    @staticmethod
    def module_repr(m):
        return '<module {!r} (frozen)>'.format(m.__name__)

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if _imp.is_frozen(fullname):
            return spec_from_loader(fullname, cls, origin='frozen')
        else:
            return

    @classmethod
    def find_module(cls, fullname, path=None):
        if _imp.is_frozen(fullname):
            return cls

    @classmethod
    def create_module(cls, spec):
        pass

    @staticmethod
    def exec_module(module):
        name = module.__spec__.name
        if not _imp.is_frozen(name):
            raise ImportError('{!r} is not a frozen module'.format(name), name=name)
        code = _call_with_frames_removed(_imp.get_frozen_object, name)
        exec(code, module.__dict__)

    @classmethod
    def load_module(cls, fullname):
        return _load_module_shim(cls, fullname)

    @classmethod
    @_requires_frozen
    def get_code(cls, fullname):
        return _imp.get_frozen_object(fullname)

    @classmethod
    @_requires_frozen
    def get_source(cls, fullname):
        pass

    @classmethod
    @_requires_frozen
    def is_package(cls, fullname):
        return _imp.is_frozen_package(fullname)

class _ImportLockContext:

    def __enter__(self):
        _imp.acquire_lock()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        _imp.release_lock()

def _resolve_name(name, package, level):
    bits = package.rsplit('.', level - 1)
    if len(bits) < level:
        raise ValueError('attempted relative import beyond top-level package')
    base = bits[0]
    if name:
        return '{}.{}'.format(base, name)
    return base

def _find_spec_legacy(finder, name, path):
    loader = finder.find_module(name, path)
    if loader is None:
        return
    return spec_from_loader(name, loader)

def _find_spec(name, path, target=None):
    meta_path = sys.meta_path
    if meta_path is None:
        raise ImportError('sys.meta_path is None, Python is likely shutting down')
    if not meta_path:
        _warnings.warn('sys.meta_path is empty', ImportWarning)
    is_reload = name in sys.modules
    for finder in meta_path:
        with _ImportLockContext():
            try:
                find_spec = finder.find_spec
            except AttributeError:
                spec = _find_spec_legacy(finder, name, path)
                if spec is None:
                    continue
            spec = find_spec(name, path, target)
        if spec is not None:
            if is_reload or name in sys.modules:
                module = sys.modules[name]
                try:
                    __spec__ = module.__spec__
                except AttributeError:
                    return spec
                if __spec__ is None:
                    return spec
                return __spec__
            else:
                return spec
    return

def _sanity_check(name, package, level):
    if not isinstance(name, str):
        raise TypeError('module name must be str, not {}'.format(type(name)))
    if level < 0:
        raise ValueError('level must be >= 0')
    if level > 0:
        if not isinstance(package, str):
            raise TypeError('__package__ not set to a string')
        elif not package:
            raise ImportError('attempted relative import with no known parent package')
    if name or level == 0:
        raise ValueError('Empty module name')
_ERR_MSG_PREFIX = 'No module named '_ERR_MSG = _ERR_MSG_PREFIX + '{!r}'
def _find_and_load_unlocked(name, import_):
    path = None
    parent = name.rpartition('.')[0]
    if parent:
        if parent not in sys.modules:
            _call_with_frames_removed(import_, parent)
        if name in sys.modules:
            return sys.modules[name]
        parent_module = sys.modules[parent]
        try:
            path = parent_module.__path__
        except AttributeError:
            msg = (_ERR_MSG + '; {!r} is not a package').format(name, parent)
            raise ModuleNotFoundError(msg, name=name) from None
    spec = _find_spec(name, path)
    if spec is None:
        raise ModuleNotFoundError(_ERR_MSG.format(name), name=name)
    else:
        module = _load_unlocked(spec)
    if parent:
        parent_module = sys.modules[parent]
        setattr(parent_module, name.rpartition('.')[2], module)
    return module
_NEEDS_LOADING = object()
def _find_and_load(name, import_):
    with _ModuleLockManager(name):
        module = sys.modules.get(name, _NEEDS_LOADING)
        if module is _NEEDS_LOADING:
            return _find_and_load_unlocked(name, import_)
    if module is None:
        message = 'import of {} halted; None in sys.modules'.format(name)
        raise ModuleNotFoundError(message, name=name)
    _lock_unlock_module(name)
    return module

def _gcd_import(name, package=None, level=0):
    _sanity_check(name, package, level)
    if level > 0:
        name = _resolve_name(name, package, level)
    return _find_and_load(name, _gcd_import)

def _handle_fromlist(module, fromlist, import_, *, recursive=False):
    if hasattr(module, '__path__'):
        for x in fromlist:
            if not isinstance(x, str):
                if recursive:
                    where = module.__name__ + '.__all__'
                else:
                    where = "``from list''"
                raise TypeError(f'Item in {where} must be str, not {type(x).__name__}')
            elif x == '*':
                if hasattr(module, '__all__'):
                    _handle_fromlist(module, module.__all__, import_, recursive=True)
                    if not hasattr(module, x):
                        from_name = '{}.{}'.format(module.__name__, x)
                        try:
                            _call_with_frames_removed(import_, from_name)
                        except ModuleNotFoundError as exc:
                            if sys.modules.get(from_name, _NEEDS_LOADING) is not None:
                                continue
                            raise
            elif not hasattr(module, x):
                from_name = '{}.{}'.format(module.__name__, x)
                try:
                    _call_with_frames_removed(import_, from_name)
                except ModuleNotFoundError as exc:
                    if sys.modules.get(from_name, _NEEDS_LOADING) is not None:
                        continue
                    raise
    return module

def _calc___package__(globals):
    package = globals.get('__package__')
    spec = globals.get('__spec__')
    if package is not None:
        if spec is not None and package != spec.parent:
            _warnings.warn(f'__package__ != __spec__.parent ({package} != {spec.parent})', ImportWarning, stacklevel=3)
        return package
    if spec is not None:
        return spec.parent
    _warnings.warn("can't resolve package from __spec__ or __package__, falling back on __name__ and __path__", ImportWarning, stacklevel=3)
    package = globals['__name__']
    if '__path__' not in globals:
        package = package.rpartition('.')[0]
    return package

def __import__(name, globals=None, locals=None, fromlist=(), level=0):
    if level == 0:
        module = _gcd_import(name)
    else:
        globals_ = globals if globals is not None else {}
        package = _calc___package__(globals_)
        module = _gcd_import(name, package, level)
    if not fromlist:
        if level == 0:
            return _gcd_import(name.partition('.')[0])
        if not name:
            return module
        cut_off = len(name) - len(name.partition('.')[0])
        return sys.modules[module.__name__[:len(module.__name__) - cut_off]]
    else:
        return _handle_fromlist(module, fromlist, _gcd_import)

def _builtin_from_name(name):
    spec = BuiltinImporter.find_spec(name)
    if spec is None:
        raise ImportError('no built-in module named ' + name)
    return _load_unlocked(spec)

def _setup(sys_module, _imp_module):
    global _imp, sys
    _imp = _imp_module
    sys = sys_module
    module_type = type(sys)
    for (name, module) in sys.modules.items():
        if name in sys.builtin_module_names:
            loader = BuiltinImporter
        elif _imp.is_frozen(name):
            loader = FrozenImporter
            spec = _spec_from_module(module, loader)
            _init_module_attrs(spec, module)
        spec = _spec_from_module(module, loader)
        _init_module_attrs(spec, module)
    self_module = sys.modules[__name__]
    for builtin_name in ('_thread', '_warnings', '_weakref'):
        if builtin_name not in sys.modules:
            builtin_module = _builtin_from_name(builtin_name)
        else:
            builtin_module = sys.modules[builtin_name]
        setattr(self_module, builtin_name, builtin_module)

def _install(sys_module, _imp_module):
    _setup(sys_module, _imp_module)
    sys.meta_path.append(BuiltinImporter)
    sys.meta_path.append(FrozenImporter)

def _install_external_importers():
    global _bootstrap_external
    import _frozen_importlib_external
    _bootstrap_external = _frozen_importlib_external
    _frozen_importlib_external._install(sys.modules[__name__])
