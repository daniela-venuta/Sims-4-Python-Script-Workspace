import sysimport socketimport selectorsfrom time import monotonic as _time__all__ = ['Telnet']DEBUGLEVEL = 0TELNET_PORT = 23IAC = bytes([255])DONT = bytes([254])DO = bytes([253])WONT = bytes([252])WILL = bytes([251])theNULL = bytes([0])SE = bytes([240])NOP = bytes([241])DM = bytes([242])BRK = bytes([243])IP = bytes([244])AO = bytes([245])AYT = bytes([246])EC = bytes([247])EL = bytes([248])GA = bytes([249])SB = bytes([250])BINARY = bytes([0])ECHO = bytes([1])RCP = bytes([2])SGA = bytes([3])NAMS = bytes([4])STATUS = bytes([5])TM = bytes([6])RCTE = bytes([7])NAOL = bytes([8])NAOP = bytes([9])NAOCRD = bytes([10])NAOHTS = bytes([11])NAOHTD = bytes([12])NAOFFD = bytes([13])NAOVTS = bytes([14])NAOVTD = bytes([15])NAOLFD = bytes([16])XASCII = bytes([17])LOGOUT = bytes([18])BM = bytes([19])DET = bytes([20])SUPDUP = bytes([21])SUPDUPOUTPUT = bytes([22])SNDLOC = bytes([23])TTYPE = bytes([24])EOR = bytes([25])TUID = bytes([26])OUTMRK = bytes([27])TTYLOC = bytes([28])VT3270REGIME = bytes([29])X3PAD = bytes([30])NAWS = bytes([31])TSPEED = bytes([32])LFLOW = bytes([33])LINEMODE = bytes([34])XDISPLOC = bytes([35])OLD_ENVIRON = bytes([36])AUTHENTICATION = bytes([37])ENCRYPT = bytes([38])NEW_ENVIRON = bytes([39])TN3270E = bytes([40])XAUTH = bytes([41])CHARSET = bytes([42])RSP = bytes([43])COM_PORT_OPTION = bytes([44])SUPPRESS_LOCAL_ECHO = bytes([45])TLS = bytes([46])KERMIT = bytes([47])SEND_URL = bytes([48])FORWARD_X = bytes([49])PRAGMA_LOGON = bytes([138])SSPI_LOGON = bytes([139])PRAGMA_HEARTBEAT = bytes([140])EXOPL = bytes([255])NOOPT = bytes([0])if hasattr(selectors, 'PollSelector'):
    _TelnetSelector = selectors.PollSelector
else:
    _TelnetSelector = selectors.SelectSelector
class Telnet:

    def __init__(self, host=None, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        self.debuglevel = DEBUGLEVEL
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.rawq = b''
        self.irawq = 0
        self.cookedq = b''
        self.eof = 0
        self.iacseq = b''
        self.sb = 0
        self.sbdataq = b''
        self.option_callback = None
        if host is not None:
            self.open(host, port, timeout)

    def open(self, host, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        self.eof = 0
        if not port:
            port = TELNET_PORT
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = socket.create_connection((host, port), timeout)

    def __del__(self):
        self.close()

    def msg(self, msg, *args):
        if self.debuglevel > 0:
            print('Telnet(%s,%s):' % (self.host, self.port), end=' ')
            if args:
                print(msg % args)
            else:
                print(msg)

    def set_debuglevel(self, debuglevel):
        self.debuglevel = debuglevel

    def close(self):
        sock = self.sock
        self.sock = None
        self.eof = True
        self.iacseq = b''
        self.sb = 0
        if sock:
            sock.close()

    def get_socket(self):
        return self.sock

    def fileno(self):
        return self.sock.fileno()

    def write(self, buffer):
        if IAC in buffer:
            buffer = buffer.replace(IAC, IAC + IAC)
        self.msg('send %r', buffer)
        self.sock.sendall(buffer)

    def read_until(self, match, timeout=None):
        n = len(match)
        self.process_rawq()
        i = self.cookedq.find(match)
        if i >= 0:
            i = i + n
            buf = self.cookedq[:i]
            self.cookedq = self.cookedq[i:]
            return buf
        if timeout is not None:
            deadline = _time() + timeout
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            if not self.eof:
                if selector.select(timeout):
                    i = max(0, len(self.cookedq) - n)
                    self.fill_rawq()
                    self.process_rawq()
                    i = self.cookedq.find(match, i)
                    if i >= 0:
                        i = i + n
                        buf = self.cookedq[:i]
                        self.cookedq = self.cookedq[i:]
                        return buf
                if timeout is not None:
                    timeout = deadline - _time()
                    if timeout < 0:
                        break
        return self.read_very_lazy()

    def read_all(self):
        self.process_rawq()
        while not self.eof:
            self.fill_rawq()
            self.process_rawq()
        buf = self.cookedq
        self.cookedq = b''
        return buf

    def read_some(self):
        self.process_rawq()
        while self.cookedq or not self.eof:
            self.fill_rawq()
            self.process_rawq()
        buf = self.cookedq
        self.cookedq = b''
        return buf

    def read_very_eager(self):
        self.process_rawq()
        while self.eof or self.sock_avail():
            self.fill_rawq()
            self.process_rawq()
        return self.read_very_lazy()

    def read_eager(self):
        self.process_rawq()
        while self.cookedq or self.eof or self.sock_avail():
            self.fill_rawq()
            self.process_rawq()
        return self.read_very_lazy()

    def read_lazy(self):
        self.process_rawq()
        return self.read_very_lazy()

    def read_very_lazy(self):
        buf = self.cookedq
        self.cookedq = b''
        if buf or not (self.eof and self.rawq):
            raise EOFError('telnet connection closed')
        return buf

    def read_sb_data(self):
        buf = self.sbdataq
        self.sbdataq = b''
        return buf

    def set_option_negotiation_callback(self, callback):
        self.option_callback = callback

    def process_rawq(self):
        buf = [b'', b'']
        try:
            while self.rawq:
                c = self.rawq_getchar()
                if not self.iacseq:
                    if c == theNULL:
                        pass
                    elif c == b'\x11':
                        pass
                    else:
                        if c != IAC:
                            buf[self.sb] = buf[self.sb] + c
                        else:
                            self.iacseq += c
                        if len(self.iacseq) == 1:
                            if c in (DO, DONT, WILL, WONT):
                                self.iacseq += c
                            else:
                                self.iacseq = b''
                                if c == IAC:
                                    buf[self.sb] = buf[self.sb] + c
                                else:
                                    if c == SB:
                                        self.sb = 1
                                        self.sbdataq = b''
                                    elif c == SE:
                                        self.sb = 0
                                        self.sbdataq = self.sbdataq + buf[1]
                                        buf[1] = b''
                                    if self.option_callback:
                                        self.option_callback(self.sock, c, NOOPT)
                                    else:
                                        self.msg('IAC %d not recognized' % ord(c))
                                if len(self.iacseq) == 2:
                                    cmd = self.iacseq[1:2]
                                    self.iacseq = b''
                                    opt = c
                                    if cmd in (DO, DONT):
                                        if cmd == DO:
                                            pass
                                        self.msg('IAC %s %d', 'DONT', ord(opt))
                                        if self.option_callback:
                                            self.option_callback(self.sock, cmd, opt)
                                        else:
                                            self.sock.sendall(IAC + WONT + opt)
                                    elif cmd in (WILL, WONT):
                                        if cmd == WILL:
                                            pass
                                        self.msg('IAC %s %d', 'WONT', ord(opt))
                                        if self.option_callback:
                                            self.option_callback(self.sock, cmd, opt)
                                        else:
                                            self.sock.sendall(IAC + DONT + opt)
                        elif len(self.iacseq) == 2:
                            cmd = self.iacseq[1:2]
                            self.iacseq = b''
                            opt = c
                            if cmd in (DO, DONT):
                                if cmd == DO:
                                    pass
                                self.msg('IAC %s %d', 'DONT', ord(opt))
                                if self.option_callback:
                                    self.option_callback(self.sock, cmd, opt)
                                else:
                                    self.sock.sendall(IAC + WONT + opt)
                            elif cmd in (WILL, WONT):
                                if cmd == WILL:
                                    pass
                                self.msg('IAC %s %d', 'WONT', ord(opt))
                                if self.option_callback:
                                    self.option_callback(self.sock, cmd, opt)
                                else:
                                    self.sock.sendall(IAC + DONT + opt)
                elif len(self.iacseq) == 1:
                    if c in (DO, DONT, WILL, WONT):
                        self.iacseq += c
                    else:
                        self.iacseq = b''
                        if c == IAC:
                            buf[self.sb] = buf[self.sb] + c
                        else:
                            if c == SB:
                                self.sb = 1
                                self.sbdataq = b''
                            elif c == SE:
                                self.sb = 0
                                self.sbdataq = self.sbdataq + buf[1]
                                buf[1] = b''
                            if self.option_callback:
                                self.option_callback(self.sock, c, NOOPT)
                            else:
                                self.msg('IAC %d not recognized' % ord(c))
                        if len(self.iacseq) == 2:
                            cmd = self.iacseq[1:2]
                            self.iacseq = b''
                            opt = c
                            if cmd in (DO, DONT):
                                if cmd == DO:
                                    pass
                                self.msg('IAC %s %d', 'DONT', ord(opt))
                                if self.option_callback:
                                    self.option_callback(self.sock, cmd, opt)
                                else:
                                    self.sock.sendall(IAC + WONT + opt)
                            elif cmd in (WILL, WONT):
                                if cmd == WILL:
                                    pass
                                self.msg('IAC %s %d', 'WONT', ord(opt))
                                if self.option_callback:
                                    self.option_callback(self.sock, cmd, opt)
                                else:
                                    self.sock.sendall(IAC + DONT + opt)
                elif len(self.iacseq) == 2:
                    cmd = self.iacseq[1:2]
                    self.iacseq = b''
                    opt = c
                    if cmd in (DO, DONT):
                        if cmd == DO:
                            pass
                        self.msg('IAC %s %d', 'DONT', ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            self.sock.sendall(IAC + WONT + opt)
                    elif cmd in (WILL, WONT):
                        if cmd == WILL:
                            pass
                        self.msg('IAC %s %d', 'WONT', ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            self.sock.sendall(IAC + DONT + opt)
        except EOFError:
            self.iacseq = b''
            self.sb = 0
        self.cookedq = self.cookedq + buf[0]
        self.sbdataq = self.sbdataq + buf[1]

    def rawq_getchar(self):
        if not self.rawq:
            self.fill_rawq()
            if self.eof:
                raise EOFError
        c = self.rawq[self.irawq:self.irawq + 1]
        self.irawq = self.irawq + 1
        if self.irawq >= len(self.rawq):
            self.rawq = b''
            self.irawq = 0
        return c

    def fill_rawq(self):
        if self.irawq >= len(self.rawq):
            self.rawq = b''
            self.irawq = 0
        buf = self.sock.recv(50)
        self.msg('recv %r', buf)
        self.eof = not buf
        self.rawq = self.rawq + buf

    def sock_avail(self):
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            return bool(selector.select(0))

    def interact(self):
        if sys.platform == 'win32':
            self.mt_interact()
            return
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            selector.register(sys.stdin, selectors.EVENT_READ)
            while True:
                for (key, events) in selector.select():
                    if key.fileobj is self:
                        try:
                            text = self.read_eager()
                        except EOFError:
                            print('*** Connection closed by remote host ***')
                            return
                        if text:
                            sys.stdout.write(text.decode('ascii'))
                            sys.stdout.flush()
                            if key.fileobj is sys.stdin:
                                line = sys.stdin.readline().encode('ascii')
                                if not line:
                                    return
                                self.write(line)
                    elif key.fileobj is sys.stdin:
                        line = sys.stdin.readline().encode('ascii')
                        if not line:
                            return
                        self.write(line)

    def mt_interact(self):
        import _thread
        _thread.start_new_thread(self.listener, ())
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            self.write(line.encode('ascii'))

    def listener(self):
        while True:
            try:
                data = self.read_eager()
            except EOFError:
                print('*** Connection closed by remote host ***')
                return
            if data:
                sys.stdout.write(data.decode('ascii'))
            else:
                sys.stdout.flush()

    def expect(self, list, timeout=None):
        re = None
        list = list[:]
        indices = range(len(list))
        for i in indices:
            if not hasattr(list[i], 'search'):
                if not re:
                    import re
                list[i] = re.compile(list[i])
        if timeout is not None:
            deadline = _time() + timeout
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            while not self.eof:
                self.process_rawq()
                for i in indices:
                    m = list[i].search(self.cookedq)
                    if m:
                        e = m.end()
                        text = self.cookedq[:e]
                        self.cookedq = self.cookedq[e:]
                        return (i, m, text)
                if timeout is not None:
                    ready = selector.select(timeout)
                    timeout = deadline - _time()
                    if not ready:
                        if timeout < 0:
                            break
                            self.fill_rawq()
                    else:
                        self.fill_rawq()
                else:
                    self.fill_rawq()
        text = self.read_very_lazy()
        if text or self.eof:
            raise EOFError
        return (-1, None, text)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

def test():
    debuglevel = 0
    while sys.argv[1:] and sys.argv[1] == '-d':
        debuglevel = debuglevel + 1
        del sys.argv[1]
    host = 'localhost'
    if sys.argv[1:]:
        host = sys.argv[1]
    port = 0
    if sys.argv[2:]:
        portstr = sys.argv[2]
        try:
            port = int(portstr)
        except ValueError:
            port = socket.getservbyname(portstr, 'tcp')
    with Telnet() as tn:
        tn.set_debuglevel(debuglevel)
        tn.open(host, port, timeout=0.5)
        tn.interact()
if __name__ == '__main__':
    test()