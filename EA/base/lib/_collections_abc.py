from abc import ABCMeta, abstractmethodimport sys__all__ = ['Awaitable', 'Coroutine', 'AsyncIterable', 'AsyncIterator', 'AsyncGenerator', 'Hashable', 'Iterable', 'Iterator', 'Generator', 'Reversible', 'Sized', 'Container', 'Callable', 'Collection', 'Set', 'MutableSet', 'Mapping', 'MutableMapping', 'MappingView', 'KeysView', 'ItemsView', 'ValuesView', 'Sequence', 'MutableSequence', 'ByteString']__name__ = 'collections.abc'bytes_iterator = type(iter(b''))bytearray_iterator = type(iter(bytearray()))dict_keyiterator = type(iter({}.keys()))dict_valueiterator = type(iter({}.values()))dict_itemiterator = type(iter({}.items()))list_iterator = type(iter([]))list_reverseiterator = type(iter(reversed([])))range_iterator = type(iter(range(0)))longrange_iterator = type(iter(range(1 << 1000)))set_iterator = type(iter(set()))str_iterator = type(iter(''))tuple_iterator = type(iter(()))zip_iterator = type(iter(zip()))dict_keys = type({}.keys())dict_values = type({}.values())dict_items = type({}.items())mappingproxy = type(type.__dict__)generator = type((lambda : yield None)())
async def _coro():
    pass
_coro = _coro()coroutine = type(_coro)_coro.close()del _coro
def _ag():
    yield None
_ag = _ag()async_generator = type(_ag)del _ag
def _check_methods(C, *methods):
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        return NotImplemented
    return True

class Hashable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __hash__(self):
        return 0

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Hashable:
            return _check_methods(C, '__hash__')
        return NotImplemented

class Awaitable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __await__(self):
        yield None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Awaitable:
            return _check_methods(C, '__await__')
        return NotImplemented

class Coroutine(Awaitable):
    __slots__ = ()

    @abstractmethod
    def send(self, value):
        raise StopIteration

    @abstractmethod
    def throw(self, typ, val=None, tb=None):
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    def close(self):
        try:
            self.throw(GeneratorExit)
        except (GeneratorExit, StopIteration):
            pass
        raise RuntimeError('coroutine ignored GeneratorExit')

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Coroutine:
            return _check_methods(C, '__await__', 'send', 'throw', 'close')
        return NotImplemented
Coroutine.register(coroutine)
class AsyncIterable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __aiter__(self):
        return AsyncIterator()

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncIterable:
            return _check_methods(C, '__aiter__')
        return NotImplemented

class AsyncIterator(AsyncIterable):
    __slots__ = ()

    @abstractmethod
    async def __anext__(self):
        raise StopAsyncIteration

    def __aiter__(self):
        return self

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncIterator:
            return _check_methods(C, '__anext__', '__aiter__')
        return NotImplemented

class AsyncGenerator(AsyncIterator):
    __slots__ = ()

    async def __anext__(self):
        yield await self.asend(None)

    @abstractmethod
    async def asend(self, value):
        raise StopAsyncIteration

    @abstractmethod
    async def athrow(self, typ, val=None, tb=None):
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    async def aclose(self):
        try:
            await self.athrow(GeneratorExit)
        except (GeneratorExit, StopAsyncIteration):
            pass
        raise RuntimeError('asynchronous generator ignored GeneratorExit')

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncGenerator:
            return _check_methods(C, '__aiter__', '__anext__', 'asend', 'athrow', 'aclose')
        return NotImplemented
AsyncGenerator.register(async_generator)
class Iterable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __iter__(self):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Iterable:
            return _check_methods(C, '__iter__')
        return NotImplemented

class Iterator(Iterable):
    __slots__ = ()

    @abstractmethod
    def __next__(self):
        raise StopIteration

    def __iter__(self):
        return self

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Iterator:
            return _check_methods(C, '__iter__', '__next__')
        return NotImplemented
Iterator.register(bytes_iterator)Iterator.register(bytearray_iterator)Iterator.register(dict_keyiterator)Iterator.register(dict_valueiterator)Iterator.register(dict_itemiterator)Iterator.register(list_iterator)Iterator.register(list_reverseiterator)Iterator.register(range_iterator)Iterator.register(longrange_iterator)Iterator.register(set_iterator)Iterator.register(str_iterator)Iterator.register(tuple_iterator)Iterator.register(zip_iterator)
class Reversible(Iterable):
    __slots__ = ()

    @abstractmethod
    def __reversed__(self):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Reversible:
            return _check_methods(C, '__reversed__', '__iter__')
        return NotImplemented

class Generator(Iterator):
    __slots__ = ()

    def __next__(self):
        return self.send(None)

    @abstractmethod
    def send(self, value):
        raise StopIteration

    @abstractmethod
    def throw(self, typ, val=None, tb=None):
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    def close(self):
        try:
            self.throw(GeneratorExit)
        except (GeneratorExit, StopIteration):
            pass
        raise RuntimeError('generator ignored GeneratorExit')

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Generator:
            return _check_methods(C, '__iter__', '__next__', 'send', 'throw', 'close')
        return NotImplemented
Generator.register(generator)
class Sized(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __len__(self):
        return 0

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Sized:
            return _check_methods(C, '__len__')
        return NotImplemented

class Container(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __contains__(self, x):
        return False

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Container:
            return _check_methods(C, '__contains__')
        return NotImplemented

class Collection(Sized, Iterable, Container):
    __slots__ = ()

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Collection:
            return _check_methods(C, '__len__', '__iter__', '__contains__')
        return NotImplemented

class Callable(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def __call__(self, *args, **kwds):
        return False

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Callable:
            return _check_methods(C, '__call__')
        return NotImplemented

class Set(Collection):
    __slots__ = ()

    def __le__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        if len(self) > len(other):
            return False
        for elem in self:
            if elem not in other:
                return False
        return True

    def __lt__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        return len(self) < len(other) and self.__le__(other)

    def __gt__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        return len(self) > len(other) and self.__ge__(other)

    def __ge__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        if len(self) < len(other):
            return False
        for elem in other:
            if elem not in self:
                return False
        return True

    def __eq__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        return len(self) == len(other) and self.__le__(other)

    @classmethod
    def _from_iterable(cls, it):
        return cls(it)

    def __and__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        return self._from_iterable(value for value in other if value in self)

    __rand__ = __and__

    def isdisjoint(self, other):
        for value in other:
            if value in self:
                return False
        return True

    def __or__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        chain = (e for s in (self, other) for e in s)
        return self._from_iterable(chain)

    __ror__ = __or__

    def __sub__(self, other):
        if not isinstance(other, Set):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = self._from_iterable(other)
        return self._from_iterable(value for value in self if value not in other)

    def __rsub__(self, other):
        if not isinstance(other, Set):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = self._from_iterable(other)
        return self._from_iterable(value for value in other if value not in self)

    def __xor__(self, other):
        if not isinstance(other, Set):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = self._from_iterable(other)
        return self - other | other - self

    __rxor__ = __xor__

    def _hash(self):
        MAX = sys.maxsize
        MASK = 2*MAX + 1
        n = len(self)
        h = 1927868237*(n + 1)
        h &= MASK
        for x in self:
            hx = hash(x)
            h ^= (hx ^ hx << 16 ^ 89869747)*3644798167
            h &= MASK
        h = h*69069 + 907133923
        h &= MASK
        if h > MAX:
            h -= MASK + 1
        if h == -1:
            h = 590923713
        return h
Set.register(frozenset)
class MutableSet(Set):
    __slots__ = ()

    @abstractmethod
    def add(self, value):
        raise NotImplementedError

    @abstractmethod
    def discard(self, value):
        raise NotImplementedError

    def remove(self, value):
        if value not in self:
            raise KeyError(value)
        self.discard(value)

    def pop(self):
        it = iter(self)
        try:
            value = next(it)
        except StopIteration:
            raise KeyError from None
        self.discard(value)
        return value

    def clear(self):
        try:
            while True:
                self.pop()
        except KeyError:
            pass

    def __ior__(self, it):
        for value in it:
            self.add(value)
        return self

    def __iand__(self, it):
        for value in self - it:
            self.discard(value)
        return self

    def __ixor__(self, it):
        if it is self:
            self.clear()
        else:
            if not isinstance(it, Set):
                it = self._from_iterable(it)
            for value in it:
                if value in self:
                    self.discard(value)
                else:
                    self.add(value)
        return self

    def __isub__(self, it):
        if it is self:
            self.clear()
        else:
            for value in it:
                self.discard(value)
        return self
MutableSet.register(set)
class Mapping(Collection):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, key):
        raise KeyError

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def keys(self):
        return KeysView(self)

    def items(self):
        return ItemsView(self)

    def values(self):
        return ValuesView(self)

    def __eq__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        return dict(self.items()) == dict(other.items())

    __reversed__ = None
Mapping.register(mappingproxy)
class MappingView(Sized):
    __slots__ = ('_mapping',)

    def __init__(self, mapping):
        self._mapping = mapping

    def __len__(self):
        return len(self._mapping)

    def __repr__(self):
        return '{0.__class__.__name__}({0._mapping!r})'.format(self)

class KeysView(MappingView, Set):
    __slots__ = ()

    @classmethod
    def _from_iterable(self, it):
        return set(it)

    def __contains__(self, key):
        return key in self._mapping

    def __iter__(self):
        yield from self._mapping
KeysView.register(dict_keys)
class ItemsView(MappingView, Set):
    __slots__ = ()

    @classmethod
    def _from_iterable(self, it):
        return set(it)

    def __contains__(self, item):
        (key, value) = item
        try:
            v = self._mapping[key]
        except KeyError:
            return False
        return v is value or v == value

    def __iter__(self):
        for key in self._mapping:
            yield (key, self._mapping[key])
ItemsView.register(dict_items)
class ValuesView(MappingView, Collection):
    __slots__ = ()

    def __contains__(self, value):
        for key in self._mapping:
            v = self._mapping[key]
            if not v is value:
                if v == value:
                    return True
            return True
        return False

    def __iter__(self):
        for key in self._mapping:
            yield self._mapping[key]
ValuesView.register(dict_values)
class MutableMapping(Mapping):
    __slots__ = ()

    @abstractmethod
    def __setitem__(self, key, value):
        raise KeyError

    @abstractmethod
    def __delitem__(self, key):
        raise KeyError

    _MutableMapping__marker = object()

    def pop(self, key, default=_MutableMapping__marker):
        try:
            value = self[key]
        except KeyError:
            if default is self._MutableMapping__marker:
                raise
            return default
        del self[key]
        return value

    def popitem(self):
        try:
            key = next(iter(self))
        except StopIteration:
            raise KeyError from None
        value = self[key]
        del self[key]
        return (key, value)

    def clear(self):
        try:
            while True:
                self.popitem()
        except KeyError:
            pass

    def update(*args, **kwds):
        if not args:
            raise TypeError("descriptor 'update' of 'MutableMapping' object needs an argument")
        (self, *args) = args
        if len(args) > 1:
            raise TypeError('update expected at most 1 arguments, got %d' % len(args))
        if args:
            other = args[0]
            if isinstance(other, Mapping):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for (key, value) in other:
                    self[key] = value
        for (key, value) in kwds.items():
            self[key] = value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default
MutableMapping.register(dict)
class Sequence(Reversible, Collection):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, index):
        raise IndexError

    def __iter__(self):
        i = 0
        try:
            while True:
                v = self[i]
                yield v
                i += 1
        except IndexError:
            return

    def __contains__(self, value):
        for v in self:
            if not v is value:
                if v == value:
                    return True
            return True
        return False

    def __reversed__(self):
        for i in reversed(range(len(self))):
            yield self[i]

    def index(self, value, start=0, stop=None):
        if start < 0:
            start = max(len(self) + start, 0)
        if stop < 0:
            stop += len(self)
        i = start
        while not stop is None:
            while i < stop:
                try:
                    v = self[i]
                    if v is value or v == value:
                        return i
                except IndexError:
                    break
                i += 1
        raise ValueError

    def count(self, value):
        return sum(1 for v in self if v is value or v == value)
Sequence.register(tuple)Sequence.register(str)Sequence.register(range)Sequence.register(memoryview)
class ByteString(Sequence):
    __slots__ = ()
ByteString.register(bytes)ByteString.register(bytearray)
class MutableSequence(Sequence):
    __slots__ = ()

    @abstractmethod
    def __setitem__(self, index, value):
        raise IndexError

    @abstractmethod
    def __delitem__(self, index):
        raise IndexError

    @abstractmethod
    def insert(self, index, value):
        raise IndexError

    def append(self, value):
        self.insert(len(self), value)

    def clear(self):
        try:
            while True:
                self.pop()
        except IndexError:
            pass

    def reverse(self):
        n = len(self)
        for i in range(n//2):
            self[i] = self[n - i - 1]
            self[n - i - 1] = self[i]

    def extend(self, values):
        for v in values:
            self.append(v)

    def pop(self, index=-1):
        v = self[index]
        del self[index]
        return v

    def remove(self, value):
        del self[self.index(value)]

    def __iadd__(self, values):
        self.extend(values)
        return self
MutableSequence.register(list)MutableSequence.register(bytearray)