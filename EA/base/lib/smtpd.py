import sysimport osimport errnoimport getoptimport timeimport socketimport asyncoreimport asynchatimport collectionsfrom warnings import warnfrom email._header_value_parser import get_addr_spec, get_angle_addr__all__ = ['SMTPChannel', 'SMTPServer', 'DebuggingServer', 'PureProxy', 'MailmanProxy']program = sys.argv[0]__version__ = 'Python SMTP proxy version 0.3'
class Devnull:

    def write(self, msg):
        pass

    def flush(self):
        pass
DEBUGSTREAM = Devnull()NEWLINE = '\n'COMMASPACE = ', 'DATA_SIZE_DEFAULT = 33554432
def usage(code, msg=''):
    print(__doc__ % globals(), file=sys.stderr)
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)

class SMTPChannel(asynchat.async_chat):
    COMMAND = 0
    DATA = 1
    command_size_limit = 512
    command_size_limits = collections.defaultdict(lambda x=command_size_limit: x)

    @property
    def max_command_size_limit(self):
        try:
            return max(self.command_size_limits.values())
        except ValueError:
            return self.command_size_limit

    def __init__(self, server, conn, addr, data_size_limit=DATA_SIZE_DEFAULT, map=None, enable_SMTPUTF8=False, decode_data=False):
        asynchat.async_chat.__init__(self, conn, map=map)
        self.smtp_server = server
        self.conn = conn
        self.addr = addr
        self.data_size_limit = data_size_limit
        self.enable_SMTPUTF8 = enable_SMTPUTF8
        self._decode_data = decode_data
        if enable_SMTPUTF8 and decode_data:
            raise ValueError('decode_data and enable_SMTPUTF8 cannot be set to True at the same time')
        if decode_data:
            self._emptystring = ''
            self._linesep = '\r\n'
            self._dotsep = '.'
            self._newline = NEWLINE
        else:
            self._emptystring = b''
            self._linesep = b'\r\n'
            self._dotsep = ord(b'.')
            self._newline = b'\n'
        self._set_rset_state()
        self.seen_greeting = ''
        self.extended_smtp = False
        self.command_size_limits.clear()
        self.fqdn = socket.getfqdn()
        try:
            self.peer = conn.getpeername()
        except OSError as err:
            self.close()
            if err.args[0] != errno.ENOTCONN:
                raise
            return
        print('Peer:', repr(self.peer), file=DEBUGSTREAM)
        self.push('220 %s %s' % (self.fqdn, __version__))

    def _set_post_data_state(self):
        self.smtp_state = self.COMMAND
        self.mailfrom = None
        self.rcpttos = []
        self.require_SMTPUTF8 = False
        self.num_bytes = 0
        self.set_terminator(b'\r\n')

    def _set_rset_state(self):
        self._set_post_data_state()
        self.received_data = ''
        self.received_lines = []

    @property
    def __server(self):
        warn("Access to __server attribute on SMTPChannel is deprecated, use 'smtp_server' instead", DeprecationWarning, 2)
        return self.smtp_server

    @_SMTPChannel__server.setter
    def __server(self, value):
        warn("Setting __server attribute on SMTPChannel is deprecated, set 'smtp_server' instead", DeprecationWarning, 2)
        self.smtp_server = value

    @property
    def __line(self):
        warn("Access to __line attribute on SMTPChannel is deprecated, use 'received_lines' instead", DeprecationWarning, 2)
        return self.received_lines

    @_SMTPChannel__line.setter
    def __line(self, value):
        warn("Setting __line attribute on SMTPChannel is deprecated, set 'received_lines' instead", DeprecationWarning, 2)
        self.received_lines = value

    @property
    def __state(self):
        warn("Access to __state attribute on SMTPChannel is deprecated, use 'smtp_state' instead", DeprecationWarning, 2)
        return self.smtp_state

    @_SMTPChannel__state.setter
    def __state(self, value):
        warn("Setting __state attribute on SMTPChannel is deprecated, set 'smtp_state' instead", DeprecationWarning, 2)
        self.smtp_state = value

    @property
    def __greeting(self):
        warn("Access to __greeting attribute on SMTPChannel is deprecated, use 'seen_greeting' instead", DeprecationWarning, 2)
        return self.seen_greeting

    @_SMTPChannel__greeting.setter
    def __greeting(self, value):
        warn("Setting __greeting attribute on SMTPChannel is deprecated, set 'seen_greeting' instead", DeprecationWarning, 2)
        self.seen_greeting = value

    @property
    def __mailfrom(self):
        warn("Access to __mailfrom attribute on SMTPChannel is deprecated, use 'mailfrom' instead", DeprecationWarning, 2)
        return self.mailfrom

    @_SMTPChannel__mailfrom.setter
    def __mailfrom(self, value):
        warn("Setting __mailfrom attribute on SMTPChannel is deprecated, set 'mailfrom' instead", DeprecationWarning, 2)
        self.mailfrom = value

    @property
    def __rcpttos(self):
        warn("Access to __rcpttos attribute on SMTPChannel is deprecated, use 'rcpttos' instead", DeprecationWarning, 2)
        return self.rcpttos

    @_SMTPChannel__rcpttos.setter
    def __rcpttos(self, value):
        warn("Setting __rcpttos attribute on SMTPChannel is deprecated, set 'rcpttos' instead", DeprecationWarning, 2)
        self.rcpttos = value

    @property
    def __data(self):
        warn("Access to __data attribute on SMTPChannel is deprecated, use 'received_data' instead", DeprecationWarning, 2)
        return self.received_data

    @_SMTPChannel__data.setter
    def __data(self, value):
        warn("Setting __data attribute on SMTPChannel is deprecated, set 'received_data' instead", DeprecationWarning, 2)
        self.received_data = value

    @property
    def __fqdn(self):
        warn("Access to __fqdn attribute on SMTPChannel is deprecated, use 'fqdn' instead", DeprecationWarning, 2)
        return self.fqdn

    @_SMTPChannel__fqdn.setter
    def __fqdn(self, value):
        warn("Setting __fqdn attribute on SMTPChannel is deprecated, set 'fqdn' instead", DeprecationWarning, 2)
        self.fqdn = value

    @property
    def __peer(self):
        warn("Access to __peer attribute on SMTPChannel is deprecated, use 'peer' instead", DeprecationWarning, 2)
        return self.peer

    @_SMTPChannel__peer.setter
    def __peer(self, value):
        warn("Setting __peer attribute on SMTPChannel is deprecated, set 'peer' instead", DeprecationWarning, 2)
        self.peer = value

    @property
    def __conn(self):
        warn("Access to __conn attribute on SMTPChannel is deprecated, use 'conn' instead", DeprecationWarning, 2)
        return self.conn

    @_SMTPChannel__conn.setter
    def __conn(self, value):
        warn("Setting __conn attribute on SMTPChannel is deprecated, set 'conn' instead", DeprecationWarning, 2)
        self.conn = value

    @property
    def __addr(self):
        warn("Access to __addr attribute on SMTPChannel is deprecated, use 'addr' instead", DeprecationWarning, 2)
        return self.addr

    @_SMTPChannel__addr.setter
    def __addr(self, value):
        warn("Setting __addr attribute on SMTPChannel is deprecated, set 'addr' instead", DeprecationWarning, 2)
        self.addr = value

    def push(self, msg):
        asynchat.async_chat.push(self, bytes(msg + '\r\n', 'utf-8' if self.require_SMTPUTF8 else 'ascii'))

    def collect_incoming_data(self, data):
        limit = None
        if self.smtp_state == self.COMMAND:
            limit = self.max_command_size_limit
        elif self.smtp_state == self.DATA:
            limit = self.data_size_limit
        if limit and self.num_bytes > limit:
            return
        if limit:
            self.num_bytes += len(data)
        if self._decode_data:
            self.received_lines.append(str(data, 'utf-8'))
        else:
            self.received_lines.append(data)

    def found_terminator(self):
        line = self._emptystring.join(self.received_lines)
        print('Data:', repr(line), file=DEBUGSTREAM)
        self.received_lines = []
        if self.smtp_state == self.COMMAND:
            sz = self.num_bytes
            self.num_bytes = 0
            if not line:
                self.push('500 Error: bad syntax')
                return
            if not self._decode_data:
                line = str(line, 'utf-8')
            i = line.find(' ')
            if i < 0:
                command = line.upper()
                arg = None
            else:
                command = line[:i].upper()
                arg = line[i + 1:].strip()
            max_sz = self.command_size_limits[command] if self.extended_smtp else self.command_size_limit
            if sz > max_sz:
                self.push('500 Error: line too long')
                return
            method = getattr(self, 'smtp_' + command, None)
            if not method:
                self.push('500 Error: command "%s" not recognized' % command)
                return
            method(arg)
            return
        if self.smtp_state != self.DATA:
            self.push('451 Internal confusion')
            self.num_bytes = 0
            return
        if self.data_size_limit and self.num_bytes > self.data_size_limit:
            self.push('552 Error: Too much mail data')
            self.num_bytes = 0
            return
        data = []
        for text in line.split(self._linesep):
            if text and text[0] == self._dotsep:
                data.append(text[1:])
            else:
                data.append(text)
        self.received_data = self._newline.join(data)
        args = (self.peer, self.mailfrom, self.rcpttos, self.received_data)
        kwargs = {}
        if not self._decode_data:
            kwargs = {'mail_options': self.mail_options, 'rcpt_options': self.rcpt_options}
        status = self.smtp_server.process_message(*args, **kwargs)
        self._set_post_data_state()
        if not status:
            self.push('250 OK')
        else:
            self.push(status)

    def smtp_HELO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        if self.seen_greeting:
            self.push('503 Duplicate HELO/EHLO')
            return
        self._set_rset_state()
        self.seen_greeting = arg
        self.push('250 %s' % self.fqdn)

    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: EHLO hostname')
            return
        if self.seen_greeting:
            self.push('503 Duplicate HELO/EHLO')
            return
        self._set_rset_state()
        self.seen_greeting = arg
        self.extended_smtp = True
        self.push('250-%s' % self.fqdn)
        if self.data_size_limit:
            self.push('250-SIZE %s' % self.data_size_limit)
            self.command_size_limits['MAIL'] += 26
        if not self._decode_data:
            self.push('250-8BITMIME')
        if self.enable_SMTPUTF8:
            self.push('250-SMTPUTF8')
            self.command_size_limits['MAIL'] += 10
        self.push('250 HELP')

    def smtp_NOOP(self, arg):
        if arg:
            self.push('501 Syntax: NOOP')
        else:
            self.push('250 OK')

    def smtp_QUIT(self, arg):
        self.push('221 Bye')
        self.close_when_done()

    def _strip_command_keyword(self, keyword, arg):
        keylen = len(keyword)
        if arg[:keylen].upper() == keyword:
            return arg[keylen:].strip()
        return ''

    def _getaddr(self, arg):
        if not arg:
            return ('', '')
        if arg.lstrip().startswith('<'):
            (address, rest) = get_angle_addr(arg)
        else:
            (address, rest) = get_addr_spec(arg)
        if not address:
            return (address, rest)
        return (address.addr_spec, rest)

    def _getparams(self, params):
        result = {}
        for param in params:
            (param, eq, value) = param.partition('=')
            if param.isalnum() and eq and not value:
                return
            result[param] = value if eq else True
        return result

    def smtp_HELP(self, arg):
        if arg:
            extended = ' [SP <mail-parameters>]'
            lc_arg = arg.upper()
            if lc_arg == 'EHLO':
                self.push('250 Syntax: EHLO hostname')
            elif lc_arg == 'HELO':
                self.push('250 Syntax: HELO hostname')
            elif lc_arg == 'MAIL':
                msg = '250 Syntax: MAIL FROM: <address>'
                if self.extended_smtp:
                    msg += extended
                self.push(msg)
            elif lc_arg == 'RCPT':
                msg = '250 Syntax: RCPT TO: <address>'
                if self.extended_smtp:
                    msg += extended
                self.push(msg)
            elif lc_arg == 'DATA':
                self.push('250 Syntax: DATA')
            elif lc_arg == 'RSET':
                self.push('250 Syntax: RSET')
            elif lc_arg == 'NOOP':
                self.push('250 Syntax: NOOP')
            elif lc_arg == 'QUIT':
                self.push('250 Syntax: QUIT')
            elif lc_arg == 'VRFY':
                self.push('250 Syntax: VRFY <address>')
            else:
                self.push('501 Supported commands: EHLO HELO MAIL RCPT DATA RSET NOOP QUIT VRFY')
        else:
            self.push('250 Supported commands: EHLO HELO MAIL RCPT DATA RSET NOOP QUIT VRFY')

    def smtp_VRFY(self, arg):
        if arg:
            (address, params) = self._getaddr(arg)
            if address:
                self.push('252 Cannot VRFY user, but will accept message and attempt delivery')
            else:
                self.push('502 Could not VRFY %s' % arg)
        else:
            self.push('501 Syntax: VRFY <address>')

    def smtp_MAIL(self, arg):
        if not self.seen_greeting:
            self.push('503 Error: send HELO first')
            return
        print('===> MAIL', arg, file=DEBUGSTREAM)
        syntaxerr = '501 Syntax: MAIL FROM: <address>'
        if self.extended_smtp:
            syntaxerr += ' [SP <mail-parameters>]'
        if arg is None:
            self.push(syntaxerr)
            return
        arg = self._strip_command_keyword('FROM:', arg)
        (address, params) = self._getaddr(arg)
        if not address:
            self.push(syntaxerr)
            return
        if self.extended_smtp or params:
            self.push(syntaxerr)
            return
        if self.mailfrom:
            self.push('503 Error: nested MAIL command')
            return
        self.mail_options = params.upper().split()
        params = self._getparams(self.mail_options)
        if params is None:
            self.push(syntaxerr)
            return
        if not self._decode_data:
            body = params.pop('BODY', '7BIT')
            if body not in ('7BIT', '8BITMIME'):
                self.push('501 Error: BODY can only be one of 7BIT, 8BITMIME')
                return
        if self.enable_SMTPUTF8:
            smtputf8 = params.pop('SMTPUTF8', False)
            if smtputf8 is True:
                self.require_SMTPUTF8 = True
            elif smtputf8 is not False:
                self.push('501 Error: SMTPUTF8 takes no arguments')
                return
        size = params.pop('SIZE', None)
        if size:
            if not size.isdigit():
                self.push(syntaxerr)
                return
            if self.data_size_limit and int(size) > self.data_size_limit:
                self.push('552 Error: message size exceeds fixed maximum message size')
                return
        if len(params.keys()) > 0:
            self.push('555 MAIL FROM parameters not recognized or not implemented')
            return
        self.mailfrom = address
        print('sender:', self.mailfrom, file=DEBUGSTREAM)
        self.push('250 OK')

    def smtp_RCPT(self, arg):
        if not self.seen_greeting:
            self.push('503 Error: send HELO first')
            return
        print('===> RCPT', arg, file=DEBUGSTREAM)
        if not self.mailfrom:
            self.push('503 Error: need MAIL command')
            return
        syntaxerr = '501 Syntax: RCPT TO: <address>'
        if self.extended_smtp:
            syntaxerr += ' [SP <mail-parameters>]'
        if arg is None:
            self.push(syntaxerr)
            return
        arg = self._strip_command_keyword('TO:', arg)
        (address, params) = self._getaddr(arg)
        if not address:
            self.push(syntaxerr)
            return
        if self.extended_smtp or params:
            self.push(syntaxerr)
            return
        self.rcpt_options = params.upper().split()
        params = self._getparams(self.rcpt_options)
        if params is None:
            self.push(syntaxerr)
            return
        if len(params.keys()) > 0:
            self.push('555 RCPT TO parameters not recognized or not implemented')
            return
        self.rcpttos.append(address)
        print('recips:', self.rcpttos, file=DEBUGSTREAM)
        self.push('250 OK')

    def smtp_RSET(self, arg):
        if arg:
            self.push('501 Syntax: RSET')
            return
        self._set_rset_state()
        self.push('250 OK')

    def smtp_DATA(self, arg):
        if not self.seen_greeting:
            self.push('503 Error: send HELO first')
            return
        if not self.rcpttos:
            self.push('503 Error: need RCPT command')
            return
        if arg:
            self.push('501 Syntax: DATA')
            return
        self.smtp_state = self.DATA
        self.set_terminator(b'\r\n.\r\n')
        self.push('354 End data with <CR><LF>.<CR><LF>')

    def smtp_EXPN(self, arg):
        self.push('502 EXPN not implemented')

class SMTPServer(asyncore.dispatcher):
    channel_class = SMTPChannel

    def __init__(self, localaddr, remoteaddr, data_size_limit=DATA_SIZE_DEFAULT, map=None, enable_SMTPUTF8=False, decode_data=False):
        self._localaddr = localaddr
        self._remoteaddr = remoteaddr
        self.data_size_limit = data_size_limit
        self.enable_SMTPUTF8 = enable_SMTPUTF8
        self._decode_data = decode_data
        if enable_SMTPUTF8 and decode_data:
            raise ValueError('decode_data and enable_SMTPUTF8 cannot be set to True at the same time')
        asyncore.dispatcher.__init__(self, map=map)
        try:
            gai_results = socket.getaddrinfo(*localaddr, type=socket.SOCK_STREAM)
            self.create_socket(gai_results[0][0], gai_results[0][1])
            self.set_reuse_addr()
            self.bind(localaddr)
            self.listen(5)
        except:
            self.close()
            raise
        print('%s started at %s\n\tLocal addr: %s\n\tRemote addr:%s' % (self.__class__.__name__, time.ctime(time.time()), localaddr, remoteaddr), file=DEBUGSTREAM)

    def handle_accepted(self, conn, addr):
        print('Incoming connection from %s' % repr(addr), file=DEBUGSTREAM)
        channel = self.channel_class(self, conn, addr, self.data_size_limit, self._map, self.enable_SMTPUTF8, self._decode_data)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        raise NotImplementedError

class DebuggingServer(SMTPServer):

    def _print_message_content(self, peer, data):
        inheaders = 1
        lines = data.splitlines()
        for line in lines:
            if not line:
                peerheader = 'X-Peer: ' + peer[0]
                if not isinstance(data, str):
                    peerheader = repr(peerheader.encode('utf-8'))
                print(peerheader)
                inheaders = 0
            if not (inheaders and isinstance(data, str)):
                line = repr(line)
            print(line)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        print('---------- MESSAGE FOLLOWS ----------')
        if kwargs:
            if kwargs.get('mail_options'):
                print('mail options: %s' % kwargs['mail_options'])
            if kwargs.get('rcpt_options'):
                print('rcpt options: %s\n' % kwargs['rcpt_options'])
        self._print_message_content(peer, data)
        print('------------ END MESSAGE ------------')

class PureProxy(SMTPServer):

    def __init__(self, *args, **kwargs):
        if 'enable_SMTPUTF8' in kwargs and kwargs['enable_SMTPUTF8']:
            raise ValueError('PureProxy does not support SMTPUTF8.')
        super(PureProxy, self).__init__(*args, **kwargs)

    def process_message(self, peer, mailfrom, rcpttos, data):
        lines = data.split('\n')
        i = 0
        for line in lines:
            if not line:
                break
            i += 1
        lines.insert(i, 'X-Peer: %s' % peer[0])
        data = NEWLINE.join(lines)
        refused = self._deliver(mailfrom, rcpttos, data)
        print('we got some refusals:', refused, file=DEBUGSTREAM)

    def _deliver(self, mailfrom, rcpttos, data):
        import smtplib
        refused = {}
        try:
            s = smtplib.SMTP()
            s.connect(self._remoteaddr[0], self._remoteaddr[1])
            try:
                refused = s.sendmail(mailfrom, rcpttos, data)
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused as e:
            print('got SMTPRecipientsRefused', file=DEBUGSTREAM)
            refused = e.recipients
        except (OSError, smtplib.SMTPException) as e:
            print('got', e.__class__, file=DEBUGSTREAM)
            errcode = getattr(e, 'smtp_code', -1)
            errmsg = getattr(e, 'smtp_error', 'ignore')
            for r in rcpttos:
                refused[r] = (errcode, errmsg)
        return refused

class MailmanProxy(PureProxy):

    def __init__(self, *args, **kwargs):
        if 'enable_SMTPUTF8' in kwargs and kwargs['enable_SMTPUTF8']:
            raise ValueError('MailmanProxy does not support SMTPUTF8.')
        super(PureProxy, self).__init__(*args, **kwargs)

    def process_message(self, peer, mailfrom, rcpttos, data):
        from io import StringIO
        from Mailman import Utils
        from Mailman import Message
        from Mailman import MailList
        listnames = []
        for rcpt in rcpttos:
            local = rcpt.lower().split('@')[0]
            parts = local.split('-')
            if len(parts) > 2:
                pass
            else:
                listname = parts[0]
                if len(parts) == 2:
                    command = parts[1]
                else:
                    command = ''
                if Utils.list_exists(listname):
                    if command not in ('', 'admin', 'owner', 'request', 'join', 'leave'):
                        pass
                    else:
                        listnames.append((rcpt, listname, command))
        for (rcpt, listname, command) in listnames:
            rcpttos.remove(rcpt)
        print('forwarding recips:', ' '.join(rcpttos), file=DEBUGSTREAM)
        if rcpttos:
            refused = self._deliver(mailfrom, rcpttos, data)
            print('we got refusals:', refused, file=DEBUGSTREAM)
        mlists = {}
        s = StringIO(data)
        msg = Message.Message(s)
        if not msg.get('from'):
            msg['From'] = mailfrom
        if not msg.get('date'):
            msg['Date'] = time.ctime(time.time())
        for (rcpt, listname, command) in listnames:
            print('sending message to', rcpt, file=DEBUGSTREAM)
            mlist = mlists.get(listname)
            if not mlist:
                mlist = MailList.MailList(listname, lock=0)
                mlists[listname] = mlist
            if command == '':
                msg.Enqueue(mlist, tolist=1)
            elif command == 'admin':
                msg.Enqueue(mlist, toadmin=1)
            elif command == 'owner':
                msg.Enqueue(mlist, toowner=1)
            elif command == 'request':
                msg.Enqueue(mlist, torequest=1)
            elif command in ('join', 'leave'):
                if command == 'join':
                    msg['Subject'] = 'subscribe'
                else:
                    msg['Subject'] = 'unsubscribe'
                msg.Enqueue(mlist, torequest=1)

class Options:
    setuid = True
    classname = 'PureProxy'
    size_limit = None
    enable_SMTPUTF8 = False

def parseargs():
    global DEBUGSTREAM
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'nVhc:s:du', ['class=', 'nosetuid', 'version', 'help', 'size=', 'debug', 'smtputf8'])
    except getopt.error as e:
        usage(1, e)
    options = Options()
    for (opt, arg) in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-V', '--version'):
            print(__version__)
            sys.exit(0)
        elif opt in ('-n', '--nosetuid'):
            options.setuid = False
        elif opt in ('-c', '--class'):
            options.classname = arg
        elif opt in ('-d', '--debug'):
            DEBUGSTREAM = sys.stderr
        elif opt in ('-u', '--smtputf8'):
            options.enable_SMTPUTF8 = True
        elif opt in ('-s', '--size'):
            try:
                int_size = int(arg)
                options.size_limit = int_size
            except:
                print('Invalid size: ' + arg, file=sys.stderr)
                sys.exit(1)
    if len(args) < 1:
        localspec = 'localhost:8025'
        remotespec = 'localhost:25'
    elif len(args) < 2:
        localspec = args[0]
        remotespec = 'localhost:25'
    elif len(args) < 3:
        localspec = args[0]
        remotespec = args[1]
    else:
        usage(1, 'Invalid arguments: %s' % COMMASPACE.join(args))
    i = localspec.find(':')
    if i < 0:
        usage(1, 'Bad local spec: %s' % localspec)
    options.localhost = localspec[:i]
    try:
        options.localport = int(localspec[i + 1:])
    except ValueError:
        usage(1, 'Bad local port: %s' % localspec)
    i = remotespec.find(':')
    if i < 0:
        usage(1, 'Bad remote spec: %s' % remotespec)
    options.remotehost = remotespec[:i]
    try:
        options.remoteport = int(remotespec[i + 1:])
    except ValueError:
        usage(1, 'Bad remote port: %s' % remotespec)
    return options
if __name__ == '__main__':
    options = parseargs()
    classname = options.classname
    if '.' in classname:
        lastdot = classname.rfind('.')
        mod = __import__(classname[:lastdot], globals(), locals(), [''])
        classname = classname[lastdot + 1:]
    else:
        import __main__ as mod
    class_ = getattr(mod, classname)
    proxy = class_((options.localhost, options.localport), (options.remotehost, options.remoteport), options.size_limit, enable_SMTPUTF8=options.enable_SMTPUTF8)
    if options.setuid:
        try:
            import pwd
        except ImportError:
            print('Cannot import module "pwd"; try running with -n option.', file=sys.stderr)
            sys.exit(1)
        nobody = pwd.getpwnam('nobody')[2]
        try:
            os.setuid(nobody)
        except PermissionError:
            print('Cannot setuid "nobody"; try running with -n option.', file=sys.stderr)
            sys.exit(1)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass