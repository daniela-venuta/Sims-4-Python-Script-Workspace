__all__ = ('Mock', 'MagicMock', 'patch', 'sentinel', 'DEFAULT', 'ANY', 'call', 'create_autospec', 'FILTER_DIR', 'NonCallableMock', 'NonCallableMagicMock', 'mock_open', 'PropertyMock', 'seal')__version__ = '1.0'import inspectimport pprintimport sysimport builtinsfrom types import ModuleTypefrom functools import wraps, partial_builtins = {name for name in dir(builtins) if not name.startswith('_')}BaseExceptions = (BaseException,)if 'java' in sys.platform:
    import java
    BaseExceptions = (BaseException, java.lang.Throwable)FILTER_DIR = True_safe_super = super
def _is_instance_mock(obj):
    return issubclass(type(obj), NonCallableMock)

def _is_exception(obj):
    return isinstance(obj, BaseExceptions) or isinstance(obj, type) and issubclass(obj, BaseExceptions)

def _get_signature_object(func, as_instance, eat_self):
    if isinstance(func, type) and not as_instance:
        try:
            func = func.__init__
        except AttributeError:
            return
        eat_self = True
    elif not isinstance(func, FunctionTypes):
        try:
            func = func.__call__
        except AttributeError:
            return
    if eat_self:
        sig_func = partial(func, None)
    else:
        sig_func = func
    try:
        return (func, inspect.signature(sig_func))
    except ValueError:
        return

def _check_signature(func, mock, skipfirst, instance=False):
    sig = _get_signature_object(func, instance, skipfirst)
    if sig is None:
        return
    (func, sig) = sig

    def checksig(_mock_self, *args, **kwargs):
        sig.bind(*args, **kwargs)

    _copy_func_details(func, checksig)
    type(mock)._mock_check_sig = checksig

def _copy_func_details(func, funcopy):
    for attribute in ('__name__', '__doc__', '__text_signature__', '__module__', '__defaults__', '__kwdefaults__'):
        try:
            setattr(funcopy, attribute, getattr(func, attribute))
        except AttributeError:
            pass

def _callable(obj):
    if isinstance(obj, type):
        return True
    elif getattr(obj, '__call__', None) is not None:
        return True
    return False

def _is_list(obj):
    return type(obj) in (list, tuple)

def _instance_callable(obj):
    if not isinstance(obj, type):
        return getattr(obj, '__call__', None) is not None
    for base in (obj,) + obj.__mro__:
        if base.__dict__.get('__call__') is not None:
            return True
    return False

def _set_signature(mock, original, instance=False):
    if not _callable(original):
        return
    skipfirst = isinstance(original, type)
    result = _get_signature_object(original, instance, skipfirst)
    if result is None:
        return mock
    (func, sig) = result

    def checksig(*args, **kwargs):
        sig.bind(*args, **kwargs)

    _copy_func_details(func, checksig)
    name = original.__name__
    if not name.isidentifier():
        name = 'funcopy'
    context = {'_checksig_': checksig, 'mock': mock}
    src = 'def %s(*args, **kwargs):\n    _checksig_(*args, **kwargs)\n    return mock(*args, **kwargs)' % name
    exec(src, context)
    funcopy = context[name]
    _setup_func(funcopy, mock)
    return funcopy

def _setup_func(funcopy, mock):
    funcopy.mock = mock
    if not _is_instance_mock(mock):
        return

    def assert_called_with(*args, **kwargs):
        return mock.assert_called_with(*args, **kwargs)

    def assert_called(*args, **kwargs):
        return mock.assert_called(*args, **kwargs)

    def assert_not_called(*args, **kwargs):
        return mock.assert_not_called(*args, **kwargs)

    def assert_called_once(*args, **kwargs):
        return mock.assert_called_once(*args, **kwargs)

    def assert_called_once_with(*args, **kwargs):
        return mock.assert_called_once_with(*args, **kwargs)

    def assert_has_calls(*args, **kwargs):
        return mock.assert_has_calls(*args, **kwargs)

    def assert_any_call(*args, **kwargs):
        return mock.assert_any_call(*args, **kwargs)

    def reset_mock():
        funcopy.method_calls = _CallList()
        funcopy.mock_calls = _CallList()
        mock.reset_mock()
        ret = funcopy.return_value
        if _is_instance_mock(ret) and ret is not mock:
            ret.reset_mock()

    funcopy.called = False
    funcopy.call_count = 0
    funcopy.call_args = None
    funcopy.call_args_list = _CallList()
    funcopy.method_calls = _CallList()
    funcopy.mock_calls = _CallList()
    funcopy.return_value = mock.return_value
    funcopy.side_effect = mock.side_effect
    funcopy._mock_children = mock._mock_children
    funcopy.assert_called_with = assert_called_with
    funcopy.assert_called_once_with = assert_called_once_with
    funcopy.assert_has_calls = assert_has_calls
    funcopy.assert_any_call = assert_any_call
    funcopy.reset_mock = reset_mock
    funcopy.assert_called = assert_called
    funcopy.assert_not_called = assert_not_called
    funcopy.assert_called_once = assert_called_once
    mock._mock_delegate = funcopy

def _is_magic(name):
    return '__%s__' % name[2:-2] == name

class _SentinelObject(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'sentinel.%s' % self.name

    def __reduce__(self):
        return 'sentinel.%s' % self.name

class _Sentinel(object):

    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name == '__bases__':
            raise AttributeError
        return self._sentinels.setdefault(name, _SentinelObject(name))

    def __reduce__(self):
        return 'sentinel'
sentinel = _Sentinel()DEFAULT = sentinel.DEFAULT_missing = sentinel.MISSING_deleted = sentinel.DELETED
def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value
_allowed_names = {'return_value', '_mock_return_value', 'side_effect', '_mock_side_effect', '_mock_parent', '_mock_new_parent', '_mock_name', '_mock_new_name'}
def _delegating_property(name):
    _allowed_names.add(name)
    _the_name = '_mock_' + name

    def _get(self, name=name, _the_name=_the_name):
        sig = self._mock_delegate
        if sig is None:
            return getattr(self, _the_name)
        return getattr(sig, name)

    def _set(self, value, name=name, _the_name=_the_name):
        sig = self._mock_delegate
        if sig is None:
            self.__dict__[_the_name] = value
        else:
            setattr(sig, name, value)

    return property(_get, _set)

class _CallList(list):

    def __contains__(self, value):
        if not isinstance(value, list):
            return list.__contains__(self, value)
        len_value = len(value)
        len_self = len(self)
        if len_value > len_self:
            return False
        for i in range(0, len_self - len_value + 1):
            sub_list = self[i:i + len_value]
            if sub_list == value:
                return True
        return False

    def __repr__(self):
        return pprint.pformat(list(self))

def _check_and_set_parent(parent, value, name, new_name):
    if not _is_instance_mock(value):
        return False
    if value._mock_name or (value._mock_new_name or value._mock_parent is not None) or value._mock_new_parent is not None:
        return False
    _parent = parent
    if _parent is not None:
        if _parent is value:
            return False
        _parent = _parent._mock_new_parent
    if new_name:
        value._mock_new_parent = parent
        value._mock_new_name = new_name
    if name:
        value._mock_parent = parent
        value._mock_name = name
    return True

class _MockIter(object):

    def __init__(self, obj):
        self.obj = iter(obj)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.obj)

class Base(object):
    _mock_return_value = DEFAULT
    _mock_side_effect = None

    def __init__(self, *args, **kwargs):
        pass

class NonCallableMock(Base):

    def __new__(cls, *args, **kw):
        new = type(cls.__name__, (cls,), {'__doc__': cls.__doc__})
        instance = object.__new__(new)
        return instance

    def __init__(self, spec=None, wraps=None, name=None, spec_set=None, parent=None, _spec_state=None, _new_name='', _new_parent=None, _spec_as_instance=False, _eat_self=None, unsafe=False, **kwargs):
        if _new_parent is None:
            _new_parent = parent
        __dict__ = self.__dict__
        __dict__['_mock_parent'] = parent
        __dict__['_mock_name'] = name
        __dict__['_mock_new_name'] = _new_name
        __dict__['_mock_new_parent'] = _new_parent
        __dict__['_mock_sealed'] = False
        if spec_set is not None:
            spec = spec_set
            spec_set = True
        if _eat_self is None:
            _eat_self = parent is not None
        self._mock_add_spec(spec, spec_set, _spec_as_instance, _eat_self)
        __dict__['_mock_children'] = {}
        __dict__['_mock_wraps'] = wraps
        __dict__['_mock_delegate'] = None
        __dict__['_mock_called'] = False
        __dict__['_mock_call_args'] = None
        __dict__['_mock_call_count'] = 0
        __dict__['_mock_call_args_list'] = _CallList()
        __dict__['_mock_mock_calls'] = _CallList()
        __dict__['method_calls'] = _CallList()
        __dict__['_mock_unsafe'] = unsafe
        if kwargs:
            self.configure_mock(**kwargs)
        _safe_super(NonCallableMock, self).__init__(spec, wraps, name, spec_set, parent, _spec_state)

    def attach_mock(self, mock, attribute):
        mock._mock_parent = None
        mock._mock_new_parent = None
        mock._mock_name = ''
        mock._mock_new_name = None
        setattr(self, attribute, mock)

    def mock_add_spec(self, spec, spec_set=False):
        self._mock_add_spec(spec, spec_set)

    def _mock_add_spec(self, spec, spec_set, _spec_as_instance=False, _eat_self=False):
        _spec_class = None
        _spec_signature = None
        if not _is_list(spec):
            if isinstance(spec, type):
                _spec_class = spec
            else:
                _spec_class = _get_class(spec)
            res = _get_signature_object(spec, _spec_as_instance, _eat_self)
            _spec_signature = res and res[1]
            spec = dir(spec)
        __dict__ = self.__dict__
        __dict__['_spec_class'] = _spec_class
        __dict__['_spec_set'] = spec_set
        __dict__['_spec_signature'] = _spec_signature
        __dict__['_mock_methods'] = spec

    def __get_return_value(self):
        ret = self._mock_return_value
        if self._mock_delegate is not None:
            ret = self._mock_delegate.return_value
        if ret is DEFAULT:
            ret = self._get_child_mock(_new_parent=self, _new_name='()')
            self.return_value = ret
        return ret

    def __set_return_value(self, value):
        if self._mock_delegate is not None:
            self._mock_delegate.return_value = value
        else:
            self._mock_return_value = value
            _check_and_set_parent(self, value, None, '()')

    _NonCallableMock__return_value_doc = 'The value to be returned when the mock is called.'
    return_value = property(_NonCallableMock__get_return_value, _NonCallableMock__set_return_value, _NonCallableMock__return_value_doc)

    @property
    def __class__(self):
        if self._spec_class is None:
            return type(self)
        return self._spec_class

    called = _delegating_property('called')
    call_count = _delegating_property('call_count')
    call_args = _delegating_property('call_args')
    call_args_list = _delegating_property('call_args_list')
    mock_calls = _delegating_property('mock_calls')

    def __get_side_effect(self):
        delegated = self._mock_delegate
        if delegated is None:
            return self._mock_side_effect
        sf = delegated.side_effect
        if not _is_exception(sf):
            sf = _MockIter(sf)
            delegated.side_effect = sf
        return sf

    def __set_side_effect(self, value):
        value = _try_iter(value)
        delegated = self._mock_delegate
        if delegated is None:
            self._mock_side_effect = value
        else:
            delegated.side_effect = value

    side_effect = property(_NonCallableMock__get_side_effect, _NonCallableMock__set_side_effect)

    def reset_mock(self, visited=None, *, return_value=False, side_effect=False):
        if visited is None:
            visited = []
        if id(self) in visited:
            return
        visited.append(id(self))
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.mock_calls = _CallList()
        self.call_args_list = _CallList()
        self.method_calls = _CallList()
        if return_value:
            self._mock_return_value = DEFAULT
        if side_effect:
            self._mock_side_effect = None
        for child in self._mock_children.values():
            if isinstance(child, _SpecState):
                pass
            else:
                child.reset_mock(visited)
        ret = self._mock_return_value
        if _is_instance_mock(ret) and ret is not self:
            ret.reset_mock(visited)

    def configure_mock(self, **kwargs):
        for (arg, val) in sorted(kwargs.items(), key=lambda entry: entry[0].count('.')):
            args = arg.split('.')
            final = args.pop()
            obj = self
            for entry in args:
                obj = getattr(obj, entry)
            setattr(obj, final, val)

    def __getattr__(self, name):
        if name in frozenset({'_mock_unsafe', '_mock_methods'}):
            raise AttributeError(name)
        elif self._mock_methods is not None:
            if name not in self._mock_methods or name in _all_magics:
                raise AttributeError('Mock object has no attribute %r' % name)
        elif _is_magic(name):
            raise AttributeError(name)
        if self._mock_unsafe or name.startswith(('assert', 'assret')):
            raise AttributeError(name)
        result = self._mock_children.get(name)
        if result is _deleted:
            raise AttributeError(name)
        elif result is None:
            wraps = None
            if self._mock_wraps is not None:
                wraps = getattr(self._mock_wraps, name)
            result = self._get_child_mock(parent=self, name=name, wraps=wraps, _new_name=name, _new_parent=self)
            self._mock_children[name] = result
        elif isinstance(result, _SpecState):
            result = create_autospec(result.spec, result.spec_set, result.instance, result.parent, result.name)
            self._mock_children[name] = result
        return result

    def _extract_mock_name(self):
        _name_list = [self._mock_new_name]
        _parent = self._mock_new_parent
        last = self
        dot = '.'
        if _name_list == ['()']:
            dot = ''
        seen = set()
        while _parent is not None:
            last = _parent
            _name_list.append(_parent._mock_new_name + dot)
            dot = '.'
            if _parent._mock_new_name == '()':
                dot = ''
            _parent = _parent._mock_new_parent
            if id(_parent) in seen:
                break
            seen.add(id(_parent))
        _name_list = list(reversed(_name_list))
        _first = last._mock_name or 'mock'
        if _name_list[1] not in ('()', '().'):
            _first += '.'
        _name_list[0] = _first
        return ''.join(_name_list)

    def __repr__(self):
        name = self._extract_mock_name()
        name_string = ''
        if name not in ('mock', 'mock.'):
            name_string = ' name=%r' % name
        spec_string = ''
        if self._spec_class is not None:
            spec_string = ' spec=%r'
            if self._spec_set:
                spec_string = ' spec_set=%r'
            spec_string = spec_string % self._spec_class.__name__
        return "<%s%s%s id='%s'>" % (type(self).__name__, name_string, spec_string, id(self))

    def __dir__(self):
        if not FILTER_DIR:
            return object.__dir__(self)
        extras = self._mock_methods or []
        from_type = dir(type(self))
        from_dict = list(self.__dict__)
        from_type = [e for e in from_type if not e.startswith('_')]
        from_dict = [e for e in from_dict if not e.startswith('_') or _is_magic(e)]
        return sorted(set(extras + from_type + from_dict + list(self._mock_children)))

    def __setattr__(self, name, value):
        if name in _allowed_names:
            return object.__setattr__(self, name, value)
        if self._spec_set and (self._mock_methods is not None and name not in self._mock_methods) and name not in self.__dict__:
            raise AttributeError("Mock object has no attribute '%s'" % name)
        elif name in _unsupported_magics:
            msg = 'Attempting to set unsupported magic method %r.' % name
            raise AttributeError(msg)
        elif name in _all_magics:
            if self._mock_methods is not None and name not in self._mock_methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)
            if not _is_instance_mock(value):
                setattr(type(self), name, _get_method(name, value))
                original = value
                value = lambda *args, **kw: original(self, *args, **kw)
            else:
                _check_and_set_parent(self, value, None, name)
                setattr(type(self), name, value)
                self._mock_children[name] = value
        else:
            if name == '__class__':
                self._spec_class = value
                return
            if _check_and_set_parent(self, value, name, name):
                self._mock_children[name] = value
        if self._mock_sealed and not hasattr(self, name):
            mock_name = f'{self._extract_mock_name()}.{name}'
            raise AttributeError(f'Cannot set {mock_name}')
        return object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name in _all_magics and name in type(self).__dict__:
            delattr(type(self), name)
            if name not in self.__dict__:
                return
        if name in self.__dict__:
            object.__delattr__(self, name)
        obj = self._mock_children.get(name, _missing)
        if obj is _deleted:
            raise AttributeError(name)
        if obj is not _missing:
            del self._mock_children[name]
        self._mock_children[name] = _deleted

    def _format_mock_call_signature(self, args, kwargs):
        name = self._mock_name or 'mock'
        return _format_call_signature(name, args, kwargs)

    def _format_mock_failure_message(self, args, kwargs):
        message = 'Expected call: %s\nActual call: %s'
        expected_string = self._format_mock_call_signature(args, kwargs)
        call_args = self.call_args
        if len(call_args) == 3:
            call_args = call_args[1:]
        actual_string = self._format_mock_call_signature(*call_args)
        return message % (expected_string, actual_string)

    def _call_matcher(self, _call):
        sig = self._spec_signature
        if sig is not None:
            if len(_call) == 2:
                name = ''
                (args, kwargs) = _call
            else:
                (name, args, kwargs) = _call
            try:
                return (name, sig.bind(*args, **kwargs))
            except TypeError as e:
                return e.with_traceback(None)
        else:
            return _call

    def assert_not_called(_mock_self):
        self = _mock_self
        if self.call_count != 0:
            msg = "Expected '%s' to not have been called. Called %s times." % (self._mock_name or 'mock', self.call_count)
            raise AssertionError(msg)

    def assert_called(_mock_self):
        self = _mock_self
        if self.call_count == 0:
            msg = "Expected '%s' to have been called." % self._mock_name or 'mock'
            raise AssertionError(msg)

    def assert_called_once(_mock_self):
        self = _mock_self
        if not self.call_count == 1:
            msg = "Expected '%s' to have been called once. Called %s times." % (self._mock_name or 'mock', self.call_count)
            raise AssertionError(msg)

    def assert_called_with(_mock_self, *args, **kwargs):
        self = _mock_self
        if self.call_args is None:
            expected = self._format_mock_call_signature(args, kwargs)
            raise AssertionError('Expected call: %s\nNot called' % (expected,))

        def _error_message():
            msg = self._format_mock_failure_message(args, kwargs)
            return msg

        expected = self._call_matcher((args, kwargs))
        actual = self._call_matcher(self.call_args)
        if expected != actual:
            cause = expected if isinstance(expected, Exception) else None
            raise AssertionError(_error_message()) from cause

    def assert_called_once_with(_mock_self, *args, **kwargs):
        self = _mock_self
        if not self.call_count == 1:
            msg = "Expected '%s' to be called once. Called %s times." % (self._mock_name or 'mock', self.call_count)
            raise AssertionError(msg)
        return self.assert_called_with(*args, **kwargs)

    def assert_has_calls(self, calls, any_order=False):
        expected = [self._call_matcher(c) for c in calls]
        cause = expected if isinstance(expected, Exception) else None
        all_calls = _CallList(self._call_matcher(c) for c in self.mock_calls)
        if not any_order:
            if expected not in all_calls:
                raise AssertionError('Calls not found.\nExpected: %r\nActual: %r' % (_CallList(calls), self.mock_calls)) from cause
            return
        all_calls = list(all_calls)
        not_found = []
        for kall in expected:
            try:
                all_calls.remove(kall)
            except ValueError:
                not_found.append(kall)
        if not_found:
            raise AssertionError('%r not all found in call list' % (tuple(not_found),)) from cause

    def assert_any_call(self, *args, **kwargs):
        expected = self._call_matcher((args, kwargs))
        actual = [self._call_matcher(c) for c in self.call_args_list]
        if expected not in actual:
            cause = expected if isinstance(expected, Exception) else None
            expected_string = self._format_mock_call_signature(args, kwargs)
            raise AssertionError('%s call not found' % expected_string) from cause

    def _get_child_mock(self, **kw):
        _type = type(self)
        if not issubclass(_type, CallableMixin):
            if issubclass(_type, NonCallableMagicMock):
                klass = MagicMock
            elif issubclass(_type, NonCallableMock):
                klass = Mock
        else:
            klass = _type.__mro__[1]
        if self._mock_sealed:
            attribute = '.' + kw['name'] if 'name' in kw else '()'
            mock_name = self._extract_mock_name() + attribute
            raise AttributeError(mock_name)
        return klass(**kw)

def _try_iter(obj):
    if obj is None:
        return obj
    if _is_exception(obj):
        return obj
    if _callable(obj):
        return obj
    try:
        return iter(obj)
    except TypeError:
        return obj

class CallableMixin(Base):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT, wraps=None, name=None, spec_set=None, parent=None, _spec_state=None, _new_name='', _new_parent=None, **kwargs):
        self.__dict__['_mock_return_value'] = return_value
        _safe_super(CallableMixin, self).__init__(spec, wraps, name, spec_set, parent, _spec_state, _new_name, _new_parent, **kwargs)
        self.side_effect = side_effect

    def _mock_check_sig(self, *args, **kwargs):
        pass

    def __call__(_mock_self, *args, **kwargs):
        _mock_self._mock_check_sig(*args, **kwargs)
        return _mock_self._mock_call(*args, **kwargs)

    def _mock_call(_mock_self, *args, **kwargs):
        self = _mock_self
        self.called = True
        self.call_count += 1
        _new_name = self._mock_new_name
        _new_parent = self._mock_new_parent
        _call = _Call((args, kwargs), two=True)
        self.call_args = _call
        self.call_args_list.append(_call)
        self.mock_calls.append(_Call(('', args, kwargs)))
        seen = set()
        skip_next_dot = _new_name == '()'
        do_method_calls = self._mock_parent is not None
        name = self._mock_name
        while _new_parent is not None:
            this_mock_call = _Call((_new_name, args, kwargs))
            if _new_parent._mock_new_name:
                dot = '.'
                if skip_next_dot:
                    dot = ''
                skip_next_dot = False
                if _new_parent._mock_new_name == '()':
                    skip_next_dot = True
                _new_name = _new_parent._mock_new_name + dot + _new_name
            if do_method_calls:
                if _new_name == name:
                    this_method_call = this_mock_call
                else:
                    this_method_call = _Call((name, args, kwargs))
                _new_parent.method_calls.append(this_method_call)
                do_method_calls = _new_parent._mock_parent is not None
                if do_method_calls:
                    name = _new_parent._mock_name + '.' + name
            _new_parent.mock_calls.append(this_mock_call)
            _new_parent = _new_parent._mock_new_parent
            _new_parent_id = id(_new_parent)
            if _new_parent_id in seen:
                break
            seen.add(_new_parent_id)
        ret_val = DEFAULT
        effect = self.side_effect
        if effect is not None:
            if _is_exception(effect):
                raise effect
            if not _callable(effect):
                result = next(effect)
                if _is_exception(result):
                    raise result
                if result is DEFAULT:
                    result = self.return_value
                return result
            ret_val = effect(*args, **kwargs)
        if self._mock_wraps is not None and self._mock_return_value is DEFAULT:
            return self._mock_wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val

class Mock(CallableMixin, NonCallableMock):
    pass

def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)

def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)
    for comp in components:
        import_path += '.%s' % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing

def _is_started(patcher):
    return hasattr(patcher, 'is_local')

class _patch(object):
    attribute_name = None
    _active_patches = []

    def __init__(self, getter, attribute, new, spec, create, spec_set, autospec, new_callable, kwargs):
        if new_callable is not None:
            if new is not DEFAULT:
                raise ValueError("Cannot use 'new' and 'new_callable' together")
            if autospec is not None:
                raise ValueError("Cannot use 'autospec' and 'new_callable' together")
        self.getter = getter
        self.attribute = attribute
        self.new = new
        self.new_callable = new_callable
        self.spec = spec
        self.create = create
        self.has_local = False
        self.spec_set = spec_set
        self.autospec = autospec
        self.kwargs = kwargs
        self.additional_patchers = []

    def copy(self):
        patcher = _patch(self.getter, self.attribute, self.new, self.spec, self.create, self.spec_set, self.autospec, self.new_callable, self.kwargs)
        patcher.attribute_name = self.attribute_name
        patcher.additional_patchers = [p.copy() for p in self.additional_patchers]
        return patcher

    def __call__(self, func):
        if isinstance(func, type):
            return self.decorate_class(func)
        return self.decorate_callable(func)

    def decorate_class(self, klass):
        for attr in dir(klass):
            if not attr.startswith(patch.TEST_PREFIX):
                pass
            else:
                attr_value = getattr(klass, attr)
                if not hasattr(attr_value, '__call__'):
                    pass
                else:
                    patcher = self.copy()
                    setattr(klass, attr, patcher(attr_value))
        return klass

    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        def patched(*args, **keywargs):
            extra_args = []
            entered_patchers = []
            exc_info = tuple()
            try:
                for patching in patched.patchings:
                    arg = patching.__enter__()
                    entered_patchers.append(patching)
                    if patching.attribute_name is not None:
                        keywargs.update(arg)
                    elif patching.new is DEFAULT:
                        extra_args.append(arg)
                args += tuple(extra_args)
                return func(*args, **keywargs)
            except:
                if patching not in entered_patchers and _is_started(patching):
                    entered_patchers.append(patching)
                exc_info = sys.exc_info()
                raise
            finally:
                for patching in reversed(entered_patchers):
                    patching.__exit__(*exc_info)

        patched.patchings = [self]
        return patched

    def get_original(self):
        target = self.getter()
        name = self.attribute
        original = DEFAULT
        local = False
        try:
            original = target.__dict__[name]
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        local = True
        if isinstance(target, ModuleType):
            self.create = True
        if name in _builtins and self.create or original is DEFAULT:
            raise AttributeError('%s does not have the attribute %r' % (target, name))
        return (original, local)

    def __enter__(self):
        new = self.new
        spec = self.spec
        spec_set = self.spec_set
        autospec = self.autospec
        kwargs = self.kwargs
        new_callable = self.new_callable
        self.target = self.getter()
        if spec is False:
            spec = None
        if spec_set is False:
            spec_set = None
        if autospec is False:
            autospec = None
        if spec is not None and autospec is not None:
            raise TypeError("Can't specify spec and autospec")
        if (spec is not None or autospec is not None) and spec_set not in (True, None):
            raise TypeError("Can't provide explicit spec_set *and* spec or autospec")
        (original, local) = self.get_original()
        if new is DEFAULT and autospec is None:
            inherit = False
            if spec is True:
                spec = original
                if spec_set is True:
                    spec_set = original
                    spec = None
            elif spec is not None:
                if spec_set is True:
                    spec_set = spec
                    spec = None
            elif spec_set is True:
                spec_set = original
            if spec is not None or spec_set is not None:
                if original is DEFAULT:
                    raise TypeError("Can't use 'spec' with create=True")
                if isinstance(original, type):
                    inherit = True
            Klass = MagicMock
            _kwargs = {}
            if new_callable is not None:
                Klass = new_callable
            elif spec is not None or spec_set is not None:
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if _is_list(this_spec):
                    not_callable = '__call__' not in this_spec
                else:
                    not_callable = not callable(this_spec)
                if not_callable:
                    Klass = NonCallableMagicMock
            if spec is not None:
                _kwargs['spec'] = spec
            if spec_set is not None:
                _kwargs['spec_set'] = spec_set
            if self.attribute:
                _kwargs['name'] = self.attribute
            _kwargs.update(kwargs)
            new = Klass(**_kwargs)
            if isinstance(Klass, type) and issubclass(Klass, NonCallableMock) and inherit and _is_instance_mock(new):
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if not _instance_callable(this_spec):
                    Klass = NonCallableMagicMock
                _kwargs.pop('name')
                new.return_value = Klass(_new_parent=new, _new_name='()', **_kwargs)
        elif autospec is not None:
            if new is not DEFAULT:
                raise TypeError("autospec creates the mock for you. Can't specify autospec and new.")
            if original is DEFAULT:
                raise TypeError("Can't use 'autospec' with create=True")
            spec_set = bool(spec_set)
            if autospec is True:
                autospec = original
            new = create_autospec(autospec, spec_set=spec_set, _name=self.attribute, **kwargs)
        elif kwargs:
            raise TypeError("Can't pass kwargs to a mock we aren't creating")
        new_attr = new
        self.temp_original = original
        self.is_local = local
        setattr(self.target, self.attribute, new_attr)
        if self.attribute_name is not None:
            extra_args = {}
            if self.new is DEFAULT:
                extra_args[self.attribute_name] = new
            for patching in self.additional_patchers:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.update(arg)
            return extra_args
        return new

    def __exit__(self, *exc_info):
        if not _is_started(self):
            raise RuntimeError('stop called on unstarted patcher')
        if self.is_local and self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
            if self.create or hasattr(self.target, self.attribute) and self.attribute in ('__doc__', '__module__', '__defaults__', '__annotations__', '__kwdefaults__'):
                setattr(self.target, self.attribute, self.temp_original)
        del self.temp_original
        del self.is_local
        del self.target
        for patcher in reversed(self.additional_patchers):
            if _is_started(patcher):
                patcher.__exit__(*exc_info)

    def start(self):
        result = self.__enter__()
        self._active_patches.append(self)
        return result

    def stop(self):
        try:
            self._active_patches.remove(self)
        except ValueError:
            pass
        return self.__exit__()

def _get_target(target):
    try:
        (target, attribute) = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError('Need a valid target to patch. You supplied: %r' % (target,))
    getter = lambda : _importer(target)
    return (getter, attribute)

def _patch_object(target, attribute, new=DEFAULT, spec=None, create=False, spec_set=None, autospec=None, new_callable=None, **kwargs):
    getter = lambda : target
    return _patch(getter, attribute, new, spec, create, spec_set, autospec, new_callable, kwargs)

def _patch_multiple(target, spec=None, create=False, spec_set=None, autospec=None, new_callable=None, **kwargs):
    if type(target) is str:
        getter = lambda : _importer(target)
    else:
        getter = lambda : target
    if not kwargs:
        raise ValueError('Must supply at least one keyword argument with patch.multiple')
    items = list(kwargs.items())
    (attribute, new) = items[0]
    patcher = _patch(getter, attribute, new, spec, create, spec_set, autospec, new_callable, {})
    patcher.attribute_name = attribute
    for (attribute, new) in items[1:]:
        this_patcher = _patch(getter, attribute, new, spec, create, spec_set, autospec, new_callable, {})
        this_patcher.attribute_name = attribute
        patcher.additional_patchers.append(this_patcher)
    return patcher

def patch(target, new=DEFAULT, spec=None, create=False, spec_set=None, autospec=None, new_callable=None, **kwargs):
    (getter, attribute) = _get_target(target)
    return _patch(getter, attribute, new, spec, create, spec_set, autospec, new_callable, kwargs)

class _patch_dict(object):

    def __init__(self, in_dict, values=(), clear=False, **kwargs):
        if isinstance(in_dict, str):
            in_dict = _importer(in_dict)
        self.in_dict = in_dict
        self.values = dict(values)
        self.values.update(kwargs)
        self.clear = clear
        self._original = None

    def __call__(self, f):
        if isinstance(f, type):
            return self.decorate_class(f)

        @wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return f(*args, **kw)
            finally:
                self._unpatch_dict()

        return _inner

    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if attr.startswith(patch.TEST_PREFIX) and hasattr(attr_value, '__call__'):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass

    def __enter__(self):
        self._patch_dict()

    def _patch_dict(self):
        values = self.values
        in_dict = self.in_dict
        clear = self.clear
        try:
            original = in_dict.copy()
        except AttributeError:
            original = {}
            for key in in_dict:
                original[key] = in_dict[key]
        self._original = original
        if clear:
            _clear_dict(in_dict)
        try:
            in_dict.update(values)
        except AttributeError:
            for key in values:
                in_dict[key] = values[key]

    def _unpatch_dict(self):
        in_dict = self.in_dict
        original = self._original
        _clear_dict(in_dict)
        try:
            in_dict.update(original)
        except AttributeError:
            for key in original:
                in_dict[key] = original[key]

    def __exit__(self, *args):
        self._unpatch_dict()
        return False

    start = __enter__
    stop = __exit__

def _clear_dict(in_dict):
    try:
        in_dict.clear()
    except AttributeError:
        keys = list(in_dict)
        for key in keys:
            del in_dict[key]

def _patch_stopall():
    for patch in reversed(_patch._active_patches):
        patch.stop()
patch.object = _patch_objectpatch.dict = _patch_dictpatch.multiple = _patch_multiplepatch.stopall = _patch_stopallpatch.TEST_PREFIX = 'test'magic_methods = 'lt le gt ge eq ne getitem setitem delitem len contains iter hash str sizeof enter exit divmod rdivmod neg pos abs invert complex int float index trunc floor ceil bool next 'numerics = 'add sub mul matmul div floordiv mod lshift rshift and xor or pow truediv'inplace = ' '.join('i%s' % n for n in numerics.split())right = ' '.join('r%s' % n for n in numerics.split())_non_defaults = {'__get__', '__set__', '__delete__', '__reversed__', '__missing__', '__reduce__', '__reduce_ex__', '__getinitargs__', '__getnewargs__', '__getstate__', '__setstate__', '__getformat__', '__setformat__', '__repr__', '__dir__', '__subclasses__', '__format__', '__getnewargs_ex__'}
def _get_method(name, func):

    def method(self, *args, **kw):
        return func(self, *args, **kw)

    method.__name__ = name
    return method
_magics = {'__%s__' % method for method in ' '.join([magic_methods, numerics, inplace, right]).split()}_all_magics = _magics | _non_defaults_unsupported_magics = {'__getattr__', '__setattr__', '__init__', '__new__', '__prepare____instancecheck__', '__subclasscheck__', '__del__'}_calculate_return_value = {'__hash__': lambda self: object.__hash__(self), '__str__': lambda self: object.__str__(self), '__sizeof__': lambda self: object.__sizeof__(self)}_return_values = {'__lt__': NotImplemented, '__gt__': NotImplemented, '__le__': NotImplemented, '__ge__': NotImplemented, '__int__': 1, '__contains__': False, '__len__': 0, '__exit__': False, '__complex__': 1j, '__float__': 1.0, '__bool__': True, '__index__': 1}
def _get_eq(self):

    def __eq__(other):
        ret_val = self.__eq__._mock_return_value
        if ret_val is not DEFAULT:
            return ret_val
        elif self is other:
            return True
        return NotImplemented

    return __eq__

def _get_ne(self):

    def __ne__(other):
        if self.__ne__._mock_return_value is not DEFAULT:
            return DEFAULT
        elif self is other:
            return False
        return NotImplemented

    return __ne__

def _get_iter(self):

    def __iter__():
        ret_val = self.__iter__._mock_return_value
        if ret_val is DEFAULT:
            return iter([])
        return iter(ret_val)

    return __iter__
_side_effect_methods = {'__eq__': _get_eq, '__ne__': _get_ne, '__iter__': _get_iter}
def _set_return_value(mock, method, name):
    fixed = _return_values.get(name, DEFAULT)
    if fixed is not DEFAULT:
        method.return_value = fixed
        return
    return_calulator = _calculate_return_value.get(name)
    if return_calulator is not None:
        try:
            return_value = return_calulator(mock)
        except AttributeError:
            return_value = AttributeError(name)
        method.return_value = return_value
        return
    side_effector = _side_effect_methods.get(name)
    if side_effector is not None:
        method.side_effect = side_effector(mock)

class MagicMixin(object):

    def __init__(self, *args, **kw):
        self._mock_set_magics()
        _safe_super(MagicMixin, self).__init__(*args, **kw)
        self._mock_set_magics()

    def _mock_set_magics(self):
        these_magics = _magics
        if getattr(self, '_mock_methods', None) is not None:
            these_magics = _magics.intersection(self._mock_methods)
            remove_magics = set()
            remove_magics = _magics - these_magics
            for entry in remove_magics:
                if entry in type(self).__dict__:
                    delattr(self, entry)
        these_magics = these_magics - set(type(self).__dict__)
        _type = type(self)
        for entry in these_magics:
            setattr(_type, entry, MagicProxy(entry, self))

class NonCallableMagicMock(MagicMixin, NonCallableMock):

    def mock_add_spec(self, spec, spec_set=False):
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()

class MagicMock(MagicMixin, Mock):

    def mock_add_spec(self, spec, spec_set=False):
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()

class MagicProxy(object):

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def __call__(self, *args, **kwargs):
        m = self.create_mock()
        return m(*args, **kwargs)

    def create_mock(self):
        entry = self.name
        parent = self.parent
        m = parent._get_child_mock(name=entry, _new_name=entry, _new_parent=parent)
        setattr(parent, entry, m)
        _set_return_value(parent, m, entry)
        return m

    def __get__(self, obj, _type=None):
        return self.create_mock()

class _ANY(object):

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return '<ANY>'
ANY = _ANY()
def _format_call_signature(name, args, kwargs):
    message = '%s(%%s)' % name
    formatted_args = ''
    args_string = ', '.join([repr(arg) for arg in args])
    kwargs_string = ', '.join(['%s=%r' % (key, value) for (key, value) in sorted(kwargs.items())])
    if args_string:
        formatted_args = args_string
    if kwargs_string:
        if formatted_args:
            formatted_args += ', '
        formatted_args += kwargs_string
    return message % formatted_args

class _Call(tuple):

    def __new__(cls, value=(), name='', parent=None, two=False, from_kall=True):
        args = ()
        kwargs = {}
        _len = len(value)
        if _len == 3:
            (name, args, kwargs) = value
        elif _len == 2:
            (first, second) = value
            if isinstance(first, str):
                name = first
                if isinstance(second, tuple):
                    args = second
                else:
                    kwargs = second
                    args = first
                    kwargs = second
            else:
                args = first
                kwargs = second
        elif _len == 1:
            (value,) = value
            if isinstance(value, str):
                name = value
            elif isinstance(value, tuple):
                args = value
            else:
                kwargs = value
        if two:
            return tuple.__new__(cls, (args, kwargs))
        return tuple.__new__(cls, (name, args, kwargs))

    def __init__(self, value=(), name=None, parent=None, two=False, from_kall=True):
        self.name = name
        self.parent = parent
        self.from_kall = from_kall

    def __eq__(self, other):
        if other is ANY:
            return True
        try:
            len_other = len(other)
        except TypeError:
            return False
        self_name = ''
        if len(self) == 2:
            (self_args, self_kwargs) = self
        else:
            (self_name, self_args, self_kwargs) = self
        other_name = ''
        if len_other == 0:
            other_args = ()
            other_kwargs = {}
        elif len_other == 3:
            (other_name, other_args, other_kwargs) = other
        elif len_other == 1:
            (value,) = other
            if isinstance(value, tuple):
                other_args = value
                other_kwargs = {}
            elif isinstance(value, str):
                other_name = value
                other_args = ()
                other_kwargs = {}
            else:
                other_args = ()
                other_kwargs = value
        elif len_other == 2:
            (first, second) = other
            if isinstance(first, str):
                other_name = first
                if isinstance(second, tuple):
                    other_args = second
                    other_kwargs = {}
                else:
                    other_args = ()
                    other_kwargs = second
            else:
                other_args = first
                other_kwargs = second
        else:
            return False
        if self_name and other_name != self_name:
            return False
        return (other_args, other_kwargs) == (self_args, self_kwargs)

    __ne__ = object.__ne__

    def __call__(self, *args, **kwargs):
        if self.name is None:
            return _Call(('', args, kwargs), name='()')
        name = self.name + '()'
        return _Call((self.name, args, kwargs), name=name, parent=self)

    def __getattr__(self, attr):
        if self.name is None:
            return _Call(name=attr, from_kall=False)
        name = '%s.%s' % (self.name, attr)
        return _Call(name=name, parent=self, from_kall=False)

    def count(self, *args, **kwargs):
        return self.__getattr__('count')(*args, **kwargs)

    def index(self, *args, **kwargs):
        return self.__getattr__('index')(*args, **kwargs)

    def __repr__(self):
        if not self.from_kall:
            name = self.name or 'call'
            if name.startswith('()'):
                name = 'call%s' % name
            return name
        if len(self) == 2:
            name = 'call'
            (args, kwargs) = self
        else:
            (name, args, kwargs) = self
            if not name:
                name = 'call'
            elif not name.startswith('()'):
                name = 'call.%s' % name
            else:
                name = 'call%s' % name
        return _format_call_signature(name, args, kwargs)

    def call_list(self):
        vals = []
        thing = self
        if thing is not None:
            if thing.from_kall:
                vals.append(thing)
            thing = thing.parent
        return _CallList(reversed(vals))
call = _Call(from_kall=False)
def create_autospec(spec, spec_set=False, instance=False, _parent=None, _name=None, **kwargs):
    if _is_list(spec):
        spec = type(spec)
    is_type = isinstance(spec, type)
    _kwargs = {'spec': spec}
    if spec_set:
        _kwargs = {'spec_set': spec}
    elif spec is None:
        _kwargs = {}
    if instance:
        _kwargs['_spec_as_instance'] = True
    _kwargs.update(kwargs)
    Klass = MagicMock
    if _kwargs and inspect.isdatadescriptor(spec):
        _kwargs = {}
    elif not _callable(spec):
        Klass = NonCallableMagicMock
    elif not _instance_callable(spec):
        Klass = NonCallableMagicMock
    _name = _kwargs.pop('name', _name)
    _new_name = _name
    if _parent is None:
        _new_name = ''
    mock = Klass(parent=_parent, _new_parent=_parent, _new_name=_new_name, name=_name, **_kwargs)
    if isinstance(spec, FunctionTypes):
        mock = _set_signature(mock, spec)
    else:
        _check_signature(spec, mock, is_type, instance)
    if not instance:
        _parent._mock_children[_name] = mock
    if 'return_value' not in kwargs:
        mock.return_value = create_autospec(spec, spec_set, instance=True, _name='()', _parent=mock)
    for entry in dir(spec):
        if _is_magic(entry):
            pass
        else:
            try:
                original = getattr(spec, entry)
            except AttributeError:
                continue
            kwargs = {'spec': original}
            if spec_set:
                kwargs = {'spec_set': original}
            if not isinstance(original, FunctionTypes):
                new = _SpecState(original, spec_set, mock, entry, instance)
                mock._mock_children[entry] = new
            else:
                parent = mock
                if isinstance(spec, FunctionTypes):
                    parent = mock.mock
                skipfirst = _must_skip(spec, entry, is_type)
                kwargs['_eat_self'] = skipfirst
                new = MagicMock(parent=parent, name=entry, _new_name=entry, _new_parent=parent, **kwargs)
                mock._mock_children[entry] = new
                _check_signature(original, new, skipfirst=skipfirst)
            if isinstance(new, FunctionTypes):
                setattr(mock, entry, new)
    return mock

def _must_skip(spec, entry, is_type):
    if not isinstance(spec, type):
        if entry in getattr(spec, '__dict__', {}):
            return False
        spec = spec.__class__
    for klass in spec.__mro__:
        result = klass.__dict__.get(entry, DEFAULT)
        if result is DEFAULT:
            pass
        else:
            if isinstance(result, (staticmethod, classmethod)):
                return False
            elif isinstance(getattr(result, '__get__', None), MethodWrapperTypes):
                return is_type
            return False
    return is_type

def _get_class(obj):
    try:
        return obj.__class__
    except AttributeError:
        return type(obj)

class _SpecState(object):

    def __init__(self, spec, spec_set=False, parent=None, name=None, ids=None, instance=False):
        self.spec = spec
        self.ids = ids
        self.spec_set = spec_set
        self.parent = parent
        self.instance = instance
        self.name = name
FunctionTypes = (type(create_autospec), type(ANY.__eq__))MethodWrapperTypes = (type(ANY.__eq__.__get__),)file_spec = None
def _iterate_read_data(read_data):
    sep = b'\n' if isinstance(read_data, bytes) else '\n'
    data_as_list = [l + sep for l in read_data.split(sep)]
    if data_as_list[-1] == sep:
        data_as_list = data_as_list[:-1]
    else:
        data_as_list[-1] = data_as_list[-1][:-1]
    for line in data_as_list:
        yield line

def mock_open(mock=None, read_data=''):
    global file_spec

    def _readlines_side_effect(*args, **kwargs):
        if handle.readlines.return_value is not None:
            return handle.readlines.return_value
        return list(_state[0])

    def _read_side_effect(*args, **kwargs):
        if handle.read.return_value is not None:
            return handle.read.return_value
        return type(read_data)().join(_state[0])

    def _readline_side_effect():
        while True:
            yield handle.readline.return_value
        for line in _state[0]:
            yield line
        while True:
            yield type(read_data)()

    if file_spec is None:
        import _io
        file_spec = list(set(dir(_io.TextIOWrapper)).union(set(dir(_io.BytesIO))))
    if mock is None:
        mock = MagicMock(name='open', spec=open)
    handle = MagicMock(spec=file_spec)
    handle.__enter__.return_value = handle
    _state = [_iterate_read_data(read_data), None]
    handle.write.return_value = None
    handle.read.return_value = None
    handle.readline.return_value = None
    handle.readlines.return_value = None
    handle.read.side_effect = _read_side_effect
    _state[1] = _readline_side_effect()
    handle.readline.side_effect = _state[1]
    handle.readlines.side_effect = _readlines_side_effect

    def reset_data(*args, **kwargs):
        _state[0] = _iterate_read_data(read_data)
        if handle.readline.side_effect == _state[1]:
            _state[1] = _readline_side_effect()
            handle.readline.side_effect = _state[1]
        return DEFAULT

    mock.side_effect = reset_data
    mock.return_value = handle
    return mock

class PropertyMock(Mock):

    def _get_child_mock(self, **kwargs):
        return MagicMock(**kwargs)

    def __get__(self, obj, obj_type):
        return self()

    def __set__(self, obj, val):
        self(val)

def seal(mock):
    mock._mock_sealed = True
    for attr in dir(mock):
        try:
            m = getattr(mock, attr)
        except AttributeError:
            continue
        if not isinstance(m, NonCallableMock):
            pass
        elif m._mock_new_parent is mock:
            seal(m)
