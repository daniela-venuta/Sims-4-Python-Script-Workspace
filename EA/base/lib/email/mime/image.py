__all__ = ['MIMEImage']import imghdrfrom email import encodersfrom email.mime.nonmultipart import MIMENonMultipart
class MIMEImage(MIMENonMultipart):

    def __init__(self, _imagedata, _subtype=None, _encoder=encoders.encode_base64, *, policy=None, **_params):
        if _subtype is None:
            _subtype = imghdr.what(None, _imagedata)
        if _subtype is None:
            raise TypeError('Could not guess image MIME subtype')
        MIMENonMultipart.__init__(self, 'image', _subtype, policy=policy, **_params)
        self.set_payload(_imagedata)
        _encoder(self)
