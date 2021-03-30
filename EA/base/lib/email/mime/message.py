__all__ = ['MIMEMessage']
class MIMEMessage(MIMENonMultipart):

    def __init__(self, _msg, _subtype='rfc822', *, policy=None):
        MIMENonMultipart.__init__(self, 'message', _subtype, policy=policy)
        if not isinstance(_msg, message.Message):
            raise TypeError('Argument is not an instance of Message')
        message.Message.attach(self, _msg)
        self.set_default_type('message/rfc822')
