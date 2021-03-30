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
    return codecs.CodecInfo(name='cp1125', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 1040, 129: 1041, 130: 1042, 131: 1043, 132: 1044, 133: 1045, 134: 1046, 135: 1047, 136: 1048, 137: 1049, 138: 1050, 139: 1051, 140: 1052, 141: 1053, 142: 1054, 143: 1055, 144: 1056, 145: 1057, 146: 1058, 147: 1059, 148: 1060, 149: 1061, 150: 1062, 151: 1063, 152: 1064, 153: 1065, 154: 1066, 155: 1067, 156: 1068, 157: 1069, 158: 1070, 159: 1071, 160: 1072, 161: 1073, 162: 1074, 163: 1075, 164: 1076, 165: 1077, 166: 1078, 167: 1079, 168: 1080, 169: 1081, 170: 1082, 171: 1083, 172: 1084, 173: 1085, 174: 1086, 175: 1087, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 9569, 182: 9570, 183: 9558, 184: 9557, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 9564, 190: 9563, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 9566, 199: 9567, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 9575, 208: 9576, 209: 9572, 210: 9573, 211: 9561, 212: 9560, 213: 9554, 214: 9555, 215: 9579, 216: 9578, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 9612, 222: 9616, 223: 9600, 224: 1088, 225: 1089, 226: 1090, 227: 1091, 228: 1092, 229: 1093, 230: 1094, 231: 1095, 232: 1096, 233: 1097, 234: 1098, 235: 1099, 236: 1100, 237: 1101, 238: 1102, 239: 1103, 240: 1025, 241: 1105, 242: 1168, 243: 1169, 244: 1028, 245: 1108, 246: 1030, 247: 1110, 248: 1031, 249: 1111, 250: 183, 251: 8730, 252: 8470, 253: 164, 254: 9632, 255: 160})