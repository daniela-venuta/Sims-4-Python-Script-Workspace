import codecsimport base64
def base64_encode(input, errors='strict'):
    return (base64.encodebytes(input), len(input))

def base64_decode(input, errors='strict'):
    return (base64.decodebytes(input), len(input))

class Codec(codecs.Codec):

    def encode(self, input, errors='strict'):
        return base64_encode(input, errors)

    def decode(self, input, errors='strict'):
        return base64_decode(input, errors)

class IncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, input, final=False):
        return base64.encodebytes(input)

class IncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, input, final=False):
        return base64.decodebytes(input)

class StreamWriter(Codec, codecs.StreamWriter):
    charbuffertype = bytes

class StreamReader(Codec, codecs.StreamReader):
    charbuffertype = bytes

def getregentry():
    return codecs.CodecInfo(name='base64', encode=base64_encode, decode=base64_decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamwriter=StreamWriter, streamreader=StreamReader, _is_text_encoding=False)
