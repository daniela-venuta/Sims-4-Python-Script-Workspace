import sys_mswindows = sys.platform == 'win32'import ioimport osimport timeimport signalimport builtinsimport warningsimport errnofrom time import monotonic as _time
class SubprocessError(Exception):
    pass

class CalledProcessError(SubprocessError):

    def __init__(self, returncode, cmd, output=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                return "Command '%s' died with %r." % (self.cmd, signal.Signals(-self.returncode))
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (self.cmd, -self.returncode)
        else:
            return "Command '%s' returned non-zero exit status %d." % (self.cmd, self.returncode)

    @property
    def stdout(self):
        return self.output

    @stdout.setter
    def stdout(self, value):
        self.output = value

class TimeoutExpired(SubprocessError):

    def __init__(self, cmd, timeout, output=None, stderr=None):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output
        self.stderr = stderr

    def __str__(self):
        return "Command '%s' timed out after %s seconds" % (self.cmd, self.timeout)

    @property
    def stdout(self):
        return self.output

    @stdout.setter
    def stdout(self, value):
        self.output = value
if _mswindows:
    import threading
    import msvcrt
    import _winapi

    class STARTUPINFO:

        def __init__(self, *, dwFlags=0, hStdInput=None, hStdOutput=None, hStdError=None, wShowWindow=0, lpAttributeList=None):
            self.dwFlags = dwFlags
            self.hStdInput = hStdInput
            self.hStdOutput = hStdOutput
            self.hStdError = hStdError
            self.wShowWindow = wShowWindow
            self.lpAttributeList = lpAttributeList or {'handle_list': []}

else:
    import _posixsubprocess
    import select
    import selectors
    import threading
    _PIPE_BUF = getattr(select, 'PIPE_BUF', 512)
    if hasattr(selectors, 'PollSelector'):
        _PopenSelector = selectors.PollSelector
    else:
        _PopenSelector = selectors.SelectSelector__all__ = ['Popen', 'PIPE', 'STDOUT', 'call', 'check_call', 'getstatusoutput', 'getoutput', 'check_output', 'run', 'CalledProcessError', 'DEVNULL', 'SubprocessError', 'TimeoutExpired', 'CompletedProcess']if _mswindows:
    from _winapi import CREATE_NEW_CONSOLE, CREATE_NEW_PROCESS_GROUP, STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE, SW_HIDE, STARTF_USESTDHANDLES, STARTF_USESHOWWINDOW, ABOVE_NORMAL_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS, HIGH_PRIORITY_CLASS, IDLE_PRIORITY_CLASS, NORMAL_PRIORITY_CLASS, REALTIME_PRIORITY_CLASS, CREATE_NO_WINDOW, DETACHED_PROCESS, CREATE_DEFAULT_ERROR_MODE, CREATE_BREAKAWAY_FROM_JOB
    __all__.extend(['CREATE_NEW_CONSOLE', 'CREATE_NEW_PROCESS_GROUP', 'STD_INPUT_HANDLE', 'STD_OUTPUT_HANDLE', 'STD_ERROR_HANDLE', 'SW_HIDE', 'STARTF_USESTDHANDLES', 'STARTF_USESHOWWINDOW', 'STARTUPINFO', 'ABOVE_NORMAL_PRIORITY_CLASS', 'BELOW_NORMAL_PRIORITY_CLASS', 'HIGH_PRIORITY_CLASS', 'IDLE_PRIORITY_CLASS', 'NORMAL_PRIORITY_CLASS', 'REALTIME_PRIORITY_CLASS', 'CREATE_NO_WINDOW', 'DETACHED_PROCESS', 'CREATE_DEFAULT_ERROR_MODE', 'CREATE_BREAKAWAY_FROM_JOB'])

    class Handle(int):
        closed = False

        def Close(self, CloseHandle=_winapi.CloseHandle):
            if not self.closed:
                self.closed = True
                CloseHandle(self)

        def Detach(self):
            if not self.closed:
                self.closed = True
                return int(self)
            raise ValueError('already closed')

        def __repr__(self):
            return '%s(%d)' % (self.__class__.__name__, int(self))

        __del__ = Close
        __str__ = __repr__
_active = []
def _cleanup():
    for inst in _active[:]:
        res = inst._internal_poll(_deadstate=sys.maxsize)
        if res is not None:
            try:
                _active.remove(inst)
            except ValueError:
                pass
PIPE = -1STDOUT = -2DEVNULL = -3
def _optim_args_from_interpreter_flags():
    args = []
    value = sys.flags.optimize
    if value > 0:
        args.append('-' + 'O'*value)
    return args

def _args_from_interpreter_flags():
    flag_opt_map = {'debug': 'd', 'dont_write_bytecode': 'B', 'no_user_site': 's', 'no_site': 'S', 'ignore_environment': 'E', 'verbose': 'v', 'bytes_warning': 'b', 'quiet': 'q'}
    args = _optim_args_from_interpreter_flags()
    for (flag, opt) in flag_opt_map.items():
        v = getattr(sys.flags, flag)
        if v > 0:
            args.append('-' + opt*v)
    warnopts = sys.warnoptions[:]
    bytes_warning = sys.flags.bytes_warning
    xoptions = getattr(sys, '_xoptions', {})
    dev_mode = 'dev' in xoptions
    if bytes_warning > 1:
        warnopts.remove('error::BytesWarning')
    elif bytes_warning:
        warnopts.remove('default::BytesWarning')
    if dev_mode:
        warnopts.remove('default')
    for opt in warnopts:
        args.append('-W' + opt)
    if dev_mode:
        args.extend(('-X', 'dev'))
    for opt in ('faulthandler', 'tracemalloc', 'importtime', 'showalloccount', 'showrefcount', 'utf8'):
        if opt in xoptions:
            value = xoptions[opt]
            if value is True:
                arg = opt
            else:
                arg = '%s=%s' % (opt, value)
            args.extend(('-X', arg))
    return args

def call(*popenargs, timeout=None, **kwargs):
    with Popen(*popenargs, **kwargs) as p:
        try:
            return p.wait(timeout=timeout)
        except:
            p.kill()
            raise

def check_call(*popenargs, **kwargs):
    retcode = call(*popenargs, **kwargs)
    if retcode:
        cmd = kwargs.get('args')
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd)
    return 0

def check_output(*popenargs, timeout=None, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    if kwargs['input'] is None:
        kwargs['input'] = '' if kwargs.get('universal_newlines', False) else b''
    return run(*popenargs, stdout=PIPE, timeout=timeout, check=True, **kwargs).stdout

class CompletedProcess(object):

    def __init__(self, args, returncode, stdout=None, stderr=None):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        args = ['args={!r}'.format(self.args), 'returncode={!r}'.format(self.returncode)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return '{}({})'.format(type(self).__name__, ', '.join(args))

    def check_returncode(self):
        if self.returncode:
            raise CalledProcessError(self.returncode, self.args, self.stdout, self.stderr)

def run(*popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs):
    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = PIPE
    if capture_output:
        if 'stdout' in kwargs or 'stderr' in kwargs:
            raise ValueError('stdout and stderr arguments may not be used with capture_output.')
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE
    with Popen(*popenargs, **kwargs) as process:
        try:
            (stdout, stderr) = process.communicate(input, timeout=timeout)
        except TimeoutExpired:
            process.kill()
            (stdout, stderr) = process.communicate()
            raise TimeoutExpired(process.args, timeout, output=stdout, stderr=stderr)
        except:
            process.kill()
            raise
        retcode = process.poll()
        if check and retcode:
            raise CalledProcessError(retcode, process.args, output=stdout, stderr=stderr)
    return CompletedProcess(process.args, retcode, stdout, stderr)

def list2cmdline(seq):
    result = []
    needquote = False
    for arg in seq:
        bs_buf = []
        if result:
            result.append(' ')
        needquote = ' ' in arg or ('\t' in arg or not arg)
        if needquote:
            result.append('"')
        for c in arg:
            if c == '\\':
                bs_buf.append(c)
            elif c == '"':
                result.append('\\'*len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)
        if bs_buf:
            result.extend(bs_buf)
        if needquote:
            result.extend(bs_buf)
            result.append('"')
    return ''.join(result)

def getstatusoutput(cmd):
    try:
        data = check_output(cmd, shell=True, text=True, stderr=STDOUT)
        exitcode = 0
    except CalledProcessError as ex:
        data = ex.output
        exitcode = ex.returncode
    if data[-1:] == '\n':
        data = data[:-1]
    return (exitcode, data)

def getoutput(cmd):
    return getstatusoutput(cmd)[1]
