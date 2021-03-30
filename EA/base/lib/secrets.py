__all__ = ['choice', 'randbelow', 'randbits', 'SystemRandom', 'token_bytes', 'token_hex', 'token_urlsafe', 'compare_digest']import base64import binasciiimport osfrom hmac import compare_digestfrom random import SystemRandom_sysrand = SystemRandom()randbits = _sysrand.getrandbitschoice = _sysrand.choice
def randbelow(exclusive_upper_bound):
    if exclusive_upper_bound <= 0:
        raise ValueError('Upper bound must be positive.')
    return _sysrand._randbelow(exclusive_upper_bound)
DEFAULT_ENTROPY = 32
def token_bytes(nbytes=None):
    if nbytes is None:
        nbytes = DEFAULT_ENTROPY
    return os.urandom(nbytes)

def token_hex(nbytes=None):
    return binascii.hexlify(token_bytes(nbytes)).decode('ascii')

def token_urlsafe(nbytes=None):
    tok = token_bytes(nbytes)
    return base64.urlsafe_b64encode(tok).rstrip(b'=').decode('ascii')
