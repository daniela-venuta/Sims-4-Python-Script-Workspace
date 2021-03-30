from _weakref import getweakrefcount, getweakrefs, ref, proxy, CallableProxyType, ProxyType, ReferenceType, _remove_dead_weakreffrom _weakrefset import WeakSet, _IterationGuardimport _collections_abcimport sysimport itertoolsProxyTypes = (ProxyType, CallableProxyType)__all__ = ['ref', 'proxy', 'getweakrefcount', 'getweakrefs', 'WeakKeyDictionary', 'ReferenceType', 'ProxyType', 'CallableProxyType', 'ProxyTypes', 'WeakValueDictionary', 'WeakSet', 'WeakMethod', 'finalize']
class WeakMethod(ref):
    __slots__ = ('_func_ref', '_meth_type', '_alive', '__weakref__')

    def __new__(cls, meth, callback=None):
        try:
            obj = meth.__self__
            func = meth.__func__
        except AttributeError:
            raise TypeError('argument should be a bound method, not {}'.format(type(meth))) from None

        def _cb(arg):
            self = self_wr()
            if self._alive:
                self._alive = False
                if callback is not None:
                    callback(self)

        self = ref.__new__(cls, obj, _cb)
        self._func_ref = ref(func, _cb)
        self._meth_type = type(meth)
        self._alive = True
        self_wr = ref(self)
        return self

    def __call__(self):
        obj = super().__call__()
        func = self._func_ref()
        if obj is None or func is None:
            return
        return self._meth_type(func, obj)

    def __eq__(self, other):
        if isinstance(other, WeakMethod):
            if not (self._alive and other._alive):
                return self is other
            else:
                return ref.__eq__(self, other) and self._func_ref == other._func_ref
        return False

    def __ne__(self, other):
        if isinstance(other, WeakMethod):
            if not (self._alive and other._alive):
                return self is not other
            else:
                return ref.__ne__(self, other) or self._func_ref != other._func_ref
        return True

    __hash__ = ref.__hash__

class WeakValueDictionary(_collections_abc.MutableMapping):

    def __init__(*args, **kw):
        if not args:
            raise TypeError("descriptor '__init__' of 'WeakValueDictionary' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))

        def remove(wr, selfref=ref(self), _atomic_removal=_remove_dead_weakref):
            self = selfref()
            if self is not None:
                if self._iterating:
                    self._pending_removals.append(wr.key)
                else:
                    _atomic_removal(d, wr.key)

        self._remove = remove
        self._pending_removals = []
        self._iterating = set()
        self.data = d = {}
        self.update(*args, **kw)

    def _commit_removals(self):
        l = self._pending_removals
        d = self.data
        while l:
            key = l.pop()
            _remove_dead_weakref(d, key)

    def __getitem__(self, key):
        if self._pending_removals:
            self._commit_removals()
        o = self.data[key]()
        if o is None:
            raise KeyError(key)
        else:
            return o

    def __delitem__(self, key):
        if self._pending_removals:
            self._commit_removals()
        del self.data[key]

    def __len__(self):
        if self._pending_removals:
            self._commit_removals()
        return len(self.data)

    def __contains__(self, key):
        if self._pending_removals:
            self._commit_removals()
        try:
            o = self.data[key]()
        except KeyError:
            return False
        return o is not None

    def __repr__(self):
        return '<%s at %#x>' % (self.__class__.__name__, id(self))

    def __setitem__(self, key, value):
        if self._pending_removals:
            self._commit_removals()
        self.data[key] = KeyedRef(value, self._remove, key)

    def copy(self):
        if self._pending_removals:
            self._commit_removals()
        new = WeakValueDictionary()
        for (key, wr) in self.data.items():
            o = wr()
            if o is not None:
                new[key] = o
        return new

    __copy__ = copy

    def __deepcopy__(self, memo):
        from copy import deepcopy
        if self._pending_removals:
            self._commit_removals()
        new = self.__class__()
        for (key, wr) in self.data.items():
            o = wr()
            if o is not None:
                new[deepcopy(key, memo)] = o
        return new

    def get(self, key, default=None):
        if self._pending_removals:
            self._commit_removals()
        try:
            wr = self.data[key]
        except KeyError:
            return default
        o = wr()
        if o is None:
            return default
        else:
            return o

    def items(self):
        if self._pending_removals:
            self._commit_removals()
        with _IterationGuard(self):
            for (k, wr) in self.data.items():
                v = wr()
                if v is not None:
                    yield (k, v)

    def keys(self):
        if self._pending_removals:
            self._commit_removals()
        with _IterationGuard(self):
            for (k, wr) in self.data.items():
                if wr() is not None:
                    yield k

    __iter__ = keys

    def itervaluerefs(self):
        if self._pending_removals:
            self._commit_removals()
        with _IterationGuard(self):
            yield from self.data.values()

    def values(self):
        if self._pending_removals:
            self._commit_removals()
        with _IterationGuard(self):
            for wr in self.data.values():
                obj = wr()
                if obj is not None:
                    yield obj

    def popitem(self):
        if self._pending_removals:
            self._commit_removals()
        while True:
            (key, wr) = self.data.popitem()
            o = wr()
            if o is not None:
                return (key, o)

    def pop(self, key, *args):
        if self._pending_removals:
            self._commit_removals()
        try:
            o = self.data.pop(key)()
        except KeyError:
            o = None
        if o is None:
            if args:
                return args[0]
            else:
                raise KeyError(key)
        else:
            return o

    def setdefault(self, key, default=None):
        try:
            o = self.data[key]()
        except KeyError:
            o = None
        if o is None:
            if self._pending_removals:
                self._commit_removals()
            self.data[key] = KeyedRef(default, self._remove, key)
            return default
        else:
            return o

    def update(*args, **kwargs):
        if not args:
            raise TypeError("descriptor 'update' of 'WeakValueDictionary' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        dict = args[0] if args else None
        if self._pending_removals:
            self._commit_removals()
        d = self.data
        if dict is not None:
            if not hasattr(dict, 'items'):
                dict = type({})(dict)
            for (key, o) in dict.items():
                d[key] = KeyedRef(o, self._remove, key)
        if len(kwargs):
            self.update(kwargs)

    def valuerefs(self):
        if self._pending_removals:
            self._commit_removals()
        return list(self.data.values())

class KeyedRef(ref):
    __slots__ = ('key',)

    def __new__(type, ob, callback, key):
        self = ref.__new__(type, ob, callback)
        self.key = key
        return self

    def __init__(self, ob, callback, key):
        super().__init__(ob, callback)

class WeakKeyDictionary(_collections_abc.MutableMapping):

    def __init__(self, dict=None):
        self.data = {}

        def remove(k, selfref=ref(self)):
            self = selfref()
            if self is not None:
                if self._iterating:
                    self._pending_removals.append(k)
                else:
                    del self.data[k]

        self._remove = remove
        self._pending_removals = []
        self._iterating = set()
        self._dirty_len = False
        if dict is not None:
            self.update(dict)

    def _commit_removals(self):
        l = self._pending_removals
        d = self.data
        while l:
            try:
                del d[l.pop()]
            except KeyError:
                pass

    def _scrub_removals(self):
        d = self.data
        self._pending_removals = [k for k in self._pending_removals if k in d]
        self._dirty_len = False

    def __delitem__(self, key):
        self._dirty_len = True
        del self.data[ref(key)]

    def __getitem__(self, key):
        return self.data[ref(key)]

    def __len__(self):
        if self._dirty_len and self._pending_removals:
            self._scrub_removals()
        return len(self.data) - len(self._pending_removals)

    def __repr__(self):
        return '<%s at %#x>' % (self.__class__.__name__, id(self))

    def __setitem__(self, key, value):
        self.data[ref(key, self._remove)] = value

    def copy(self):
        new = WeakKeyDictionary()
        for (key, value) in self.data.items():
            o = key()
            if o is not None:
                new[o] = value
        return new

    __copy__ = copy

    def __deepcopy__(self, memo):
        from copy import deepcopy
        new = self.__class__()
        for (key, value) in self.data.items():
            o = key()
            if o is not None:
                new[o] = deepcopy(value, memo)
        return new

    def get(self, key, default=None):
        return self.data.get(ref(key), default)

    def __contains__(self, key):
        try:
            wr = ref(key)
        except TypeError:
            return False
        return wr in self.data

    def items(self):
        with _IterationGuard(self):
            for (wr, value) in self.data.items():
                key = wr()
                if key is not None:
                    yield (key, value)

    def keys(self):
        with _IterationGuard(self):
            for wr in self.data:
                obj = wr()
                if obj is not None:
                    yield obj

    __iter__ = keys

    def values(self):
        with _IterationGuard(self):
            for (wr, value) in self.data.items():
                if wr() is not None:
                    yield value

    def keyrefs(self):
        return list(self.data)

    def popitem(self):
        self._dirty_len = True
        while True:
            (key, value) = self.data.popitem()
            o = key()
            if o is not None:
                return (o, value)

    def pop(self, key, *args):
        self._dirty_len = True
        return self.data.pop(ref(key), *args)

    def setdefault(self, key, default=None):
        return self.data.setdefault(ref(key, self._remove), default)

    def update(self, dict=None, **kwargs):
        d = self.data
        if dict is not None:
            if not hasattr(dict, 'items'):
                dict = type({})(dict)
            for (key, value) in dict.items():
                d[ref(key, self._remove)] = value
        if len(kwargs):
            self.update(kwargs)

class finalize:
    __slots__ = ()
    _registry = {}
    _shutdown = False
    _index_iter = itertools.count()
    _dirty = False
    _registered_with_atexit = False

    class _Info:
        __slots__ = ('weakref', 'func', 'args', 'kwargs', 'atexit', 'index')

    def __init__(self, obj, func, *args, **kwargs):
        if not self._registered_with_atexit:
            import atexit
            atexit.register(self._exitfunc)
            finalize._registered_with_atexit = True
        info = self._Info()
        info.weakref = ref(obj, self)
        info.func = func
        info.args = args
        info.kwargs = kwargs or None
        info.atexit = True
        info.index = next(self._index_iter)
        self._registry[self] = info
        finalize._dirty = True

    def __call__(self, _=None):
        info = self._registry.pop(self, None)
        if info and not self._shutdown:
            return info.func(*info.args, **info.kwargs or {})

    def detach(self):
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is not None and self._registry.pop(self, None):
            return (obj, info.func, info.args, info.kwargs or {})

    def peek(self):
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is not None:
            return (obj, info.func, info.args, info.kwargs or {})

    @property
    def alive(self):
        return self in self._registry

    @property
    def atexit(self):
        info = self._registry.get(self)
        return bool(info) and info.atexit

    @atexit.setter
    def atexit(self, value):
        info = self._registry.get(self)
        if info:
            info.atexit = bool(value)

    def __repr__(self):
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is None:
            return '<%s object at %#x; dead>' % (type(self).__name__, id(self))
        else:
            return '<%s object at %#x; for %r at %#x>' % (type(self).__name__, id(self), type(obj).__name__, id(obj))

    @classmethod
    def _select_for_exit(cls):
        L = [(f, i) for (f, i) in cls._registry.items() if i.atexit]
        L.sort(key=lambda item: item[1].index)
        return [f for (f, i) in L]

    @classmethod
    def _exitfunc(cls):
        reenable_gc = False
        try:
            if cls._registry:
                import gc
                if gc.isenabled():
                    reenable_gc = True
                    gc.disable()
                pending = None
                while True:
                    if pending is None or finalize._dirty:
                        pending = cls._select_for_exit()
                        finalize._dirty = False
                    if not pending:
                        break
                    f = pending.pop()
                    try:
                        f()
                    except Exception:
                        sys.excepthook(*sys.exc_info())
        finally:
            finalize._shutdown = True
            if reenable_gc:
                gc.enable()
