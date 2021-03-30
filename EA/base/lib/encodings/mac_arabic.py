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
    return codecs.CodecInfo(name='mac-arabic', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))decoding_map.update({128: 196, 129: 160, 130: 199, 131: 201, 132: 209, 133: 214, 134: 220, 135: 225, 136: 224, 137: 226, 138: 228, 139: 1722, 140: 171, 141: 231, 142: 233, 143: 232, 144: 234, 145: 235, 146: 237, 147: 8230, 148: 238, 149: 239, 150: 241, 151: 243, 152: 187, 153: 244, 154: 246, 155: 247, 156: 250, 157: 249, 158: 251, 159: 252, 160: 32, 161: 33, 162: 34, 163: 35, 164: 36, 165: 1642, 166: 38, 167: 39, 168: 40, 169: 41, 170: 42, 171: 43, 172: 1548, 173: 45, 174: 46, 175: 47, 176: 1632, 177: 1633, 178: 1634, 179: 1635, 180: 1636, 181: 1637, 182: 1638, 183: 1639, 184: 1640, 185: 1641, 186: 58, 187: 1563, 188: 60, 189: 61, 190: 62, 191: 1567, 192: 10058, 193: 1569, 194: 1570, 195: 1571, 196: 1572, 197: 1573, 198: 1574, 199: 1575, 200: 1576, 201: 1577, 202: 1578, 203: 1579, 204: 1580, 205: 1581, 206: 1582, 207: 1583, 208: 1584, 209: 1585, 210: 1586, 211: 1587, 212: 1588, 213: 1589, 214: 1590, 215: 1591, 216: 1592, 217: 1593, 218: 1594, 219: 91, 220: 92, 221: 93, 222: 94, 223: 95, 224: 1600, 225: 1601, 226: 1602, 227: 1603, 228: 1604, 229: 1605, 230: 1606, 231: 1607, 232: 1608, 233: 1609, 234: 1610, 235: 1611, 236: 1612, 237: 1613, 238: 1614, 239: 1615, 240: 1616, 241: 1617, 242: 1618, 243: 1662, 244: 1657, 245: 1670, 246: 1749, 247: 1700, 248: 1711, 249: 1672, 250: 1681, 251: 123, 252: 124, 253: 125, 254: 1688, 255: 1746})