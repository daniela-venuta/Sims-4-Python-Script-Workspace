import sysimport osimport timeimport ioimport tracebackimport warningsimport weakrefimport collections.abcfrom string import Template__all__ = ['BASIC_FORMAT', 'BufferingFormatter', 'CRITICAL', 'DEBUG', 'ERROR', 'FATAL', 'FileHandler', 'Filter', 'Formatter', 'Handler', 'INFO', 'LogRecord', 'Logger', 'LoggerAdapter', 'NOTSET', 'NullHandler', 'StreamHandler', 'WARN', 'WARNING', 'addLevelName', 'basicConfig', 'captureWarnings', 'critical', 'debug', 'disable', 'error', 'exception', 'fatal', 'getLevelName', 'getLogger', 'getLoggerClass', 'info', 'log', 'makeLogRecord', 'setLoggerClass', 'shutdown', 'warn', 'warning', 'getLogRecordFactory', 'setLogRecordFactory', 'lastResort', 'raiseExceptions']import threading__author__ = 'Vinay Sajip <vinay_sajip@red-dove.com>'__status__ = 'production'__version__ = '0.5.1.2'__date__ = '07 February 2010'_startTime = time.time()raiseExceptions = TruelogThreads = TruelogMultiprocessing = TruelogProcesses = TrueCRITICAL = 50FATAL = CRITICALERROR = 40WARNING = 30WARN = WARNINGINFO = 20DEBUG = 10NOTSET = 0_levelToName = {NOTSET: 'NOTSET', DEBUG: 'DEBUG', INFO: 'INFO', WARNING: 'WARNING', ERROR: 'ERROR', CRITICAL: 'CRITICAL'}_nameToLevel = {'CRITICAL': CRITICAL, 'FATAL': FATAL, 'ERROR': ERROR, 'WARN': WARNING, 'WARNING': WARNING, 'INFO': INFO, 'DEBUG': DEBUG, 'NOTSET': NOTSET}
def getLevelName(level):
    result = _levelToName.get(level)
    if result is not None:
        return result
    result = _nameToLevel.get(level)
    if result is not None:
        return result
    return 'Level %s' % level

def addLevelName(level, levelName):
    _acquireLock()
    try:
        _levelToName[level] = levelName
        _nameToLevel[levelName] = level
    finally:
        _releaseLock()
if hasattr(sys, '_getframe'):
    currentframe = lambda : sys._getframe(3)
else:

    def currentframe():
        try:
            raise Exception
        except Exception:
            return sys.exc_info()[2].tb_frame.f_back
_srcfile = os.path.normcase(addLevelName.__code__.co_filename)
def _checkLevel(level):
    if isinstance(level, int):
        rv = level
    elif str(level) == level:
        if level not in _nameToLevel:
            raise ValueError('Unknown level: %r' % level)
        rv = _nameToLevel[level]
    else:
        raise TypeError('Level not an integer or a valid string: %r' % level)
    return rv
_lock = threading.RLock()
def _acquireLock():
    if _lock:
        _lock.acquire()

def _releaseLock():
    if _lock:
        _lock.release()

class LogRecord(object):

    def __init__(self, name, level, pathname, lineno, msg, args, exc_info, func=None, sinfo=None, **kwargs):
        ct = time.time()
        self.name = name
        self.msg = msg
        if args[0]:
            args = args[0]
        self.args = args
        self.levelname = getLevelName(level)
        self.levelno = level
        self.pathname = pathname
        try:
            self.filename = os.path.basename(pathname)
            self.module = os.path.splitext(self.filename)[0]
        except (TypeError, ValueError, AttributeError):
            self.filename = pathname
            self.module = 'Unknown module'
        self.exc_info = exc_info
        self.exc_text = None
        self.stack_info = sinfo
        self.lineno = lineno
        self.funcName = func
        self.created = ct
        self.msecs = (ct - int(ct))*1000
        self.relativeCreated = (self.created - _startTime)*1000
        if args and (len(args) == 1 and isinstance(args[0], collections.abc.Mapping)) and logThreads:
            self.thread = threading.get_ident()
            self.threadName = threading.current_thread().name
        else:
            self.thread = None
            self.threadName = None
        if not logMultiprocessing:
            self.processName = None
        else:
            self.processName = 'MainProcess'
            mp = sys.modules.get('multiprocessing')
            if mp is not None:
                try:
                    self.processName = mp.current_process().name
                except Exception:
                    pass
        if logProcesses and hasattr(os, 'getpid'):
            self.process = os.getpid()
        else:
            self.process = None

    def __str__(self):
        return '<LogRecord: %s, %s, %s, %s, "%s">' % (self.name, self.levelno, self.pathname, self.lineno, self.msg)

    __repr__ = __str__

    def getMessage(self):
        msg = str(self.msg)
        if self.args:
            msg = msg % self.args
        return msg
_logRecordFactory = LogRecord
def setLogRecordFactory(factory):
    global _logRecordFactory
    _logRecordFactory = factory

def getLogRecordFactory():
    return _logRecordFactory

def makeLogRecord(dict):
    rv = _logRecordFactory(None, None, '', 0, '', (), None, None)
    rv.__dict__.update(dict)
    return rv

class PercentStyle(object):
    default_format = '%(message)s'
    asctime_format = '%(asctime)s'
    asctime_search = '%(asctime)'

    def __init__(self, fmt):
        self._fmt = fmt or self.default_format

    def usesTime(self):
        return self._fmt.find(self.asctime_search) >= 0

    def format(self, record):
        return self._fmt % record.__dict__

class StrFormatStyle(PercentStyle):
    default_format = '{message}'
    asctime_format = '{asctime}'
    asctime_search = '{asctime'

    def format(self, record):
        return self._fmt.format(**record.__dict__)

class StringTemplateStyle(PercentStyle):
    default_format = '${message}'
    asctime_format = '${asctime}'
    asctime_search = '${asctime}'

    def __init__(self, fmt):
        self._fmt = fmt or self.default_format
        self._tpl = Template(self._fmt)

    def usesTime(self):
        fmt = self._fmt
        return fmt.find('$asctime') >= 0 or fmt.find(self.asctime_format) >= 0

    def format(self, record):
        return self._tpl.substitute(**record.__dict__)
BASIC_FORMAT = '%(levelname)s:%(name)s:%(message)s'_STYLES = {'%': (PercentStyle, BASIC_FORMAT), '{': (StrFormatStyle, '{levelname}:{name}:{message}'), '$': (StringTemplateStyle, '${levelname}:${name}:${message}')}
class Formatter(object):
    converter = time.localtime

    def __init__(self, fmt=None, datefmt=None, style='%'):
        if style not in _STYLES:
            raise ValueError('Style must be one of: %s' % ','.join(_STYLES.keys()))
        self._style = _STYLES[style][0](fmt)
        self._fmt = self._style._fmt
        self.datefmt = datefmt

    default_time_format = '%Y-%m-%d %H:%M:%S'
    default_msec_format = '%s,%03d'

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime(self.default_time_format, ct)
            s = self.default_msec_format % (t, record.msecs)
        return s

    def formatException(self, ei):
        sio = io.StringIO()
        tb = ei[2]
        traceback.print_exception(ei[0], ei[1], tb, None, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == '\n':
            s = s[:-1]
        return s

    def usesTime(self):
        return self._style.usesTime()

    def formatMessage(self, record):
        return self._style.format(record)

    def formatStack(self, stack_info):
        return stack_info

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_info and record.exc_text:
            if s[-1:] != '\n':
                s = s + '\n'
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != '\n':
                s = s + '\n'
            s = s + self.formatStack(record.stack_info)
        return s
_defaultFormatter = Formatter()
class BufferingFormatter(object):

    def __init__(self, linefmt=None):
        if linefmt:
            self.linefmt = linefmt
        else:
            self.linefmt = _defaultFormatter

    def formatHeader(self, records):
        return ''

    def formatFooter(self, records):
        return ''

    def format(self, records):
        rv = ''
        if len(records) > 0:
            rv = rv + self.formatHeader(records)
            for record in records:
                rv = rv + self.linefmt.format(record)
            rv = rv + self.formatFooter(records)
        return rv

class Filter(object):

    def __init__(self, name=''):
        self.name = name
        self.nlen = len(name)

    def filter(self, record):
        if self.nlen == 0:
            return True
        if self.name == record.name:
            return True
        if record.name.find(self.name, 0, self.nlen) != 0:
            return False
        return record.name[self.nlen] == '.'

class Filterer(object):

    def __init__(self):
        self.filters = []

    def addFilter(self, filter):
        if filter not in self.filters:
            self.filters.append(filter)

    def removeFilter(self, filter):
        if filter in self.filters:
            self.filters.remove(filter)

    def filter(self, record):
        rv = True
        for f in self.filters:
            if hasattr(f, 'filter'):
                result = f.filter(record)
            else:
                result = f(record)
            if not result:
                rv = False
                break
        return rv
_handlers = weakref.WeakValueDictionary()_handlerList = []
def _removeHandlerRef(wr):
    acquire = _acquireLock
    release = _releaseLock
    handlers = _handlerList
    if handlers:
        acquire()
        try:
            if wr in handlers:
                handlers.remove(wr)
        finally:
            release()

def _addHandlerRef(handler):
    _acquireLock()
    try:
        _handlerList.append(weakref.ref(handler, _removeHandlerRef))
    finally:
        _releaseLock()

class Handler(Filterer):

    def __init__(self, level=NOTSET):
        Filterer.__init__(self)
        self._name = None
        self.level = _checkLevel(level)
        self.formatter = None
        _addHandlerRef(self)
        self.createLock()

    def get_name(self):
        return self._name

    def set_name(self, name):
        _acquireLock()
        try:
            if self._name in _handlers:
                del _handlers[self._name]
            self._name = name
            if name:
                _handlers[name] = self
        finally:
            _releaseLock()

    name = property(get_name, set_name)

    def createLock(self):
        self.lock = threading.RLock()

    def acquire(self):
        if self.lock:
            self.lock.acquire()

    def release(self):
        if self.lock:
            self.lock.release()

    def setLevel(self, level):
        self.level = _checkLevel(level)

    def format(self, record):
        if self.formatter:
            fmt = self.formatter
        else:
            fmt = _defaultFormatter
        return fmt.format(record)

    def emit(self, record):
        raise NotImplementedError('emit must be implemented by Handler subclasses')

    def handle(self, record):
        rv = self.filter(record)
        if rv:
            self.acquire()
            try:
                self.emit(record)
            finally:
                self.release()
        return rv

    def setFormatter(self, fmt):
        self.formatter = fmt

    def flush(self):
        pass

    def close(self):
        _acquireLock()
        try:
            if self._name in _handlers:
                del _handlers[self._name]
        finally:
            _releaseLock()

    def handleError(self, record):
        if sys.stderr:
            (t, v, tb) = sys.exc_info()
            try:
                sys.stderr.write('--- Logging error ---\n')
                traceback.print_exception(t, v, tb, None, sys.stderr)
                sys.stderr.write('Call stack:\n')
                frame = tb.tb_frame
                while frame and os.path.dirname(frame.f_code.co_filename) == __path__[0]:
                    frame = frame.f_back
                if frame:
                    traceback.print_stack(frame, file=sys.stderr)
                else:
                    sys.stderr.write('Logged from file %s, line %s\n' % (record.filename, record.lineno))
                try:
                    sys.stderr.write('Message: %r\nArguments: %s\n' % (record.msg, record.args))
                except Exception:
                    sys.stderr.write('Unable to print the message and arguments - possible formatting error.\nUse the traceback above to help find the error.\n')
            except OSError:
                pass
            finally:
                del t
                del v
                del tb

    def __repr__(self):
        level = getLevelName(self.level)
        return '<%s (%s)>' % (self.__class__.__name__, level)

class StreamHandler(Handler):
    terminator = '\n'

    def __init__(self, stream=None):
        Handler.__init__(self)
        if stream is None:
            stream = sys.stderr
        self.stream = stream

    def flush(self):
        self.acquire()
        try:
            if self.stream and hasattr(self.stream, 'flush'):
                self.stream.flush()
        finally:
            self.release()

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg)
            stream.write(self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

    def setStream(self, stream):
        if stream is self.stream:
            result = None
        else:
            result = self.stream
            self.acquire()
            try:
                self.flush()
                self.stream = stream
            finally:
                self.release()
        return result

    def __repr__(self):
        level = getLevelName(self.level)
        name = getattr(self.stream, 'name', '')
        if name:
            name += ' '
        return '<%s %s(%s)>' % (self.__class__.__name__, name, level)

class FileHandler(StreamHandler):

    def __init__(self, filename, mode='a', encoding=None, delay=False):
        filename = os.fspath(filename)
        self.baseFilename = os.path.abspath(filename)
        self.mode = mode
        self.encoding = encoding
        self.delay = delay
        if delay:
            Handler.__init__(self)
            self.stream = None
        else:
            StreamHandler.__init__(self, self._open())

    def close(self):
        self.acquire()
        try:
            try:
                if self.stream:
                    try:
                        self.flush()
                    finally:
                        stream = self.stream
                        self.stream = None
                        if hasattr(stream, 'close'):
                            stream.close()
            finally:
                StreamHandler.close(self)
        finally:
            self.release()

    def _open(self):
        return open(self.baseFilename, self.mode, encoding=self.encoding)

    def emit(self, record):
        if self.stream is None:
            self.stream = self._open()
        StreamHandler.emit(self, record)

    def __repr__(self):
        level = getLevelName(self.level)
        return '<%s %s (%s)>' % (self.__class__.__name__, self.baseFilename, level)

class _StderrHandler(StreamHandler):

    def __init__(self, level=NOTSET):
        Handler.__init__(self, level)

    @property
    def stream(self):
        return sys.stderr
_defaultLastResort = _StderrHandler(WARNING)lastResort = _defaultLastResort
class PlaceHolder(object):

    def __init__(self, alogger):
        self.loggerMap = {alogger: None}

    def append(self, alogger):
        if alogger not in self.loggerMap:
            self.loggerMap[alogger] = None

def setLoggerClass(klass):
    global _loggerClass
    if klass != Logger and not issubclass(klass, Logger):
        raise TypeError('logger not derived from logging.Logger: ' + klass.__name__)
    _loggerClass = klass

def getLoggerClass():
    return _loggerClass

class Manager(object):

    def __init__(self, rootnode):
        self.root = rootnode
        self.disable = 0
        self.emittedNoHandlerWarning = False
        self.loggerDict = {}
        self.loggerClass = None
        self.logRecordFactory = None

    def getLogger(self, name):
        rv = None
        if not isinstance(name, str):
            raise TypeError('A logger name must be a string')
        _acquireLock()
        try:
            if name in self.loggerDict:
                rv = self.loggerDict[name]
                if isinstance(rv, PlaceHolder):
                    ph = rv
                    rv = (self.loggerClass or _loggerClass)(name)
                    rv.manager = self
                    self.loggerDict[name] = rv
                    self._fixupChildren(ph, rv)
                    self._fixupParents(rv)
            else:
                rv = (self.loggerClass or _loggerClass)(name)
                rv.manager = self
                self.loggerDict[name] = rv
                self._fixupParents(rv)
        finally:
            _releaseLock()
        return rv

    def setLoggerClass(self, klass):
        if klass != Logger and not issubclass(klass, Logger):
            raise TypeError('logger not derived from logging.Logger: ' + klass.__name__)
        self.loggerClass = klass

    def setLogRecordFactory(self, factory):
        self.logRecordFactory = factory

    def _fixupParents(self, alogger):
        name = alogger.name
        i = name.rfind('.')
        rv = None
        while i > 0 and not rv:
            substr = name[:i]
            if substr not in self.loggerDict:
                self.loggerDict[substr] = PlaceHolder(alogger)
            else:
                obj = self.loggerDict[substr]
                if isinstance(obj, Logger):
                    rv = obj
                else:
                    obj.append(alogger)
            i = name.rfind('.', 0, i - 1)
        if not rv:
            rv = self.root
        alogger.parent = rv

    def _fixupChildren(self, ph, alogger):
        name = alogger.name
        namelen = len(name)
        for c in ph.loggerMap.keys():
            if c.parent.name[:namelen] != name:
                alogger.parent = c.parent
                c.parent = alogger

    def _clear_cache(self):
        _acquireLock()
        for logger in self.loggerDict.values():
            if isinstance(logger, Logger):
                logger._cache.clear()
        self.root._cache.clear()
        _releaseLock()

class Logger(Filterer):

    def __init__(self, name, level=NOTSET):
        Filterer.__init__(self)
        self.name = name
        self.level = _checkLevel(level)
        self.parent = None
        self.propagate = True
        self.handlers = []
        self.disabled = False
        self._cache = {}

    def setLevel(self, level):
        self.level = _checkLevel(level)
        self.manager._clear_cache()

    def debug(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG):
            self._log(DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self.isEnabledFor(INFO):
            self._log(INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self.isEnabledFor(WARNING):
            self._log(WARNING, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        warnings.warn("The 'warn' method is deprecated, use 'warning' instead", DeprecationWarning, 2)
        self.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self.isEnabledFor(ERROR):
            self._log(ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if self.isEnabledFor(CRITICAL):
            self._log(CRITICAL, msg, *args, **kwargs)

    fatal = critical

    def log(self, level, msg, *args, **kwargs):
        if not isinstance(level, int):
            if raiseExceptions:
                raise TypeError('level must be an integer')
            else:
                return
        if self.isEnabledFor(level):
            self._log(level, msg, *args, **kwargs)

    def findCaller(self, stack_info=False):
        f = currentframe()
        if f is not None:
            f = f.f_back
        rv = ('(unknown file)', 0, '(unknown function)', None)
        while hasattr(f, 'f_code'):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename == _srcfile:
                f = f.f_back
            else:
                sinfo = None
                if stack_info:
                    sio = io.StringIO()
                    sio.write('Stack (most recent call last):\n')
                    traceback.print_stack(f, file=sio)
                    sinfo = sio.getvalue()
                    if sinfo[-1] == '\n':
                        sinfo = sinfo[:-1]
                    sio.close()
                rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
                break
        return rv

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        rv = _logRecordFactory(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra is not None:
            for key in extra:
                if key in ('message', 'asctime') or key in rv.__dict__:
                    raise KeyError('Attempt to overwrite %r in LogRecord' % key)
                rv.__dict__[key] = extra[key]
        return rv

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        sinfo = None
        if _srcfile:
            try:
                (fn, lno, func, sinfo) = self.findCaller(stack_info)
            except ValueError:
                (fn, lno, func) = ('(unknown file)', 0, '(unknown function)')
        else:
            (fn, lno, func) = ('(unknown file)', 0, '(unknown function)')
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = self.makeRecord(self.name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
        self.handle(record)

    def handle(self, record):
        if self.disabled or self.filter(record):
            self.callHandlers(record)

    def addHandler(self, hdlr):
        _acquireLock()
        try:
            if hdlr not in self.handlers:
                self.handlers.append(hdlr)
        finally:
            _releaseLock()

    def removeHandler(self, hdlr):
        _acquireLock()
        try:
            if hdlr in self.handlers:
                self.handlers.remove(hdlr)
        finally:
            _releaseLock()

    def hasHandlers(self):
        c = self
        rv = False
        while c:
            if c.handlers:
                rv = True
                break
            if not c.propagate:
                break
            else:
                c = c.parent
        return rv

    def callHandlers(self, record):
        c = self
        found = 0
        while c:
            for hdlr in c.handlers:
                found = found + 1
                if record.levelno >= hdlr.level:
                    hdlr.handle(record)
            if not c.propagate:
                c = None
            else:
                c = c.parent
        if lastResort:
            if record.levelno >= lastResort.level:
                lastResort.handle(record)
        elif not self.manager.emittedNoHandlerWarning:
            sys.stderr.write('No handlers could be found for logger "%s"\n' % self.name)
            self.manager.emittedNoHandlerWarning = True

    def getEffectiveLevel(self):
        logger = self
        if logger:
            if logger.level:
                return logger.level
            logger = logger.parent
        return NOTSET

    def isEnabledFor(self, level):
        try:
            return self._cache[level]
        except KeyError:
            _acquireLock()
            if self.manager.disable >= level:
                is_enabled = self._cache[level] = False
            else:
                is_enabled = self._cache[level] = level >= self.getEffectiveLevel()
            _releaseLock()
            return is_enabled

    def getChild(self, suffix):
        if self.root is not self:
            suffix = '.'.join((self.name, suffix))
        return self.manager.getLogger(suffix)

    def __repr__(self):
        level = getLevelName(self.getEffectiveLevel())
        return '<%s %s (%s)>' % (self.__class__.__name__, self.name, level)

    def __reduce__(self):
        if getLogger(self.name) is not self:
            import pickle
            raise pickle.PicklingError('logger cannot be pickled')
        return (getLogger, (self.name,))

class RootLogger(Logger):

    def __init__(self, level):
        Logger.__init__(self, 'root', level)

    def __reduce__(self):
        return (getLogger, ())
_loggerClass = Logger
class LoggerAdapter(object):

    def __init__(self, logger, extra):
        self.logger = logger
        self.extra = extra

    def process(self, msg, kwargs):
        kwargs['extra'] = self.extra
        return (msg, kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log(DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(WARNING, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        warnings.warn("The 'warn' method is deprecated, use 'warning' instead", DeprecationWarning, 2)
        self.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.log(ERROR, msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(CRITICAL, msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            (msg, kwargs) = self.process(msg, kwargs)
            self.logger.log(level, msg, *args, **kwargs)

    def isEnabledFor(self, level):
        return self.logger.isEnabledFor(level)

    def setLevel(self, level):
        self.logger.setLevel(level)

    def getEffectiveLevel(self):
        return self.logger.getEffectiveLevel()

    def hasHandlers(self):
        return self.logger.hasHandlers()

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        return self.logger._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)

    @property
    def manager(self):
        return self.logger.manager

    @manager.setter
    def manager(self, value):
        self.logger.manager = value

    @property
    def name(self):
        return self.logger.name

    def __repr__(self):
        logger = self.logger
        level = getLevelName(logger.getEffectiveLevel())
        return '<%s %s (%s)>' % (self.__class__.__name__, logger.name, level)
root = RootLogger(WARNING)Logger.root = rootLogger.manager = Manager(Logger.root)
def basicConfig(**kwargs):
    _acquireLock()
    try:
        if len(root.handlers) == 0:
            handlers = kwargs.pop('handlers', None)
            if handlers is None:
                if 'stream' in kwargs and 'filename' in kwargs:
                    raise ValueError("'stream' and 'filename' should not be specified together")
            elif 'stream' in kwargs or 'filename' in kwargs:
                raise ValueError("'stream' or 'filename' should not be specified together with 'handlers'")
            if handlers is None:
                filename = kwargs.pop('filename', None)
                mode = kwargs.pop('filemode', 'a')
                if filename:
                    h = FileHandler(filename, mode)
                else:
                    stream = kwargs.pop('stream', None)
                    h = StreamHandler(stream)
                handlers = [h]
            dfs = kwargs.pop('datefmt', None)
            style = kwargs.pop('style', '%')
            if style not in _STYLES:
                raise ValueError('Style must be one of: %s' % ','.join(_STYLES.keys()))
            fs = kwargs.pop('format', _STYLES[style][1])
            fmt = Formatter(fs, dfs, style)
            for h in handlers:
                if h.formatter is None:
                    h.setFormatter(fmt)
                root.addHandler(h)
            level = kwargs.pop('level', None)
            if level is not None:
                root.setLevel(level)
            if kwargs:
                keys = ', '.join(kwargs.keys())
                raise ValueError('Unrecognised argument(s): %s' % keys)
    finally:
        _releaseLock()

def getLogger(name=None):
    if name:
        return Logger.manager.getLogger(name)
    else:
        return root

def critical(msg, *args, **kwargs):
    if len(root.handlers) == 0:
        basicConfig()
    root.critical(msg, *args, **kwargs)
fatal = critical
def error(msg, *args, **kwargs):
    if len(root.handlers) == 0:
        basicConfig()
    root.error(msg, *args, **kwargs)

def exception(msg, *args, exc_info=True, **kwargs):
    error(msg, *args, exc_info=exc_info, **kwargs)

def warning(msg, *args, **kwargs):
    if len(root.handlers) == 0:
        basicConfig()
    root.warning(msg, *args, **kwargs)

def warn(msg, *args, **kwargs):
    warnings.warn("The 'warn' function is deprecated, use 'warning' instead", DeprecationWarning, 2)
    warning(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    if len(root.handlers) == 0:
        basicConfig()
    root.info(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    if len(root.handlers) == 0:
        basicConfig()
    root.debug(msg, *args, **kwargs)

def log(level, msg, *args, **kwargs):
    if len(root.handlers) == 0:
        basicConfig()
    root.log(level, msg, *args, **kwargs)

def disable(level=CRITICAL):
    root.manager.disable = level
    root.manager._clear_cache()

def shutdown(handlerList=_handlerList):
    for wr in reversed(handlerList[:]):
        try:
            h = wr()
            try:
                h.acquire()
                h.flush()
                h.close()
            except (OSError, ValueError):
                pass
            finally:
                h.release()
        except:
            if raiseExceptions:
                raise
import atexitatexit.register(shutdown)
class NullHandler(Handler):

    def handle(self, record):
        pass

    def emit(self, record):
        pass

    def createLock(self):
        self.lock = None
_warnings_showwarning = None
def _showwarning(message, category, filename, lineno, file=None, line=None):
    if file is not None:
        if _warnings_showwarning is not None:
            _warnings_showwarning(message, category, filename, lineno, file, line)
    else:
        s = warnings.formatwarning(message, category, filename, lineno, line)
        logger = getLogger('py.warnings')
        if not logger.handlers:
            logger.addHandler(NullHandler())
        logger.warning('%s', s)

def captureWarnings(capture):
    global _warnings_showwarning
    if capture:
        if _warnings_showwarning is None:
            _warnings_showwarning = warnings.showwarning
            warnings.showwarning = _showwarning
    elif _warnings_showwarning is not None:
        warnings.showwarning = _warnings_showwarning
        _warnings_showwarning = None
