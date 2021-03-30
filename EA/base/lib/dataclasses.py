import reimport sysimport copyimport typesimport inspectimport keyword__all__ = ['dataclass', 'field', 'Field', 'FrozenInstanceError', 'InitVar', 'MISSING', 'fields', 'asdict', 'astuple', 'make_dataclass', 'replace', 'is_dataclass']
class FrozenInstanceError(AttributeError):
    pass

class _HAS_DEFAULT_FACTORY_CLASS:

    def __repr__(self):
        return '<factory>'
_HAS_DEFAULT_FACTORY = _HAS_DEFAULT_FACTORY_CLASS()
class _MISSING_TYPE:
    pass
MISSING = _MISSING_TYPE()_EMPTY_METADATA = types.MappingProxyType({})
class _FIELD_BASE:

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name
_FIELD = _FIELD_BASE('_FIELD')_FIELD_CLASSVAR = _FIELD_BASE('_FIELD_CLASSVAR')_FIELD_INITVAR = _FIELD_BASE('_FIELD_INITVAR')_FIELDS = '__dataclass_fields__'_PARAMS = '__dataclass_params__'_POST_INIT_NAME = '__post_init__'_MODULE_IDENTIFIER_RE = re.compile('^(?:\\s*(\\w+)\\s*\\.)?\\s*(\\w+)')
class _InitVarMeta(type):

    def __getitem__(self, params):
        return self

class InitVar(metaclass=_InitVarMeta):
    pass

class Field:
    __slots__ = ('name', 'type', 'default', 'default_factory', 'repr', 'hash', 'init', 'compare', 'metadata', '_field_type')

    def __init__(self, default, default_factory, init, repr, hash, compare, metadata):
        self.name = None
        self.type = None
        self.default = default
        self.default_factory = default_factory
        self.init = init
        self.repr = repr
        self.hash = hash
        self.compare = compare
        self.metadata = _EMPTY_METADATA if metadata is None or len(metadata) == 0 else types.MappingProxyType(metadata)
        self._field_type = None

    def __repr__(self):
        return f'Field(name={self.name},type={self.type},default={self.default},default_factory={self.default_factory},init={self.init},repr={self.repr},hash={self.hash},compare={self.compare},metadata={self.metadata},_field_type={self._field_type})'

    def __set_name__(self, owner, name):
        func = getattr(type(self.default), '__set_name__', None)
        if func:
            func(self.default, owner, name)

class _DataclassParams:
    __slots__ = ('init', 'repr', 'eq', 'order', 'unsafe_hash', 'frozen')

    def __init__(self, init, repr, eq, order, unsafe_hash, frozen):
        self.init = init
        self.repr = repr
        self.eq = eq
        self.order = order
        self.unsafe_hash = unsafe_hash
        self.frozen = frozen

    def __repr__(self):
        return f'_DataclassParams(init={self.init},repr={self.repr},eq={self.eq},order={self.order},unsafe_hash={self.unsafe_hash},frozen={self.frozen})'

def field(*, default=MISSING, default_factory=MISSING, init=True, repr=True, hash=None, compare=True, metadata=None):
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError('cannot specify both default and default_factory')
    return Field(default, default_factory, init, repr, hash, compare, metadata)

def _tuple_str(obj_name, fields):
    if not fields:
        return '()'
    return f'({','.join([f'{obj_name}.{f.name}' for f in fields])},)'

def _create_fn(name, args, body, *, globals=None, locals=None, return_type=MISSING):
    if locals is None:
        locals = {}
    return_annotation = ''
    if return_type is not MISSING:
        locals['_return_type'] = return_type
        return_annotation = '->_return_type'
    args = ','.join(args)
    body = '\n'.join(f' {b}' for b in body)
    txt = f'def {name}({args}){return_annotation}:
{body}'
    exec(txt, globals, locals)
    return locals[name]

def _field_assign(frozen, name, value, self_name):
    if frozen:
        return f'object.__setattr__({self_name},{name},{value})'
    return f'{self_name}.{name}={value}'

def _field_init(f, frozen, globals, self_name):
    default_name = f'_dflt_{f.name}'
    if f.default_factory is not MISSING:
        if f.init:
            globals[default_name] = f.default_factory
            value = f'{default_name}() if {f.name} is _HAS_DEFAULT_FACTORY else {f.name}'
        else:
            globals[default_name] = f.default_factory
            value = f'{default_name}()'
    elif f.init:
        if f.default is MISSING:
            value = f.name
        elif f.default is not MISSING:
            globals[default_name] = f.default
            value = f.name
    else:
        return
    if f._field_type is _FIELD_INITVAR:
        return
    return _field_assign(frozen, f.name, value, self_name)

def _init_param(f):
    if f.default is MISSING and f.default_factory is MISSING:
        default = ''
    elif f.default is not MISSING:
        default = f'=_dflt_{f.name}'
    elif f.default_factory is not MISSING:
        default = '=_HAS_DEFAULT_FACTORY'
    return f'{f.name}:_type_{f.name}{default}'

def _init_fn(fields, frozen, has_post_init, self_name):
    seen_default = False
    for f in fields:
        if f.init:
            if not (f.default is MISSING and f.default_factory is MISSING):
                seen_default = True
            elif seen_default:
                raise TypeError(f'non-default argument {f.name} follows default argument')
    globals = {'MISSING': MISSING, '_HAS_DEFAULT_FACTORY': _HAS_DEFAULT_FACTORY}
    body_lines = []
    for f in fields:
        line = _field_init(f, frozen, globals, self_name)
        if line:
            body_lines.append(line)
    if has_post_init:
        params_str = ','.join(f.name for f in fields if f._field_type is _FIELD_INITVAR)
        body_lines.append(f'{self_name}.{_POST_INIT_NAME}({params_str})')
    if not body_lines:
        body_lines = ['pass']
    locals = {f'_type_{f.name}': f.type for f in fields}
    return _create_fn('__init__', [self_name] + [_init_param(f) for f in fields if f.init], body_lines, locals=locals, globals=globals, return_type=None)

def _repr_fn(fields):
    return _create_fn('__repr__', ('self',), ['return self.__class__.__qualname__ + f"(' + ', '.join([f'{f.name}={self.{f.name}!r}' for f in fields]) + ')"'])

def _frozen_get_del_attr(cls, fields):
    globals = {'cls': cls, 'FrozenInstanceError': FrozenInstanceError}
    if fields:
        fields_str = '(' + ','.join(repr(f.name) for f in fields) + ',)'
    else:
        fields_str = '()'
    return (_create_fn('__setattr__', ('self', 'name', 'value'), (f'if type(self) is cls or name in {fields_str}:', ' raise FrozenInstanceError(f"cannot assign to field {name!r}")', 'super(cls, self).__setattr__(name, value)'), globals=globals), _create_fn('__delattr__', ('self', 'name'), (f'if type(self) is cls or name in {fields_str}:', ' raise FrozenInstanceError(f"cannot delete field {name!r}")', 'super(cls, self).__delattr__(name)'), globals=globals))

def _cmp_fn(name, op, self_tuple, other_tuple):
    return _create_fn(name, ('self', 'other'), ['if other.__class__ is self.__class__:', f' return {self_tuple}{op}{other_tuple}', 'return NotImplemented'])

def _hash_fn(fields):
    self_tuple = _tuple_str('self', fields)
    return _create_fn('__hash__', ('self',), [f'return hash({self_tuple})'])

def _is_classvar(a_type, typing):
    return a_type is typing.ClassVar or type(a_type) is typing._GenericAlias and a_type.__origin__ is typing.ClassVar

def _is_initvar(a_type, dataclasses):
    return a_type is dataclasses.InitVar

def _is_type(annotation, cls, a_module, a_type, is_type_predicate):
    match = _MODULE_IDENTIFIER_RE.match(annotation)
    if match:
        ns = None
        module_name = match.group(1)
        if not module_name:
            ns = sys.modules.get(cls.__module__).__dict__
        else:
            module = sys.modules.get(cls.__module__)
            if module.__dict__.get(module_name) is a_module:
                ns = sys.modules.get(a_type.__module__).__dict__
        if ns and is_type_predicate(ns.get(match.group(2)), a_module):
            return True
    return False

def _get_field(cls, a_name, a_type):
    default = getattr(cls, a_name, MISSING)
    if isinstance(default, Field):
        f = default
    else:
        if isinstance(default, types.MemberDescriptorType):
            default = MISSING
        f = field(default=default)
    f.name = a_name
    f.type = a_type
    f._field_type = _FIELD
    typing = sys.modules.get('typing')
    if _is_type(f.type, cls, typing, typing.ClassVar, _is_classvar):
        f._field_type = _FIELD_CLASSVAR
    if typing and (_is_classvar(a_type, typing) or isinstance(f.type, str)) and f._field_type is _FIELD:
        dataclasses = sys.modules[__name__]
        if _is_type(f.type, cls, dataclasses, dataclasses.InitVar, _is_initvar):
            f._field_type = _FIELD_INITVAR
    if f._field_type in (_FIELD_CLASSVAR, _FIELD_INITVAR) and f.default_factory is not MISSING:
        raise TypeError(f'field {f.name} cannot have a default factory')
    if f._field_type is _FIELD and isinstance(f.default, (list, dict, set)):
        raise ValueError(f'mutable default {type(f.default)} for field {f.name} is not allowed: use default_factory')
    return f

def _set_new_attribute(cls, name, value):
    if name in cls.__dict__:
        return True
    setattr(cls, name, value)
    return False

def _hash_set_none(cls, fields):
    pass
