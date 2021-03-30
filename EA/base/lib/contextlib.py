import abcimport sysimport _collections_abcfrom collections import dequefrom functools import wraps__all__ = ['asynccontextmanager', 'contextmanager', 'closing', 'nullcontext', 'AbstractContextManager', 'AbstractAsyncContextManager', 'AsyncExitStack', 'ContextDecorator', 'ExitStack', 'redirect_stdout', 'redirect_stderr', 'suppress']
class AbstractContextManager(abc.ABC):

    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractContextManager:
            return _collections_abc._check_methods(C, '__enter__', '__exit__')
        return NotImplemented

class AbstractAsyncContextManager(abc.ABC):

    async def __aenter__(self):
        yield self

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractAsyncContextManager:
            return _collections_abc._check_methods(C, '__aenter__', '__aexit__')
        return NotImplemented

class ContextDecorator(object):

    def _recreate_cm(self):
        return self

    def __call__(self, func):

        @wraps(func)
        def inner(*args, **kwds):
            with self._recreate_cm():
                return func(*args, **kwds)

        return inner

class _GeneratorContextManagerBase:

    def __init__(self, func, args, kwds):
        self.gen = func(*args, **kwds)
        self.func = func
        self.args = args
        self.kwds = kwds
        doc = getattr(func, '__doc__', None)
        if doc is None:
            doc = type(self).__doc__
        self.__doc__ = doc

class _GeneratorContextManager(_GeneratorContextManagerBase, AbstractContextManager, ContextDecorator):

    def _recreate_cm(self):
        return self.__class__(self.func, self.args, self.kwds)

    def __enter__(self):
        del self.args
        del self.kwds
        del self.func
        try:
            return next(self.gen)
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                next(self.gen)
            except StopIteration:
                return False
            raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                value = type()
            try:
                self.gen.throw(type, value, traceback)
            except StopIteration as exc:
                return exc is not value
            except RuntimeError as exc:
                if exc is value:
                    return False
                if type is StopIteration and exc.__cause__ is value:
                    return False
                raise
            except:
                if sys.exc_info()[1] is value:
                    return False
            raise

class _AsyncGeneratorContextManager(_GeneratorContextManagerBase, AbstractAsyncContextManager):

    async def __aenter__(self):
        try:
            yield await self.gen.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("generator didn't yield") from None

    async def __aexit__(self, typ, value, traceback):
        if typ is None:
            try:
                await self.gen.__anext__()
            except StopAsyncIteration:
                return
            raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                value = typ()
            try:
                await self.gen.athrow(typ, value, traceback)
                raise RuntimeError("generator didn't stop after throw()")
            except StopAsyncIteration as exc:
                yield exc is not value
            except RuntimeError as exc:
                if exc is value:
                    yield False
                if isinstance(value, (StopIteration, StopAsyncIteration)) and exc.__cause__ is value:
                    yield False
                raise
            except BaseException as exc:
                if exc is not value:
                    raise

def contextmanager(func):

    @wraps(func)
    def helper(*args, **kwds):
        return _GeneratorContextManager(func, args, kwds)

    return helper

def asynccontextmanager(func):

    @wraps(func)
    def helper(*args, **kwds):
        return _AsyncGeneratorContextManager(func, args, kwds)

    return helper

class closing(AbstractContextManager):

    def __init__(self, thing):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, *exc_info):
        self.thing.close()

class _RedirectStream(AbstractContextManager):
    _stream = None

    def __init__(self, new_target):
        self._new_target = new_target
        self._old_targets = []

    def __enter__(self):
        self._old_targets.append(getattr(sys, self._stream))
        setattr(sys, self._stream, self._new_target)
        return self._new_target

    def __exit__(self, exctype, excinst, exctb):
        setattr(sys, self._stream, self._old_targets.pop())

class redirect_stdout(_RedirectStream):
    _stream = 'stdout'

class redirect_stderr(_RedirectStream):
    _stream = 'stderr'

class suppress(AbstractContextManager):

    def __init__(self, *exceptions):
        self._exceptions = exceptions

    def __enter__(self):
        pass

    def __exit__(self, exctype, excinst, exctb):
        return exctype is not None and issubclass(exctype, self._exceptions)

class _BaseExitStack:

    @staticmethod
    def _create_exit_wrapper(cm, cm_exit):

        def _exit_wrapper(exc_type, exc, tb):
            return cm_exit(cm, exc_type, exc, tb)

        return _exit_wrapper

    @staticmethod
    def _create_cb_wrapper(callback, *args, **kwds):

        def _exit_wrapper(exc_type, exc, tb):
            callback(*args, **kwds)

        return _exit_wrapper

    def __init__(self):
        self._exit_callbacks = deque()

    def pop_all(self):
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = deque()
        return new_stack

    def push(self, exit):
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__exit__
        except AttributeError:
            self._push_exit_callback(exit)
        self._push_cm_exit(exit, exit_method)
        return exit

    def enter_context(self, cm):
        _cm_type = type(cm)
        _exit = _cm_type.__exit__
        result = _cm_type.__enter__(cm)
        self._push_cm_exit(cm, _exit)
        return result

    def callback(self, callback, *args, **kwds):
        _exit_wrapper = self._create_cb_wrapper(callback, *args, **kwds)
        _exit_wrapper.__wrapped__ = callback
        self._push_exit_callback(_exit_wrapper)
        return callback

    def _push_cm_exit(self, cm, cm_exit):
        _exit_wrapper = self._create_exit_wrapper(cm, cm_exit)
        _exit_wrapper.__self__ = cm
        self._push_exit_callback(_exit_wrapper, True)

    def _push_exit_callback(self, callback, is_sync=True):
        self._exit_callbacks.append((is_sync, callback))

class ExitStack(_BaseExitStack, AbstractContextManager):

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        received_exc = exc_details[0] is not None
        frame_exc = sys.exc_info()[1]

        def _fix_exception_context(new_exc, old_exc):
            while True:
                exc_context = new_exc.__context__
                if exc_context is old_exc:
                    return
                if exc_context is None or exc_context is frame_exc:
                    break
                new_exc = exc_context
            new_exc.__context__ = old_exc

        suppressed_exc = False
        pending_raise = False
        while self._exit_callbacks:
            (is_sync, cb) = self._exit_callbacks.pop()
            try:
                suppressed_exc = True
                pending_raise = False
                exc_details = (None, None, None)
            except:
                new_exc_details = sys.exc_info()
                _fix_exception_context(new_exc_details[1], exc_details[1])
                pending_raise = True
                exc_details = new_exc_details
        if pending_raise:
            try:
                fixed_ctx = exc_details[1].__context__
                raise exc_details[1]
            except BaseException:
                exc_details[1].__context__ = fixed_ctx
                raise
        return received_exc and suppressed_exc

    def close(self):
        self.__exit__(None, None, None)

class AsyncExitStack(_BaseExitStack, AbstractAsyncContextManager):

    @staticmethod
    def _create_async_exit_wrapper(cm, cm_exit):

        async def _exit_wrapper(exc_type, exc, tb):
            yield await cm_exit(cm, exc_type, exc, tb)

        return _exit_wrapper

    @staticmethod
    def _create_async_cb_wrapper(callback, *args, **kwds):

        async def _exit_wrapper(exc_type, exc, tb):
            await callback(*args, **kwds)

        return _exit_wrapper

    async def enter_async_context(self, cm):
        _cm_type = type(cm)
        _exit = _cm_type.__aexit__
        result = await _cm_type.__aenter__(cm)
        self._push_async_cm_exit(cm, _exit)
        yield result

    def push_async_exit(self, exit):
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__aexit__
        except AttributeError:
            self._push_exit_callback(exit, False)
        self._push_async_cm_exit(exit, exit_method)
        return exit

    def push_async_callback(self, callback, *args, **kwds):
        _exit_wrapper = self._create_async_cb_wrapper(callback, *args, **kwds)
        _exit_wrapper.__wrapped__ = callback
        self._push_exit_callback(_exit_wrapper, False)
        return callback

    async def aclose(self):
        await self.__aexit__(None, None, None)

    def _push_async_cm_exit(self, cm, cm_exit):
        _exit_wrapper = self._create_async_exit_wrapper(cm, cm_exit)
        _exit_wrapper.__self__ = cm
        self._push_exit_callback(_exit_wrapper, False)

    async def __aenter__(self):
        yield self

    async def __aexit__(self, *exc_details):
        received_exc = exc_details[0] is not None
        frame_exc = sys.exc_info()[1]

        def _fix_exception_context(new_exc, old_exc):
            while True:
                exc_context = new_exc.__context__
                if exc_context is old_exc:
                    return
                if exc_context is None or exc_context is frame_exc:
                    break
                new_exc = exc_context
            new_exc.__context__ = old_exc

        suppressed_exc = False
        pending_raise = False
        while self._exit_callbacks:
            (is_sync, cb) = self._exit_callbacks.pop()
            try:
                if is_sync:
                    cb_suppress = cb(*exc_details)
                else:
                    cb_suppress = await cb(*exc_details)
                suppressed_exc = True
                pending_raise = False
                exc_details = (None, None, None)
            except:
                new_exc_details = sys.exc_info()
                _fix_exception_context(new_exc_details[1], exc_details[1])
                pending_raise = True
                exc_details = new_exc_details
        if pending_raise:
            try:
                fixed_ctx = exc_details[1].__context__
                raise exc_details[1]
            except BaseException:
                exc_details[1].__context__ = fixed_ctx
                raise
        yield received_exc and suppressed_exc

class nullcontext(AbstractContextManager):

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
        pass
