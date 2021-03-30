__all__ = ['help']__author__ = 'Ka-Ping Yee <ping@lfw.org>'__date__ = '26 February 2001'__credits__ = 'Guido van Rossum, for an excellent programming language.\nTommy Burnette, the original creator of manpy.\nPaul Prescod, for all his work on onlinehelp.\nRichard Chamberlain, for the first implementation of textdoc.\n'import builtinsimport importlib._bootstrapimport importlib._bootstrap_externalimport importlib.machineryimport importlib.utilimport inspectimport ioimport osimport pkgutilimport platformimport reimport sysimport timeimport tokenizeimport urllib.parseimport warningsfrom collections import dequefrom reprlib import Reprfrom traceback import format_exception_only
def pathdirs():
    dirs = []
    normdirs = []
    for dir in sys.path:
        dir = os.path.abspath(dir or '.')
        normdir = os.path.normcase(dir)
        if normdir not in normdirs and os.path.isdir(dir):
            dirs.append(dir)
            normdirs.append(normdir)
    return dirs

def getdoc(object):
    result = inspect.getdoc(object) or inspect.getcomments(object)
    if result:
        pass
    return ''

def splitdoc(doc):
    lines = doc.strip().split('\n')
    if len(lines) == 1:
        return (lines[0], '')
    if len(lines) >= 2 and not lines[1].rstrip():
        return (lines[0], '\n'.join(lines[2:]))
    return ('', '\n'.join(lines))

def classname(object, modname):
    name = object.__name__
    if object.__module__ != modname:
        name = object.__module__ + '.' + name
    return name

def isdata(object):
    return not (inspect.ismodule(object) or (inspect.isclass(object) or (inspect.isroutine(object) or (inspect.isframe(object) or (inspect.istraceback(object) or inspect.iscode(object))))))

def replace(text, *pairs):
    while pairs:
        text = pairs[1].join(text.split(pairs[0]))
        pairs = pairs[2:]
    return text

def cram(text, maxlen):
    if len(text) > maxlen:
        pre = max(0, (maxlen - 3)//2)
        post = max(0, maxlen - 3 - pre)
        return text[:pre] + '...' + text[len(text) - post:]
    return text
_re_stripid = re.compile(' at 0x[0-9a-f]{6,16}(>+)$', re.IGNORECASE)
def stripid(text):
    return _re_stripid.sub('\\1', text)

def _is_some_method(obj):
    return inspect.isfunction(obj) or (inspect.ismethod(obj) or (inspect.isbuiltin(obj) or inspect.ismethoddescriptor(obj)))

def _is_bound_method(fn):
    if inspect.ismethod(fn):
        return True
    elif inspect.isbuiltin(fn):
        self = getattr(fn, '__self__', None)
        return not (inspect.ismodule(self) or self is None)
    return False

def allmethods(cl):
    methods = {}
    for (key, value) in inspect.getmembers(cl, _is_some_method):
        methods[key] = 1
    for base in cl.__bases__:
        methods.update(allmethods(base))
    for key in methods.keys():
        methods[key] = getattr(cl, key)
    return methods

def _split_list(s, predicate):
    yes = []
    no = []
    for x in s:
        if predicate(x):
            yes.append(x)
        else:
            no.append(x)
    return (yes, no)

def visiblename(name, all=None, obj=None):
    if name in frozenset({'__file__', '__date__', '__spec__', '__cached__', '__doc__', '__version__', '__qualname__', '__loader__', '__author__', '__package__', '__name__', '__builtins__', '__path__', '__credits__', '__slots__', '__module__'}):
        return 0
    if name.startswith('__') and name.endswith('__'):
        return 1
    if name.startswith('_') and hasattr(obj, '_fields'):
        return True
    if all is not None:
        return name in all
    else:
        return not name.startswith('_')

def classify_class_attrs(object):
    results = []
    for (name, kind, cls, value) in inspect.classify_class_attrs(object):
        if inspect.isdatadescriptor(value):
            kind = 'data descriptor'
        results.append((name, kind, cls, value))
    return results

def sort_attributes(attrs, object):
    fields = getattr(object, '_fields', [])
    try:
        field_order = {name: i - len(fields) for (i, name) in enumerate(fields)}
    except TypeError:
        field_order = {}
    keyfunc = lambda attr: (field_order.get(attr[0], 0), attr[0])
    attrs.sort(key=keyfunc)

def ispackage(path):
    if os.path.isdir(path):
        for ext in ('.py', '.pyc'):
            if os.path.isfile(os.path.join(path, '__init__' + ext)):
                return True
    return False

def source_synopsis(file):
    line = file.readline()
    while True:
        while line[:1] == '#' or not line.strip():
            line = file.readline()
            if not line:
                break
    line = line.strip()
    if line[:4] == 'r"""':
        line = line[1:]
    if line[:3] == '"""':
        line = line[3:]
        if line[-1:] == '\\':
            line = line[:-1]
        while not line.strip():
            line = file.readline()
            if not line:
                break
        result = line.split('"""')[0].strip()
    else:
        result = None
    return result

def synopsis(filename, cache={}):
    mtime = os.stat(filename).st_mtime
    (lastupdate, result) = cache.get(filename, (None, None))
    if lastupdate is None or lastupdate < mtime:
        if filename.endswith(tuple(importlib.machinery.BYTECODE_SUFFIXES)):
            loader_cls = importlib.machinery.SourcelessFileLoader
        elif filename.endswith(tuple(importlib.machinery.EXTENSION_SUFFIXES)):
            loader_cls = importlib.machinery.ExtensionFileLoader
        else:
            loader_cls = None
        if loader_cls is None:
            try:
                file = tokenize.open(filename)
            except OSError:
                return
            with file:
                result = source_synopsis(file)
        else:
            loader = loader_cls('__temp__', filename)
            spec = importlib.util.spec_from_file_location('__temp__', filename, loader=loader)
            try:
                module = importlib._bootstrap._load(spec)
            except:
                return
            del sys.modules['__temp__']
            result = module.__doc__.splitlines()[0] if module.__doc__ else None
        cache[filename] = (mtime, result)
    return result

class ErrorDuringImport(Exception):

    def __init__(self, filename, exc_info):
        self.filename = filename
        (self.exc, self.value, self.tb) = exc_info

    def __str__(self):
        exc = self.exc.__name__
        return 'problem in %s - %s: %s' % (self.filename, exc, self.value)

def importfile(path):
    magic = importlib.util.MAGIC_NUMBER
    with open(path, 'rb') as file:
        is_bytecode = magic == file.read(len(magic))
    filename = os.path.basename(path)
    (name, ext) = os.path.splitext(filename)
    if is_bytecode:
        loader = importlib._bootstrap_external.SourcelessFileLoader(name, path)
    else:
        loader = importlib._bootstrap_external.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_file_location(name, path, loader=loader)
    try:
        return importlib._bootstrap._load(spec)
    except:
        raise ErrorDuringImport(path, sys.exc_info())

def safeimport(path, forceload=0, cache={}):
    try:
        if path not in sys.builtin_module_names:
            subs = [m for m in sys.modules if m.startswith(path + '.')]
            for key in [path] + subs:
                cache[key] = sys.modules[key]
                del sys.modules[key]
        module = __import__(path)
    except:
        (exc, value, tb) = info = sys.exc_info()
        if path in sys.modules:
            raise ErrorDuringImport(sys.modules[path].__file__, info)
        elif exc is SyntaxError:
            raise ErrorDuringImport(value.filename, info)
        else:
            if issubclass(exc, ImportError) and value.name == path:
                return
            raise ErrorDuringImport(path, sys.exc_info())

class Doc:
    PYTHONDOCS = os.environ.get('PYTHONDOCS', 'https://docs.python.org/%d.%d/library' % sys.version_info[:2])

    def document(self, object, name=None, *args):
        args = (object, name) + args
        if inspect.isgetsetdescriptor(object):
            return self.docdata(*args)
        if inspect.ismemberdescriptor(object):
            return self.docdata(*args)
        try:
            if inspect.ismodule(object):
                return self.docmodule(*args)
            if inspect.isclass(object):
                return self.docclass(*args)
            if inspect.isroutine(object):
                return self.docroutine(*args)
        except AttributeError:
            pass
        if isinstance(object, property):
            return self.docproperty(*args)
        return self.docother(*args)

    def fail(self, object, name=None, *args):
        message = "don't know how to document object%s of type %s" % (name and ' ' + repr(name), type(object).__name__)
        raise TypeError(message)

    docmodule = docclass = docroutine = docother = docproperty = docdata = fail

    def getdocloc(self, object, basedir=os.path.join(sys.base_exec_prefix, 'lib', 'python%d.%d' % sys.version_info[:2])):
        try:
            file = inspect.getabsfile(object)
        except TypeError:
            file = '(built-in)'
        docloc = os.environ.get('PYTHONDOCS', self.PYTHONDOCS)
        basedir = os.path.normcase(basedir)
        if isinstance(object, type(os)) and (object.__name__ in ('errno', 'exceptions', 'gc', 'imp', 'marshal', 'posix', 'signal', 'sys', '_thread', 'zipimport') or file.startswith(basedir)) and (file.startswith(os.path.join(basedir, 'site-packages')) or object.__name__ not in ('xml.etree', 'test.pydoc_mod')):
            if docloc.startswith(('http://', 'https://')):
                docloc = '%s/%s' % (docloc.rstrip('/'), object.__name__.lower())
            else:
                docloc = os.path.join(docloc, object.__name__.lower() + '.html')
        else:
            docloc = None
        return docloc

class HTMLRepr(Repr):

    def __init__(self):
        Repr.__init__(self)
        self.maxlist = self.maxtuple = 20
        self.maxdict = 10
        self.maxstring = self.maxother = 100

    def escape(self, text):
        return replace(text, '&', '&amp;', '<', '&lt;', '>', '&gt;')

    def repr(self, object):
        return Repr.repr(self, object)

    def repr1(self, x, level):
        if hasattr(type(x), '__name__'):
            methodname = 'repr_' + '_'.join(type(x).__name__.split())
            if hasattr(self, methodname):
                return getattr(self, methodname)(x, level)
        return self.escape(cram(stripid(repr(x)), self.maxother))

    def repr_string(self, x, level):
        test = cram(x, self.maxstring)
        testrepr = repr(test)
        if '\\' in test and '\\' not in replace(testrepr, '\\\\', ''):
            return 'r' + testrepr[0] + self.escape(test) + testrepr[0]
        return re.sub('((\\\\[\\\\abfnrtv\\\'"]|\\\\[0-9]..|\\\\x..|\\\\u....)+)', '<font color="#c040c0">\\1</font>', self.escape(testrepr))

    repr_str = repr_string

    def repr_instance(self, x, level):
        try:
            return self.escape(cram(stripid(repr(x)), self.maxstring))
        except:
            return self.escape('<%s instance>' % x.__class__.__name__)

    repr_unicode = repr_string

class HTMLDoc(Doc):
    _repr_instance = HTMLRepr()
    repr = _repr_instance.repr
    escape = _repr_instance.escape

    def page(self, title, contents):
        return '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">\n<html><head><title>Python: %s</title>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n</head><body bgcolor="#f0f0f8">\n%s\n</body></html>' % (title, contents)

    def heading(self, title, fgcol, bgcol, extras=''):
        return '\n<table width="100%%" cellspacing=0 cellpadding=2 border=0 summary="heading">\n<tr bgcolor="%s">\n<td valign=bottom>&nbsp;<br>\n<font color="%s" face="helvetica, arial">&nbsp;<br>%s</font></td\n><td align=right valign=bottom\n><font color="%s" face="helvetica, arial">%s</font></td></tr></table>\n    ' % (bgcol, fgcol, title, fgcol, extras or '&nbsp;')

    def section(self, title, fgcol, bgcol, contents, width=6, prelude='', marginalia=None, gap='&nbsp;'):
        if marginalia is None:
            marginalia = '<tt>' + '&nbsp;'*width + '</tt>'
        result = '<p>\n<table width="100%%" cellspacing=0 cellpadding=2 border=0 summary="section">\n<tr bgcolor="%s">\n<td colspan=3 valign=bottom>&nbsp;<br>\n<font color="%s" face="helvetica, arial">%s</font></td></tr>\n    ' % (bgcol, fgcol, title)
        if prelude:
            result = result + '\n<tr bgcolor="%s"><td rowspan=2>%s</td>\n<td colspan=2>%s</td></tr>\n<tr><td>%s</td>' % (bgcol, marginalia, prelude, gap)
        else:
            result = result + '\n<tr><td bgcolor="%s">%s</td><td>%s</td>' % (bgcol, marginalia, gap)
        return result + '\n<td width="100%%">%s</td></tr></table>' % contents

    def bigsection(self, title, *args):
        title = '<big><strong>%s</strong></big>' % title
        return self.section(title, *args)

    def preformat(self, text):
        text = self.escape(text.expandtabs())
        return replace(text, '\n\n', '\n \n', '\n\n', '\n \n', ' ', '&nbsp;', '\n', '<br>\n')

    def multicolumn(self, list, format, cols=4):
        result = ''
        rows = (len(list) + cols - 1)//cols
        for col in range(cols):
            result = result + '<td width="%d%%" valign=top>' % (100//cols)
            for i in range(rows*col, rows*col + rows):
                if i < len(list):
                    result = result + format(list[i]) + '<br>\n'
            result = result + '</td>'
        return '<table width="100%%" summary="list"><tr>%s</tr></table>' % result

    def grey(self, text):
        return '<font color="#909090">%s</font>' % text

    def namelink(self, name, *dicts):
        for dict in dicts:
            if name in dict:
                return '<a href="%s">%s</a>' % (dict[name], name)
        return name

    def classlink(self, object, modname):
        name = object.__name__
        module = sys.modules.get(object.__module__)
        if hasattr(module, name) and getattr(module, name) is object:
            return '<a href="%s.html#%s">%s</a>' % (module.__name__, name, classname(object, modname))
        return classname(object, modname)

    def modulelink(self, object):
        return '<a href="%s.html">%s</a>' % (object.__name__, object.__name__)

    def modpkglink(self, modpkginfo):
        (name, path, ispackage, shadowed) = modpkginfo
        if shadowed:
            return self.grey(name)
        if path:
            url = '%s.%s.html' % (path, name)
        else:
            url = '%s.html' % name
        if ispackage:
            text = '<strong>%s</strong>&nbsp;(package)' % name
        else:
            text = name
        return '<a href="%s">%s</a>' % (url, text)

    def filelink(self, url, path):
        return '<a href="file:%s">%s</a>' % (url, path)

    def markup(self, text, escape=None, funcs={}, classes={}, methods={}):
        escape = escape or self.escape
        results = []
        here = 0
        pattern = re.compile('\\b((http|ftp)://\\S+[\\w/]|RFC[- ]?(\\d+)|PEP[- ]?(\\d+)|(self\\.)?(\\w+))')
        while True:
            match = pattern.search(text, here)
            if not match:
                break
            (start, end) = match.span()
            results.append(escape(text[here:start]))
            (all, scheme, rfc, pep, selfdot, name) = match.groups()
            if scheme:
                url = escape(all).replace('"', '&quot;')
                results.append('<a href="%s">%s</a>' % (url, url))
            elif rfc:
                url = 'http://www.rfc-editor.org/rfc/rfc%d.txt' % int(rfc)
                results.append('<a href="%s">%s</a>' % (url, escape(all)))
            elif pep:
                url = 'http://www.python.org/dev/peps/pep-%04d/' % int(pep)
                results.append('<a href="%s">%s</a>' % (url, escape(all)))
            elif selfdot:
                if text[end:end + 1] == '(':
                    results.append('self.' + self.namelink(name, methods))
                else:
                    results.append('self.<strong>%s</strong>' % name)
            elif text[end:end + 1] == '(':
                results.append(self.namelink(name, methods, funcs, classes))
            else:
                results.append(self.namelink(name, classes))
            here = end
        results.append(escape(text[here:]))
        return ''.join(results)

    def formattree(self, tree, modname, parent=None):
        result = ''
        for entry in tree:
            if type(entry) is type(()):
                (c, bases) = entry
                result = result + '<dt><font face="helvetica, arial">'
                result = result + self.classlink(c, modname)
                if bases != (parent,):
                    parents = []
                    for base in bases:
                        parents.append(self.classlink(base, modname))
                    result = result + '(' + ', '.join(parents) + ')'
                result = result + '\n</font></dt>'
            elif type(entry) is type([]):
                result = result + '<dd>\n%s</dd>\n' % self.formattree(entry, modname, c)
        return '<dl>\n%s</dl>\n' % result

    def docmodule(self, object, name=None, mod=None, *ignored):
        name = object.__name__
        try:
            all = object.__all__
        except AttributeError:
            all = None
        parts = name.split('.')
        links = []
        for i in range(len(parts) - 1):
            links.append('<a href="%s.html"><font color="#ffffff">%s</font></a>' % ('.'.join(parts[:i + 1]), parts[i]))
        linkedname = '.'.join(links + parts[-1:])
        head = '<big><big><strong>%s</strong></big></big>' % linkedname
        try:
            path = inspect.getabsfile(object)
            url = urllib.parse.quote(path)
            filelink = self.filelink(url, path)
        except TypeError:
            filelink = '(built-in)'
        info = []
        if hasattr(object, '__version__'):
            version = str(object.__version__)
            if version[-1:] == '$':
                version = version[11:-1].strip()
            info.append('version %s' % self.escape(version))
        if hasattr(object, '__date__'):
            info.append(self.escape(str(object.__date__)))
        if info:
            head = head + ' (%s)' % ', '.join(info)
        docloc = self.getdocloc(object)
        if docloc is not None:
            docloc = '<br><a href="%(docloc)s">Module Reference</a>' % locals()
        else:
            docloc = ''
        result = self.heading(head, '#ffffff', '#7799ee', '<a href=".">index</a><br>' + filelink + docloc)
        modules = inspect.getmembers(object, inspect.ismodule)
        classes = []
        cdict = {}
        for (key, value) in inspect.getmembers(object, inspect.isclass):
            if not all is not None:
                pass
            if visiblename(key, all, object):
                classes.append((key, value))
                cdict[key] = cdict[value] = '#' + key
        for (key, value) in classes:
            for base in value.__bases__:
                key = base.__name__
                modname = base.__module__
                module = sys.modules.get(modname)
                if modname != name and (module and (hasattr(module, key) and getattr(module, key) is base)) and key not in cdict:
                    cdict[key] = cdict[base] = modname + '.html#' + key
        funcs = []
        fdict = {}
        for (key, value) in inspect.getmembers(object, inspect.isroutine):
            if not inspect.isbuiltin(value):
                pass
            if all is not None or visiblename(key, all, object):
                funcs.append((key, value))
                fdict[key] = '#-' + key
                if inspect.isfunction(value):
                    fdict[value] = fdict[key]
        data = []
        for (key, value) in inspect.getmembers(object, isdata):
            if visiblename(key, all, object):
                data.append((key, value))
        doc = self.markup(getdoc(object), self.preformat, fdict, cdict)
        doc = doc and '<tt>%s</tt>' % doc
        result = result + '<p>%s</p>\n' % doc
        if hasattr(object, '__path__'):
            modpkgs = []
            for (importer, modname, ispkg) in pkgutil.iter_modules(object.__path__):
                modpkgs.append((modname, name, ispkg, 0))
            modpkgs.sort()
            contents = self.multicolumn(modpkgs, self.modpkglink)
            result = result + self.bigsection('Package Contents', '#ffffff', '#aa55cc', contents)
        elif modules:
            contents = self.multicolumn(modules, lambda t: self.modulelink(t[1]))
            result = result + self.bigsection('Modules', '#ffffff', '#aa55cc', contents)
        if classes:
            classlist = [value for (key, value) in classes]
            contents = [self.formattree(inspect.getclasstree(classlist, 1), name)]
            for (key, value) in classes:
                contents.append(self.document(value, key, name, fdict, cdict))
            result = result + self.bigsection('Classes', '#ffffff', '#ee77aa', ' '.join(contents))
        if funcs:
            contents = []
            for (key, value) in funcs:
                contents.append(self.document(value, key, name, fdict, cdict))
            result = result + self.bigsection('Functions', '#ffffff', '#eeaa77', ' '.join(contents))
        if data:
            contents = []
            for (key, value) in data:
                contents.append(self.document(value, key))
            result = result + self.bigsection('Data', '#ffffff', '#55aa55', '<br>\n'.join(contents))
        if hasattr(object, '__author__'):
            contents = self.markup(str(object.__author__), self.preformat)
            result = result + self.bigsection('Author', '#ffffff', '#7799ee', contents)
        if hasattr(object, '__credits__'):
            contents = self.markup(str(object.__credits__), self.preformat)
            result = result + self.bigsection('Credits', '#ffffff', '#7799ee', contents)
        return result

    def docclass(self, object, name=None, mod=None, funcs={}, classes={}, *ignored):
        realname = object.__name__
        name = name or realname
        bases = object.__bases__
        contents = []
        push = contents.append

        class HorizontalRule:

            def __init__(self):
                self.needone = 0

            def maybe(self):
                if self.needone:
                    push('<hr>\n')
                self.needone = 1

        hr = HorizontalRule()
        mro = deque(inspect.getmro(object))
        if len(mro) > 2:
            hr.maybe()
            push('<dl><dt>Method resolution order:</dt>\n')
            for base in mro:
                push('<dd>%s</dd>\n' % self.classlink(base, object.__module__))
            push('</dl>\n')

        def spill(msg, attrs, predicate):
            (ok, attrs) = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for (name, kind, homecls, value) in ok:
                    try:
                        value = getattr(object, name)
                    except Exception:
                        push(self._docdescriptor(name, value, mod))
                    push(self.document(value, name, mod, funcs, classes, mdict, object))
                    push('\n')
            return attrs

        def spilldescriptors(msg, attrs, predicate):
            (ok, attrs) = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for (name, kind, homecls, value) in ok:
                    push(self._docdescriptor(name, value, mod))
            return attrs

        def spilldata(msg, attrs, predicate):
            (ok, attrs) = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for (name, kind, homecls, value) in ok:
                    base = self.docother(getattr(object, name), name, mod)
                    if callable(value) or inspect.isdatadescriptor(value):
                        doc = getattr(value, '__doc__', None)
                    else:
                        doc = None
                    if doc is None:
                        push('<dl><dt>%s</dl>\n' % base)
                    else:
                        doc = self.markup(getdoc(value), self.preformat, funcs, classes, mdict)
                        doc = '<dd><tt>%s</tt>' % doc
                        push('<dl><dt>%s%s</dl>\n' % (base, doc))
                    push('\n')
            return attrs

        attrs = [(name, kind, cls, value) for (name, kind, cls, value) in classify_class_attrs(object) if visiblename(name, obj=object)]
        mdict = {}
        for (key, kind, homecls, value) in attrs:
            mdict[key] = anchor = '#' + name + '-' + key
            try:
                value = getattr(object, name)
            except Exception:
                pass
            try:
                mdict[value] = anchor
            except TypeError:
                pass
        if attrs:
            if mro:
                thisclass = mro.popleft()
            else:
                thisclass = attrs[0][2]
            (attrs, inherited) = _split_list(attrs, lambda t: t[2] is thisclass)
            if thisclass is builtins.object:
                attrs = inherited
            elif thisclass is object:
                tag = 'defined here'
            else:
                tag = 'inherited from %s' % self.classlink(thisclass, object.__module__)
            tag += ':<br>\n'
            sort_attributes(attrs, object)
            attrs = spill('Methods %s' % tag, attrs, lambda t: t[1] == 'method')
            attrs = spill('Class methods %s' % tag, attrs, lambda t: t[1] == 'class method')
            attrs = spill('Static methods %s' % tag, attrs, lambda t: t[1] == 'static method')
            attrs = spilldescriptors('Data descriptors %s' % tag, attrs, lambda t: t[1] == 'data descriptor')
            attrs = spilldata('Data and other attributes %s' % tag, attrs, lambda t: t[1] == 'data')
            attrs = inherited
        contents = ''.join(contents)
        if name == realname:
            title = '<a name="%s">class <strong>%s</strong></a>' % (name, realname)
        else:
            title = '<strong>%s</strong> = <a name="%s">class %s</a>' % (name, name, realname)
        if bases:
            parents = []
            for base in bases:
                parents.append(self.classlink(base, object.__module__))
            title = title + '(%s)' % ', '.join(parents)
        decl = ''
        try:
            signature = inspect.signature(object)
        except (ValueError, TypeError):
            signature = None
        if signature:
            argspec = str(signature)
            if argspec != '()':
                decl = name + self.escape(argspec) + '\n\n'
        doc = getdoc(object)
        if decl:
            doc = decl + (doc or '')
        doc = self.markup(doc, self.preformat, funcs, classes, mdict)
        doc = doc and '<tt>%s<br>&nbsp;</tt>' % doc
        return self.section(title, '#000000', '#ffc8d8', contents, 3, doc)

    def formatvalue(self, object):
        return self.grey('=' + self.repr(object))

    def docroutine(self, object, name=None, mod=None, funcs={}, classes={}, methods={}, cl=None):
        realname = object.__name__
        name = name or realname
        if cl:
            pass
        anchor = '' + '-' + name
        note = ''
        skipdocs = 0
        if _is_bound_method(object):
            imclass = object.__self__.__class__
            if cl:
                if imclass is not cl:
                    note = ' from ' + self.classlink(imclass, mod)
            elif object.__self__ is not None:
                note = ' method of %s instance' % self.classlink(object.__self__.__class__, mod)
            else:
                note = ' unbound %s method' % self.classlink(imclass, mod)
        if name == realname:
            title = '<a name="%s"><strong>%s</strong></a>' % (anchor, realname)
        else:
            if cl and realname in cl.__dict__ and cl.__dict__[realname] is object:
                reallink = '<a href="#%s">%s</a>' % (cl.__name__ + '-' + realname, realname)
                skipdocs = 1
            else:
                reallink = realname
            title = '<a name="%s"><strong>%s</strong></a> = %s' % (anchor, name, reallink)
        argspec = None
        if inspect.isroutine(object):
            try:
                signature = inspect.signature(object)
            except (ValueError, TypeError):
                signature = None
            if signature:
                argspec = str(signature)
                if realname == '<lambda>':
                    title = '<strong>%s</strong> <em>lambda</em> ' % name
                    argspec = argspec[1:-1]
        if not argspec:
            argspec = '(...)'
        decl = title + self.escape(argspec) + (note and self.grey('<font face="helvetica, arial">%s</font>' % note))
        if skipdocs:
            return '<dl><dt>%s</dt></dl>\n' % decl
        else:
            doc = self.markup(getdoc(object), self.preformat, funcs, classes, methods)
            doc = doc and '<dd><tt>%s</tt></dd>' % doc
            return '<dl><dt>%s</dt>%s</dl>\n' % (decl, doc)

    def _docdescriptor(self, name, value, mod):
        results = []
        push = results.append
        if name:
            push('<dl><dt><strong>%s</strong></dt>\n' % name)
        if value.__doc__ is not None:
            doc = self.markup(getdoc(value), self.preformat)
            push('<dd><tt>%s</tt></dd>\n' % doc)
        push('</dl>\n')
        return ''.join(results)

    def docproperty(self, object, name=None, mod=None, cl=None):
        return self._docdescriptor(name, object, mod)

    def docother(self, object, name=None, mod=None, *ignored):
        if name:
            pass
        lhs = ''
        return lhs + self.repr(object)

    def docdata(self, object, name=None, mod=None, cl=None):
        return self._docdescriptor(name, object, mod)

    def index(self, dir, shadowed=None):
        modpkgs = []
        if shadowed is None:
            shadowed = {}
        for (importer, name, ispkg) in pkgutil.iter_modules([dir]):
            if any(55296 <= ord(ch) <= 57343 for ch in name):
                pass
            else:
                modpkgs.append((name, '', ispkg, name in shadowed))
                shadowed[name] = 1
        modpkgs.sort()
        contents = self.multicolumn(modpkgs, self.modpkglink)
        return self.bigsection(dir, '#ffffff', '#ee77aa', contents)

class TextRepr(Repr):

    def __init__(self):
        Repr.__init__(self)
        self.maxlist = self.maxtuple = 20
        self.maxdict = 10
        self.maxstring = self.maxother = 100

    def repr1(self, x, level):
        if hasattr(type(x), '__name__'):
            methodname = 'repr_' + '_'.join(type(x).__name__.split())
            if hasattr(self, methodname):
                return getattr(self, methodname)(x, level)
        return cram(stripid(repr(x)), self.maxother)

    def repr_string(self, x, level):
        test = cram(x, self.maxstring)
        testrepr = repr(test)
        if '\\' in test and '\\' not in replace(testrepr, '\\\\', ''):
            return 'r' + testrepr[0] + test + testrepr[0]
        return testrepr

    repr_str = repr_string

    def repr_instance(self, x, level):
        try:
            return cram(stripid(repr(x)), self.maxstring)
        except:
            return '<%s instance>' % x.__class__.__name__

class TextDoc(Doc):
    _repr_instance = TextRepr()
    repr = _repr_instance.repr

    def bold(self, text):
        return ''.join(ch + '\x08' + ch for ch in text)

    def indent(self, text, prefix='    '):
        if not text:
            return ''
        lines = [prefix + line for line in text.split('\n')]
        if lines:
            lines[-1] = lines[-1].rstrip()
        return '\n'.join(lines)

    def section(self, title, contents):
        clean_contents = self.indent(contents).rstrip()
        return self.bold(title) + '\n' + clean_contents + '\n\n'

    def formattree(self, tree, modname, parent=None, prefix=''):
        result = ''
        for entry in tree:
            if type(entry) is type(()):
                (c, bases) = entry
                result = result + prefix + classname(c, modname)
                if bases != (parent,):
                    parents = (classname(c, modname) for c in bases)
                    result = result + '(%s)' % ', '.join(parents)
                result = result + '\n'
            elif type(entry) is type([]):
                result = result + self.formattree(entry, modname, c, prefix + '    ')
        return result

    def docmodule(self, object, name=None, mod=None):
        name = object.__name__
        (synop, desc) = splitdoc(getdoc(object))
        result = self.section('NAME', name + (synop and ' - ' + synop))
        all = getattr(object, '__all__', None)
        docloc = self.getdocloc(object)
        if docloc is not None:
            result = result + self.section('MODULE REFERENCE', docloc + '\n\nThe following documentation is automatically generated from the Python\nsource files.  It may be incomplete, incorrect or include features that\nare considered implementation detail and may vary between Python\nimplementations.  When in doubt, consult the module reference at the\nlocation listed above.\n')
        if desc:
            result = result + self.section('DESCRIPTION', desc)
        classes = []
        for (key, value) in inspect.getmembers(object, inspect.isclass):
            if not all is not None:
                pass
            if visiblename(key, all, object):
                classes.append((key, value))
        funcs = []
        for (key, value) in inspect.getmembers(object, inspect.isroutine):
            if not inspect.isbuiltin(value):
                pass
            if all is not None or visiblename(key, all, object):
                funcs.append((key, value))
        data = []
        for (key, value) in inspect.getmembers(object, isdata):
            if visiblename(key, all, object):
                data.append((key, value))
        modpkgs = []
        modpkgs_names = set()
        if hasattr(object, '__path__'):
            for (importer, modname, ispkg) in pkgutil.iter_modules(object.__path__):
                modpkgs_names.add(modname)
                if ispkg:
                    modpkgs.append(modname + ' (package)')
                else:
                    modpkgs.append(modname)
            modpkgs.sort()
            result = result + self.section('PACKAGE CONTENTS', '\n'.join(modpkgs))
        submodules = []
        for (key, value) in inspect.getmembers(object, inspect.ismodule):
            if value.__name__.startswith(name + '.') and key not in modpkgs_names:
                submodules.append(key)
        if submodules:
            submodules.sort()
            result = result + self.section('SUBMODULES', '\n'.join(submodules))
        if classes:
            classlist = [value for (key, value) in classes]
            contents = [self.formattree(inspect.getclasstree(classlist, 1), name)]
            for (key, value) in classes:
                contents.append(self.document(value, key, name))
            result = result + self.section('CLASSES', '\n'.join(contents))
        if funcs:
            contents = []
            for (key, value) in funcs:
                contents.append(self.document(value, key, name))
            result = result + self.section('FUNCTIONS', '\n'.join(contents))
        if data:
            contents = []
            for (key, value) in data:
                contents.append(self.docother(value, key, name, maxlen=70))
            result = result + self.section('DATA', '\n'.join(contents))
        if hasattr(object, '__version__'):
            version = str(object.__version__)
            if version[-1:] == '$':
                version = version[11:-1].strip()
            result = result + self.section('VERSION', version)
        if hasattr(object, '__date__'):
            result = result + self.section('DATE', str(object.__date__))
        if hasattr(object, '__author__'):
            result = result + self.section('AUTHOR', str(object.__author__))
        if hasattr(object, '__credits__'):
            result = result + self.section('CREDITS', str(object.__credits__))
        try:
            file = inspect.getabsfile(object)
        except TypeError:
            file = '(built-in)'
        result = result + self.section('FILE', file)
        return result

    def docclass(self, object, name=None, mod=None, *ignored):
        realname = object.__name__
        name = name or realname
        bases = object.__bases__

        def makename(c, m=object.__module__):
            return classname(c, m)

        if name == realname:
            title = 'class ' + self.bold(realname)
        else:
            title = self.bold(name) + ' = class ' + realname
        if bases:
            parents = map(makename, bases)
            title = title + '(%s)' % ', '.join(parents)
        contents = []
        push = contents.append
        try:
            signature = inspect.signature(object)
        except (ValueError, TypeError):
            signature = None
        if signature:
            argspec = str(signature)
            if argspec and argspec != '()':
                push(name + argspec + '\n')
        doc = getdoc(object)
        if doc:
            push(doc + '\n')
        mro = deque(inspect.getmro(object))
        if len(mro) > 2:
            push('Method resolution order:')
            for base in mro:
                push('    ' + makename(base))
            push('')

        class HorizontalRule:

            def __init__(self):
                self.needone = 0

            def maybe(self):
                if self.needone:
                    push('----------------------------------------------------------------------')
                self.needone = 1

        hr = HorizontalRule()

        def spill(msg, attrs, predicate):
            (ok, attrs) = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for (name, kind, homecls, value) in ok:
                    try:
                        value = getattr(object, name)
                    except Exception:
                        push(self._docdescriptor(name, value, mod))
                    push(self.document(value, name, mod, object))
            return attrs

        def spilldescriptors(msg, attrs, predicate):
            (ok, attrs) = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for (name, kind, homecls, value) in ok:
                    push(self._docdescriptor(name, value, mod))
            return attrs

        def spilldata(msg, attrs, predicate):
            (ok, attrs) = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for (name, kind, homecls, value) in ok:
                    if callable(value) or inspect.isdatadescriptor(value):
                        doc = getdoc(value)
                    else:
                        doc = None
                    try:
                        obj = getattr(object, name)
                    except AttributeError:
                        obj = homecls.__dict__[name]
                    push(self.docother(obj, name, mod, maxlen=70, doc=doc) + '\n')
            return attrs

        attrs = [(name, kind, cls, value) for (name, kind, cls, value) in classify_class_attrs(object) if visiblename(name, obj=object)]
        if attrs:
            if mro:
                thisclass = mro.popleft()
            else:
                thisclass = attrs[0][2]
            (attrs, inherited) = _split_list(attrs, lambda t: t[2] is thisclass)
            if thisclass is builtins.object:
                attrs = inherited
            elif thisclass is object:
                tag = 'defined here'
            else:
                tag = 'inherited from %s' % classname(thisclass, object.__module__)
            sort_attributes(attrs, object)
            attrs = spill('Methods %s:\n' % tag, attrs, lambda t: t[1] == 'method')
            attrs = spill('Class methods %s:\n' % tag, attrs, lambda t: t[1] == 'class method')
            attrs = spill('Static methods %s:\n' % tag, attrs, lambda t: t[1] == 'static method')
            attrs = spilldescriptors('Data descriptors %s:\n' % tag, attrs, lambda t: t[1] == 'data descriptor')
            attrs = spilldata('Data and other attributes %s:\n' % tag, attrs, lambda t: t[1] == 'data')
            attrs = inherited
        contents = '\n'.join(contents)
        if not contents:
            return title + '\n'
        return title + '\n' + self.indent(contents.rstrip(), ' |  ') + '\n'

    def formatvalue(self, object):
        return '=' + self.repr(object)

    def docroutine(self, object, name=None, mod=None, cl=None):
        realname = object.__name__
        name = name or realname
        note = ''
        skipdocs = 0
        if _is_bound_method(object):
            imclass = object.__self__.__class__
            if cl:
                if imclass is not cl:
                    note = ' from ' + classname(imclass, mod)
            elif object.__self__ is not None:
                note = ' method of %s instance' % classname(object.__self__.__class__, mod)
            else:
                note = ' unbound %s method' % classname(imclass, mod)
        if name == realname:
            title = self.bold(realname)
        else:
            if cl.__dict__[realname] is object:
                skipdocs = 1
            title = self.bold(name) + ' = ' + realname
        argspec = None
        if inspect.isroutine(object):
            try:
                signature = inspect.signature(object)
            except (ValueError, TypeError):
                signature = None
            if signature:
                argspec = str(signature)
                if realname == '<lambda>':
                    title = self.bold(name) + ' lambda '
                    argspec = argspec[1:-1]
        if not argspec:
            argspec = '(...)'
        decl = title + argspec + note
        if skipdocs:
            return decl + '\n'
        else:
            doc = getdoc(object) or ''
            return decl + '\n' + (doc and self.indent(doc).rstrip() + '\n')

    def _docdescriptor(self, name, value, mod):
        results = []
        push = results.append
        if name:
            push(self.bold(name))
            push('\n')
        doc = getdoc(value) or ''
        if doc:
            push(self.indent(doc))
            push('\n')
        return ''.join(results)

    def docproperty(self, object, name=None, mod=None, cl=None):
        return self._docdescriptor(name, object, mod)

    def docdata(self, object, name=None, mod=None, cl=None):
        return self._docdescriptor(name, object, mod)

    def docother(self, object, name=None, mod=None, parent=None, maxlen=None, doc=None):
        repr = self.repr(object)
        if maxlen:
            if name:
                pass
            line = '' + repr
            chop = maxlen - len(line)
            if chop < 0:
                repr = repr[:chop] + '...'
        if name:
            pass
        line = '' + repr
        if doc is not None:
            line += '\n' + self.indent(str(doc))
        return line

class _PlainTextDoc(TextDoc):

    def bold(self, text):
        return text

def pager(text):
    global pager
    pager = getpager()
    pager(text)

def getpager():
    if not hasattr(sys.stdin, 'isatty'):
        return plainpager
    if not hasattr(sys.stdout, 'isatty'):
        return plainpager
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return plainpager
    use_pager = os.environ.get('MANPAGER') or os.environ.get('PAGER')
    if use_pager:
        if sys.platform == 'win32':
            return lambda text: tempfilepager(plain(text), use_pager)
        if os.environ.get('TERM') in ('dumb', 'emacs'):
            return lambda text: pipepager(plain(text), use_pager)
        return lambda text: pipepager(text, use_pager)
    if os.environ.get('TERM') in ('dumb', 'emacs'):
        return plainpager
    if sys.platform == 'win32':
        return lambda text: tempfilepager(plain(text), 'more <')
    if hasattr(os, 'system') and os.system('(less) 2>/dev/null') == 0:
        return lambda text: pipepager(text, 'less')
    else:
        import tempfile
        (fd, filename) = tempfile.mkstemp()
        os.close(fd)
        try:
            if hasattr(os, 'system') and os.system('more "%s"' % filename) == 0:
                return lambda text: pipepager(text, 'more')
            return ttypager
        finally:
            os.unlink(filename)
    return ttypager
    os.unlink(filename)

def plain(text):
    return re.sub('.\x08', '', text)

def pipepager(text, cmd):
    import subprocess
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
    try:
        with io.TextIOWrapper(proc.stdin, errors='backslashreplace') as pipe:
            try:
                pipe.write(text)
            except KeyboardInterrupt:
                pass
    except OSError:
        pass
    while True:
        try:
            proc.wait()
            break
        except KeyboardInterrupt:
            pass

def tempfilepager(text, cmd):
    import tempfile
    filename = tempfile.mktemp()
    with open(filename, 'w', errors='backslashreplace') as file:
        file.write(text)
    try:
        os.system(cmd + ' "' + filename + '"')
    finally:
        os.unlink(filename)

def _escape_stdout(text):
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    return text.encode(encoding, 'backslashreplace').decode(encoding)

def ttypager(text):
    lines = plain(_escape_stdout(text)).split('\n')
    try:
        import tty
        fd = sys.stdin.fileno()
        old = tty.tcgetattr(fd)
        tty.setcbreak(fd)
        getchar = lambda : sys.stdin.read(1)
    except (ImportError, AttributeError, io.UnsupportedOperation):
        tty = None
        getchar = lambda : sys.stdin.readline()[:-1][:1]
    try:
        try:
            h = int(os.environ.get('LINES', 0))
        except ValueError:
            h = 0
        if h <= 1:
            h = 25
        r = inc = h - 1
        sys.stdout.write('\n'.join(lines[:inc]) + '\n')
        while lines[r:]:
            sys.stdout.write('-- more --')
            sys.stdout.flush()
            c = getchar()
            if c in ('q', 'Q'):
                sys.stdout.write('\r          \r')
                break
            elif c in ('\r', '\n'):
                sys.stdout.write('\r          \r' + lines[r] + '\n')
                r = r + 1
            else:
                if c in ('b', 'B', '\x1b'):
                    r = r - inc - inc
                    if r < 0:
                        r = 0
                sys.stdout.write('\n' + '\n'.join(lines[r:r + inc]) + '\n')
                r = r + inc
            if c in ('b', 'B', '\x1b'):
                r = r - inc - inc
                if r < 0:
                    r = 0
            sys.stdout.write('\n' + '\n'.join(lines[r:r + inc]) + '\n')
            r = r + inc
    finally:
        if tty:
            tty.tcsetattr(fd, tty.TCSAFLUSH, old)

def plainpager(text):
    sys.stdout.write(plain(_escape_stdout(text)))

def describe(thing):
    if inspect.ismodule(thing):
        if thing.__name__ in sys.builtin_module_names:
            return 'built-in module ' + thing.__name__
        if hasattr(thing, '__path__'):
            return 'package ' + thing.__name__
        return 'module ' + thing.__name__
    if inspect.isbuiltin(thing):
        return 'built-in function ' + thing.__name__
    if inspect.isgetsetdescriptor(thing):
        return 'getset descriptor %s.%s.%s' % (thing.__objclass__.__module__, thing.__objclass__.__name__, thing.__name__)
    if inspect.ismemberdescriptor(thing):
        return 'member descriptor %s.%s.%s' % (thing.__objclass__.__module__, thing.__objclass__.__name__, thing.__name__)
    if inspect.isclass(thing):
        return 'class ' + thing.__name__
    if inspect.isfunction(thing):
        return 'function ' + thing.__name__
    if inspect.ismethod(thing):
        return 'method ' + thing.__name__
    return type(thing).__name__

def locate(path, forceload=0):
    parts = [part for part in path.split('.') if part]
    (module, n) = (None, 0)
    while n < len(parts):
        nextmodule = safeimport('.'.join(parts[:n + 1]), forceload)
        if nextmodule:
            module = nextmodule
            n = n + 1
        else:
            break
    if module:
        object = module
    else:
        object = builtins
    for part in parts[n:]:
        try:
            object = getattr(object, part)
        except AttributeError:
            return
    return object
text = TextDoc()plaintext = _PlainTextDoc()html = HTMLDoc()
def resolve(thing, forceload=0):
    if isinstance(thing, str):
        object = locate(thing, forceload)
        if object is None:
            raise ImportError('No Python documentation found for %r.\nUse help() to get the interactive help utility.\nUse help(str) for help on the str class.' % thing)
        return (object, thing)
    else:
        name = getattr(thing, '__name__', None)
        return (thing, name if isinstance(name, str) else None)

def render_doc(thing, title='Python Library Documentation: %s', forceload=0, renderer=None):
    if renderer is None:
        renderer = text
    (object, name) = resolve(thing, forceload)
    desc = describe(object)
    module = inspect.getmodule(object)
    if name and '.' in name:
        desc += ' in ' + name[:name.rfind('.')]
    elif module is not object:
        desc += ' in module ' + module.__name__
    if not isinstance(object, property):
        object = type(object)
        desc += ' object'
    return title % desc + '\n\n' + renderer.document(object, name)

def doc(thing, title='Python Library Documentation: %s', forceload=0, output=None):
    try:
        if output is None:
            pager(render_doc(thing, title, forceload))
        else:
            output.write(render_doc(thing, title, forceload, plaintext))
    except (ImportError, ErrorDuringImport) as value:
        print(value)

def writedoc(thing, forceload=0):
    try:
        (object, name) = resolve(thing, forceload)
        page = html.page(describe(object), html.document(object, name))
        with open(name + '.html', 'w', encoding='utf-8') as file:
            file.write(page)
        print('wrote', name + '.html')
    except (ImportError, ErrorDuringImport) as value:
        print(value)

def writedocs(dir, pkgpath='', done=None):
    if done is None:
        done = {}
    for (importer, modname, ispkg) in pkgutil.walk_packages([dir], pkgpath):
        writedoc(modname)
