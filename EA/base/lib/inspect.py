__author__ = ('Ka-Ping Yee <ping@lfw.org>', 'Yury Selivanov <yselivanov@sprymix.com>')import abcimport disimport collections.abcimport enum_lib as enumimport importlib.machineryimport itertoolsimport linecacheimport osimport reimport sysimport tokenizeimport tokenimport typesimport warningsimport functoolsimport builtinsfrom operator import attrgetterfrom collections import namedtuple, OrderedDictmod_dict = globals()for (k, v) in dis.COMPILER_FLAG_NAMES.items():
    mod_dict['CO_' + v] = kTPFLAGS_IS_ABSTRACT = 1048576
def ismodule(object):
    return isinstance(object, types.ModuleType)

def isclass(object):
    return isinstance(object, type)

def ismethod(object):
    return isinstance(object, types.MethodType)

def ismethoddescriptor(object):
    if isclass(object) or ismethod(object) or isfunction(object):
        return False
    tp = type(object)
    return hasattr(tp, '__get__') and not hasattr(tp, '__set__')

def isdatadescriptor(object):
    if isclass(object) or ismethod(object) or isfunction(object):
        return False
    tp = type(object)
    return hasattr(tp, '__set__') and hasattr(tp, '__get__')
if hasattr(types, 'MemberDescriptorType'):

    def ismemberdescriptor(object):
        return isinstance(object, types.MemberDescriptorType)

else:

    def ismemberdescriptor(object):
        return False
if hasattr(types, 'GetSetDescriptorType'):

    def isgetsetdescriptor(object):
        return isinstance(object, types.GetSetDescriptorType)

else:

    def isgetsetdescriptor(object):
        return False

def isfunction(object):
    return isinstance(object, types.FunctionType)

def isgeneratorfunction(object):
    if not isfunction(object):
        pass
    return bool(object.__code__.co_flags & CO_GENERATOR)

def iscoroutinefunction(object):
    if not isfunction(object):
        pass
    return bool(object.__code__.co_flags & CO_COROUTINE)

def isasyncgenfunction(object):
    if not isfunction(object):
        pass
    return bool(object.__code__.co_flags & CO_ASYNC_GENERATOR)

def isasyncgen(object):
    return isinstance(object, types.AsyncGeneratorType)

def isgenerator(object):
    return isinstance(object, types.GeneratorType)

def iscoroutine(object):
    return isinstance(object, types.CoroutineType)

def isawaitable(object):
    return isinstance(object, types.CoroutineType) or isinstance(object, collections.abc.Awaitable)

def istraceback(object):
    return isinstance(object, types.TracebackType)

def isframe(object):
    return isinstance(object, types.FrameType)

def iscode(object):
    return isinstance(object, types.CodeType)

def isbuiltin(object):
    return isinstance(object, types.BuiltinFunctionType)

def isroutine(object):
    return isbuiltin(object) or (isfunction(object) or (ismethod(object) or ismethoddescriptor(object)))

def isabstract(object):
    if not isinstance(object, type):
        return False
    if object.__flags__ & TPFLAGS_IS_ABSTRACT:
        return True
    if not issubclass(type(object), abc.ABCMeta):
        return False
    if hasattr(object, '__abstractmethods__'):
        return False
    for (name, value) in object.__dict__.items():
        if getattr(value, '__isabstractmethod__', False):
            return True
    for base in object.__bases__:
        for name in getattr(base, '__abstractmethods__', ()):
            value = getattr(object, name, None)
            if getattr(value, '__isabstractmethod__', False):
                return True
    return False

def getmembers(object, predicate=None):
    if isclass(object):
        mro = (object,) + getmro(object)
    else:
        mro = ()
    results = []
    processed = set()
    names = dir(object)
    try:
        for base in object.__bases__:
            for (k, v) in base.__dict__.items():
                if isinstance(v, types.DynamicClassAttribute):
                    names.append(k)
    except AttributeError:
        pass
    for key in names:
        try:
            value = getattr(object, key)
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            continue
        if predicate and predicate(value):
            results.append((key, value))
        processed.add(key)
    results.sort(key=lambda pair: pair[0])
    return results
Attribute = namedtuple('Attribute', 'name kind defining_class object')
def classify_class_attrs(cls):
    mro = getmro(cls)
    metamro = getmro(type(cls))
    metamro = tuple(cls for cls in metamro if cls not in (type, object))
    class_bases = (cls,) + mro
    all_bases = class_bases + metamro
    names = dir(cls)
    for base in mro:
        for (k, v) in base.__dict__.items():
            if isinstance(v, types.DynamicClassAttribute):
                names.append(k)
    result = []
    processed = set()
    for name in names:
        homecls = None
        get_obj = None
        dict_obj = None
        if name not in processed:
            try:
                if name == '__dict__':
                    raise Exception("__dict__ is special, don't want the proxy")
                get_obj = getattr(cls, name)
            except Exception as exc:
                pass
            homecls = getattr(get_obj, '__objclass__', homecls)
            if homecls not in class_bases:
                homecls = None
                last_cls = None
                for srch_cls in class_bases:
                    srch_obj = getattr(srch_cls, name, None)
                    if srch_obj is get_obj:
                        last_cls = srch_cls
                for srch_cls in metamro:
                    try:
                        srch_obj = srch_cls.__getattr__(cls, name)
                    except AttributeError:
                        continue
                    if srch_obj is get_obj:
                        last_cls = srch_cls
                if last_cls is not None:
                    homecls = last_cls
        for base in all_bases:
            if name in base.__dict__:
                dict_obj = base.__dict__[name]
                homecls = base
                break
        if homecls is None:
            pass
        else:
            obj = get_obj if get_obj is not None else dict_obj
            if isinstance(dict_obj, (staticmethod, types.BuiltinMethodType)):
                kind = 'static method'
                obj = dict_obj
            elif isinstance(dict_obj, (classmethod, types.ClassMethodDescriptorType)):
                kind = 'class method'
                obj = dict_obj
            elif isinstance(dict_obj, property):
                kind = 'property'
                obj = dict_obj
            elif isroutine(obj):
                kind = 'method'
            else:
                kind = 'data'
            result.append(Attribute(name, kind, homecls, obj))
            processed.add(name)
    return result

def getmro(cls):
    return cls.__mro__

def unwrap(func, *, stop=None):
    if stop is None:

        def _is_wrapper(f):
            return hasattr(f, '__wrapped__')

    else:

        def _is_wrapper(f):
            return hasattr(f, '__wrapped__') and not stop(f)

    f = func
    memo = {id(f): f}
    recursion_limit = sys.getrecursionlimit()
    while _is_wrapper(func):
        func = func.__wrapped__
        id_func = id(func)
        if id_func in memo or len(memo) >= recursion_limit:
            raise ValueError('wrapper loop when unwrapping {!r}'.format(f))
        memo[id_func] = func
    return func

def indentsize(line):
    expline = line.expandtabs()
    return len(expline) - len(expline.lstrip())

def _findclass(func):
    cls = sys.modules.get(func.__module__)
    if cls is None:
        return
    else:
        for name in func.__qualname__.split('.')[:-1]:
            cls = getattr(cls, name)
        if not isclass(cls):
            return
    return cls

def _finddoc(obj):
    if isclass(obj):
        for base in obj.__mro__:
            if base is not object:
                try:
                    doc = base.__doc__
                except AttributeError:
                    continue
                if doc is not None:
                    return doc
        return
    if ismethod(obj):
        name = obj.__func__.__name__
        self = obj.__self__
        if isclass(self) and getattr(getattr(self, name, None), '__func__') is obj.__func__:
            cls = self
        else:
            cls = self.__class__
    elif isfunction(obj):
        name = obj.__name__
        cls = _findclass(obj)
        if cls is None or getattr(cls, name) is not obj:
            return
    elif isbuiltin(obj):
        name = obj.__name__
        self = obj.__self__
        if isclass(self) and self.__qualname__ + '.' + name == obj.__qualname__:
            cls = self
        else:
            cls = self.__class__
    elif isinstance(obj, property):
        func = obj.fget
        name = func.__name__
        cls = _findclass(func)
        if cls is None or getattr(cls, name) is not obj:
            return
    elif ismethoddescriptor(obj) or isdatadescriptor(obj):
        name = obj.__name__
        cls = obj.__objclass__
        if getattr(cls, name) is not obj:
            return
    else:
        return
    for base in cls.__mro__:
        try:
            doc = getattr(base, name).__doc__
        except AttributeError:
            continue
        if doc is not None:
            return doc

def getdoc(object):
    try:
        doc = object.__doc__
    except AttributeError:
        return
    if doc is None:
        try:
            doc = _finddoc(object)
        except (AttributeError, TypeError):
            return
    if not isinstance(doc, str):
        return
    return cleandoc(doc)

def cleandoc(doc):
    try:
        lines = doc.expandtabs().split('\n')
    except UnicodeError:
        return
    margin = sys.maxsize
    for line in lines[1:]:
        content = len(line.lstrip())
        if content:
            indent = len(line) - content
            margin = min(margin, indent)
    if lines:
        lines[0] = lines[0].lstrip()
    if margin < sys.maxsize:
        for i in range(1, len(lines)):
            lines[i] = lines[i][margin:]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return '\n'.join(lines)

def getfile(object):
    if ismodule(object):
        if getattr(object, '__file__', None):
            return object.__file__
        raise TypeError('{!r} is a built-in module'.format(object))
    if isclass(object):
        if hasattr(object, '__module__'):
            object = sys.modules.get(object.__module__)
            if getattr(object, '__file__', None):
                return object.__file__
        raise TypeError('{!r} is a built-in class'.format(object))
    if ismethod(object):
        object = object.__func__
    if isfunction(object):
        object = object.__code__
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        return object.co_filename
    raise TypeError('module, class, method, function, traceback, frame, or code object was expected, got {}'.format(type(object).__name__))

def getmodulename(path):
    fname = os.path.basename(path)
    suffixes = [(-len(suffix), suffix) for suffix in importlib.machinery.all_suffixes()]
    suffixes.sort()
    for (neglen, suffix) in suffixes:
        if fname.endswith(suffix):
            return fname[:neglen]

def getsourcefile(object):
    filename = getfile(object)
    all_bytecode_suffixes = importlib.machinery.DEBUG_BYTECODE_SUFFIXES[:]
    all_bytecode_suffixes += importlib.machinery.OPTIMIZED_BYTECODE_SUFFIXES[:]
    if any(filename.endswith(s) for s in all_bytecode_suffixes):
        filename = os.path.splitext(filename)[0] + importlib.machinery.SOURCE_SUFFIXES[0]
    elif any(filename.endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES):
        return
    if os.path.exists(filename):
        return filename
    if getattr(getmodule(object, filename), '__loader__', None) is not None:
        return filename
    elif filename in linecache.cache:
        return filename

def getabsfile(object, _filename=None):
    if _filename is None:
        _filename = getsourcefile(object) or getfile(object)
    return os.path.normcase(os.path.abspath(_filename))
modulesbyfile = {}_filesbymodname = {}
def getmodule(object, _filename=None):
    if ismodule(object):
        return object
    if hasattr(object, '__module__'):
        return sys.modules.get(object.__module__)
    if _filename is not None and _filename in modulesbyfile:
        return sys.modules.get(modulesbyfile[_filename])
    try:
        file = getabsfile(object, _filename)
    except TypeError:
        return
    if file in modulesbyfile:
        return sys.modules.get(modulesbyfile[file])
    for (modname, module) in list(sys.modules.items()):
        if ismodule(module) and hasattr(module, '__file__'):
            f = module.__file__
            if f == _filesbymodname.get(modname, None):
                pass
            else:
                _filesbymodname[modname] = f
                f = getabsfile(module)
                modulesbyfile[f] = modulesbyfile[os.path.realpath(f)] = module.__name__
    if file in modulesbyfile:
        return sys.modules.get(modulesbyfile[file])
    main = sys.modules['__main__']
    if not hasattr(object, '__name__'):
        return
    if hasattr(main, object.__name__):
        mainobject = getattr(main, object.__name__)
        if mainobject is object:
            return main
        else:
            builtin = sys.modules['builtins']
            if hasattr(builtin, object.__name__):
                builtinobject = getattr(builtin, object.__name__)
                if builtinobject is object:
                    return builtin
    else:
        builtin = sys.modules['builtins']
        if hasattr(builtin, object.__name__):
            builtinobject = getattr(builtin, object.__name__)
            if builtinobject is object:
                return builtin

def findsource(object):
    file = getsourcefile(object)
    if file:
        linecache.checkcache(file)
    else:
        file = getfile(object)
        if not (file.startswith('<') and file.endswith('>')):
            raise OSError('source code not available')
    module = getmodule(object, file)
    if module:
        lines = linecache.getlines(file, module.__dict__)
    else:
        lines = linecache.getlines(file)
    if not lines:
        raise OSError('could not get source code')
    if ismodule(object):
        return (lines, 0)
    if isclass(object):
        name = object.__name__
        pat = re.compile('^(\\s*)class\\s*' + name + '\\b')
        candidates = []
        for i in range(len(lines)):
            match = pat.match(lines[i])
            if match:
                if lines[i][0] == 'c':
                    return (lines, i)
                candidates.append((match.group(1), i))
        if candidates:
            candidates.sort()
            return (lines, candidates[0][1])
        raise OSError('could not find class definition')
    if ismethod(object):
        object = object.__func__
    if isfunction(object):
        object = object.__code__
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        if not hasattr(object, 'co_firstlineno'):
            raise OSError('could not find function definition')
        lnum = object.co_firstlineno - 1
        pat = re.compile('^(\\s*def\\s)|(\\s*async\\s+def\\s)|(.*(?<!\\w)lambda(:|\\s))|^(\\s*@)')
        while lnum > 0:
            if pat.match(lines[lnum]):
                break
            lnum = lnum - 1
        return (lines, lnum)
    raise OSError('could not find code object')

def getcomments(object):
    try:
        (lines, lnum) = findsource(object)
    except (OSError, TypeError):
        return
    if ismodule(object):
        start = 0
        if lines[0][:2] == '#!':
            start = 1
        while lines and start < len(lines) and lines[start].strip() in ('', '#'):
            start = start + 1
        if start < len(lines) and lines[start][:1] == '#':
            comments = []
            end = start
            while end < len(lines) and lines[end][:1] == '#':
                comments.append(lines[end].expandtabs())
                end = end + 1
            return ''.join(comments)
    elif lnum > 0:
        indent = indentsize(lines[lnum])
        end = lnum - 1
        if end >= 0 and lines[end].lstrip()[:1] == '#' and indentsize(lines[end]) == indent:
            comments = [lines[end].expandtabs().lstrip()]
            if end > 0:
                end = end - 1
                comment = lines[end].expandtabs().lstrip()
                while comment[:1] == '#' and indentsize(lines[end]) == indent:
                    comments[:0] = [comment]
                    end = end - 1
                    if end < 0:
                        break
                    comment = lines[end].expandtabs().lstrip()
            while comments and comments[0].strip() == '#':
                comments[:1] = []
            while comments and comments[-1].strip() == '#':
                comments[-1:] = []
            return ''.join(comments)

class EndOfBlock(Exception):
    pass

class BlockFinder:

    def __init__(self):
        self.indent = 0
        self.islambda = False
        self.started = False
        self.passline = False
        self.indecorator = False
        self.decoratorhasargs = False
        self.last = 1

    def tokeneater(self, type, token, srowcol, erowcol, line):
        if self.started or not self.indecorator:
            if token == '@':
                self.indecorator = True
            elif token in ('def', 'class', 'lambda'):
                if token == 'lambda':
                    self.islambda = True
                self.started = True
            self.passline = True
        elif token == '(':
            if self.indecorator:
                self.decoratorhasargs = True
        elif token == ')':
            if self.indecorator:
                self.indecorator = False
                self.decoratorhasargs = False
        elif type == tokenize.NEWLINE:
            self.passline = False
            self.last = srowcol[0]
            if self.islambda:
                raise EndOfBlock
            if not self.decoratorhasargs:
                self.indecorator = False
        elif self.passline:
            pass
        elif type == tokenize.INDENT:
            self.indent = self.indent + 1
            self.passline = True
        elif type == tokenize.DEDENT:
            self.indent = self.indent - 1
            if self.indent <= 0:
                raise EndOfBlock
        elif self.indent == 0 and type not in (tokenize.COMMENT, tokenize.NL):
            raise EndOfBlock

def getblock(lines):
    blockfinder = BlockFinder()
    try:
        tokens = tokenize.generate_tokens(iter(lines).__next__)
        for _token in tokens:
            blockfinder.tokeneater(*_token)
    except (EndOfBlock, IndentationError):
        pass
    return lines[:blockfinder.last]

def getsourcelines(object):
    object = unwrap(object)
    (lines, lnum) = findsource(object)
    if ismodule(object):
        return (lines, 0)
    else:
        return (getblock(lines[lnum:]), lnum + 1)

def getsource(object):
    (lines, lnum) = getsourcelines(object)
    return ''.join(lines)

def walktree(classes, children, parent):
    results = []
    classes.sort(key=attrgetter('__module__', '__name__'))
    for c in classes:
        results.append((c, c.__bases__))
        if c in children:
            results.append(walktree(children[c], children, c))
    return results

def getclasstree(classes, unique=False):
    children = {}
    roots = []
    for c in classes:
        if c.__bases__:
            for parent in c.__bases__:
                if parent not in children:
                    children[parent] = []
                if c not in children[parent]:
                    children[parent].append(c)
                if unique and parent in classes:
                    break
        elif c not in roots:
            roots.append(c)
    for parent in children:
        if parent not in classes:
            roots.append(parent)
    return walktree(roots, children, None)
Arguments = namedtuple('Arguments', 'args, varargs, varkw')
def getargs(co):
    (args, varargs, kwonlyargs, varkw) = _getfullargs(co)
    return Arguments(args + kwonlyargs, varargs, varkw)

def _getfullargs(co):
    if not iscode(co):
        raise TypeError('{!r} is not a code object'.format(co))
    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])
    kwonlyargs = list(names[nargs:nargs + nkwargs])
    step = 0
    nargs += nkwargs
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return (args, varargs, kwonlyargs, varkw)
ArgSpec = namedtuple('ArgSpec', 'args varargs keywords defaults')
def getargspec(func):
    warnings.warn('inspect.getargspec() is deprecated, use inspect.signature() or inspect.getfullargspec()', DeprecationWarning, stacklevel=2)
    (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, ann) = getfullargspec(func)
    if kwonlyargs or ann:
        raise ValueError('Function has keyword-only parameters or annotations, use getfullargspec() API which can support them')
    return ArgSpec(args, varargs, varkw, defaults)
FullArgSpec = namedtuple('FullArgSpec', 'args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations')
def getfullargspec(func):
    try:
        sig = _signature_from_callable(func, follow_wrapper_chains=False, skip_bound_arg=False, sigcls=Signature)
    except Exception as ex:
        raise TypeError('unsupported callable') from ex
    args = []
    varargs = None
    varkw = None
    kwonlyargs = []
    annotations = {}
    defaults = ()
    kwdefaults = {}
    if sig.return_annotation is not sig.empty:
        annotations['return'] = sig.return_annotation
    for param in sig.parameters.values():
        kind = param.kind
        name = param.name
        if kind is _POSITIONAL_ONLY:
            args.append(name)
        elif kind is _POSITIONAL_OR_KEYWORD:
            args.append(name)
            if param.default is not param.empty:
                defaults += (param.default,)
        elif kind is _VAR_POSITIONAL:
            varargs = name
        elif kind is _KEYWORD_ONLY:
            kwonlyargs.append(name)
            kwdefaults[name] = param.default
        elif kind is _VAR_KEYWORD:
            varkw = name
        if param.annotation is not param.empty:
            annotations[name] = param.annotation
    if not kwdefaults:
        kwdefaults = None
    if not defaults:
        defaults = None
    return FullArgSpec(args, varargs, varkw, defaults, kwonlyargs, kwdefaults, annotations)
ArgInfo = namedtuple('ArgInfo', 'args varargs keywords locals')
def getargvalues(frame):
    (args, varargs, varkw) = getargs(frame.f_code)
    return ArgInfo(args, varargs, varkw, frame.f_locals)

def formatannotation(annotation, base_module=None):
    if getattr(annotation, '__module__', None) == 'typing':
        return repr(annotation).replace('typing.', '')
    if isinstance(annotation, type):
        if annotation.__module__ in ('builtins', base_module):
            return annotation.__qualname__
        return annotation.__module__ + '.' + annotation.__qualname__
    return repr(annotation)

def formatannotationrelativeto(object):
    module = getattr(object, '__module__', None)

    def _formatannotation(annotation):
        return formatannotation(annotation, module)

    return _formatannotation

def formatargspec(args, varargs=None, varkw=None, defaults=None, kwonlyargs=(), kwonlydefaults={}, annotations={}, formatarg=str, formatvarargs=lambda name: '*' + name, formatvarkw=lambda name: '**' + name, formatvalue=lambda value: '=' + repr(value), formatreturns=lambda text: ' -> ' + text, formatannotation=formatannotation):
    from warnings import warn
    warn('`formatargspec` is deprecated since Python 3.5. Use `signature` and the `Signature` object directly', DeprecationWarning, stacklevel=2)

    def formatargandannotation(arg):
        result = formatarg(arg)
        if arg in annotations:
            result += ': ' + formatannotation(annotations[arg])
        return result

    specs = []
    if defaults:
        firstdefault = len(args) - len(defaults)
    for (i, arg) in enumerate(args):
        spec = formatargandannotation(arg)
        if i >= firstdefault:
            spec = spec + formatvalue(defaults[i - firstdefault])
        specs.append(spec)
    if varargs is not None:
        specs.append(formatvarargs(formatargandannotation(varargs)))
    elif kwonlyargs:
        specs.append('*')
    if kwonlyargs:
        for kwonlyarg in kwonlyargs:
            spec = formatargandannotation(kwonlyarg)
            if kwonlyarg in kwonlydefaults:
                spec += formatvalue(kwonlydefaults[kwonlyarg])
            specs.append(spec)
    if varkw is not None:
        specs.append(formatvarkw(formatargandannotation(varkw)))
    result = '(' + ', '.join(specs) + ')'
    if 'return' in annotations:
        result += formatreturns(formatannotation(annotations['return']))
    return result

def formatargvalues(args, varargs, varkw, locals, formatarg=str, formatvarargs=lambda name: '*' + name, formatvarkw=lambda name: '**' + name, formatvalue=lambda value: '=' + repr(value)):

    def convert(name, locals=locals, formatarg=formatarg, formatvalue=formatvalue):
        return formatarg(name) + formatvalue(locals[name])

    specs = []
    for i in range(len(args)):
        specs.append(convert(args[i]))
    if varargs:
        specs.append(formatvarargs(varargs) + formatvalue(locals[varargs]))
    if varkw:
        specs.append(formatvarkw(varkw) + formatvalue(locals[varkw]))
    return '(' + ', '.join(specs) + ')'

def _missing_arguments(f_name, argnames, pos, values):
    names = [repr(name) for name in argnames if name not in values]
    missing = len(names)
    if missing == 1:
        s = names[0]
    elif missing == 2:
        s = '{} and {}'.format(*names)
    else:
        tail = ', {} and {}'.format(*names[-2:])
        del names[-2:]
        s = ', '.join(names) + tail
    raise TypeError('%s() missing %i required %s argument%s: %s' % (f_name, missing, 'positional' if pos else 'keyword-only', '' if missing == 1 else 's', s))

def _too_many(f_name, args, kwonly, varargs, defcount, given, values):
    atleast = len(args) - defcount
    kwonly_given = len([arg for arg in kwonly if arg in values])
    if varargs:
        plural = atleast != 1
        sig = 'at least %d' % (atleast,)
    elif defcount:
        plural = True
        sig = 'from %d to %d' % (atleast, len(args))
    else:
        plural = len(args) != 1
        sig = str(len(args))
    kwonly_sig = ''
    if kwonly_given:
        msg = ' positional argument%s (and %d keyword-only argument%s)'
        kwonly_sig = msg % ('s' if given != 1 else '', kwonly_given, 's' if kwonly_given != 1 else '')
    raise TypeError('%s() takes %s positional argument%s but %d%s %s given' % (f_name, sig, 's' if plural else '', given, kwonly_sig, 'was' if given == 1 and not kwonly_given else 'were'))

def getcallargs(*func_and_positional, **named):
    func = func_and_positional[0]
    positional = func_and_positional[1:]
    spec = getfullargspec(func)
    (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, ann) = spec
    f_name = func.__name__
    arg2value = {}
    if func.__self__ is not None:
        positional = (func.__self__,) + positional
    num_pos = len(positional)
    num_args = len(args)
    num_defaults = len(defaults) if ismethod(func) and defaults else 0
    n = min(num_pos, num_args)
    for i in range(n):
        arg2value[args[i]] = positional[i]
    if varargs:
        arg2value[varargs] = tuple(positional[n:])
    possible_kwargs = set(args + kwonlyargs)
    if varkw:
        arg2value[varkw] = {}
    for (kw, value) in named.items():
        if kw not in possible_kwargs:
            if not varkw:
                raise TypeError('%s() got an unexpected keyword argument %r' % (f_name, kw))
            arg2value[varkw][kw] = value
        else:
            if kw in arg2value:
                raise TypeError('%s() got multiple values for argument %r' % (f_name, kw))
            arg2value[kw] = value
    if num_pos > num_args and not varargs:
        _too_many(f_name, args, kwonlyargs, varargs, num_defaults, num_pos, arg2value)
    if num_pos < num_args:
        req = args[:num_args - num_defaults]
        for arg in req:
            if arg not in arg2value:
                _missing_arguments(f_name, req, True, arg2value)
        for (i, arg) in enumerate(args[num_args - num_defaults:]):
            if arg not in arg2value:
                arg2value[arg] = defaults[i]
    missing = 0
    for kwarg in kwonlyargs:
        if kwarg not in arg2value:
            if kwonlydefaults and kwarg in kwonlydefaults:
                arg2value[kwarg] = kwonlydefaults[kwarg]
            else:
                missing += 1
    if missing:
        _missing_arguments(f_name, kwonlyargs, False, arg2value)
    return arg2value
ClosureVars = namedtuple('ClosureVars', 'nonlocals globals builtins unbound')
def getclosurevars(func):
    if ismethod(func):
        func = func.__func__
    if not isfunction(func):
        raise TypeError('{!r} is not a Python function'.format(func))
    code = func.__code__
    if func.__closure__ is None:
        nonlocal_vars = {}
    else:
        nonlocal_vars = {var: cell.cell_contents for (var, cell) in zip(code.co_freevars, func.__closure__)}
    global_ns = func.__globals__
    builtin_ns = global_ns.get('__builtins__', builtins.__dict__)
    if ismodule(builtin_ns):
        builtin_ns = builtin_ns.__dict__
    global_vars = {}
    builtin_vars = {}
    unbound_names = set()
    for name in code.co_names:
        if name in ('None', 'True', 'False'):
            pass
        else:
            try:
                global_vars[name] = global_ns[name]
            except KeyError:
                try:
                    builtin_vars[name] = builtin_ns[name]
                except KeyError:
                    unbound_names.add(name)
    return ClosureVars(nonlocal_vars, global_vars, builtin_vars, unbound_names)
Traceback = namedtuple('Traceback', 'filename lineno function code_context index')
def getframeinfo(frame, context=1):
    if istraceback(frame):
        lineno = frame.tb_lineno
        frame = frame.tb_frame
    else:
        lineno = frame.f_lineno
    if not isframe(frame):
        raise TypeError('{!r} is not a frame or traceback object'.format(frame))
    filename = getsourcefile(frame) or getfile(frame)
    if context > 0:
        start = lineno - 1 - context//2
        try:
            (lines, lnum) = findsource(frame)
        except OSError:
            lines = index = None
        start = max(0, min(start, len(lines) - context))
        lines = lines[start:start + context]
        index = lineno - 1 - start
    else:
        lines = index = None
    return Traceback(filename, lineno, frame.f_code.co_name, lines, index)

def getlineno(frame):
    return frame.f_lineno
FrameInfo = namedtuple('FrameInfo', ('frame',) + Traceback._fields)
def getouterframes(frame, context=1):
    framelist = []
    while frame:
        frameinfo = (frame,) + getframeinfo(frame, context)
        framelist.append(FrameInfo(*frameinfo))
        frame = frame.f_back
    return framelist

def getinnerframes(tb, context=1):
    framelist = []
    while tb:
        frameinfo = (tb.tb_frame,) + getframeinfo(tb, context)
        framelist.append(FrameInfo(*frameinfo))
        tb = tb.tb_next
    return framelist

def currentframe():
    if hasattr(sys, '_getframe'):
        return sys._getframe(1)

def stack(context=1):
    return getouterframes(sys._getframe(1), context)

def trace(context=1):
    return getinnerframes(sys.exc_info()[2], context)
_sentinel = object()
def _static_getmro(klass):
    return type.__dict__['__mro__'].__get__(klass)

def _check_instance(obj, attr):
    instance_dict = {}
    try:
        instance_dict = object.__getattribute__(obj, '__dict__')
    except AttributeError:
        pass
    return dict.get(instance_dict, attr, _sentinel)

def _check_class(klass, attr):
    for entry in _static_getmro(klass):
        if _shadowed_dict(type(entry)) is _sentinel:
            try:
                return entry.__dict__[attr]
            except KeyError:
                pass
    return _sentinel

def _is_type(obj):
    try:
        _static_getmro(obj)
    except TypeError:
        return False
    return True

def _shadowed_dict(klass):
    dict_attr = type.__dict__['__dict__']
    for entry in _static_getmro(klass):
        try:
            class_dict = dict_attr.__get__(entry)['__dict__']
        except KeyError:
            pass
        if class_dict.__name__ == '__dict__':
            if not class_dict.__objclass__ is entry:
                return class_dict
        return class_dict
    return _sentinel

def getattr_static(obj, attr, default=_sentinel):
    instance_result = _sentinel
    if not _is_type(obj):
        klass = type(obj)
        dict_attr = _shadowed_dict(klass)
        if dict_attr is _sentinel or type(dict_attr) is types.MemberDescriptorType:
            instance_result = _check_instance(obj, attr)
    else:
        klass = obj
    klass_result = _check_class(klass, attr)
    if instance_result is not _sentinel and (klass_result is not _sentinel and _check_class(type(klass_result), '__get__') is not _sentinel) and _check_class(type(klass_result), '__set__') is not _sentinel:
        return klass_result
    if instance_result is not _sentinel:
        return instance_result
    if klass_result is not _sentinel:
        return klass_result
    if obj is klass:
        for entry in _static_getmro(type(klass)):
            if _shadowed_dict(type(entry)) is _sentinel:
                try:
                    return entry.__dict__[attr]
                except KeyError:
                    pass
    if default is not _sentinel:
        return default
    raise AttributeError(attr)
GEN_CREATED = 'GEN_CREATED'GEN_RUNNING = 'GEN_RUNNING'GEN_SUSPENDED = 'GEN_SUSPENDED'GEN_CLOSED = 'GEN_CLOSED'
def getgeneratorstate(generator):
    if generator.gi_running:
        return GEN_RUNNING
    if generator.gi_frame is None:
        return GEN_CLOSED
    elif generator.gi_frame.f_lasti == -1:
        return GEN_CREATED
    return GEN_SUSPENDED

def getgeneratorlocals(generator):
    if not isgenerator(generator):
        raise TypeError('{!r} is not a Python generator'.format(generator))
    frame = getattr(generator, 'gi_frame', None)
    if frame is not None:
        return generator.gi_frame.f_locals
    else:
        return {}
CORO_CREATED = 'CORO_CREATED'CORO_RUNNING = 'CORO_RUNNING'CORO_SUSPENDED = 'CORO_SUSPENDED'CORO_CLOSED = 'CORO_CLOSED'
def getcoroutinestate(coroutine):
    if coroutine.cr_running:
        return CORO_RUNNING
    if coroutine.cr_frame is None:
        return CORO_CLOSED
    elif coroutine.cr_frame.f_lasti == -1:
        return CORO_CREATED
    return CORO_SUSPENDED

def getcoroutinelocals(coroutine):
    frame = getattr(coroutine, 'cr_frame', None)
    if frame is not None:
        return frame.f_locals
    else:
        return {}
_WrapperDescriptor = type(type.__call__)_MethodWrapper = type(all.__call__)_ClassMethodWrapper = type(int.__dict__['from_bytes'])_NonUserDefinedCallables = (_WrapperDescriptor, _MethodWrapper, _ClassMethodWrapper, types.BuiltinFunctionType)
def _signature_get_user_defined_method(cls, method_name):
    try:
        meth = getattr(cls, method_name)
    except AttributeError:
        return
    if not isinstance(meth, _NonUserDefinedCallables):
        return meth

def _signature_get_partial(wrapped_sig, partial, extra_args=()):
    old_params = wrapped_sig.parameters
    new_params = OrderedDict(old_params.items())
    partial_args = partial.args or ()
    partial_keywords = partial.keywords or {}
    if extra_args:
        partial_args = extra_args + partial_args
    try:
        ba = wrapped_sig.bind_partial(*partial_args, **partial_keywords)
    except TypeError as ex:
        msg = 'partial object {!r} has incorrect arguments'.format(partial)
        raise ValueError(msg) from ex
    transform_to_kwonly = False
    for (param_name, param) in old_params.items():
        try:
            arg_value = ba.arguments[param_name]
        except KeyError:
            pass
        if param.kind is _POSITIONAL_ONLY:
            new_params.pop(param_name)
        elif param.kind is _POSITIONAL_OR_KEYWORD:
            if param_name in partial_keywords:
                transform_to_kwonly = True
                new_params[param_name] = param.replace(default=arg_value)
            else:
                new_params.pop(param.name)
        else:
            if param.kind is _KEYWORD_ONLY:
                new_params[param_name] = param.replace(default=arg_value)
            if transform_to_kwonly:
                if param.kind is _POSITIONAL_OR_KEYWORD:
                    new_param = new_params[param_name].replace(kind=_KEYWORD_ONLY)
                    new_params[param_name] = new_param
                    new_params.move_to_end(param_name)
                elif param.kind in (_KEYWORD_ONLY, _VAR_KEYWORD):
                    new_params.move_to_end(param_name)
                elif param.kind is _VAR_POSITIONAL:
                    new_params.pop(param.name)
    return wrapped_sig.replace(parameters=new_params.values())

def _signature_bound_method(sig):
    params = tuple(sig.parameters.values())
    if params and params[0].kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
        raise ValueError('invalid method signature')
    kind = params[0].kind
    if kind in (_POSITIONAL_OR_KEYWORD, _POSITIONAL_ONLY):
        params = params[1:]
    elif kind is not _VAR_POSITIONAL:
        raise ValueError('invalid argument type')
    return sig.replace(parameters=params)

def _signature_is_builtin(obj):
    return isbuiltin(obj) or (ismethoddescriptor(obj) or (isinstance(obj, _NonUserDefinedCallables) or obj in (type, object)))

def _signature_is_functionlike(obj):
    if callable(obj) and isclass(obj):
        return False
    name = getattr(obj, '__name__', None)
    code = getattr(obj, '__code__', None)
    defaults = getattr(obj, '__defaults__', _void)
    kwdefaults = getattr(obj, '__kwdefaults__', _void)
    annotations = getattr(obj, '__annotations__', None)
    return isinstance(code, types.CodeType) and (isinstance(name, str) and isinstance(annotations, dict))

def _signature_get_bound_param(spec):
    pos = spec.find(',')
    if pos == -1:
        pos = spec.find(')')
    cpos = spec.find(':')
    cpos = spec.find('=')
    return spec[2:pos]

def _signature_strip_non_python_syntax(signature):
    if not signature:
        return (signature, None, None)
    self_parameter = None
    last_positional_only = None
    lines = [l.encode('ascii') for l in signature.split('\n')]
    generator = iter(lines).__next__
    token_stream = tokenize.tokenize(generator)
    delayed_comma = False
    skip_next_comma = False
    text = []
    add = text.append
    current_parameter = 0
    OP = token.OP
    ERRORTOKEN = token.ERRORTOKEN
    t = next(token_stream)
    for t in token_stream:
        type = t.type
        string = t.string
        if type == OP:
            if string == ',':
                if skip_next_comma:
                    skip_next_comma = False
                else:
                    delayed_comma = True
                    current_parameter += 1
                    if string == '/':
                        skip_next_comma = True
                        last_positional_only = current_parameter - 1
                    elif type == ERRORTOKEN and string == '$':
                        self_parameter = current_parameter
                    else:
                        if delayed_comma:
                            delayed_comma = False
                            if not (type == OP and string == ')'):
                                add(', ')
                        add(string)
                        if string == ',':
                            add(' ')
            elif string == '/':
                skip_next_comma = True
                last_positional_only = current_parameter - 1
            elif type == ERRORTOKEN and string == '$':
                self_parameter = current_parameter
            else:
                if delayed_comma:
                    delayed_comma = False
                    if not (type == OP and string == ')'):
                        add(', ')
                add(string)
                if string == ',':
                    add(' ')
        if type == ERRORTOKEN and string == '$':
            self_parameter = current_parameter
        else:
            if delayed_comma:
                delayed_comma = False
                if not (type == OP and string == ')'):
                    add(', ')
            add(string)
            if string == ',':
                add(' ')
    clean_signature = ''.join(text)
    return (clean_signature, self_parameter, last_positional_only)

def _signature_fromstr(cls, obj, s, skip_bound_arg=True):
    import ast
    Parameter = cls._parameter_cls
    (clean_signature, self_parameter, last_positional_only) = _signature_strip_non_python_syntax(s)
    program = 'def foo' + clean_signature + ': pass'
    try:
        module = ast.parse(program)
    except SyntaxError:
        module = None
    if not isinstance(module, ast.Module):
        raise ValueError('{!r} builtin has invalid signature'.format(obj))
    f = module.body[0]
    parameters = []
    empty = Parameter.empty
    invalid = object()
    module = None
    module_dict = {}
    module_name = getattr(obj, '__module__', None)
    if module_name:
        module = sys.modules.get(module_name, None)
        if module:
            module_dict = module.__dict__
    sys_module_dict = sys.modules

    def parse_name(node):
        if node.annotation != None:
            raise ValueError('Annotations are not currently supported')
        return node.arg

    def wrap_value(s):
        try:
            value = eval(s, module_dict)
        except NameError:
            try:
                value = eval(s, sys_module_dict)
            except NameError:
                raise RuntimeError()
        if isinstance(value, str):
            return ast.Str(value)
        if isinstance(value, (int, float)):
            return ast.Num(value)
        if isinstance(value, bytes):
            return ast.Bytes(value)
        if value in (True, False, None):
            return ast.NameConstant(value)
        raise RuntimeError()

    class RewriteSymbolics(ast.NodeTransformer):

        def visit_Attribute(self, node):
            a = []
            n = node
            while isinstance(n, ast.Attribute):
                a.append(n.attr)
                n = n.value
            if not isinstance(n, ast.Name):
                raise RuntimeError()
            a.append(n.id)
            value = '.'.join(reversed(a))
            return wrap_value(value)

        def visit_Name(self, node):
            if not isinstance(node.ctx, ast.Load):
                raise ValueError()
            return wrap_value(node.id)

    def p(name_node, default_node, default=empty):
        name = parse_name(name_node)
        if name is invalid:
            return
        if default_node is not _empty:
            try:
                default_node = RewriteSymbolics().visit(default_node)
                o = ast.literal_eval(default_node)
            except ValueError:
                o = invalid
            if o is invalid:
                return
            default = o if o is not invalid else default
        parameters.append(Parameter(name, kind, default=default, annotation=empty))

    args = reversed(f.args.args)
    defaults = reversed(f.args.defaults)
    iter = itertools.zip_longest(args, defaults, fillvalue=None)
    if last_positional_only is not None:
        kind = Parameter.POSITIONAL_ONLY
    else:
        kind = Parameter.POSITIONAL_OR_KEYWORD
    for (i, (name, default)) in enumerate(reversed(list(iter))):
        p(name, default)
        if i == last_positional_only:
            kind = Parameter.POSITIONAL_OR_KEYWORD
    if f.args.vararg:
        kind = Parameter.VAR_POSITIONAL
        p(f.args.vararg, empty)
    kind = Parameter.KEYWORD_ONLY
    for (name, default) in zip(f.args.kwonlyargs, f.args.kw_defaults):
        p(name, default)
    if f.args.kwarg:
        kind = Parameter.VAR_KEYWORD
        p(f.args.kwarg, empty)
    if self_parameter is not None:
        _self = getattr(obj, '__self__', None)
        self_isbound = _self is not None
        self_ismodule = ismodule(_self)
        if self_isbound and (self_ismodule or skip_bound_arg):
            parameters.pop(0)
        else:
            p = parameters[0].replace(kind=Parameter.POSITIONAL_ONLY)
            parameters[0] = p
    return cls(parameters, return_annotation=cls.empty)

def _signature_from_builtin(cls, func, skip_bound_arg=True):
    if not _signature_is_builtin(func):
        raise TypeError('{!r} is not a Python builtin function'.format(func))
    s = getattr(func, '__text_signature__', None)
    if not s:
        raise ValueError('no signature found for builtin {!r}'.format(func))
    return _signature_fromstr(cls, func, s, skip_bound_arg)

def _signature_from_function(cls, func):
    is_duck_function = False
    if not isfunction(func):
        if _signature_is_functionlike(func):
            is_duck_function = True
        else:
            raise TypeError('{!r} is not a Python function'.format(func))
    Parameter = cls._parameter_cls
    func_code = func.__code__
    pos_count = func_code.co_argcount
    arg_names = func_code.co_varnames
    positional = tuple(arg_names[:pos_count])
    keyword_only_count = func_code.co_kwonlyargcount
    keyword_only = arg_names[pos_count:pos_count + keyword_only_count]
    annotations = func.__annotations__
    defaults = func.__defaults__
    kwdefaults = func.__kwdefaults__
    if defaults:
        pos_default_count = len(defaults)
    else:
        pos_default_count = 0
    parameters = []
    non_default_count = pos_count - pos_default_count
    for name in positional[:non_default_count]:
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation, kind=_POSITIONAL_OR_KEYWORD))
    for (offset, name) in enumerate(positional[non_default_count:]):
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation, kind=_POSITIONAL_OR_KEYWORD, default=defaults[offset]))
    if func_code.co_flags & CO_VARARGS:
        name = arg_names[pos_count + keyword_only_count]
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation, kind=_VAR_POSITIONAL))
    for name in keyword_only:
        default = _empty
        if kwdefaults is not None:
            default = kwdefaults.get(name, _empty)
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation, kind=_KEYWORD_ONLY, default=default))
    if func_code.co_flags & CO_VARKEYWORDS:
        index = pos_count + keyword_only_count
        if func_code.co_flags & CO_VARARGS:
            index += 1
        name = arg_names[index]
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation, kind=_VAR_KEYWORD))
    return cls(parameters, return_annotation=annotations.get('return', _empty), __validate_parameters__=is_duck_function)

def _signature_from_callable(obj, *, follow_wrapper_chains=True, skip_bound_arg=True, sigcls):
    if not callable(obj):
        raise TypeError('{!r} is not a callable object'.format(obj))
    if isinstance(obj, types.MethodType):
        sig = _signature_from_callable(obj.__func__, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
        if skip_bound_arg:
            return _signature_bound_method(sig)
        return sig
    if follow_wrapper_chains:
        obj = unwrap(obj, stop=lambda f: hasattr(f, '__signature__'))
        if isinstance(obj, types.MethodType):
            return _signature_from_callable(obj, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
    try:
        sig = obj.__signature__
    except AttributeError:
        pass
    if sig is not None:
        if not isinstance(sig, Signature):
            raise TypeError('unexpected object {!r} in __signature__ attribute'.format(sig))
        return sig
    try:
        partialmethod = obj._partialmethod
    except AttributeError:
        pass
    if isinstance(partialmethod, functools.partialmethod):
        wrapped_sig = _signature_from_callable(partialmethod.func, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
        sig = _signature_get_partial(wrapped_sig, partialmethod, (None,))
        first_wrapped_param = tuple(wrapped_sig.parameters.values())[0]
        if first_wrapped_param.kind is Parameter.VAR_POSITIONAL:
            return sig
        sig_params = tuple(sig.parameters.values())
        new_params = (first_wrapped_param,) + sig_params
        return sig.replace(parameters=new_params)
    if isfunction(obj) or _signature_is_functionlike(obj):
        return _signature_from_function(sigcls, obj)
    if _signature_is_builtin(obj):
        return _signature_from_builtin(sigcls, obj, skip_bound_arg=skip_bound_arg)
    if isinstance(obj, functools.partial):
        wrapped_sig = _signature_from_callable(obj.func, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
        return _signature_get_partial(wrapped_sig, obj)
    sig = None
    if isinstance(obj, type):
        call = _signature_get_user_defined_method(type(obj), '__call__')
        if call is not None:
            sig = _signature_from_callable(call, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
        else:
            new = _signature_get_user_defined_method(obj, '__new__')
            if new is not None:
                sig = _signature_from_callable(new, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
            else:
                init = _signature_get_user_defined_method(obj, '__init__')
                if init is not None:
                    sig = _signature_from_callable(init, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
        if sig is None:
            for base in obj.__mro__[:-1]:
                try:
                    text_sig = base.__text_signature__
                except AttributeError:
                    pass
                if text_sig:
                    return _signature_fromstr(sigcls, obj, text_sig)
            if type not in obj.__mro__:
                if obj.__init__ is object.__init__ and obj.__new__ is object.__new__:
                    return signature(object)
                else:
                    raise ValueError('no signature found for builtin type {!r}'.format(obj))
                    if sig is not None:
                        if skip_bound_arg:
                            return _signature_bound_method(sig)
                        return sig
    elif not isinstance(obj, _NonUserDefinedCallables):
        call = _signature_get_user_defined_method(type(obj), '__call__')
        if call is not None:
            try:
                sig = _signature_from_callable(call, follow_wrapper_chains=follow_wrapper_chains, skip_bound_arg=skip_bound_arg, sigcls=sigcls)
            except ValueError as ex:
                msg = 'no signature found for {!r}'.format(obj)
                raise ValueError(msg) from ex
    if sig is not None:
        if skip_bound_arg:
            return _signature_bound_method(sig)
        return sig
    if isinstance(obj, types.BuiltinFunctionType):
        msg = 'no signature found for builtin function {!r}'.format(obj)
        raise ValueError(msg)
    raise ValueError('callable {!r} is not supported by signature'.format(obj))

class _void:
    pass

class _empty:
    pass

class _ParameterKind(enum.IntEnum):
    POSITIONAL_ONLY = 0
    POSITIONAL_OR_KEYWORD = 1
    VAR_POSITIONAL = 2
    KEYWORD_ONLY = 3
    VAR_KEYWORD = 4

    def __str__(self):
        return self._name_
_POSITIONAL_ONLY = _ParameterKind.POSITIONAL_ONLY_POSITIONAL_OR_KEYWORD = _ParameterKind.POSITIONAL_OR_KEYWORD_VAR_POSITIONAL = _ParameterKind.VAR_POSITIONAL_KEYWORD_ONLY = _ParameterKind.KEYWORD_ONLY_VAR_KEYWORD = _ParameterKind.VAR_KEYWORD_PARAM_NAME_MAPPING = {_VAR_KEYWORD: 'variadic keyword', _KEYWORD_ONLY: 'keyword-only', _VAR_POSITIONAL: 'variadic positional', _POSITIONAL_OR_KEYWORD: 'positional or keyword', _POSITIONAL_ONLY: 'positional-only'}_get_paramkind_descr = _PARAM_NAME_MAPPING.__getitem__
class Parameter:
    __slots__ = ('_name', '_kind', '_default', '_annotation')
    POSITIONAL_ONLY = _POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD = _POSITIONAL_OR_KEYWORD
    VAR_POSITIONAL = _VAR_POSITIONAL
    KEYWORD_ONLY = _KEYWORD_ONLY
    VAR_KEYWORD = _VAR_KEYWORD
    empty = _empty

    def __init__(self, name, kind, *, default=_empty, annotation=_empty):
        try:
            self._kind = _ParameterKind(kind)
        except ValueError:
            raise ValueError(f'value {kind} is not a valid Parameter.kind')
        if default is not _empty and self._kind in (_VAR_POSITIONAL, _VAR_KEYWORD):
            msg = '{} parameters cannot have default values'
            msg = msg.format(_get_paramkind_descr(self._kind))
            raise ValueError(msg)
        self._default = default
        self._annotation = annotation
        if name is _empty:
            raise ValueError('name is a required attribute for Parameter')
        if not isinstance(name, str):
            msg = 'name must be a str, not a {}'.format(type(name).__name__)
            raise TypeError(msg)
        if name[1:].isdigit():
            if self._kind != _POSITIONAL_OR_KEYWORD:
                msg = 'implicit arguments must be passed as positional or keyword arguments, not {}'
                msg = msg.format(_get_paramkind_descr(self._kind))
                raise ValueError(msg)
            self._kind = _POSITIONAL_ONLY
            name = 'implicit{}'.format(name[1:])
        if not (name[0] == '.' and name.isidentifier()):
            raise ValueError('{!r} is not a valid parameter name'.format(name))
        self._name = name

    def __reduce__(self):
        return (type(self), (self._name, self._kind), {'_default': self._default, '_annotation': self._annotation})

    def __setstate__(self, state):
        self._default = state['_default']
        self._annotation = state['_annotation']

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def annotation(self):
        return self._annotation

    @property
    def kind(self):
        return self._kind

    def replace(self, *, name=_void, kind=_void, annotation=_void, default=_void):
        if name is _void:
            name = self._name
        if kind is _void:
            kind = self._kind
        if annotation is _void:
            annotation = self._annotation
        if default is _void:
            default = self._default
        return type(self)(name, kind, default=default, annotation=annotation)

    def __str__(self):
        kind = self.kind
        formatted = self._name
        if self._annotation is not _empty:
            formatted = '{}: {}'.format(formatted, formatannotation(self._annotation))
        if self._default is not _empty:
            if self._annotation is not _empty:
                formatted = '{} = {}'.format(formatted, repr(self._default))
            else:
                formatted = '{}={}'.format(formatted, repr(self._default))
        if kind == _VAR_POSITIONAL:
            formatted = '*' + formatted
        elif kind == _VAR_KEYWORD:
            formatted = '**' + formatted
        return formatted

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self)

    def __hash__(self):
        return hash((self.name, self.kind, self.annotation, self.default))

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Parameter):
            return NotImplemented
        return self._name == other._name and (self._kind == other._kind and (self._default == other._default and self._annotation == other._annotation))

class BoundArguments:
    __slots__ = ('arguments', '_signature', '__weakref__')

    def __init__(self, signature, arguments):
        self.arguments = arguments
        self._signature = signature

    @property
    def signature(self):
        return self._signature

    @property
    def args(self):
        args = []
        for (param_name, param) in self._signature.parameters.items():
            if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
                break
            try:
                arg = self.arguments[param_name]
            except KeyError:
                break
            if param.kind == _VAR_POSITIONAL:
                args.extend(arg)
            else:
                args.append(arg)
        return tuple(args)

    @property
    def kwargs(self):
        kwargs = {}
        kwargs_started = False
        for (param_name, param) in self._signature.parameters.items():
            if not kwargs_started:
                if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
                    kwargs_started = True
                elif param_name not in self.arguments:
                    kwargs_started = True
                elif not kwargs_started:
                    pass
                else:
                    try:
                        arg = self.arguments[param_name]
                    except KeyError:
                        pass
                    if param.kind == _VAR_KEYWORD:
                        kwargs.update(arg)
                    else:
                        kwargs[param_name] = arg
            elif not kwargs_started:
                pass
            else:
                try:
                    arg = self.arguments[param_name]
                except KeyError:
                    pass
                if param.kind == _VAR_KEYWORD:
                    kwargs.update(arg)
                else:
                    kwargs[param_name] = arg
        return kwargs

    def apply_defaults(self):
        arguments = self.arguments
        new_arguments = []
        for (name, param) in self._signature.parameters.items():
            try:
                new_arguments.append((name, arguments[name]))
            except KeyError:
                if param.default is not _empty:
                    val = param.default
                elif param.kind is _VAR_POSITIONAL:
                    val = ()
                elif param.kind is _VAR_KEYWORD:
                    val = {}
                else:
                    continue
                new_arguments.append((name, val))
        self.arguments = OrderedDict(new_arguments)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, BoundArguments):
            return NotImplemented
        return self.signature == other.signature and self.arguments == other.arguments

    def __setstate__(self, state):
        self._signature = state['_signature']
        self.arguments = state['arguments']

    def __getstate__(self):
        return {'_signature': self._signature, 'arguments': self.arguments}

    def __repr__(self):
        args = []
        for (arg, value) in self.arguments.items():
            args.append('{}={!r}'.format(arg, value))
        return '<{} ({})>'.format(self.__class__.__name__, ', '.join(args))

class Signature:
    __slots__ = ('_return_annotation', '_parameters')
    _parameter_cls = Parameter
    _bound_arguments_cls = BoundArguments
    empty = _empty

    def __init__(self, parameters=None, *, return_annotation=_empty, __validate_parameters__=True):
        if parameters is None:
            params = OrderedDict()
        elif __validate_parameters__:
            params = OrderedDict()
            top_kind = _POSITIONAL_ONLY
            kind_defaults = False
            for (idx, param) in enumerate(parameters):
                kind = param.kind
                name = param.name
                if kind < top_kind:
                    msg = 'wrong parameter order: {} parameter before {} parameter'
                    msg = msg.format(_get_paramkind_descr(top_kind), _get_paramkind_descr(kind))
                    raise ValueError(msg)
                elif kind > top_kind:
                    kind_defaults = False
                    top_kind = kind
                if param.default is _empty:
                    if kind_defaults:
                        msg = 'non-default argument follows default argument'
                        raise ValueError(msg)
                else:
                    kind_defaults = True
                if kind in (_POSITIONAL_ONLY, _POSITIONAL_OR_KEYWORD) and name in params:
                    msg = 'duplicate parameter name: {!r}'.format(name)
                    raise ValueError(msg)
                params[name] = param
        else:
            params = OrderedDict((param.name, param) for param in parameters)
        self._parameters = types.MappingProxyType(params)
        self._return_annotation = return_annotation

    @classmethod
    def from_function(cls, func):
        warnings.warn('inspect.Signature.from_function() is deprecated, use Signature.from_callable()', DeprecationWarning, stacklevel=2)
        return _signature_from_function(cls, func)

    @classmethod
    def from_builtin(cls, func):
        warnings.warn('inspect.Signature.from_builtin() is deprecated, use Signature.from_callable()', DeprecationWarning, stacklevel=2)
        return _signature_from_builtin(cls, func)

    @classmethod
    def from_callable(cls, obj, *, follow_wrapped=True):
        return _signature_from_callable(obj, sigcls=cls, follow_wrapper_chains=follow_wrapped)

    @property
    def parameters(self):
        return self._parameters

    @property
    def return_annotation(self):
        return self._return_annotation

    def replace(self, *, parameters=_void, return_annotation=_void):
        if parameters is _void:
            parameters = self.parameters.values()
        if return_annotation is _void:
            return_annotation = self._return_annotation
        return type(self)(parameters, return_annotation=return_annotation)

    def _hash_basis(self):
        params = tuple(param for param in self.parameters.values() if param.kind != _KEYWORD_ONLY)
        kwo_params = {param.name: param for param in self.parameters.values() if param.kind == _KEYWORD_ONLY}
        return (params, kwo_params, self.return_annotation)

    def __hash__(self):
        (params, kwo_params, return_annotation) = self._hash_basis()
        kwo_params = frozenset(kwo_params.values())
        return hash((params, kwo_params, return_annotation))

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Signature):
            return NotImplemented
        return self._hash_basis() == other._hash_basis()

    def _bind(self, args, kwargs, *, partial=False):
        arguments = OrderedDict()
        parameters = iter(self.parameters.values())
        parameters_ex = ()
        arg_vals = iter(args)
        while True:
            try:
                arg_val = next(arg_vals)
            except StopIteration:
                try:
                    param = next(parameters)
                except StopIteration:
                    break
                if param.kind == _VAR_POSITIONAL:
                    break
                elif param.name in kwargs:
                    if param.kind == _POSITIONAL_ONLY:
                        msg = '{arg!r} parameter is positional only, but was passed as a keyword'
                        msg = msg.format(arg=param.name)
                        raise TypeError(msg) from None
                    parameters_ex = (param,)
                    break
                elif param.kind == _VAR_KEYWORD or param.default is not _empty:
                    parameters_ex = (param,)
                    break
                elif partial:
                    parameters_ex = (param,)
                    break
                else:
                    msg = 'missing a required argument: {arg!r}'
                    msg = msg.format(arg=param.name)
                    raise TypeError(msg) from None
            try:
                param = next(parameters)
            except StopIteration:
                raise TypeError('too many positional arguments') from None
            if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
                raise TypeError('too many positional arguments') from None
            if param.kind == _VAR_POSITIONAL:
                values = [arg_val]
                values.extend(arg_vals)
                arguments[param.name] = tuple(values)
                break
            if param.name in kwargs:
                raise TypeError('multiple values for argument {arg!r}'.format(arg=param.name)) from None
            arguments[param.name] = arg_val
        kwargs_param = None
        for param in itertools.chain(parameters_ex, parameters):
            if param.kind == _VAR_KEYWORD:
                kwargs_param = param
            elif param.kind == _VAR_POSITIONAL:
                pass
            else:
                param_name = param.name
                try:
                    arg_val = kwargs.pop(param_name)
                except KeyError:
                    if partial or param.kind != _VAR_POSITIONAL and param.default is _empty:
                        raise TypeError('missing a required argument: {arg!r}'.format(arg=param_name)) from None
                if param.kind == _POSITIONAL_ONLY:
                    raise TypeError('{arg!r} parameter is positional only, but was passed as a keyword'.format(arg=param.name))
                arguments[param_name] = arg_val
        if kwargs:
            if kwargs_param is not None:
                arguments[kwargs_param.name] = kwargs
            else:
                raise TypeError('got an unexpected keyword argument {arg!r}'.format(arg=next(iter(kwargs))))
        return self._bound_arguments_cls(self, arguments)

    def bind(*args, **kwargs):
        return args[0]._bind(args[1:], kwargs)

    def bind_partial(*args, **kwargs):
        return args[0]._bind(args[1:], kwargs, partial=True)

    def __reduce__(self):
        return (type(self), (tuple(self._parameters.values()),), {'_return_annotation': self._return_annotation})

    def __setstate__(self, state):
        self._return_annotation = state['_return_annotation']

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self)

    def __str__(self):
        result = []
        render_pos_only_separator = False
        render_kw_only_separator = True
        for param in self.parameters.values():
            formatted = str(param)
            kind = param.kind
            if kind == _POSITIONAL_ONLY:
                render_pos_only_separator = True
            elif render_pos_only_separator:
                result.append('/')
                render_pos_only_separator = False
            if kind == _VAR_POSITIONAL:
                render_kw_only_separator = False
            elif render_kw_only_separator:
                result.append('*')
                render_kw_only_separator = False
            result.append(formatted)
        if render_pos_only_separator:
            result.append('/')
        rendered = '({})'.format(', '.join(result))
        if self.return_annotation is not _empty:
            anno = formatannotation(self.return_annotation)
            rendered += ' -> {}'.format(anno)
        return rendered

def signature(obj, *, follow_wrapped=True):
    return Signature.from_callable(obj, follow_wrapped=follow_wrapped)

def _main():
    import argparse
    import importlib
    parser = argparse.ArgumentParser()
    parser.add_argument('object', help="The object to be analysed. It supports the 'module:qualname' syntax")
    parser.add_argument('-d', '--details', action='store_true', help='Display info about the module rather than its source code')
    args = parser.parse_args()
    target = args.object
    (mod_name, has_attrs, attrs) = target.partition(':')
    try:
        obj = module = importlib.import_module(mod_name)
    except Exception as exc:
        msg = 'Failed to import {} ({}: {})'.format(mod_name, type(exc).__name__, exc)
        print(msg, file=sys.stderr)
        exit(2)
    if has_attrs:
        parts = attrs.split('.')
        obj = module
        for part in parts:
            obj = getattr(obj, part)
    if module.__name__ in sys.builtin_module_names:
        print("Can't get info for builtin modules.", file=sys.stderr)
        exit(1)
    if args.details:
        print('Target: {}'.format(target))
        print('Origin: {}'.format(getsourcefile(module)))
        print('Cached: {}'.format(module.__cached__))
        if obj is module:
            print('Loader: {}'.format(repr(module.__loader__)))
            if hasattr(module, '__path__'):
                print('Submodule search path: {}'.format(module.__path__))
        else:
            try:
                (__, lineno) = findsource(obj)
            except Exception:
                pass
            print('Line: {}'.format(lineno))
        print('\n')
    else:
        print(getsource(obj))
if __name__ == '__main__':
    _main()