__all__ = ['deque', 'defaultdict', 'namedtuple', 'UserDict', 'UserList', 'UserString', 'Counter', 'OrderedDict', 'ChainMap']import _collections_abcfrom operator import itemgetter as _itemgetter, eq as _eqfrom keyword import iskeyword as _iskeywordimport sys as _sysimport heapq as _heapqfrom _weakref import proxy as _proxyfrom itertools import repeat as _repeat, chain as _chain, starmap as _starmapfrom reprlib import recursive_repr as _recursive_reprtry:
    from _collections import deque
except ImportError:
    pass_collections_abc.MutableSequence.register(deque)try:
    from _collections import defaultdict
except ImportError:
    pass
def __getattr__(name):
    if name in _collections_abc.__all__:
        obj = getattr(_collections_abc, name)
        import warnings
        warnings.warn("Using or importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated, and in 3.8 it will stop working", DeprecationWarning, stacklevel=2)
        globals()[name] = obj
        return obj
    raise AttributeError(f'module {__name__} has no attribute {name}')

class _OrderedDictKeysView(_collections_abc.KeysView):

    def __reversed__(self):
        yield from reversed(self._mapping)

class _OrderedDictItemsView(_collections_abc.ItemsView):

    def __reversed__(self):
        for key in reversed(self._mapping):
            yield (key, self._mapping[key])

class _OrderedDictValuesView(_collections_abc.ValuesView):

    def __reversed__(self):
        for key in reversed(self._mapping):
            yield self._mapping[key]

class _Link(object):
    __slots__ = ('prev', 'next', 'key', '__weakref__')

class OrderedDict(dict):

    def __init__(*args, **kwds):
        if not args:
            raise TypeError("descriptor '__init__' of 'OrderedDict' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self._OrderedDict__root
        except AttributeError:
            self._OrderedDict__hardroot = _Link()
            self._OrderedDict__root = root = _proxy(self._OrderedDict__hardroot)
            root.prev = root.next = root
            self._OrderedDict__map = {}
        self._OrderedDict__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__, proxy=_proxy, Link=_Link):
        if key not in self:
            self._OrderedDict__map[key] = link = Link()
            root = self._OrderedDict__root
            last = root.prev
            link.prev = last
            link.next = root
            link.key = key
            last.next = link
            root.prev = proxy(link)
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        dict_delitem(self, key)
        link = self._OrderedDict__map.pop(key)
        link_prev = link.prev
        link_next = link.next
        link_prev.next = link_next
        link_next.prev = link_prev
        link.prev = None
        link.next = None

    def __iter__(self):
        root = self._OrderedDict__root
        curr = root.next
        while curr is not root:
            yield curr.key
            curr = curr.next

    def __reversed__(self):
        root = self._OrderedDict__root
        curr = root.prev
        while curr is not root:
            yield curr.key
            curr = curr.prev

    def clear(self):
        root = self._OrderedDict__root
        root.prev = root.next = root
        self._OrderedDict__map.clear()
        dict.clear(self)

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        root = self._OrderedDict__root
        if last:
            link = root.prev
            link_prev = link.prev
            link_prev.next = root
            root.prev = link_prev
        else:
            link = root.next
            link_next = link.next
            root.next = link_next
            link_next.prev = root
        key = link.key
        del self._OrderedDict__map[key]
        value = dict.pop(self, key)
        return (key, value)

    def move_to_end(self, key, last=True):
        link = self._OrderedDict__map[key]
        link_prev = link.prev
        link_next = link.next
        soft_link = link_next.prev
        link_prev.next = link_next
        link_next.prev = link_prev
        root = self._OrderedDict__root
        if last:
            last = root.prev
            link.prev = last
            link.next = root
            root.prev = soft_link
            last.next = link
        else:
            first = root.next
            link.prev = root
            link.next = first
            first.prev = soft_link
            root.next = link

    def __sizeof__(self):
        sizeof = _sys.getsizeof
        n = len(self) + 1
        size = sizeof(self.__dict__)
        size += sizeof(self._OrderedDict__map)*2
        size += sizeof(self._OrderedDict__hardroot)*n
        size += sizeof(self._OrderedDict__root)*n
        return size

    update = _OrderedDict__update = _collections_abc.MutableMapping.update

    def keys(self):
        return _OrderedDictKeysView(self)

    def items(self):
        return _OrderedDictItemsView(self)

    def values(self):
        return _OrderedDictValuesView(self)

    __ne__ = _collections_abc.MutableMapping.__ne__
    _OrderedDict__marker = object()

    def pop(self, key, default=_OrderedDict__marker):
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self._OrderedDict__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return default

    @_recursive_repr()
    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self.items()))

    def __reduce__(self):
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        return (self.__class__, (), inst_dict or None, None, iter(self.items()))

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        self = cls()
        for key in iterable:
            self[key] = value
        return self

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return dict.__eq__(self, other) and all(map(_eq, self, other))
        return dict.__eq__(self, other)
try:
    from _collections import OrderedDict
except ImportError:
    pass_nt_itemgetters = {}
def namedtuple(typename, field_names, *, rename=False, defaults=None, module=None):
    if isinstance(field_names, str):
        field_names = field_names.replace(',', ' ').split()
    field_names = list(map(str, field_names))
    typename = _sys.intern(str(typename))
    if rename:
        seen = set()
        for (index, name) in enumerate(field_names):
            if name.isidentifier() and (_iskeyword(name) or name.startswith('_') or name in seen):
                field_names[index] = f'_{index}'
            seen.add(name)
    for name in [typename] + field_names:
        if type(name) is not str:
            raise TypeError('Type names and field names must be strings')
        if not name.isidentifier():
            raise ValueError(f'Type names and field names must be valid identifiers: {name}')
        if _iskeyword(name):
            raise ValueError(f'Type names and field names cannot be a keyword: {name}')
    seen = set()
    for name in field_names:
        if name.startswith('_') and not rename:
            raise ValueError(f'Field names cannot start with an underscore: {name}')
        if name in seen:
            raise ValueError(f'Encountered duplicate field name: {name}')
        seen.add(name)
    field_defaults = {}
    if defaults is not None:
        defaults = tuple(defaults)
        if len(defaults) > len(field_names):
            raise TypeError('Got more default values than field names')
        field_defaults = dict(reversed(list(zip(reversed(field_names), reversed(defaults)))))
    field_names = tuple(map(_sys.intern, field_names))
    num_fields = len(field_names)
    arg_list = repr(field_names).replace("'", '')[1:-1]
    repr_fmt = '(' + ', '.join(f'{name}=%r' for name in field_names) + ')'
    tuple_new = tuple.__new__
    _len = len
    s = f'def __new__(_cls, {arg_list}): return _tuple_new(_cls, ({arg_list}))'
    namespace = {'_tuple_new': tuple_new, '__name__': f'namedtuple_{typename}'}
    exec(s, namespace)
    __new__ = namespace['__new__']
    __new__.__doc__ = f'Create new instance of {typename}({arg_list})'
    if defaults is not None:
        __new__.__defaults__ = defaults

    @classmethod
    def _make(cls, iterable):
        result = tuple_new(cls, iterable)
        if _len(result) != num_fields:
            raise TypeError(f'Expected {num_fields} arguments, got {len(result)}')
        return result

    _make.__func__.__doc__ = f'Make a new {typename} object from a sequence or iterable'

    def _replace(_self, **kwds):
        result = _self._make(map(kwds.pop, field_names, _self))
        if kwds:
            raise ValueError(f'Got unexpected field names: {list(kwds)}')
        return result

    _replace.__doc__ = f'Return a new {typename} object replacing specified fields with new values'

    def __repr__(self):
        return self.__class__.__name__ + repr_fmt % self

    def _asdict(self):
        return OrderedDict(zip(self._fields, self))

    def __getnewargs__(self):
        return tuple(self)

    for method in (__new__, _make.__func__, _replace, __repr__, _asdict, __getnewargs__):
        method.__qualname__ = f'{typename}.{method.__name__}'
    class_namespace = {'__doc__': f'{typename}({arg_list})', '__slots__': (), '_fields': field_names, '_fields_defaults': field_defaults, '__new__': __new__, '_make': _make, '_replace': _replace, '__repr__': __repr__, '_asdict': _asdict, '__getnewargs__': __getnewargs__}
    cache = _nt_itemgetters
    for (index, name) in enumerate(field_names):
        try:
            (itemgetter_object, doc) = cache[index]
        except KeyError:
            itemgetter_object = _itemgetter(index)
            doc = f'Alias for field number {index}'
            cache[index] = (itemgetter_object, doc)
        class_namespace[name] = property(itemgetter_object, doc=doc)
    result = type(typename, (tuple,), class_namespace)
    if module is None:
        try:
            module = _sys._getframe(1).f_globals.get('__name__', '__main__')
        except (AttributeError, ValueError):
            pass
    if module is not None:
        result.__module__ = module
    return result

def _count_elements(mapping, iterable):
    mapping_get = mapping.get
    for elem in iterable:
        mapping[elem] = mapping_get(elem, 0) + 1
try:
    from _collections import _count_elements
except ImportError:
    pass
class Counter(dict):

    def __init__(*args, **kwds):
        if not args:
            raise TypeError("descriptor '__init__' of 'Counter' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        super(Counter, self).__init__()
        self.update(*args, **kwds)

    def __missing__(self, key):
        return 0

    def most_common(self, n=None):
        if n is None:
            return sorted(self.items(), key=_itemgetter(1), reverse=True)
        return _heapq.nlargest(n, self.items(), key=_itemgetter(1))

    def elements(self):
        return _chain.from_iterable(_starmap(_repeat, self.items()))

    @classmethod
    def fromkeys(cls, iterable, v=None):
        raise NotImplementedError('Counter.fromkeys() is undefined.  Use Counter(iterable) instead.')

    def update(*args, **kwds):
        if not args:
            raise TypeError("descriptor 'update' of 'Counter' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        iterable = args[0] if args else None
        if iterable is not None:
            if isinstance(iterable, _collections_abc.Mapping):
                if self:
                    self_get = self.get
                    for (elem, count) in iterable.items():
                        self[elem] = count + self_get(elem, 0)
                else:
                    super(Counter, self).update(iterable)
            else:
                _count_elements(self, iterable)
        if kwds:
            self.update(kwds)

    def subtract(*args, **kwds):
        if not args:
            raise TypeError("descriptor 'subtract' of 'Counter' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        iterable = args[0] if args else None
        if iterable is not None:
            self_get = self.get
            if isinstance(iterable, _collections_abc.Mapping):
                for (elem, count) in iterable.items():
                    self[elem] = self_get(elem, 0) - count
            else:
                for elem in iterable:
                    self[elem] = self_get(elem, 0) - 1
        if kwds:
            self.subtract(kwds)

    def copy(self):
        return self.__class__(self)

    def __reduce__(self):
        return (self.__class__, (dict(self),))

    def __delitem__(self, elem):
        if elem in self:
            super().__delitem__(elem)

    def __repr__(self):
        if not self:
            return '%s()' % self.__class__.__name__
        try:
            items = ', '.join(map('%r: %r'.__mod__, self.most_common()))
            return '%s({%s})' % (self.__class__.__name__, items)
        except TypeError:
            return '{0}({1!r})'.format(self.__class__.__name__, dict(self))

    def __add__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            newcount = count + other[elem]
            if newcount > 0:
                result[elem] = newcount
        for (elem, count) in other.items():
            if elem not in self and count > 0:
                result[elem] = count
        return result

    def __sub__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            newcount = count - other[elem]
            if newcount > 0:
                result[elem] = newcount
        for (elem, count) in other.items():
            if elem not in self and count < 0:
                result[elem] = 0 - count
        return result

    def __or__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            other_count = other[elem]
            newcount = other_count if count < other_count else count
            if newcount > 0:
                result[elem] = newcount
        for (elem, count) in other.items():
            if elem not in self and count > 0:
                result[elem] = count
        return result

    def __and__(self, other):
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            other_count = other[elem]
            newcount = count if count < other_count else other_count
            if newcount > 0:
                result[elem] = newcount
        return result

    def __pos__(self):
        result = Counter()
        for (elem, count) in self.items():
            if count > 0:
                result[elem] = count
        return result

    def __neg__(self):
        result = Counter()
        for (elem, count) in self.items():
            if count < 0:
                result[elem] = 0 - count
        return result

    def _keep_positive(self):
        nonpositive = [elem for (elem, count) in self.items() if not count > 0]
        for elem in nonpositive:
            del self[elem]
        return self

    def __iadd__(self, other):
        for (elem, count) in other.items():
            self[elem] += count
        return self._keep_positive()

    def __isub__(self, other):
        for (elem, count) in other.items():
            self[elem] -= count
        return self._keep_positive()

    def __ior__(self, other):
        for (elem, other_count) in other.items():
            count = self[elem]
            if other_count > count:
                self[elem] = other_count
        return self._keep_positive()

    def __iand__(self, other):
        for (elem, count) in self.items():
            other_count = other[elem]
            if other_count < count:
                self[elem] = other_count
        return self._keep_positive()

class ChainMap(_collections_abc.MutableMapping):

    def __init__(self, *maps):
        self.maps = list(maps) or [{}]

    def __missing__(self, key):
        raise KeyError(key)

    def __getitem__(self, key):
        for mapping in self.maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        return self.__missing__(key)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def __len__(self):
        return len(set().union(*self.maps))

    def __iter__(self):
        d = {}
        for mapping in reversed(self.maps):
            d.update(mapping)
        return iter(d)

    def __contains__(self, key):
        return any(key in m for m in self.maps)

    def __bool__(self):
        return any(self.maps)

    @_recursive_repr()
    def __repr__(self):
        return '{0.__class__.__name__}({1})'.format(self, ', '.join(map(repr, self.maps)))

    @classmethod
    def fromkeys(cls, iterable, *args):
        return cls(dict.fromkeys(iterable, *args))

    def copy(self):
        return self.__class__(self.maps[0].copy(), self.maps[1:])

    __copy__ = copy

    def new_child(self, m=None):
        if m is None:
            m = {}
        return self.__class__(m, self.maps)

    @property
    def parents(self):
        return self.__class__(*self.maps[1:])

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError('Key not found in the first mapping: {!r}'.format(key))

    def popitem(self):
        try:
            return self.maps[0].popitem()
        except KeyError:
            raise KeyError('No keys found in the first mapping.')

    def pop(self, key, *args):
        try:
            return self.maps[0].pop(key, *args)
        except KeyError:
            raise KeyError('Key not found in the first mapping: {!r}'.format(key))

    def clear(self):
        self.maps[0].clear()

class UserDict(_collections_abc.MutableMapping):

    def __init__(*args, **kwargs):
        if not args:
            raise TypeError("descriptor '__init__' of 'UserDict' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        if args:
            dict = args[0]
        elif 'dict' in kwargs:
            dict = kwargs.pop('dict')
            import warnings
            warnings.warn("Passing 'dict' as keyword argument is deprecated", DeprecationWarning, stacklevel=2)
        else:
            dict = None
        self.data = {}
        if dict is not None:
            self.update(dict)
        if len(kwargs):
            self.update(kwargs)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, '__missing__'):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)

    def __setitem__(self, key, item):
        self.data[key] = item

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, key):
        return key in self.data

    def __repr__(self):
        return repr(self.data)

    def copy(self):
        if self.__class__ is UserDict:
            return UserDict(self.data.copy())
        import copy
        data = self.data
        try:
            self.data = {}
            c = copy.copy(self)
        finally:
            self.data = data
        c.update(self)
        return c

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

class UserList(_collections_abc.MutableSequence):

    def __init__(self, initlist=None):
        self.data = []
        if initlist is not None:
            if type(initlist) == type(self.data):
                self.data[:] = initlist
            elif isinstance(initlist, UserList):
                self.data[:] = initlist.data[:]
            else:
                self.data = list(initlist)

    def __repr__(self):
        return repr(self.data)

    def __lt__(self, other):
        return self.data < self._UserList__cast(other)

    def __le__(self, other):
        return self.data <= self._UserList__cast(other)

    def __eq__(self, other):
        return self.data == self._UserList__cast(other)

    def __gt__(self, other):
        return self.data > self._UserList__cast(other)

    def __ge__(self, other):
        return self.data >= self._UserList__cast(other)

    def __cast(self, other):
        if isinstance(other, UserList):
            return other.data
        return other

    def __contains__(self, item):
        return item in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, item):
        self.data[i] = item

    def __delitem__(self, i):
        del self.data[i]

    def __add__(self, other):
        if isinstance(other, UserList):
            return self.__class__(self.data + other.data)
        if isinstance(other, type(self.data)):
            return self.__class__(self.data + other)
        return self.__class__(self.data + list(other))

    def __radd__(self, other):
        if isinstance(other, UserList):
            return self.__class__(other.data + self.data)
        if isinstance(other, type(self.data)):
            return self.__class__(other + self.data)
        return self.__class__(list(other) + self.data)

    def __iadd__(self, other):
        if isinstance(other, UserList):
            self.data += other.data
        elif isinstance(other, type(self.data)):
            self.data += other
        else:
            self.data += list(other)
        return self

    def __mul__(self, n):
        return self.__class__(self.data*n)

    __rmul__ = __mul__

    def __imul__(self, n):
        self.data *= n
        return self

    def append(self, item):
        self.data.append(item)

    def insert(self, i, item):
        self.data.insert(i, item)

    def pop(self, i=-1):
        return self.data.pop(i)

    def remove(self, item):
        self.data.remove(item)

    def clear(self):
        self.data.clear()

    def copy(self):
        return self.__class__(self)

    def count(self, item):
        return self.data.count(item)

    def index(self, item, *args):
        return self.data.index(item, *args)

    def reverse(self):
        self.data.reverse()

    def sort(self, *args, **kwds):
        self.data.sort(*args, **kwds)

    def extend(self, other):
        if isinstance(other, UserList):
            self.data.extend(other.data)
        else:
            self.data.extend(other)

class UserString(_collections_abc.Sequence):

    def __init__(self, seq):
        if isinstance(seq, str):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)

    def __int__(self):
        return int(self.data)

    def __float__(self):
        return float(self.data)

    def __complex__(self):
        return complex(self.data)

    def __hash__(self):
        return hash(self.data)

    def __getnewargs__(self):
        return (self.data[:],)

    def __eq__(self, string):
        if isinstance(string, UserString):
            return self.data == string.data
        return self.data == string

    def __lt__(self, string):
        if isinstance(string, UserString):
            return self.data < string.data
        return self.data < string

    def __le__(self, string):
        if isinstance(string, UserString):
            return self.data <= string.data
        return self.data <= string

    def __gt__(self, string):
        if isinstance(string, UserString):
            return self.data > string.data
        return self.data > string

    def __ge__(self, string):
        if isinstance(string, UserString):
            return self.data >= string.data
        return self.data >= string

    def __contains__(self, char):
        if isinstance(char, UserString):
            char = char.data
        return char in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.__class__(self.data[index])

    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__(self.data + other.data)
        if isinstance(other, str):
            return self.__class__(self.data + other)
        return self.__class__(self.data + str(other))

    def __radd__(self, other):
        if isinstance(other, str):
            return self.__class__(other + self.data)
        return self.__class__(str(other) + self.data)

    def __mul__(self, n):
        return self.__class__(self.data*n)

    __rmul__ = __mul__

    def __mod__(self, args):
        return self.__class__(self.data % args)

    def __rmod__(self, format):
        return self.__class__(format % args)

    def capitalize(self):
        return self.__class__(self.data.capitalize())

    def casefold(self):
        return self.__class__(self.data.casefold())

    def center(self, width, *args):
        return self.__class__(self.data.center(width, *args))

    def count(self, sub, start=0, end=_sys.maxsize):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.count(sub, start, end)

    def encode(self, encoding=None, errors=None):
        if encoding:
            if errors:
                return self.__class__(self.data.encode(encoding, errors))
            return self.__class__(self.data.encode(encoding))
        return self.__class__(self.data.encode())

    def endswith(self, suffix, start=0, end=_sys.maxsize):
        return self.data.endswith(suffix, start, end)

    def expandtabs(self, tabsize=8):
        return self.__class__(self.data.expandtabs(tabsize))

    def find(self, sub, start=0, end=_sys.maxsize):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.find(sub, start, end)

    def format(self, *args, **kwds):
        return self.data.format(*args, **kwds)

    def format_map(self, mapping):
        return self.data.format_map(mapping)

    def index(self, sub, start=0, end=_sys.maxsize):
        return self.data.index(sub, start, end)

    def isalpha(self):
        return self.data.isalpha()

    def isalnum(self):
        return self.data.isalnum()

    def isascii(self):
        return self.data.isascii()

    def isdecimal(self):
        return self.data.isdecimal()

    def isdigit(self):
        return self.data.isdigit()

    def isidentifier(self):
        return self.data.isidentifier()

    def islower(self):
        return self.data.islower()

    def isnumeric(self):
        return self.data.isnumeric()

    def isprintable(self):
        return self.data.isprintable()

    def isspace(self):
        return self.data.isspace()

    def istitle(self):
        return self.data.istitle()

    def isupper(self):
        return self.data.isupper()

    def join(self, seq):
        return self.data.join(seq)

    def ljust(self, width, *args):
        return self.__class__(self.data.ljust(width, *args))

    def lower(self):
        return self.__class__(self.data.lower())

    def lstrip(self, chars=None):
        return self.__class__(self.data.lstrip(chars))

    maketrans = str.maketrans

    def partition(self, sep):
        return self.data.partition(sep)

    def replace(self, old, new, maxsplit=-1):
        if isinstance(old, UserString):
            old = old.data
        if isinstance(new, UserString):
            new = new.data
        return self.__class__(self.data.replace(old, new, maxsplit))

    def rfind(self, sub, start=0, end=_sys.maxsize):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.rfind(sub, start, end)

    def rindex(self, sub, start=0, end=_sys.maxsize):
        return self.data.rindex(sub, start, end)

    def rjust(self, width, *args):
        return self.__class__(self.data.rjust(width, *args))

    def rpartition(self, sep):
        return self.data.rpartition(sep)

    def rstrip(self, chars=None):
        return self.__class__(self.data.rstrip(chars))

    def split(self, sep=None, maxsplit=-1):
        return self.data.split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=-1):
        return self.data.rsplit(sep, maxsplit)

    def splitlines(self, keepends=False):
        return self.data.splitlines(keepends)

    def startswith(self, prefix, start=0, end=_sys.maxsize):
        return self.data.startswith(prefix, start, end)

    def strip(self, chars=None):
        return self.__class__(self.data.strip(chars))

    def swapcase(self):
        return self.__class__(self.data.swapcase())

    def title(self):
        return self.__class__(self.data.title())

    def translate(self, *args):
        return self.__class__(self.data.translate(*args))

    def upper(self):
        return self.__class__(self.data.upper())

    def zfill(self, width):
        return self.__class__(self.data.zfill(width))
