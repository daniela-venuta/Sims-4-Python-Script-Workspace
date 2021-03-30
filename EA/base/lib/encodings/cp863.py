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
    return codecs.CodecInfo(name='cp863', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 199, 129: 252, 130: 233, 131: 226, 132: 194, 133: 224, 134: 182, 135: 231, 136: 234, 137: 235, 138: 232, 139: 239, 140: 238, 141: 8215, 142: 192, 143: 167, 144: 201, 145: 200, 146: 202, 147: 244, 148: 203, 149: 207, 150: 251, 151: 249, 152: 164, 153: 212, 154: 220, 155: 162, 156: 163, 157: 217, 158: 219, 159: 402, 160: 166, 161: 180, 162: 243, 163: 250, 164: 168, 165: 184, 166: 179, 167: 175, 168: 206, 169: 8976, 170: 172, 171: 189, 172: 188, 173: 190, 174: 171, 175: 187, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 9569, 182: 9570, 183: 9558, 184: 9557, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 9564, 190: 9563, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 9566, 199: 9567, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 9575, 208: 9576, 209: 9572, 210: 9573, 211: 9561, 212: 9560, 213: 9554, 214: 9555, 215: 9579, 216: 9578, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 9612, 222: 9616, 223: 9600, 224: 945, 225: 223, 226: 915, 227: 960, 228: 931, 229: 963, 230: 181, 231: 964, 232: 934, 233: 920, 234: 937, 235: 948, 236: 8734, 237: 966, 238: 949, 239: 8745, 240: 8801, 241: 177, 242: 8805, 243: 8804, 244: 8992, 245: 8993, 246: 247, 247: 8776, 248: 176, 249: 8729, 250: 183, 251: 8730, 252: 8319, 253: 178, 254: 9632, 255: 160})