import warnings as _warningsfrom _operator import _compare_digest as compare_digesttry:
    import _hashlib as _hashopenssl
except ImportError:
    _hashopenssl = None
    _openssl_md_meths = None_openssl_md_meths = frozenset(_hashopenssl.openssl_md_meth_names)import hashlib as _hashlibtrans_5C = bytes(x ^ 92 for x in range(256))trans_36 = bytes(x ^ 54 for x in range(256))digest_size = None
class HMAC:
    blocksize = 64

    def __init__(self, key, msg=None, digestmod=None):
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError('key: expected bytes or bytearray, but got %r' % type(key).__name__)
        if digestmod is None:
            _warnings.warn('HMAC() without an explicit digestmod argument is deprecated since Python 3.4, and will be removed in 3.8', DeprecationWarning, 2)
            digestmod = _hashlib.md5
        if callable(digestmod):
            self.digest_cons = digestmod
        elif isinstance(digestmod, str):
            self.digest_cons = lambda d=b'': _hashlib.new(digestmod, d)
        else:
            self.digest_cons = lambda d=b'': digestmod.new(d)
        self.outer = self.digest_cons()
        self.inner = self.digest_cons()
        self.digest_size = self.inner.digest_size
        if hasattr(self.inner, 'block_size'):
            blocksize = self.inner.block_size
            if blocksize < 16:
                _warnings.warn('block_size of %d seems too small; using our default of %d.' % (blocksize, self.blocksize), RuntimeWarning, 2)
                blocksize = self.blocksize
        else:
            _warnings.warn('No block_size attribute on given digest object; Assuming %d.' % self.blocksize, RuntimeWarning, 2)
            blocksize = self.blocksize
        self.block_size = blocksize
        if len(key) > blocksize:
            key = self.digest_cons(key).digest()
        key = key.ljust(blocksize, b'\x00')
        self.outer.update(key.translate(trans_5C))
        self.inner.update(key.translate(trans_36))
        if msg is not None:
            self.update(msg)

    @property
    def name(self):
        return 'hmac-' + self.inner.name

    def update(self, msg):
        self.inner.update(msg)

    def copy(self):
        other = self.__class__.__new__(self.__class__)
        other.digest_cons = self.digest_cons
        other.digest_size = self.digest_size
        other.inner = self.inner.copy()
        other.outer = self.outer.copy()
        return other

    def _current(self):
        h = self.outer.copy()
        h.update(self.inner.digest())
        return h

    def digest(self):
        h = self._current()
        return h.digest()

    def hexdigest(self):
        h = self._current()
        return h.hexdigest()

def new(key, msg=None, digestmod=None):
    return HMAC(key, msg, digestmod)

def digest(key, msg, digest):
    if _hashopenssl is not None and isinstance(digest, str) and digest in _openssl_md_meths:
        return _hashopenssl.hmac_digest(key, msg, digest)
    if callable(digest):
        digest_cons = digest
    elif isinstance(digest, str):
        digest_cons = lambda d=b'': _hashlib.new(digest, d)
    else:
        digest_cons = lambda d=b'': digest.new(d)
    inner = digest_cons()
    outer = digest_cons()
    blocksize = getattr(inner, 'block_size', 64)
    if len(key) > blocksize:
        key = digest_cons(key).digest()
    key = key + b'\x00'*(blocksize - len(key))
    inner.update(key.translate(trans_36))
    outer.update(key.translate(trans_5C))
    inner.update(msg)
    outer.update(inner.digest())
    return outer.digest()
