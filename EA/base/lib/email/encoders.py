__all__ = ['encode_7or8bit', 'encode_base64', 'encode_noop', 'encode_quopri']from base64 import encodebytes as _bencodefrom quopri import encodestring as _encodestring
def _qencode(s):
    enc = _encodestring(s, quotetabs=True)
    return enc.replace(b' ', b'=20')

def encode_base64(msg):
    orig = msg.get_payload(decode=True)
    encdata = str(_bencode(orig), 'ascii')
    msg.set_payload(encdata)
    msg['Content-Transfer-Encoding'] = 'base64'

def encode_quopri(msg):
    orig = msg.get_payload(decode=True)
    encdata = _qencode(orig)
    msg.set_payload(encdata)
    msg['Content-Transfer-Encoding'] = 'quoted-printable'

def encode_7or8bit(msg):
    orig = msg.get_payload(decode=True)
    if orig is None:
        msg['Content-Transfer-Encoding'] = '7bit'
        return
    try:
        orig.decode('ascii')
    except UnicodeError:
        msg['Content-Transfer-Encoding'] = '8bit'
    msg['Content-Transfer-Encoding'] = '7bit'

def encode_noop(msg):
    pass
