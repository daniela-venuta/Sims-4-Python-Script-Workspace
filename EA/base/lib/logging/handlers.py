import loggingimport socketimport osimport pickleimport structimport timeimport refrom stat import ST_DEV, ST_INO, ST_MTIMEimport queueimport threadingDEFAULT_TCP_LOGGING_PORT = 9020DEFAULT_UDP_LOGGING_PORT = 9021DEFAULT_HTTP_LOGGING_PORT = 9022DEFAULT_SOAP_LOGGING_PORT = 9023SYSLOG_UDP_PORT = 514SYSLOG_TCP_PORT = 514_MIDNIGHT = 86400
class BaseRotatingHandler(logging.FileHandler):

    def __init__(self, filename, mode, encoding=None, delay=False):
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)
        self.mode = mode
        self.encoding = encoding
        self.namer = None
        self.rotator = None

    def emit(self, record):
        try:
            if self.shouldRollover(record):
                self.doRollover()
            logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def rotation_filename(self, default_name):
        if not callable(self.namer):
            result = default_name
        else:
            result = self.namer(default_name)
        return result

    def rotate(self, source, dest):
        if not callable(self.rotator):
            if os.path.exists(source):
                os.rename(source, dest)
        else:
            self.rotator(source, dest)

class RotatingFileHandler(BaseRotatingHandler):

    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        if maxBytes > 0:
            mode = 'a'
        BaseRotatingHandler.__init__(self, filename, mode, encoding, delay)
        self.maxBytes = maxBytes
        self.backupCount = backupCount

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename('%s.%d' % (self.baseFilename, i))
                dfn = self.rotation_filename('%s.%d' % (self.baseFilename, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.rotation_filename(self.baseFilename + '.1')
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
        if not self.delay:
            self.stream = self._open()

    def shouldRollover(self, record):
        if self.stream is None:
            self.stream = self._open()
        if self.maxBytes > 0:
            msg = '%s\n' % self.format(record)
            self.stream.seek(0, 2)
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return 1
        return 0

class TimedRotatingFileHandler(BaseRotatingHandler):

    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None):
        BaseRotatingHandler.__init__(self, filename, 'a', encoding, delay)
        self.when = when.upper()
        self.backupCount = backupCount
        self.utc = utc
        self.atTime = atTime
        if self.when == 'S':
            self.interval = 1
            self.suffix = '%Y-%m-%d_%H-%M-%S'
            self.extMatch = '^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}(\\.\\w+)?$'
        elif self.when == 'M':
            self.interval = 60
            self.suffix = '%Y-%m-%d_%H-%M'
            self.extMatch = '^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}(\\.\\w+)?$'
        elif self.when == 'H':
            self.interval = 3600
            self.suffix = '%Y-%m-%d_%H'
            self.extMatch = '^\\d{4}-\\d{2}-\\d{2}_\\d{2}(\\.\\w+)?$'
        elif self.when == 'D' or self.when == 'MIDNIGHT':
            self.interval = 86400
            self.suffix = '%Y-%m-%d'
            self.extMatch = '^\\d{4}-\\d{2}-\\d{2}(\\.\\w+)?$'
        elif self.when.startswith('W'):
            self.interval = 604800
            if len(self.when) != 2:
                raise ValueError('You must specify a day for weekly rollover from 0 to 6 (0 is Monday): %s' % self.when)
            if self.when[1] < '0' or self.when[1] > '6':
                raise ValueError('Invalid day specified for weekly rollover: %s' % self.when)
            self.dayOfWeek = int(self.when[1])
            self.suffix = '%Y-%m-%d'
            self.extMatch = '^\\d{4}-\\d{2}-\\d{2}(\\.\\w+)?$'
        else:
            raise ValueError('Invalid rollover interval specified: %s' % self.when)
        self.extMatch = re.compile(self.extMatch, re.ASCII)
        self.interval = self.interval*interval
        filename = self.baseFilename
        if os.path.exists(filename):
            t = os.stat(filename)[ST_MTIME]
        else:
            t = int(time.time())
        self.rolloverAt = self.computeRollover(t)

    def computeRollover(self, currentTime):
        result = currentTime + self.interval
        if self.when == 'MIDNIGHT' or self.when.startswith('W'):
            if self.utc:
                t = time.gmtime(currentTime)
            else:
                t = time.localtime(currentTime)
            currentHour = t[3]
            currentMinute = t[4]
            currentSecond = t[5]
            currentDay = t[6]
            if self.atTime is None:
                rotate_ts = _MIDNIGHT
            else:
                rotate_ts = (self.atTime.hour*60 + self.atTime.minute)*60 + self.atTime.second
            r = rotate_ts - ((currentHour*60 + currentMinute)*60 + currentSecond)
            if r < 0:
                r += _MIDNIGHT
                currentDay = (currentDay + 1) % 7
            result = currentTime + r
            if self.when.startswith('W'):
                day = currentDay
                if day != self.dayOfWeek:
                    if day < self.dayOfWeek:
                        daysToWait = self.dayOfWeek - day
                    else:
                        daysToWait = 6 - day + self.dayOfWeek + 1
                    newRolloverAt = result + daysToWait*86400
                    if not self.utc:
                        dstNow = t[-1]
                        dstAtRollover = time.localtime(newRolloverAt)[-1]
                        if dstNow != dstAtRollover:
                            if not dstNow:
                                addend = -3600
                            else:
                                addend = 3600
                            newRolloverAt += addend
                    result = newRolloverAt
        return result

    def shouldRollover(self, record):
        t = int(time.time())
        if t >= self.rolloverAt:
            return 1
        return 0

    def getFilesToDelete(self):
        (dirName, baseName) = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName + '.'
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        if len(result) < self.backupCount:
            result = []
        else:
            result.sort()
            result = result[:len(result) - self.backupCount]
        return result

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)
        dfn = self.rotation_filename(self.baseFilename + '.' + time.strftime(self.suffix, timeTuple))
        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        if not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:
                    addend = -3600
                else:
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt

class WatchedFileHandler(logging.FileHandler):

    def __init__(self, filename, mode='a', encoding=None, delay=False):
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)
        (self.dev, self.ino) = (-1, -1)
        self._statstream()

    def _statstream(self):
        if self.stream:
            sres = os.fstat(self.stream.fileno())
            self.dev = sres[ST_DEV]
            self.ino = sres[ST_INO]

    def reopenIfNeeded(self):
        try:
            sres = os.stat(self.baseFilename)
        except FileNotFoundError:
            sres = None
        if sres and (sres[ST_DEV] != self.dev or sres[ST_INO] != self.ino) and self.stream is not None:
            self.stream.flush()
            self.stream.close()
            self.stream = None
            self.stream = self._open()
            self._statstream()

    def emit(self, record):
        self.reopenIfNeeded()
        logging.FileHandler.emit(self, record)

class SocketHandler(logging.Handler):

    def __init__(self, host, port):
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        if port is None:
            self.address = host
        else:
            self.address = (host, port)
        self.sock = None
        self.closeOnError = False
        self.retryTime = None
        self.retryStart = 1.0
        self.retryMax = 30.0
        self.retryFactor = 2.0

    def makeSocket(self, timeout=1):
        if self.port is not None:
            result = socket.create_connection(self.address, timeout=timeout)
        else:
            result = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            result.settimeout(timeout)
            try:
                result.connect(self.address)
            except OSError:
                result.close()
                raise
        return result

    def createSocket(self):
        now = time.time()
        if self.retryTime is None:
            attempt = True
        else:
            attempt = now >= self.retryTime
        if attempt:
            try:
                self.sock = self.makeSocket()
                self.retryTime = None
            except OSError:
                if self.retryTime is None:
                    self.retryPeriod = self.retryStart
                else:
                    self.retryPeriod = self.retryPeriod*self.retryFactor
                    if self.retryPeriod > self.retryMax:
                        self.retryPeriod = self.retryMax
                self.retryTime = now + self.retryPeriod

    def send(self, s):
        if self.sock is None:
            self.createSocket()
        if self.sock:
            try:
                self.sock.sendall(s)
            except OSError:
                self.sock.close()
                self.sock = None

    def makePickle(self, record):
        ei = record.exc_info
        if ei:
            dummy = self.format(record)
        d = dict(record.__dict__)
        d['msg'] = record.getMessage()
        d['args'] = None
        d['exc_info'] = None
        d.pop('message', None)
        s = pickle.dumps(d, 1)
        slen = struct.pack('>L', len(s))
        return slen + s

    def handleError(self, record):
        if self.closeOnError and self.sock:
            self.sock.close()
            self.sock = None
        else:
            logging.Handler.handleError(self, record)

    def emit(self, record):
        try:
            s = self.makePickle(record)
            self.send(s)
        except Exception:
            self.handleError(record)

    def close(self):
        self.acquire()
        try:
            sock = self.sock
            if sock:
                self.sock = None
                sock.close()
            logging.Handler.close(self)
        finally:
            self.release()

class DatagramHandler(SocketHandler):

    def __init__(self, host, port):
        SocketHandler.__init__(self, host, port)
        self.closeOnError = False

    def makeSocket(self):
        if self.port is None:
            family = socket.AF_UNIX
        else:
            family = socket.AF_INET
        s = socket.socket(family, socket.SOCK_DGRAM)
        return s

    def send(self, s):
        if self.sock is None:
            self.createSocket()
        self.sock.sendto(s, self.address)

class SysLogHandler(logging.Handler):
    LOG_EMERG = 0
    LOG_ALERT = 1
    LOG_CRIT = 2
    LOG_ERR = 3
    LOG_WARNING = 4
    LOG_NOTICE = 5
    LOG_INFO = 6
    LOG_DEBUG = 7
    LOG_KERN = 0
    LOG_USER = 1
    LOG_MAIL = 2
    LOG_DAEMON = 3
    LOG_AUTH = 4
    LOG_SYSLOG = 5
    LOG_LPR = 6
    LOG_NEWS = 7
    LOG_UUCP = 8
    LOG_CRON = 9
    LOG_AUTHPRIV = 10
    LOG_FTP = 11
    LOG_LOCAL0 = 16
    LOG_LOCAL1 = 17
    LOG_LOCAL2 = 18
    LOG_LOCAL3 = 19
    LOG_LOCAL4 = 20
    LOG_LOCAL5 = 21
    LOG_LOCAL6 = 22
    LOG_LOCAL7 = 23
    priority_names = {'alert': LOG_ALERT, 'crit': LOG_CRIT, 'critical': LOG_CRIT, 'debug': LOG_DEBUG, 'emerg': LOG_EMERG, 'err': LOG_ERR, 'error': LOG_ERR, 'info': LOG_INFO, 'notice': LOG_NOTICE, 'panic': LOG_EMERG, 'warn': LOG_WARNING, 'warning': LOG_WARNING}
    facility_names = {'auth': LOG_AUTH, 'authpriv': LOG_AUTHPRIV, 'cron': LOG_CRON, 'daemon': LOG_DAEMON, 'ftp': LOG_FTP, 'kern': LOG_KERN, 'lpr': LOG_LPR, 'mail': LOG_MAIL, 'news': LOG_NEWS, 'security': LOG_AUTH, 'syslog': LOG_SYSLOG, 'user': LOG_USER, 'uucp': LOG_UUCP, 'local0': LOG_LOCAL0, 'local1': LOG_LOCAL1, 'local2': LOG_LOCAL2, 'local3': LOG_LOCAL3, 'local4': LOG_LOCAL4, 'local5': LOG_LOCAL5, 'local6': LOG_LOCAL6, 'local7': LOG_LOCAL7}
    priority_map = {'DEBUG': 'debug', 'INFO': 'info', 'WARNING': 'warning', 'ERROR': 'error', 'CRITICAL': 'critical'}

    def __init__(self, address=('localhost', SYSLOG_UDP_PORT), facility=LOG_USER, socktype=None):
        logging.Handler.__init__(self)
        self.address = address
        self.facility = facility
        self.socktype = socktype
        if isinstance(address, str):
            self.unixsocket = True
            try:
                self._connect_unixsocket(address)
            except OSError:
                pass
        else:
            self.unixsocket = False
            if socktype is None:
                socktype = socket.SOCK_DGRAM
            (host, port) = address
            ress = socket.getaddrinfo(host, port, 0, socktype)
            if not ress:
                raise OSError('getaddrinfo returns an empty list')
            for res in ress:
                (af, socktype, proto, _, sa) = res
                err = sock = None
                try:
                    sock = socket.socket(af, socktype, proto)
                    if socktype == socket.SOCK_STREAM:
                        sock.connect(sa)
                    break
                except OSError as exc:
                    err = exc
                    if sock is not None:
                        sock.close()
            if err is not None:
                raise err
            self.socket = sock
            self.socktype = socktype

    def _connect_unixsocket(self, address):
        use_socktype = self.socktype
        if use_socktype is None:
            use_socktype = socket.SOCK_DGRAM
        self.socket = socket.socket(socket.AF_UNIX, use_socktype)
        try:
            self.socket.connect(address)
            self.socktype = use_socktype
        except OSError:
            self.socket.close()
            if self.socktype is not None:
                raise
            use_socktype = socket.SOCK_STREAM
            self.socket = socket.socket(socket.AF_UNIX, use_socktype)
            try:
                self.socket.connect(address)
                self.socktype = use_socktype
            except OSError:
                self.socket.close()
                raise

    def encodePriority(self, facility, priority):
        if isinstance(facility, str):
            facility = self.facility_names[facility]
        if isinstance(priority, str):
            priority = self.priority_names[priority]
        return facility << 3 | priority

    def close(self):
        self.acquire()
        try:
            self.socket.close()
            logging.Handler.close(self)
        finally:
            self.release()

    def mapPriority(self, levelName):
        return self.priority_map.get(levelName, 'warning')

    ident = ''
    append_nul = True

    def emit(self, record):
        try:
            msg = self.format(record)
            if self.ident:
                msg = self.ident + msg
            if self.append_nul:
                msg += '\x00'
            prio = '<%d>' % self.encodePriority(self.facility, self.mapPriority(record.levelname))
            prio = prio.encode('utf-8')
            msg = msg.encode('utf-8')
            msg = prio + msg
            if self.unixsocket:
                try:
                    self.socket.send(msg)
                except OSError:
                    self.socket.close()
                    self._connect_unixsocket(self.address)
                    self.socket.send(msg)
            elif self.socktype == socket.SOCK_DGRAM:
                self.socket.sendto(msg, self.address)
            else:
                self.socket.sendall(msg)
        except Exception:
            self.handleError(record)

class SMTPHandler(logging.Handler):

    def __init__(self, mailhost, fromaddr, toaddrs, subject, credentials=None, secure=None, timeout=5.0):
        logging.Handler.__init__(self)
        if isinstance(mailhost, (list, tuple)):
            (self.mailhost, self.mailport) = mailhost
        else:
            self.mailhost = mailhost
            self.mailport = None
        if isinstance(credentials, (list, tuple)):
            (self.username, self.password) = credentials
        else:
            self.username = None
        self.fromaddr = fromaddr
        if isinstance(toaddrs, str):
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject
        self.secure = secure
        self.timeout = timeout

    def getSubject(self, record):
        return self.subject

    def emit(self, record):
        try:
            import smtplib
            from email.message import EmailMessage
            import email.utils
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port, timeout=self.timeout)
            msg = EmailMessage()
            msg['From'] = self.fromaddr
            msg['To'] = ','.join(self.toaddrs)
            msg['Subject'] = self.getSubject(record)
            msg['Date'] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.username:
                if self.secure is not None:
                    smtp.ehlo()
                    smtp.starttls(*self.secure)
                    smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.send_message(msg)
            smtp.quit()
        except Exception:
            self.handleError(record)

class NTEventLogHandler(logging.Handler):

    def __init__(self, appname, dllname=None, logtype='Application'):
        logging.Handler.__init__(self)
        try:
            import win32evtlogutil
            import win32evtlog
            self.appname = appname
            self._welu = win32evtlogutil
            if not dllname:
                dllname = os.path.split(self._welu.__file__)
                dllname = os.path.split(dllname[0])
                dllname = os.path.join(dllname[0], 'win32service.pyd')
            self.dllname = dllname
            self.logtype = logtype
            self._welu.AddSourceToRegistry(appname, dllname, logtype)
            self.deftype = win32evtlog.EVENTLOG_ERROR_TYPE
            self.typemap = {logging.CRITICAL: win32evtlog.EVENTLOG_ERROR_TYPE, logging.ERROR: win32evtlog.EVENTLOG_ERROR_TYPE, logging.WARNING: win32evtlog.EVENTLOG_WARNING_TYPE, logging.INFO: win32evtlog.EVENTLOG_INFORMATION_TYPE, logging.DEBUG: win32evtlog.EVENTLOG_INFORMATION_TYPE}
        except ImportError:
            print('The Python Win32 extensions for NT (service, event logging) appear not to be available.')
            self._welu = None

    def getMessageID(self, record):
        return 1

    def getEventCategory(self, record):
        return 0

    def getEventType(self, record):
        return self.typemap.get(record.levelno, self.deftype)

    def emit(self, record):
        if self._welu:
            try:
                id = self.getMessageID(record)
                cat = self.getEventCategory(record)
                type = self.getEventType(record)
                msg = self.format(record)
                self._welu.ReportEvent(self.appname, id, cat, type, [msg])
            except Exception:
                self.handleError(record)

    def close(self):
        logging.Handler.close(self)

class HTTPHandler(logging.Handler):

    def __init__(self, host, url, method='GET', secure=False, credentials=None, context=None):
        logging.Handler.__init__(self)
        method = method.upper()
        if method not in ('GET', 'POST'):
            raise ValueError('method must be GET or POST')
        if secure or context is not None:
            raise ValueError('context parameter only makes sense with secure=True')
        self.host = host
        self.url = url
        self.method = method
        self.secure = secure
        self.credentials = credentials
        self.context = context

    def mapLogRecord(self, record):
        return record.__dict__

    def emit(self, record):
        try:
            import http.client
            import urllib.parse
            host = self.host
            if self.secure:
                h = http.client.HTTPSConnection(host, context=self.context)
            else:
                h = http.client.HTTPConnection(host)
            url = self.url
            data = urllib.parse.urlencode(self.mapLogRecord(record))
            if self.method == 'GET':
                if url.find('?') >= 0:
                    sep = '&'
                else:
                    sep = '?'
                url = url + '%c%s' % (sep, data)
            h.putrequest(self.method, url)
            i = host.find(':')
            if i >= 0:
                host = host[:i]
            if self.method == 'POST':
                h.putheader('Content-type', 'application/x-www-form-urlencoded')
                h.putheader('Content-length', str(len(data)))
            if self.credentials:
                import base64
                s = ('%s:%s' % self.credentials).encode('utf-8')
                s = 'Basic ' + base64.b64encode(s).strip().decode('ascii')
                h.putheader('Authorization', s)
            h.endheaders()
            if self.method == 'POST':
                h.send(data.encode('utf-8'))
            h.getresponse()
        except Exception:
            self.handleError(record)

class BufferingHandler(logging.Handler):

    def __init__(self, capacity):
        logging.Handler.__init__(self)
        self.capacity = capacity
        self.buffer = []

    def shouldFlush(self, record):
        return len(self.buffer) >= self.capacity

    def emit(self, record):
        self.buffer.append(record)
        if self.shouldFlush(record):
            self.flush()

    def flush(self):
        self.acquire()
        try:
            self.buffer = []
        finally:
            self.release()

    def close(self):
        try:
            self.flush()
        finally:
            logging.Handler.close(self)

class MemoryHandler(BufferingHandler):

    def __init__(self, capacity, flushLevel=logging.ERROR, target=None, flushOnClose=True):
        BufferingHandler.__init__(self, capacity)
        self.flushLevel = flushLevel
        self.target = target
        self.flushOnClose = flushOnClose

    def shouldFlush(self, record):
        return len(self.buffer) >= self.capacity or record.levelno >= self.flushLevel

    def setTarget(self, target):
        self.target = target

    def flush(self):
        self.acquire()
        try:
            if self.target:
                for record in self.buffer:
                    self.target.handle(record)
                self.buffer = []
        finally:
            self.release()

    def close(self):
        try:
            if self.flushOnClose:
                self.flush()
        finally:
            self.acquire()
            try:
                self.target = None
                BufferingHandler.close(self)
            finally:
                self.release()

class QueueHandler(logging.Handler):

    def __init__(self, queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def enqueue(self, record):
        self.queue.put_nowait(record)

    def prepare(self, record):
        msg = self.format(record)
        record.message = msg
        record.msg = msg
        record.args = None
        record.exc_info = None
        return record

    def emit(self, record):
        try:
            self.enqueue(self.prepare(record))
        except Exception:
            self.handleError(record)

class QueueListener(object):
    _sentinel = None

    def __init__(self, queue, *handlers, respect_handler_level=False):
        self.queue = queue
        self.handlers = handlers
        self._thread = None
        self.respect_handler_level = respect_handler_level

    def dequeue(self, block):
        return self.queue.get(block)

    def start(self):
        self._thread = t = threading.Thread(target=self._monitor)
        t.daemon = True
        t.start()

    def prepare(self, record):
        return record

    def handle(self, record):
        record = self.prepare(record)
        for handler in self.handlers:
            if not self.respect_handler_level:
                process = True
            else:
                process = record.levelno >= handler.level
            if process:
                handler.handle(record)

    def _monitor(self):
        q = self.queue
        has_task_done = hasattr(q, 'task_done')
        while True:
            try:
                record = self.dequeue(True)
                if record is self._sentinel:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                break

    def enqueue_sentinel(self):
        self.queue.put_nowait(self._sentinel)

    def stop(self):
        self.enqueue_sentinel()
        self._thread.join()
        self._thread = None
