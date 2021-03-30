import socket
class SMTPException(OSError):
    pass

class SMTPNotSupportedError(SMTPException):
    pass

class SMTPServerDisconnected(SMTPException):
    pass

class SMTPResponseException(SMTPException):

    def __init__(self, code, msg):
        self.smtp_code = code
        self.smtp_error = msg
        self.args = (code, msg)

class SMTPSenderRefused(SMTPResponseException):

    def __init__(self, code, msg, sender):
        self.smtp_code = code
        self.smtp_error = msg
        self.sender = sender
        self.args = (code, msg, sender)

class SMTPRecipientsRefused(SMTPException):

    def __init__(self, recipients):
        self.recipients = recipients
        self.args = (recipients,)

class SMTPDataError(SMTPResponseException):
    pass

class SMTPConnectError(SMTPResponseException):
    pass

class SMTPHeloError(SMTPResponseException):
    pass

class SMTPAuthenticationError(SMTPResponseException):
    pass

def quoteaddr(addrstring):
    (displayname, addr) = email.utils.parseaddr(addrstring)
    if (displayname, addr) == ('', ''):
        if addrstring.strip().startswith('<'):
            return addrstring
        return '<%s>' % addrstring
    return '<%s>' % addr

def _addr_only(addrstring):
    (displayname, addr) = email.utils.parseaddr(addrstring)
    if (displayname, addr) == ('', ''):
        return addrstring
    return addr

def quotedata(data):
    return re.sub('(?m)^\\.', '..', re.sub('(?:\\r\\n|\\n|\\r(?!\\n))', CRLF, data))

def _quote_periods(bindata):
    return re.sub(b'(?m)^\\.', b'..', bindata)

def _fix_eols(data):
    return re.sub('(?:\\r\\n|\\n|\\r(?!\\n))', CRLF, data)

    import ssl
except ImportError:
    _have_ssl = False