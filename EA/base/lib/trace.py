__all__ = ['Trace', 'CoverageResults']import linecacheimport osimport reimport sysimport tokenimport tokenizeimport inspectimport gcimport disimport picklefrom time import monotonic as _timeimport threading
def _settrace(func):
    threading.settrace(func)
    sys.settrace(func)

def _unsettrace():
    sys.settrace(None)
    threading.settrace(None)
PRAGMA_NOCOVER = '#pragma NO COVER'
class _Ignore:

    def __init__(self, modules=None, dirs=None):
        self._mods = set() if not modules else set(modules)
        self._dirs = [] if not dirs else [os.path.normpath(d) for d in dirs]
        self._ignore = {'<string>': 1}

    def names(self, filename, modulename):
        if modulename in self._ignore:
            return self._ignore[modulename]
        if modulename in self._mods:
            self._ignore[modulename] = 1
            return 1
        for mod in self._mods:
            if modulename.startswith(mod + '.'):
                self._ignore[modulename] = 1
                return 1
        if filename is None:
            self._ignore[modulename] = 1
            return 1
        for d in self._dirs:
            if filename.startswith(d + os.sep):
                self._ignore[modulename] = 1
                return 1
        self._ignore[modulename] = 0
        return 0

def _modname(path):
    base = os.path.basename(path)
    (filename, ext) = os.path.splitext(base)
    return filename

def _fullmodname(path):
    comparepath = os.path.normcase(path)
    longest = ''
    for dir in sys.path:
        dir = os.path.normcase(dir)
        if comparepath.startswith(dir) and comparepath[len(dir)] == os.sep and len(dir) > len(longest):
            longest = dir
    if longest:
        base = path[len(longest) + 1:]
    else:
        base = path
    (drive, base) = os.path.splitdrive(base)
    base = base.replace(os.sep, '.')
    if os.altsep:
        base = base.replace(os.altsep, '.')
    (filename, ext) = os.path.splitext(base)
    return filename.lstrip('.')

class CoverageResults:

    def __init__(self, counts=None, calledfuncs=None, infile=None, callers=None, outfile=None):
        self.counts = counts
        if self.counts is None:
            self.counts = {}
        self.counter = self.counts.copy()
        self.calledfuncs = calledfuncs
        if self.calledfuncs is None:
            self.calledfuncs = {}
        self.calledfuncs = self.calledfuncs.copy()
        self.callers = callers
        if self.callers is None:
            self.callers = {}
        self.callers = self.callers.copy()
        self.infile = infile
        self.outfile = outfile
        if self.infile:
            try:
                with open(self.infile, 'rb') as f:
                    (counts, calledfuncs, callers) = pickle.load(f)
                self.update(self.__class__(counts, calledfuncs, callers))
            except (OSError, EOFError, ValueError) as err:
                print('Skipping counts file %r: %s' % (self.infile, err), file=sys.stderr)

    def is_ignored_filename(self, filename):
        return filename.startswith('<') and filename.endswith('>')

    def update(self, other):
        counts = self.counts
        calledfuncs = self.calledfuncs
        callers = self.callers
        other_counts = other.counts
        other_calledfuncs = other.calledfuncs
        other_callers = other.callers
        for key in other_counts:
            counts[key] = counts.get(key, 0) + other_counts[key]
        for key in other_calledfuncs:
            calledfuncs[key] = 1
        for key in other_callers:
            callers[key] = 1

    def write_results(self, show_missing=True, summary=False, coverdir=None):
        if self.calledfuncs:
            print()
            print('functions called:')
            calls = self.calledfuncs
            for (filename, modulename, funcname) in sorted(calls):
                print('filename: %s, modulename: %s, funcname: %s' % (filename, modulename, funcname))
        if self.callers:
            print()
            print('calling relationships:')
            lastfile = lastcfile = ''
            for ((pfile, pmod, pfunc), (cfile, cmod, cfunc)) in sorted(self.callers):
                if pfile != lastfile:
                    print()
                    print('***', pfile, '***')
                    lastfile = pfile
                    lastcfile = ''
                if lastcfile != cfile:
                    print('  -->', cfile)
                    lastcfile = cfile
                print('    %s.%s -> %s.%s' % (pmod, pfunc, cmod, cfunc))
        per_file = {}
        for (filename, lineno) in self.counts:
            lines_hit = per_file[filename] = per_file.get(filename, {})
            lines_hit[lineno] = self.counts[(filename, lineno)]
        sums = {}
        for (filename, count) in per_file.items():
            if self.is_ignored_filename(filename):
                pass
            else:
                if filename.endswith('.pyc'):
                    filename = filename[:-1]
                if coverdir is None:
                    dir = os.path.dirname(os.path.abspath(filename))
                    modulename = _modname(filename)
                else:
                    dir = coverdir
                    if not os.path.exists(dir):
                        os.makedirs(dir)
                    modulename = _fullmodname(filename)
                if show_missing:
                    lnotab = _find_executable_linenos(filename)
                else:
                    lnotab = {}
                source = linecache.getlines(filename)
                coverpath = os.path.join(dir, modulename + '.cover')
                with open(filename, 'rb') as fp:
                    (encoding, _) = tokenize.detect_encoding(fp.readline)
                (n_hits, n_lines) = self.write_results_file(coverpath, source, lnotab, count, encoding)
                if summary and n_lines:
                    percent = int(100*n_hits/n_lines)
                    sums[modulename] = (n_lines, percent, modulename, filename)
        if sums:
            print('lines   cov%   module   (path)')
            for m in sorted(sums):
                (n_lines, percent, modulename, filename) = sums[m]
                print('%5d   %3d%%   %s   (%s)' % sums[m])
        if summary and self.outfile:
            try:
                pickle.dump((self.counts, self.calledfuncs, self.callers), open(self.outfile, 'wb'), 1)
            except OSError as err:
                print("Can't save counts files because %s" % err, file=sys.stderr)

    def write_results_file(self, path, lines, lnotab, lines_hit, encoding=None):
        try:
            outfile = open(path, 'w', encoding=encoding)
        except OSError as err:
            print('trace: Could not open %r for writing: %s- skipping' % (path, err), file=sys.stderr)
            return (0, 0)
        n_lines = 0
        n_hits = 0
        with outfile:
            for (lineno, line) in enumerate(lines, 1):
                if lineno in lines_hit:
                    outfile.write('%5d: ' % lines_hit[lineno])
                    n_hits += 1
                    n_lines += 1
                elif lineno in lnotab and PRAGMA_NOCOVER not in line:
                    outfile.write('>>>>>> ')
                    n_lines += 1
                else:
                    outfile.write('       ')
                outfile.write(line.expandtabs(8))
        return (n_hits, n_lines)

def _find_lines_from_code(code, strs):
    linenos = {}
    for (_, lineno) in dis.findlinestarts(code):
        if lineno not in strs:
            linenos[lineno] = 1
    return linenos

def _find_lines(code, strs):
    linenos = _find_lines_from_code(code, strs)
    for c in code.co_consts:
        if inspect.iscode(c):
            linenos.update(_find_lines(c, strs))
    return linenos

def _find_strings(filename, encoding=None):
    d = {}
    prev_ttype = token.INDENT
    with open(filename, encoding=encoding) as f:
        tok = tokenize.generate_tokens(f.readline)
        for (ttype, tstr, start, end, line) in tok:
            if prev_ttype == token.INDENT:
                (sline, scol) = start
                (eline, ecol) = end
                for i in range(sline, eline + 1):
                    d[i] = 1
            prev_ttype = ttype
    return d

def _find_executable_linenos(filename):
    try:
        with tokenize.open(filename) as f:
            prog = f.read()
            encoding = f.encoding
    except OSError as err:
        print('Not printing coverage data for %r: %s' % (filename, err), file=sys.stderr)
        return {}
    code = compile(prog, filename, 'exec')
    strs = _find_strings(filename, encoding)
    return _find_lines(code, strs)

class Trace:

    def __init__(self, count=1, trace=1, countfuncs=0, countcallers=0, ignoremods=(), ignoredirs=(), infile=None, outfile=None, timing=False):
        self.infile = infile
        self.outfile = outfile
        self.ignore = _Ignore(ignoremods, ignoredirs)
        self.counts = {}
        self.pathtobasename = {}
        self.donothing = 0
        self.trace = trace
        self._calledfuncs = {}
        self._callers = {}
        self._caller_cache = {}
        self.start_time = None
        if timing:
            self.start_time = _time()
        if countcallers:
            self.globaltrace = self.globaltrace_trackcallers
        elif countfuncs:
            self.globaltrace = self.globaltrace_countfuncs
        elif trace and count:
            self.globaltrace = self.globaltrace_lt
            self.localtrace = self.localtrace_trace_and_count
        elif trace:
            self.globaltrace = self.globaltrace_lt
            self.localtrace = self.localtrace_trace
        elif count:
            self.globaltrace = self.globaltrace_lt
            self.localtrace = self.localtrace_count
        else:
            self.donothing = 1

    def run(self, cmd):
        import __main__
        dict = __main__.__dict__
        self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals=None, locals=None):
        if globals is None:
            globals = {}
        if locals is None:
            locals = {}
        if not self.donothing:
            _settrace(self.globaltrace)
        try:
            exec(cmd, globals, locals)
        finally:
            if not self.donothing:
                _unsettrace()

    def runfunc(self, func, *args, **kw):
        result = None
        if not self.donothing:
            sys.settrace(self.globaltrace)
        try:
            result = func(*args, **kw)
        finally:
            if not self.donothing:
                sys.settrace(None)
        return result

    def file_module_function_of(self, frame):
        code = frame.f_code
        filename = code.co_filename
        if filename:
            modulename = _modname(filename)
        else:
            modulename = None
        funcname = code.co_name
        clsname = None
        if code in self._caller_cache:
            if self._caller_cache[code] is not None:
                clsname = self._caller_cache[code]
        else:
            self._caller_cache[code] = None
            funcs = [f for f in gc.get_referrers(code) if inspect.isfunction(f)]
            if len(funcs) == 1:
                dicts = [d for d in gc.get_referrers(funcs[0]) if isinstance(d, dict)]
                if len(dicts) == 1:
                    classes = [c for c in gc.get_referrers(dicts[0]) if hasattr(c, '__bases__')]
                    if len(classes) == 1:
                        clsname = classes[0].__name__
                        self._caller_cache[code] = clsname
        if clsname is not None:
            funcname = '%s.%s' % (clsname, funcname)
        return (filename, modulename, funcname)

    def globaltrace_trackcallers(self, frame, why, arg):
        if why == 'call':
            this_func = self.file_module_function_of(frame)
            parent_func = self.file_module_function_of(frame.f_back)
            self._callers[(parent_func, this_func)] = 1

    def globaltrace_countfuncs(self, frame, why, arg):
        if why == 'call':
            this_func = self.file_module_function_of(frame)
            self._calledfuncs[this_func] = 1

    def globaltrace_lt(self, frame, why, arg):
        if why == 'call':
            code = frame.f_code
            filename = frame.f_globals.get('__file__', None)
            if filename:
                modulename = _modname(filename)
                if modulename is not None:
                    ignore_it = self.ignore.names(filename, modulename)
                    if not ignore_it:
                        if self.trace:
                            print(' --- modulename: %s, funcname: %s' % (modulename, code.co_name))
                        return self.localtrace
            else:
                return

    def localtrace_trace_and_count(self, frame, why, arg):
        if why == 'line':
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            key = (filename, lineno)
            self.counts[key] = self.counts.get(key, 0) + 1
            if self.start_time:
                print('%.2f' % (_time() - self.start_time), end=' ')
            bname = os.path.basename(filename)
            print('%s(%d): %s' % (bname, lineno, linecache.getline(filename, lineno)), end='')
        return self.localtrace

    def localtrace_trace(self, frame, why, arg):
        if why == 'line':
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            if self.start_time:
                print('%.2f' % (_time() - self.start_time), end=' ')
            bname = os.path.basename(filename)
            print('%s(%d): %s' % (bname, lineno, linecache.getline(filename, lineno)), end='')
        return self.localtrace

    def localtrace_count(self, frame, why, arg):
        if why == 'line':
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            key = (filename, lineno)
            self.counts[key] = self.counts.get(key, 0) + 1
        return self.localtrace

    def results(self):
        return CoverageResults(self.counts, infile=self.infile, outfile=self.outfile, calledfuncs=self._calledfuncs, callers=self._callers)
