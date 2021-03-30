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
    return codecs.CodecInfo(name='cp775', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 262, 129: 252, 130: 233, 131: 257, 132: 228, 133: 291, 134: 229, 135: 263, 136: 322, 137: 275, 138: 342, 139: 343, 140: 299, 141: 377, 142: 196, 143: 197, 144: 201, 145: 230, 146: 198, 147: 333, 148: 246, 149: 290, 150: 162, 151: 346, 152: 347, 153: 214, 154: 220, 155: 248, 156: 163, 157: 216, 158: 215, 159: 164, 160: 256, 161: 298, 162: 243, 163: 379, 164: 380, 165: 378, 166: 8221, 167: 166, 168: 169, 169: 174, 170: 172, 171: 189, 172: 188, 173: 321, 174: 171, 175: 187, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 260, 182: 268, 183: 280, 184: 278, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 302, 190: 352, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 370, 199: 362, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 381, 208: 261, 209: 269, 210: 281, 211: 279, 212: 303, 213: 353, 214: 371, 215: 363, 216: 382, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 9612, 222: 9616, 223: 9600, 224: 211, 225: 223, 226: 332, 227: 323, 228: 245, 229: 213, 230: 181, 231: 324, 232: 310, 233: 311, 234: 315, 235: 316, 236: 326, 237: 274, 238: 325, 239: 8217, 240: 173, 241: 177, 242: 8220, 243: 190, 244: 182, 245: 167, 246: 247, 247: 8222, 248: 176, 249: 8729, 250: 183, 251: 185, 252: 179, 253: 178, 254: 9632, 255: 160})