__version__ = '0.4'import socketimport selectorsimport osimport sysimport threadingfrom io import BufferedIOBasefrom time import monotonic as time__all__ = ['BaseServer', 'TCPServer', 'UDPServer', 'ThreadingUDPServer', 'ThreadingTCPServer', 'BaseRequestHandler', 'StreamRequestHandler', 'DatagramRequestHandler', 'ThreadingMixIn']if hasattr(os, 'fork'):
    __all__.extend(['ForkingUDPServer', 'ForkingTCPServer', 'ForkingMixIn'])if hasattr(socket, 'AF_UNIX'):
    __all__.extend(['UnixStreamServer', 'UnixDatagramServer', 'ThreadingUnixStreamServer', 'ThreadingUnixDatagramServer'])if hasattr(selectors, 'PollSelector'):
    _ServerSelector = selectors.PollSelector
else:
    _ServerSelector = selectors.SelectSelector
class BaseServer:
    timeout = None

    def __init__(self, server_address, RequestHandlerClass):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self._BaseServer__is_shut_down = threading.Event()
        self._BaseServer__shutdown_request = False

    def server_activate(self):
        pass

    def serve_forever(self, poll_interval=0.5):
        self._BaseServer__is_shut_down.clear()
        try:
            with _ServerSelector() as selector:
                selector.register(self, selectors.EVENT_READ)
                while not self._BaseServer__shutdown_request:
                    ready = selector.select(poll_interval)
                    if ready:
                        self._handle_request_noblock()
                    self.service_actions()
        finally:
            self._BaseServer__shutdown_request = False
            self._BaseServer__is_shut_down.set()

    def shutdown(self):
        self._BaseServer__shutdown_request = True
        self._BaseServer__is_shut_down.wait()

    def service_actions(self):
        pass

    def handle_request(self):
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        if timeout is not None:
            deadline = time() + timeout
        with _ServerSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            while True:
                ready = selector.select(timeout)
                if ready:
                    return self._handle_request_noblock()
                if timeout is not None:
                    timeout = deadline - time()
                    if timeout < 0:
                        return self.handle_timeout()

    def _handle_request_noblock(self):
        try:
            (request, client_address) = self.get_request()
        except OSError:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except Exception:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
            except:
                self.shutdown_request(request)
                raise
        else:
            self.shutdown_request(request)

    def handle_timeout(self):
        pass

    def verify_request(self, request, client_address):
        return True

    def process_request(self, request, client_address):
        self.finish_request(request, client_address)
        self.shutdown_request(request)

    def server_close(self):
        pass

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self)

    def shutdown_request(self, request):
        self.close_request(request)

    def close_request(self, request):
        pass

    def handle_error(self, request, client_address):
        print('----------------------------------------', file=sys.stderr)
        print('Exception happened during processing of request from', client_address, file=sys.stderr)
        import traceback
        traceback.print_exc()
        print('----------------------------------------', file=sys.stderr)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.server_close()

class TCPServer(BaseServer):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = False

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        BaseServer.__init__(self, server_address, RequestHandlerClass)
        self.socket = socket.socket(self.address_family, self.socket_type)
        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
            except:
                self.server_close()
                raise

    def server_bind(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def server_activate(self):
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        self.socket.close()

    def fileno(self):
        return self.socket.fileno()

    def get_request(self):
        return self.socket.accept()

    def shutdown_request(self, request):
        try:
            request.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        self.close_request(request)

    def close_request(self, request):
        request.close()

class UDPServer(TCPServer):
    allow_reuse_address = False
    socket_type = socket.SOCK_DGRAM
    max_packet_size = 8192

    def get_request(self):
        (data, client_addr) = self.socket.recvfrom(self.max_packet_size)
        return ((data, self.socket), client_addr)

    def server_activate(self):
        pass

    def shutdown_request(self, request):
        self.close_request(request)

    def close_request(self, request):
        pass
if hasattr(os, 'fork'):

    class ForkingMixIn:
        timeout = 300
        active_children = None
        max_children = 40
        block_on_close = True

        def collect_children(self, *, blocking=False):
            if self.active_children is None:
                return
            while len(self.active_children) >= self.max_children:
                try:
                    (pid, _) = os.waitpid(-1, 0)
                    self.active_children.discard(pid)
                except ChildProcessError:
                    self.active_children.clear()
                except OSError:
                    break
            for pid in self.active_children.copy():
                try:
                    flags = 0 if blocking else os.WNOHANG
                    (pid, _) = os.waitpid(pid, flags)
                    self.active_children.discard(pid)
                except ChildProcessError:
                    self.active_children.discard(pid)
                except OSError:
                    pass

        def handle_timeout(self):
            self.collect_children()

        def service_actions(self):
            self.collect_children()

        def process_request(self, request, client_address):
            pid = os.fork()
            if pid:
                if self.active_children is None:
                    self.active_children = set()
                self.active_children.add(pid)
                self.close_request(request)
                return
            status = 1
            try:
                self.finish_request(request, client_address)
                status = 0
            except Exception:
                self.handle_error(request, client_address)
            finally:
                try:
                    self.shutdown_request(request)
                finally:
                    os._exit(status)

        def server_close(self):
            super().server_close()
            self.collect_children(blocking=self.block_on_close)

class ThreadingMixIn:
    daemon_threads = False
    block_on_close = True
    _threads = None

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        t = threading.Thread(target=self.process_request_thread, args=(request, client_address))
        t.daemon = self.daemon_threads
        if t.daemon or self.block_on_close:
            if self._threads is None:
                self._threads = []
            self._threads.append(t)
        t.start()

    def server_close(self):
        super().server_close()
        if self.block_on_close:
            threads = self._threads
            self._threads = None
            if threads:
                for thread in threads:
                    thread.join()
if hasattr(os, 'fork'):

    class ForkingUDPServer(ForkingMixIn, UDPServer):
        pass

    class ForkingTCPServer(ForkingMixIn, TCPServer):
        pass

class ThreadingUDPServer(ThreadingMixIn, UDPServer):
    pass

class ThreadingTCPServer(ThreadingMixIn, TCPServer):
    pass
if hasattr(socket, 'AF_UNIX'):

    class UnixStreamServer(TCPServer):
        address_family = socket.AF_UNIX

    class UnixDatagramServer(UDPServer):
        address_family = socket.AF_UNIX

    class ThreadingUnixStreamServer(ThreadingMixIn, UnixStreamServer):
        pass

    class ThreadingUnixDatagramServer(ThreadingMixIn, UnixDatagramServer):
        pass

class BaseRequestHandler:

    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def setup(self):
        pass

    def handle(self):
        pass

    def finish(self):
        pass

class StreamRequestHandler(BaseRequestHandler):
    rbufsize = -1
    wbufsize = 0
    timeout = None
    disable_nagle_algorithm = False

    def setup(self):
        self.connection = self.request
        if self.timeout is not None:
            self.connection.settimeout(self.timeout)
        if self.disable_nagle_algorithm:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        if self.wbufsize == 0:
            self.wfile = _SocketWriter(self.connection)
        else:
            self.wfile = self.connection.makefile('wb', self.wbufsize)

    def finish(self):
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except socket.error:
                pass
        self.wfile.close()
        self.rfile.close()

class _SocketWriter(BufferedIOBase):

    def __init__(self, sock):
        self._sock = sock

    def writable(self):
        return True

    def write(self, b):
        self._sock.sendall(b)
        with memoryview(b) as view:
            return view.nbytes

    def fileno(self):
        return self._sock.fileno()

class DatagramRequestHandler(BaseRequestHandler):

    def setup(self):
        from io import BytesIO
        (self.packet, self.socket) = self.request
        self.rfile = BytesIO(self.packet)
        self.wfile = BytesIO()

    def finish(self):
        self.socket.sendto(self.wfile.getvalue(), self.client_address)
