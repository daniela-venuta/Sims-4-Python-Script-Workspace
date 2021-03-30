__all__ = ['MIMEText']from email.charset import Charsetfrom email.mime.nonmultipart import MIMENonMultipart
class MIMEText(MIMENonMultipart):

    def __init__(self, _text, _subtype='plain', _charset=None, *, policy=None):
        if _charset is None:
            try:
                _text.encode('us-ascii')
                _charset = 'us-ascii'
            except UnicodeEncodeError:
                _charset = 'utf-8'
        MIMENonMultipart.__init__(self, 'text', _subtype, charset=str(_charset), policy=policy)
        self.set_payload(_text, _charset)
