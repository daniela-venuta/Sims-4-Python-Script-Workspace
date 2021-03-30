__all__ = ['MIMEBase']import email.policyfrom email import message
class MIMEBase(message.Message):

    def __init__(self, _maintype, _subtype, *, policy=None, **_params):
        if policy is None:
            policy = email.policy.compat32
        message.Message.__init__(self, policy=policy)
        ctype = '%s/%s' % (_maintype, _subtype)
        self.add_header('Content-Type', ctype, **_params)
        self['MIME-Version'] = '1.0'
