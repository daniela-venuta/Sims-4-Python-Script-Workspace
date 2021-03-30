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
    return codecs.CodecInfo(name='cp855', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 1106, 129: 1026, 130: 1107, 131: 1027, 132: 1105, 133: 1025, 134: 1108, 135: 1028, 136: 1109, 137: 1029, 138: 1110, 139: 1030, 140: 1111, 141: 1031, 142: 1112, 143: 1032, 144: 1113, 145: 1033, 146: 1114, 147: 1034, 148: 1115, 149: 1035, 150: 1116, 151: 1036, 152: 1118, 153: 1038, 154: 1119, 155: 1039, 156: 1102, 157: 1070, 158: 1098, 159: 1066, 160: 1072, 161: 1040, 162: 1073, 163: 1041, 164: 1094, 165: 1062, 166: 1076, 167: 1044, 168: 1077, 169: 1045, 170: 1092, 171: 1060, 172: 1075, 173: 1043, 174: 171, 175: 187, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 1093, 182: 1061, 183: 1080, 184: 1048, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 1081, 190: 1049, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 1082, 199: 1050, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 164, 208: 1083, 209: 1051, 210: 1084, 211: 1052, 212: 1085, 213: 1053, 214: 1086, 215: 1054, 216: 1087, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 1055, 222: 1103, 223: 9600, 224: 1071, 225: 1088, 226: 1056, 227: 1089, 228: 1057, 229: 1090, 230: 1058, 231: 1091, 232: 1059, 233: 1078, 234: 1046, 235: 1074, 236: 1042, 237: 1100, 238: 1068, 239: 8470, 240: 173, 241: 1099, 242: 1067, 243: 1079, 244: 1047, 245: 1096, 246: 1064, 247: 1101, 248: 1069, 249: 1097, 250: 1065, 251: 1095, 252: 1063, 253: 167, 254: 9632, 255: 160})