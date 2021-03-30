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
    return codecs.CodecInfo(name='cp852', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 199, 129: 252, 130: 233, 131: 226, 132: 228, 133: 367, 134: 263, 135: 231, 136: 322, 137: 235, 138: 336, 139: 337, 140: 238, 141: 377, 142: 196, 143: 262, 144: 201, 145: 313, 146: 314, 147: 244, 148: 246, 149: 317, 150: 318, 151: 346, 152: 347, 153: 214, 154: 220, 155: 356, 156: 357, 157: 321, 158: 215, 159: 269, 160: 225, 161: 237, 162: 243, 163: 250, 164: 260, 165: 261, 166: 381, 167: 382, 168: 280, 169: 281, 170: 172, 171: 378, 172: 268, 173: 351, 174: 171, 175: 187, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 193, 182: 194, 183: 282, 184: 350, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 379, 190: 380, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 258, 199: 259, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 164, 208: 273, 209: 272, 210: 270, 211: 203, 212: 271, 213: 327, 214: 205, 215: 206, 216: 283, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 354, 222: 366, 223: 9600, 224: 211, 225: 223, 226: 212, 227: 323, 228: 324, 229: 328, 230: 352, 231: 353, 232: 340, 233: 218, 234: 341, 235: 368, 236: 253, 237: 221, 238: 355, 239: 180, 240: 173, 241: 733, 242: 731, 243: 711, 244: 728, 245: 167, 246: 247, 247: 184, 248: 176, 249: 168, 250: 729, 251: 369, 252: 344, 253: 345, 254: 9632, 255: 160})