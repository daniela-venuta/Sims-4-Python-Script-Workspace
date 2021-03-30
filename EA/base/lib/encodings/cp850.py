import codecs
class Codec(codecs.Codec):

    def encode(self, input, errors='strict'):
        return codecs.charmap_encode(input, errors, encoding_map)

    def decode(self, input, errors='strict'):
        return codecs.charmap_decode(input, errors, decoding_table)

class IncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, input, final=False):
        return codecs.charmap_encode(input, self.errors, encoding_map)[0]

class IncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, input, final=False):
        return codecs.charmap_decode(input, self.errors, decoding_table)[0]

class StreamWriter(Codec, codecs.StreamWriter):
    pass

class StreamReader(Codec, codecs.StreamReader):
    pass

def getregentry():
    return codecs.CodecInfo(name='cp850', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 199, 129: 252, 130: 233, 131: 226, 132: 228, 133: 224, 134: 229, 135: 231, 136: 234, 137: 235, 138: 232, 139: 239, 140: 238, 141: 236, 142: 196, 143: 197, 144: 201, 145: 230, 146: 198, 147: 244, 148: 246, 149: 242, 150: 251, 151: 249, 152: 255, 153: 214, 154: 220, 155: 248, 156: 163, 157: 216, 158: 215, 159: 402, 160: 225, 161: 237, 162: 243, 163: 250, 164: 241, 165: 209, 166: 170, 167: 186, 168: 191, 169: 174, 170: 172, 171: 189, 172: 188, 173: 161, 174: 171, 175: 187, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 193, 182: 194, 183: 192, 184: 169, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 162, 190: 165, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 227, 199: 195, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 164, 208: 240, 209: 208, 210: 202, 211: 203, 212: 200, 213: 305, 214: 205, 215: 206, 216: 207, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 166, 222: 204, 223: 9600, 224: 211, 225: 223, 226: 212, 227: 210, 228: 245, 229: 213, 230: 181, 231: 254, 232: 222, 233: 218, 234: 219, 235: 217, 236: 253, 237: 221, 238: 175, 239: 180, 240: 173, 241: 177, 242: 8215, 243: 190, 244: 182, 245: 167, 246: 247, 247: 184, 248: 176, 249: 168, 250: 183, 251: 185, 252: 179, 253: 178, 254: 9632, 255: 160})