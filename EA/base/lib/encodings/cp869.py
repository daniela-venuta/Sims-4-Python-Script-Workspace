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
    return codecs.CodecInfo(name='cp869', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: None, 129: None, 130: None, 131: None, 132: None, 133: None, 134: 902, 135: None, 136: 183, 137: 172, 138: 166, 139: 8216, 140: 8217, 141: 904, 142: 8213, 143: 905, 144: 906, 145: 938, 146: 908, 147: None, 148: None, 149: 910, 150: 939, 151: 169, 152: 911, 153: 178, 154: 179, 155: 940, 156: 163, 157: 941, 158: 942, 159: 943, 160: 970, 161: 912, 162: 972, 163: 973, 164: 913, 165: 914, 166: 915, 167: 916, 168: 917, 169: 918, 170: 919, 171: 189, 172: 920, 173: 921, 174: 171, 175: 187, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 922, 182: 923, 183: 924, 184: 925, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 926, 190: 927, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 928, 199: 929, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 931, 208: 932, 209: 933, 210: 934, 211: 935, 212: 936, 213: 937, 214: 945, 215: 946, 216: 947, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 948, 222: 949, 223: 9600, 224: 950, 225: 951, 226: 952, 227: 953, 228: 954, 229: 955, 230: 956, 231: 957, 232: 958, 233: 959, 234: 960, 235: 961, 236: 963, 237: 962, 238: 964, 239: 900, 240: 173, 241: 177, 242: 965, 243: 966, 244: 967, 245: 167, 246: 968, 247: 901, 248: 176, 249: 168, 250: 969, 251: 971, 252: 944, 253: 974, 254: 9632, 255: 160})