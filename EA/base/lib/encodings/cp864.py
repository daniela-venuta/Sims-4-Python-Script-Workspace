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
    return codecs.CodecInfo(name='cp864', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({37: 1642, 128: 176, 129: 183, 130: 8729, 131: 8730, 132: 9618, 133: 9472, 134: 9474, 135: 9532, 136: 9508, 137: 9516, 138: 9500, 139: 9524, 140: 9488, 141: 9484, 142: 9492, 143: 9496, 144: 946, 145: 8734, 146: 966, 147: 177, 148: 189, 149: 188, 150: 8776, 151: 171, 152: 187, 153: 65271, 154: 65272, 155: None, 156: None, 157: 65275, 158: 65276, 159: None, 161: 173, 162: 65154, 165: 65156, 166: None, 167: None, 168: 65166, 169: 65167, 170: 65173, 171: 65177, 172: 1548, 173: 65181, 174: 65185, 175: 65189, 176: 1632, 177: 1633, 178: 1634, 179: 1635, 180: 1636, 181: 1637, 182: 1638, 183: 1639, 184: 1640, 185: 1641, 186: 65233, 187: 1563, 188: 65201, 189: 65205, 190: 65209, 191: 1567, 192: 162, 193: 65152, 194: 65153, 195: 65155, 196: 65157, 197: 65226, 198: 65163, 199: 65165, 200: 65169, 201: 65171, 202: 65175, 203: 65179, 204: 65183, 205: 65187, 206: 65191, 207: 65193, 208: 65195, 209: 65197, 210: 65199, 211: 65203, 212: 65207, 213: 65211, 214: 65215, 215: 65217, 216: 65221, 217: 65227, 218: 65231, 219: 166, 220: 172, 221: 247, 222: 215, 223: 65225, 224: 1600, 225: 65235, 226: 65239, 227: 65243, 228: 65247, 229: 65251, 230: 65255, 231: 65259, 232: 65261, 233: 65263, 234: 65267, 235: 65213, 236: 65228, 237: 65230, 238: 65229, 239: 65249, 240: 65149, 241: 1617, 242: 65253, 243: 65257, 244: 65260, 245: 65264, 246: 65266, 247: 65232, 248: 65237, 249: 65269, 250: 65270, 251: 65245, 252: 65241, 253: 65265, 254: 9632, 255: None})