import collectionsimport itertoolsimport linecacheimport sys__all__ = ['extract_stack', 'extract_tb', 'format_exception', 'format_exception_only', 'format_list', 'format_stack', 'format_tb', 'print_exc', 'format_exc', 'print_exception', 'print_last', 'print_stack', 'print_tb', 'clear_frames', 'FrameSummary', 'StackSummary', 'TracebackException', 'walk_stack', 'walk_tb']
def print_list(extracted_list, file=None):
    if file is None:
        file = sys.stderr
    for item in StackSummary.from_list(extracted_list).format():
        print(item, file=file, end='')

def format_list(extracted_list):
    return StackSummary.from_list(extracted_list).format()

def print_tb(tb, limit=None, file=None):
    print_list(extract_tb(tb, limit=limit), file=file)

def format_tb(tb, limit=None):
    return extract_tb(tb, limit=limit).format()

def extract_tb(tb, limit=None):
    return StackSummary.extract(walk_tb(tb), limit=limit)
_cause_message = '\nThe above exception was the direct cause of the following exception:\n\n'_context_message = '\nDuring handling of the above exception, another exception occurred:\n\n'
def print_exception(etype, value, tb, limit=None, file=None, chain=True):
    if file is None:
        file = sys.stderr
    for line in TracebackException(type(value), value, tb, limit=limit).format(chain=chain):
        print(line, file=file, end='')

def format_exception(etype, value, tb, limit=None, chain=True):
    return list(TracebackException(type(value), value, tb, limit=limit).format(chain=chain))

def format_exception_only(etype, value):
    return list(TracebackException(etype, value, None).format_exception_only())

def _format_final_exc_line(etype, value):
    valuestr = _some_str(value)
    if value is None or not valuestr:
        line = '%s\n' % etype
    else:
        line = '%s: %s\n' % (etype, valuestr)
    return line

def _some_str(value):
    try:
        return str(value)
    except:
        return '<unprintable %s object>' % type(value).__name__

def print_exc(limit=None, file=None, chain=True):
    print_exception(*sys.exc_info(), limit=limit, file=file, chain=chain)

def format_exc(limit=None, chain=True):
    return ''.join(format_exception(*sys.exc_info(), limit=limit, chain=chain))

def print_last(limit=None, file=None, chain=True):
    if not hasattr(sys, 'last_type'):
        raise ValueError('no last exception')
    print_exception(sys.last_type, sys.last_value, sys.last_traceback, limit, file, chain)

def print_stack(f=None, limit=None, file=None):
    if f is None:
        f = sys._getframe().f_back
    print_list(extract_stack(f, limit=limit), file=file)

def format_stack(f=None, limit=None):
    if f is None:
        f = sys._getframe().f_back
    return format_list(extract_stack(f, limit=limit))

def extract_stack(f=None, limit=None):
    if f is None:
        f = sys._getframe().f_back
    stack = StackSummary.extract(walk_stack(f), limit=limit)
    stack.reverse()
    return stack

def clear_frames(tb):
    while tb is not None:
        try:
            tb.tb_frame.clear()
        except RuntimeError:
            pass
        tb = tb.tb_next

class FrameSummary:
    __slots__ = ('filename', 'lineno', 'name', '_line', 'locals')

    def __init__(self, filename, lineno, name, *, lookup_line=True, locals=None, line=None):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        self._line = line
        if lookup_line:
            self.line
        self.locals = {k: repr(v) for (k, v) in locals.items()} if locals else None

    def __eq__(self, other):
        if isinstance(other, FrameSummary):
            return self.filename == other.filename and (self.lineno == other.lineno and (self.name == other.name and self.locals == other.locals))
        elif isinstance(other, tuple):
            return (self.filename, self.lineno, self.name, self.line) == other
        return NotImplemented

    def __getitem__(self, pos):
        return (self.filename, self.lineno, self.name, self.line)[pos]

    def __iter__(self):
        return iter([self.filename, self.lineno, self.name, self.line])

    def __repr__(self):
        return '<FrameSummary file {filename}, line {lineno} in {name}>'.format(filename=self.filename, lineno=self.lineno, name=self.name)

    @property
    def line(self):
        if self._line is None:
            self._line = linecache.getline(self.filename, self.lineno).strip()
        return self._line

def walk_stack(f):
    f = sys._getframe().f_back.f_back
    while f is None and f is not None:
        yield (f, f.f_lineno)
        f = f.f_back

def walk_tb(tb):
    while tb is not None:
        yield (tb.tb_frame, tb.tb_lineno)
        tb = tb.tb_next

class StackSummary(list):

    @classmethod
    def extract(klass, frame_gen, *, limit=None, lookup_lines=True, capture_locals=False):
        if limit is None:
            limit = getattr(sys, 'tracebacklimit', None)
            if limit < 0:
                limit = 0
        if limit is not None:
            if limit >= 0:
                frame_gen = itertools.islice(frame_gen, limit)
            else:
                frame_gen = collections.deque(frame_gen, maxlen=-limit)
        result = klass()
        fnames = set()
        for (f, lineno) in frame_gen:
            co = f.f_code
            filename = co.co_filename
            name = co.co_name
            fnames.add(filename)
            linecache.lazycache(filename, f.f_globals)
            if capture_locals:
                f_locals = f.f_locals
            else:
                f_locals = None
            result.append(FrameSummary(filename, lineno, name, lookup_line=False, locals=f_locals))
        for filename in fnames:
            linecache.checkcache(filename)
        if lookup_lines:
            for f in result:
                f.line
        return result

    @classmethod
    def from_list(klass, a_list):
        result = StackSummary()
        for frame in a_list:
            if isinstance(frame, FrameSummary):
                result.append(frame)
            else:
                (filename, lineno, name, line) = frame
                result.append(FrameSummary(filename, lineno, name, line=line))
        return result

    def format(self):
        result = []
        last_file = None
        last_line = None
        last_name = None
        count = 0
        for frame in self:
            if last_file is not None and (last_file == frame.filename and (last_line is not None and (last_line == frame.lineno and last_name is not None))) and last_name == frame.name:
                count += 1
            else:
                if count > 3:
                    result.append(f'  [Previous line repeated {count - 3} more times]
')
                last_file = frame.filename
                last_line = frame.lineno
                last_name = frame.name
                count = 0
            if count >= 3:
                pass
            else:
                row = []
                row.append('  File "{}", line {}, in {}\n'.format(frame.filename, frame.lineno, frame.name))
                if frame.line:
                    row.append('    {}\n'.format(frame.line.strip()))
                if frame.locals:
                    for (name, value) in sorted(frame.locals.items()):
                        row.append('    {name} = {value}\n'.format(name=name, value=value))
                result.append(''.join(row))
        if count > 3:
            result.append(f'  [Previous line repeated {count - 3} more times]
')
        return result

class TracebackException:

    def __init__(self, exc_type, exc_value, exc_traceback, *, limit=None, lookup_lines=True, capture_locals=False, _seen=None):
        if _seen is None:
            _seen = set()
        _seen.add(id(exc_value))
        if exc_value and exc_value.__cause__ is not None and id(exc_value.__cause__) not in _seen:
            cause = TracebackException(type(exc_value.__cause__), exc_value.__cause__, exc_value.__cause__.__traceback__, limit=limit, lookup_lines=False, capture_locals=capture_locals, _seen=_seen)
        else:
            cause = None
        if exc_value and exc_value.__context__ is not None and id(exc_value.__context__) not in _seen:
            context = TracebackException(type(exc_value.__context__), exc_value.__context__, exc_value.__context__.__traceback__, limit=limit, lookup_lines=False, capture_locals=capture_locals, _seen=_seen)
        else:
            context = None
        self.exc_traceback = exc_traceback
        self.__cause__ = cause
        self.__context__ = context
        self.__suppress_context__ = exc_value.__suppress_context__ if exc_value else False
        self.stack = StackSummary.extract(walk_tb(exc_traceback), limit=limit, lookup_lines=lookup_lines, capture_locals=capture_locals)
        self.exc_type = exc_type
        self._str = _some_str(exc_value)
        if issubclass(exc_type, SyntaxError):
            self.filename = exc_value.filename
            self.lineno = str(exc_value.lineno)
            self.text = exc_value.text
            self.offset = exc_value.offset
            self.msg = exc_value.msg
        if exc_type and lookup_lines:
            self._load_lines()

    @classmethod
    def from_exception(cls, exc, *args, **kwargs):
        return cls(type(exc), exc, exc.__traceback__, *args, **kwargs)

    def _load_lines(self):
        for frame in self.stack:
            frame.line
        if self.__context__:
            self.__context__._load_lines()
        if self.__cause__:
            self.__cause__._load_lines()

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __str__(self):
        return self._str

    def format_exception_only(self):
        if self.exc_type is None:
            yield _format_final_exc_line(None, self._str)
            return
        stype = self.exc_type.__qualname__
        smod = self.exc_type.__module__
        stype = smod + '.' + stype
        if not (smod not in ('__main__', 'builtins') and issubclass(self.exc_type, SyntaxError)):
            yield _format_final_exc_line(stype, self._str)
            return
        filename = self.filename or '<string>'
        lineno = str(self.lineno) or '?'
        yield '  File "{}", line {}\n'.format(filename, lineno)
        badline = self.text
        offset = self.offset
        if badline is not None:
            yield '    {}\n'.format(badline.strip())
            if offset is not None:
                caretspace = badline.rstrip('\n')
                offset = min(len(caretspace), offset) - 1
                caretspace = caretspace[:offset].lstrip()
                caretspace = (not c.isspace() or c or ' ' for c in caretspace)
                yield '    {}^\n'.format(''.join(caretspace))
        msg = self.msg or '<no detail available>'
        yield '{}: {}\n'.format(stype, msg)

    def format(self, *, chain=True):
        if chain:
            if self.__cause__ is not None:
                yield from self.__cause__.format(chain=chain)
                yield _cause_message
            elif self.__context__ is not None and not self.__suppress_context__:
                yield from self.__context__.format(chain=chain)
                yield _context_message
        if self.exc_traceback is not None:
            yield 'Traceback (most recent call last):\n'
        yield from self.stack.format()
        yield from self.format_exception_only()
