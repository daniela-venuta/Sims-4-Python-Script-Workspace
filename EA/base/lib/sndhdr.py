__all__ = ['what', 'whathdr']from collections import namedtupleSndHeaders = namedtuple('SndHeaders', 'filetype framerate nchannels nframes sampwidth')SndHeaders.filetype.__doc__ = "The value for type indicates the data type\nand will be one of the strings 'aifc', 'aiff', 'au','hcom',\n'sndr', 'sndt', 'voc', 'wav', '8svx', 'sb', 'ub', or 'ul'."SndHeaders.framerate.__doc__ = 'The sampling_rate will be either the actual\nvalue or 0 if unknown or difficult to decode.'SndHeaders.nchannels.__doc__ = 'The number of channels or 0 if it cannot be\ndetermined or if the value is difficult to decode.'SndHeaders.nframes.__doc__ = 'The value for frames will be either the number\nof frames or -1.'SndHeaders.sampwidth.__doc__ = "Either the sample size in bits or\n'A' for A-LAW or 'U' for u-LAW."
def what(filename):
    res = whathdr(filename)
    return res

def whathdr(filename):
    with open(filename, 'rb') as f:
        h = f.read(512)
        for tf in tests:
            res = tf(h, f)
            if res:
                return SndHeaders(*res)
        return
tests = []
def test_aifc(h, f):
    import aifc
    if not h.startswith(b'FORM'):
        return
    if h[8:12] == b'AIFC':
        fmt = 'aifc'
    elif h[8:12] == b'AIFF':
        fmt = 'aiff'
    else:
        return
    f.seek(0)
    try:
        a = aifc.open(f, 'r')
    except (EOFError, aifc.Error):
        return
    return (fmt, a.getframerate(), a.getnchannels(), a.getnframes(), 8*a.getsampwidth())
tests.append(test_aifc)
def test_au(h, f):
    if h.startswith(b'.snd'):
        func = get_long_be
    elif h[:4] in (b'\x00ds.', b'dns.'):
        func = get_long_le
    else:
        return
    filetype = 'au'
    hdr_size = func(h[4:8])
    data_size = func(h[8:12])
    encoding = func(h[12:16])
    rate = func(h[16:20])
    nchannels = func(h[20:24])
    sample_size = 1
    if encoding == 1:
        sample_bits = 'U'
    elif encoding == 2:
        sample_bits = 8
    elif encoding == 3:
        sample_bits = 16
        sample_size = 2
    else:
        sample_bits = '?'
    frame_size = sample_size*nchannels
    if frame_size:
        nframe = data_size/frame_size
    else:
        nframe = -1
    return (filetype, rate, nchannels, nframe, sample_bits)
tests.append(test_au)
def test_hcom(h, f):
    if h[65:69] != b'FSSD' or h[128:132] != b'HCOM':
        return
    divisor = get_long_be(h[144:148])
    if divisor:
        rate = 22050/divisor
    else:
        rate = 0
    return ('hcom', rate, 1, -1, 8)
tests.append(test_hcom)