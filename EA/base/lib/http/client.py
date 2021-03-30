import email.parserimport email.messageimport httpimport ioimport reimport socketimport collections.abcfrom urllib.parse import urlsplit__all__ = ['HTTPResponse', 'HTTPConnection', 'HTTPException', 'NotConnected', 'UnknownProtocol', 'UnknownTransferEncoding', 'UnimplementedFileMode', 'IncompleteRead', 'InvalidURL', 'ImproperConnectionState', 'CannotSendRequest', 'CannotSendHeader', 'ResponseNotReady', 'BadStatusLine', 'LineTooLong', 'RemoteDisconnected', 'error', 'responses']HTTP_PORT = 80HTTPS_PORT = 443_UNKNOWN = 'UNKNOWN'_CS_IDLE = 'Idle'_CS_REQ_STARTED = 'Request-started'_CS_REQ_SENT = 'Request-sent'globals().update(http.HTTPStatus.__members__)responses = {v: v.phrase for v in http.HTTPStatus.__members__.values()}MAXAMOUNT = 1048576_MAXLINE = 65536_MAXHEADERS = 100_is_legal_header_name = re.compile(b'[^:\\s][^:\\r\\n]*').fullmatch_is_illegal_header_value = re.compile(b'\\n(?![ \\t])|\\r(?![ \\t\\n])').search_METHODS_EXPECTING_BODY = {'PATCH', 'POST', 'PUT'}
def _encode(data, name='data'):
    try:
        return data.encode('latin-1')
    except UnicodeEncodeError as err:
        raise UnicodeEncodeError(err.encoding, err.object, err.start, err.end, "%s (%.20r) is not valid Latin-1. Use %s.encode('utf-8') if you want to send it encoded in UTF-8." % (name.title(), data[err.start:err.end], name)) from None

class HTTPMessage(email.message.Message):

    def getallmatchingheaders(self, name):
        name = name.lower() + ':'
        n = len(name)
        lst = []
        hit = 0
        for line in self.keys():
            if line[:n].lower() == name:
                hit = 1
            elif not line[:1].isspace():
                hit = 0
            if hit:
                lst.append(line)
        return lst

def parse_headers(fp, _class=HTTPMessage):
    headers = []
    while True:
        line = fp.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise LineTooLong('header line')
        headers.append(line)
        if len(headers) > _MAXHEADERS:
            raise HTTPException('got more than %d headers' % _MAXHEADERS)
        if line in (b'\r\n', b'\n', b''):
            break
    hstring = b''.join(headers).decode('iso-8859-1')
    return email.parser.Parser(_class=_class).parsestr(hstring)
