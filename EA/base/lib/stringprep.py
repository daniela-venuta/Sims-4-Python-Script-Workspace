from unicodedata import ucd_3_2_0 as unicodedata
def in_table_a1(code):
    if unicodedata.category(code) != 'Cn':
        return False
    c = ord(code)
    if 64976 <= c and c < 65008:
        return False
    return c & 65535 not in (65534, 65535)
b1_set = set([173, 847, 6150, 6155, 6156, 6157, 8203, 8204, 8205, 8288, 65279] + list(range(65024, 65040)))
def in_table_b1(code):
    return ord(code) in b1_set
