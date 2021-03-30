__all__ = ['update_wrapper', 'wraps', 'WRAPPER_ASSIGNMENTS', 'WRAPPER_UPDATES', 'total_ordering', 'cmp_to_key', 'lru_cache', 'reduce', 'partial', 'partialmethod', 'singledispatch']try:
    from _functools import reduce
except ImportError:
    passfrom abc import get_cache_tokenfrom collections import namedtuplefrom reprlib import recursive_reprfrom _thread import RLockWRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__', '__annotations__')WRAPPER_UPDATES = ('__dict__',)
def update_wrapper(wrapper, wrapped, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES):
    for attr in assigned:
        try:
            value = getattr(wrapped, attr)
        except AttributeError:
            pass
        setattr(wrapper, attr, value)
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    wrapper.__wrapped__ = wrapped
    return wrapper

def wraps(wrapped, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES):
    return partial(update_wrapper, wrapped=wrapped, assigned=assigned, updated=updated)

def _gt_from_lt(self, other, NotImplemented=NotImplemented):
    op_result = self.__lt__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result and self != other

def _le_from_lt(self, other, NotImplemented=NotImplemented):
    op_result = self.__lt__(other)
    return op_result or self == other

def _ge_from_lt(self, other, NotImplemented=NotImplemented):
    op_result = self.__lt__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result

def _ge_from_le(self, other, NotImplemented=NotImplemented):
    op_result = self.__le__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result or self == other

def _lt_from_le(self, other, NotImplemented=NotImplemented):
    op_result = self.__le__(other)
    if op_result is NotImplemented:
        return op_result
    return op_result and self != other

def _gt_from_le(self, other, NotImplemented=NotImplemented):
    op_result = self.__le__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result

def _lt_from_gt(self, other, NotImplemented=NotImplemented):
    op_result = self.__gt__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result and self != other

def _ge_from_gt(self, other, NotImplemented=NotImplemented):
    op_result = self.__gt__(other)
    return op_result or self == other

def _le_from_gt(self, other, NotImplemented=NotImplemented):
    op_result = self.__gt__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result

def _le_from_ge(self, other, NotImplemented=NotImplemented):
    op_result = self.__ge__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result or self == other

def _gt_from_ge(self, other, NotImplemented=NotImplemented):
    op_result = self.__ge__(other)
    if op_result is NotImplemented:
        return op_result
    return op_result and self != other

def _lt_from_ge(self, other, NotImplemented=NotImplemented):
    op_result = self.__ge__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result
_convert = {'__lt__': [('__gt__', _gt_from_lt), ('__le__', _le_from_lt), ('__ge__', _ge_from_lt)], '__le__': [('__ge__', _ge_from_le), ('__lt__', _lt_from_le), ('__gt__', _gt_from_le)], '__gt__': [('__lt__', _lt_from_gt), ('__ge__', _ge_from_gt), ('__le__', _le_from_gt)], '__ge__': [('__le__', _le_from_ge), ('__gt__', _gt_from_ge), ('__lt__', _lt_from_ge)]}
def total_ordering(cls):
    roots = {op for op in _convert if getattr(cls, op, None) is not getattr(object, op, None)}
    if not roots:
        raise ValueError('must define at least one ordering operation: < > <= >=')
    root = max(roots)
    for (opname, opfunc) in _convert[root]:
        if opname not in roots:
            opfunc.__name__ = opname
            setattr(cls, opname, opfunc)
    return cls

def cmp_to_key(mycmp):

    class K(object):
        __slots__ = ['obj']

        def __init__(self, obj):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        __hash__ = None

    return K
try:
    from _functools import cmp_to_key
except ImportError:
    pass
class partial:
    __slots__ = ('func', 'args', 'keywords', '__dict__', '__weakref__')

    def __new__(*args, **keywords):
        if not args:
            raise TypeError("descriptor '__new__' of partial needs an argument")
        if len(args) < 2:
            raise TypeError("type 'partial' takes at least one argument")
        (cls, func, *args) = args
        if not callable(func):
            raise TypeError('the first argument must be callable')
        args = tuple(args)
        if hasattr(func, 'func'):
            args = func.args + args
            tmpkw = func.keywords.copy()
            tmpkw.update(keywords)
            keywords = tmpkw
            del tmpkw
            func = func.func
        self = super(partial, cls).__new__(cls)
        self.func = func
        self.args = args
        self.keywords = keywords
        return self

    def __call__(*args, **keywords):
        if not args:
            raise TypeError("descriptor '__call__' of partial needs an argument")
        (self, *args) = args
        newkeywords = self.keywords.copy()
        newkeywords.update(keywords)
        return self.func(self.args, *args, **newkeywords)

    @recursive_repr()
    def __repr__(self):
        qualname = type(self).__qualname__
        args = [repr(self.func)]
        args.extend(repr(x) for x in self.args)
        args.extend(f'{k}={v}' for (k, v) in self.keywords.items())
        if type(self).__module__ == 'functools':
            return f'functools.{qualname}({', '.join(args)})'
        return f'{qualname}({', '.join(args)})'

    def __reduce__(self):
        return (type(self), (self.func,), (self.func, self.args, self.keywords or None, self.__dict__ or None))

    def __setstate__(self, state):
        if not isinstance(state, tuple):
            raise TypeError('argument to __setstate__ must be a tuple')
        if len(state) != 4:
            raise TypeError(f'expected 4 items in state, got {len(state)}')
        (func, args, kwds, namespace) = state
        if callable(func) and (isinstance(args, tuple) and (kwds is not None and isinstance(kwds, dict) and namespace is not None)) and not isinstance(namespace, dict):
            raise TypeError('invalid partial state')
        args = tuple(args)
        if kwds is None:
            kwds = {}
        elif type(kwds) is not dict:
            kwds = dict(kwds)
        if namespace is None:
            namespace = {}
        self.__dict__ = namespace
        self.func = func
        self.args = args
        self.keywords = kwds
try:
    from _functools import partial
except ImportError:
    pass
class partialmethod(object):

    def __init__(self, func, *args, **keywords):
        if callable(func) or not hasattr(func, '__get__'):
            raise TypeError('{!r} is not callable or a descriptor'.format(func))
        if isinstance(func, partialmethod):
            self.func = func.func
            self.args = func.args + args
            self.keywords = func.keywords.copy()
            self.keywords.update(keywords)
        else:
            self.func = func
            self.args = args
            self.keywords = keywords

    def __repr__(self):
        args = ', '.join(map(repr, self.args))
        keywords = ', '.join('{}={!r}'.format(k, v) for (k, v) in self.keywords.items())
        format_string = '{module}.{cls}({func}, {args}, {keywords})'
        return format_string.format(module=self.__class__.__module__, cls=self.__class__.__qualname__, func=self.func, args=args, keywords=keywords)

    def _make_unbound_method(self):

        def _method(*args, **keywords):
            call_keywords = self.keywords.copy()
            call_keywords.update(keywords)
            (cls_or_self, *rest) = args
            call_args = (cls_or_self,) + self.args + tuple(rest)
            return self.func(*call_args, **call_keywords)

        _method.__isabstractmethod__ = self.__isabstractmethod__
        _method._partialmethod = self
        return _method

    def __get__(self, obj, cls):
        get = getattr(self.func, '__get__', None)
        result = None
        if get is not None:
            new_func = get(obj, cls)
            if new_func is not self.func:
                result = partial(new_func, self.args, **self.keywords)
                try:
                    result.__self__ = new_func.__self__
                except AttributeError:
                    pass
        if result is None:
            result = self._make_unbound_method().__get__(obj, cls)
        return result

    @property
    def __isabstractmethod__(self):
        return getattr(self.func, '__isabstractmethod__', False)
_CacheInfo = namedtuple('CacheInfo', ['hits', 'misses', 'maxsize', 'currsize'])
class _HashedSeq(list):
    __slots__ = 'hashvalue'

    def __init__(self, tup, hash=hash):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue

def _make_key(args, kwds, typed, kwd_mark=(object(),), fasttypes={int, str, frozenset, type(None)}, tuple=tuple, type=type, len=len):
    key = args
    if kwds:
        key += kwd_mark
        for item in kwds.items():
            key += item
    if typed:
        key += tuple(type(v) for v in args)
        if kwds:
            key += tuple(type(v) for v in kwds.values())
    elif len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return _HashedSeq(key)

def lru_cache(maxsize=128, typed=False):
    if maxsize is not None and not isinstance(maxsize, int):
        raise TypeError('Expected maxsize to be an integer or None')

    def decorating_function(user_function):
        wrapper = _lru_cache_wrapper(user_function, maxsize, typed, _CacheInfo)
        return update_wrapper(wrapper, user_function)

    return decorating_function

def _lru_cache_wrapper(user_function, maxsize, typed, _CacheInfo):
    sentinel = object()
    make_key = _make_key
    (PREV, NEXT, KEY, RESULT) = (0, 1, 2, 3)
    cache = {}
    hits = misses = 0
    full = False
    cache_get = cache.get
    cache_len = cache.__len__
    lock = RLock()
    root = []
    root[:] = [root, root, None, None]
    if maxsize == 0:

        def wrapper(*args, **kwds):
            nonlocal misses
            result = user_function(*args, **kwds)
            misses += 1
            return result

    elif maxsize is None:

        def wrapper(*args, **kwds):
            nonlocal hits, misses
            key = make_key(args, kwds, typed)
            result = cache_get(key, sentinel)
            if result is not sentinel:
                hits += 1
                return result
            result = user_function(*args, **kwds)
            cache[key] = result
            misses += 1
            return result

    else:

        def wrapper(*args, **kwds):
            nonlocal hits, root, full, misses
            key = make_key(args, kwds, typed)
            with lock:
                link = cache_get(key)
                if link is not None:
                    (link_prev, link_next, _key, result) = link
                    link_prev[NEXT] = link_next
                    link_next[PREV] = link_prev
                    last = root[PREV]
                    last[NEXT] = root[PREV] = link
                    link[PREV] = last
                    link[NEXT] = root
                    hits += 1
                    return result
            result = user_function(*args, **kwds)
            with lock:
                if key in cache:
                    pass
                elif full:
                    oldroot = root
                    oldroot[KEY] = key
                    oldroot[RESULT] = result
                    root = oldroot[NEXT]
                    oldkey = root[KEY]
                    oldresult = root[RESULT]
                    root[KEY] = root[RESULT] = None
                    del cache[oldkey]
                    cache[key] = oldroot
                else:
                    last = root[PREV]
                    link = [last, root, key, result]
                    last[NEXT] = root[PREV] = cache[key] = link
                    full = cache_len() >= maxsize
                misses += 1
            return result

    def cache_info():
        with lock:
            return _CacheInfo(hits, misses, maxsize, cache_len())

    def cache_clear():
        nonlocal hits, misses, full
        with lock:
            cache.clear()
            root[:] = [root, root, None, None]
            hits = misses = 0
            full = False

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper
try:
    from _functools import _lru_cache_wrapper
except ImportError:
    pass
def _c3_merge(sequences):
    result = []
    sequences = [s for s in sequences if s]
    if not sequences:
        return result
    for s1 in sequences:
        candidate = s1[0]
        for s2 in sequences:
            if candidate in s2[1:]:
                candidate = None
                break
        break
    if candidate is None:
        raise RuntimeError('Inconsistent hierarchy')
    result.append(candidate)
    for seq in sequences:
        if seq[0] == candidate:
            del seq[0]

def _c3_mro(cls, abcs=None):
    for (i, base) in enumerate(reversed(cls.__bases__)):
        if hasattr(base, '__abstractmethods__'):
            boundary = len(cls.__bases__) - i
            break
    boundary = 0
    abcs = list(abcs) if abcs else []
    explicit_bases = list(cls.__bases__[:boundary])
    abstract_bases = []
    other_bases = list(cls.__bases__[boundary:])
    for base in abcs:
        if issubclass(cls, base) and not any(issubclass(b, base) for b in cls.__bases__):
            abstract_bases.append(base)
    for base in abstract_bases:
        abcs.remove(base)
    explicit_c3_mros = [_c3_mro(base, abcs=abcs) for base in explicit_bases]
    abstract_c3_mros = [_c3_mro(base, abcs=abcs) for base in abstract_bases]
    other_c3_mros = [_c3_mro(base, abcs=abcs) for base in other_bases]
    return _c3_merge([[cls]] + explicit_c3_mros + abstract_c3_mros + other_c3_mros + [explicit_bases] + [abstract_bases] + [other_bases])

def _compose_mro(cls, types):
    bases = set(cls.__mro__)

    def is_related(typ):
        return typ not in bases and (hasattr(typ, '__mro__') and issubclass(cls, typ))

    types = [n for n in types if is_related(n)]

    def is_strict_base(typ):
        for other in types:
            if typ != other and typ in other.__mro__:
                return True
        return False

    types = [n for n in types if not is_strict_base(n)]
    type_set = set(types)
    mro = []
    for typ in types:
        found = []
        for sub in typ.__subclasses__():
            if sub not in bases and issubclass(cls, sub):
                found.append([s for s in sub.__mro__ if s in type_set])
        if not found:
            mro.append(typ)
        else:
            found.sort(key=len, reverse=True)
            for sub in found:
                for subcls in sub:
                    if subcls not in mro:
                        mro.append(subcls)
    return _c3_mro(cls, abcs=mro)

def _find_impl(cls, registry):
    mro = _compose_mro(cls, registry.keys())
    match = None
    for t in mro:
        if match is not None:
            if t in registry and (t not in cls.__mro__ and match not in cls.__mro__) and not issubclass(match, t):
                raise RuntimeError('Ambiguous dispatch: {} or {}'.format(match, t))
            break
        if t in registry:
            match = t
    return registry.get(match)

def singledispatch(func):
    import types
    import weakref
    registry = {}
    dispatch_cache = weakref.WeakKeyDictionary()
    cache_token = None

    def dispatch(cls):
        nonlocal cache_token
        if cache_token is not None:
            current_token = get_cache_token()
            if cache_token != current_token:
                dispatch_cache.clear()
                cache_token = current_token
        try:
            impl = dispatch_cache[cls]
        except KeyError:
            try:
                impl = registry[cls]
            except KeyError:
                impl = _find_impl(cls, registry)
            dispatch_cache[cls] = impl
        return impl

    def register(cls, func=None):
        nonlocal cache_token
        if func is None:
            if isinstance(cls, type):
                return lambda f: register(cls, f)
            ann = getattr(cls, '__annotations__', {})
            if not ann:
                raise TypeError(f'Invalid first argument to `register()`: {cls}. Use either `@register(some_class)` or plain `@register` on an annotated function.')
            func = cls
            from typing import get_type_hints
            (argname, cls) = next(iter(get_type_hints(func).items()))
        registry[cls] = func
        if hasattr(cls, '__abstractmethods__'):
            cache_token = get_cache_token()
        dispatch_cache.clear()
        return func

    def wrapper(*args, **kw):
        return dispatch(args[0].__class__)(*args, **kw)

    registry[object] = func
    wrapper.register = register
    wrapper.dispatch = dispatch
    wrapper.registry = types.MappingProxyType(registry)
    wrapper._clear_cache = dispatch_cache.clear
    update_wrapper(wrapper, func)
    return wrapper
