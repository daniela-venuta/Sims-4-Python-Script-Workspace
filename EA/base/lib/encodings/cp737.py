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
    return codecs.CodecInfo(name='cp737', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 913, 129: 914, 130: 915, 131: 916, 132: 917, 133: 918, 134: 919, 135: 920, 136: 921, 137: 922, 138: 923, 139: 924, 140: 925, 141: 926, 142: 927, 143: 928, 144: 929, 145: 931, 146: 932, 147: 933, 148: 934, 149: 935, 150: 936, 151: 937, 152: 945, 153: 946, 154: 947, 155: 948, 156: 949, 157: 950, 158: 951, 159: 952, 160: 953, 161: 954, 162: 955, 163: 956, 164: 957, 165: 958, 166: 959, 167: 960, 168: 961, 169: 963, 170: 962, 171: 964, 172: 965, 173: 966, 174: 967, 175: 968, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 9569, 182: 9570, 183: 9558, 184: 9557, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 9564, 190: 9563, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 9566, 199: 9567, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 9575, 208: 9576, 209: 9572, 210: 9573, 211: 9561, 212: 9560, 213: 9554, 214: 9555, 215: 9579, 216: 9578, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 9612, 222: 9616, 223: 9600, 224: 969, 225: 940, 226: 941, 227: 942, 228: 970, 229: 943, 230: 972, 231: 973, 232: 971, 233: 974, 234: 902, 235: 904, 236: 905, 237: 906, 238: 908, 239: 910, 240: 911, 241: 177, 242: 8805, 243: 8804, 244: 938, 245: 939, 246: 247, 247: 8776, 248: 176, 249: 8729, 250: 183, 251: 8730, 252: 8319, 253: 178, 254: 9632, 255: 160})