__all__ = ['abs', 'add', 'and_', 'attrgetter', 'concat', 'contains', 'countOf', 'delitem', 'eq', 'floordiv', 'ge', 'getitem', 'gt', 'iadd', 'iand', 'iconcat', 'ifloordiv', 'ilshift', 'imatmul', 'imod', 'imul', 'index', 'indexOf', 'inv', 'invert', 'ior', 'ipow', 'irshift', 'is_', 'is_not', 'isub', 'itemgetter', 'itruediv', 'ixor', 'le', 'length_hint', 'lshift', 'lt', 'matmul', 'methodcaller', 'mod', 'mul', 'ne', 'neg', 'not_', 'or_', 'pos', 'pow', 'rshift', 'setitem', 'sub', 'truediv', 'truth', 'xor']from builtins import abs as _abs
def lt(a, b):
    return a < b

def le(a, b):
    return a <= b

def eq(a, b):
    return a == b

def ne(a, b):
    return a != b

def ge(a, b):
    return a >= b

def gt(a, b):
    return a > b

def not_(a):
    return not a

def truth(a):
    if a:
        return True
    return False

def is_(a, b):
    return a is b

def is_not(a, b):
    return a is not b

def abs(a):
    return _abs(a)

def add(a, b):
    return a + b

def and_(a, b):
    return a & b

def floordiv(a, b):
    return a//b

def index(a):
    return a.__index__()

def inv(a):
    return ~a
invert = inv
def lshift(a, b):
    return a << b

def mod(a, b):
    return a % b

def mul(a, b):
    return a*b

def matmul(a, b):
    return a @ b

def neg(a):
    return -a

def or_(a, b):
    return a | b

def pos(a):
    return +a

def pow(a, b):
    return a**b

def rshift(a, b):
    return a >> b

def sub(a, b):
    return a - b

def truediv(a, b):
    return a/b

def xor(a, b):
    return a ^ b

def concat(a, b):
    if not hasattr(a, '__getitem__'):
        msg = "'%s' object can't be concatenated" % type(a).__name__
        raise TypeError(msg)
    return a + b

def contains(a, b):
    return b in a

def countOf(a, b):
    count = 0
    for i in a:
        if i == b:
            count += 1
    return count

def delitem(a, b):
    del a[b]

def getitem(a, b):
    return a[b]

def indexOf(a, b):
    for (i, j) in enumerate(a):
        if j == b:
            return i
    raise ValueError('sequence.index(x): x not in sequence')

def setitem(a, b, c):
    a[b] = c

def length_hint(obj, default=0):
    if not isinstance(default, int):
        msg = "'%s' object cannot be interpreted as an integer" % type(default).__name__
        raise TypeError(msg)
    try:
        return len(obj)
    except TypeError:
        pass
    try:
        hint = type(obj).__length_hint__
    except AttributeError:
        return default
    try:
        val = hint(obj)
    except TypeError:
        return default
    if val is NotImplemented:
        return default
    if not isinstance(val, int):
        msg = '__length_hint__ must be integer, not %s' % type(val).__name__
        raise TypeError(msg)
    if val < 0:
        msg = '__length_hint__() should return >= 0'
        raise ValueError(msg)
    return val

class attrgetter:
    __slots__ = ('_attrs', '_call')

    def __init__(self, attr, *attrs):
        if not attrs:
            if not isinstance(attr, str):
                raise TypeError('attribute name must be a string')
            self._attrs = (attr,)
            names = attr.split('.')

            def func(obj):
                for name in names:
                    obj = getattr(obj, name)
                return obj

            self._call = func
        else:
            self._attrs = (attr,) + attrs
            getters = tuple(map(attrgetter, self._attrs))

            def func(obj):
                return tuple(getter(obj) for getter in getters)

            self._call = func

    def __call__(self, obj):
        return self._call(obj)

    def __repr__(self):
        return '%s.%s(%s)' % (self.__class__.__module__, self.__class__.__qualname__, ', '.join(map(repr, self._attrs)))

    def __reduce__(self):
        return (self.__class__, self._attrs)

class itemgetter:
    __slots__ = ('_items', '_call')

    def __init__(self, item, *items):
        if not items:
            self._items = (item,)

            def func(obj):
                return obj[item]

            self._call = func
        else:
            self._items = items = (item,) + items

            def func(obj):
                return tuple(obj[i] for i in items)

            self._call = func

    def __call__(self, obj):
        return self._call(obj)

    def __repr__(self):
        return '%s.%s(%s)' % (self.__class__.__module__, self.__class__.__name__, ', '.join(map(repr, self._items)))

    def __reduce__(self):
        return (self.__class__, self._items)

class methodcaller:
    __slots__ = ('_name', '_args', '_kwargs')

    def __init__(*args, **kwargs):
        if len(args) < 2:
            msg = 'methodcaller needs at least one argument, the method name'
            raise TypeError(msg)
        self = args[0]
        self._name = args[1]
        if not isinstance(self._name, str):
            raise TypeError('method name must be a string')
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj):
        return getattr(obj, self._name)(*self._args, **self._kwargs)

    def __repr__(self):
        args = [repr(self._name)]
        args.extend(map(repr, self._args))
        args.extend('%s=%r' % (k, v) for (k, v) in self._kwargs.items())
        return '%s.%s(%s)' % (self.__class__.__module__, self.__class__.__name__, ', '.join(args))

    def __reduce__(self):
        if not self._kwargs:
            return (self.__class__, (self._name,) + self._args)
        else:
            from functools import partial
            return (partial(self.__class__, self._name, **self._kwargs), self._args)

def iadd(a, b):
    a += b
    return a

def iand(a, b):
    a &= b
    return a

def iconcat(a, b):
    if not hasattr(a, '__getitem__'):
        msg = "'%s' object can't be concatenated" % type(a).__name__
        raise TypeError(msg)
    a += b
    return a

def ifloordiv(a, b):
    a //= b
    return a

def ilshift(a, b):
    a <<= b
    return a

def imod(a, b):
    a %= b
    return a

def imul(a, b):
    a *= b
    return a

def imatmul(a, b):
    a @= b
    return a

def ior(a, b):
    a |= b
    return a

def ipow(a, b):
    a **= b
    return a

def irshift(a, b):
    a >>= b
    return a

def isub(a, b):
    a -= b
    return a

def itruediv(a, b):
    a /= b
    return a

def ixor(a, b):
    a ^= b
    return a
try:
    from _operator import *
except ImportError:
    passfrom _operator import __doc____lt__ = lt__le__ = le__eq__ = eq__ne__ = ne__ge__ = ge__gt__ = gt__not__ = not___abs__ = abs__add__ = add__and__ = and___floordiv__ = floordiv__index__ = index__inv__ = inv__invert__ = invert__lshift__ = lshift__mod__ = mod__mul__ = mul__matmul__ = matmul__neg__ = neg__or__ = or___pos__ = pos__pow__ = pow__rshift__ = rshift__sub__ = sub__truediv__ = truediv__xor__ = xor__concat__ = concat__contains__ = contains__delitem__ = delitem__getitem__ = getitem__setitem__ = setitem__iadd__ = iadd__iand__ = iand__iconcat__ = iconcat__ifloordiv__ = ifloordiv__ilshift__ = ilshift__imod__ = imod__imul__ = imul__imatmul__ = imatmul__ior__ = ior__ipow__ = ipow__irshift__ = irshift__isub__ = isub__itruediv__ = itruediv__ixor__ = ixor