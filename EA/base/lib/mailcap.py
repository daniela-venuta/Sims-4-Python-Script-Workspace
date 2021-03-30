import osimport warnings__all__ = ['getcaps', 'findmatch']
def lineno_sort_key(entry):
    if 'lineno' in entry:
        return (0, entry['lineno'])
    else:
        return (1, 0)

def getcaps():
    caps = {}
    lineno = 0
    for mailcap in listmailcapfiles():
        try:
            fp = open(mailcap, 'r')
        except OSError:
            continue
        with fp:
            (morecaps, lineno) = _readmailcapfile(fp, lineno)
        for (key, value) in morecaps.items():
            if key not in caps:
                caps[key] = value
            else:
                caps[key] = caps[key] + value
    return caps

def listmailcapfiles():
    if 'MAILCAPS' in os.environ:
        pathstr = os.environ['MAILCAPS']
        mailcaps = pathstr.split(os.pathsep)
    else:
        if 'HOME' in os.environ:
            home = os.environ['HOME']
        else:
            home = '.'
        mailcaps = [home + '/.mailcap', '/etc/mailcap', '/usr/etc/mailcap', '/usr/local/etc/mailcap']
    return mailcaps

def readmailcapfile(fp):
    warnings.warn('readmailcapfile is deprecated, use getcaps instead', DeprecationWarning, 2)
    (caps, _) = _readmailcapfile(fp, None)
    return caps

def _readmailcapfile(fp, lineno):
    caps = {}
    while True:
        line = fp.readline()
        if not line:
            break
        if not line[0] == '#':
            if line.strip() == '':
                pass
            else:
                nextline = line
                while nextline[-2:] == '\\\n':
                    nextline = fp.readline()
                    if not nextline:
                        nextline = '\n'
                    line = line[:-2] + nextline
                (key, fields) = parseline(line)
                if key:
                    if not fields:
                        pass
                    else:
                        if lineno is not None:
                            fields['lineno'] = lineno
                            lineno += 1
                        types = key.split('/')
                        for j in range(len(types)):
                            types[j] = types[j].strip()
                        key = '/'.join(types).lower()
                        if key in caps:
                            caps[key].append(fields)
                        else:
                            caps[key] = [fields]
    return (caps, lineno)

def parseline(line):
    fields = []
    i = 0
    n = len(line)
    while i < n:
        (field, i) = parsefield(line, i, n)
        fields.append(field)
        i = i + 1
    if len(fields) < 2:
        return (None, None)
    key = fields[0]
    view = fields[1]
    rest = fields[2:]
    fields = {'view': view}
    for field in rest:
        i = field.find('=')
        if i < 0:
            fkey = field
            fvalue = ''
        else:
            fkey = field[:i].strip()
            fvalue = field[i + 1:].strip()
        if fkey in fields:
            pass
        else:
            fields[fkey] = fvalue
    return (key, fields)

def parsefield(line, i, n):
    start = i
    while i < n:
        c = line[i]
        if c == ';':
            break
        elif c == '\\':
            i = i + 2
        else:
            i = i + 1
    return (line[start:i].strip(), i)

def findmatch(caps, MIMEtype, key='view', filename='/dev/null', plist=[]):
    entries = lookup(caps, MIMEtype, key)
    for e in entries:
        if 'test' in e:
            test = subst(e['test'], filename, plist)
            if test and os.system(test) != 0:
                pass
            else:
                command = subst(e[key], MIMEtype, filename, plist)
                return (command, e)
        else:
            command = subst(e[key], MIMEtype, filename, plist)
            return (command, e)
    return (None, None)

def lookup(caps, MIMEtype, key=None):
    entries = []
    if MIMEtype in caps:
        entries = entries + caps[MIMEtype]
    MIMEtypes = MIMEtype.split('/')
    MIMEtype = MIMEtypes[0] + '/*'
    if MIMEtype in caps:
        entries = entries + caps[MIMEtype]
    if key is not None:
        entries = [e for e in entries if key in e]
    entries = sorted(entries, key=lineno_sort_key)
    return entries

def subst(field, MIMEtype, filename, plist=[]):
    res = ''
    i = 0
    n = len(field)
    while i < n:
        c = field[i]
        i = i + 1
        if c != '%':
            if c == '\\':
                c = field[i:i + 1]
                i = i + 1
            res = res + c
        else:
            c = field[i]
            i = i + 1
            if c == '%':
                res = res + c
            elif c == 's':
                res = res + filename
            elif c == 't':
                res = res + MIMEtype
            elif c == '{':
                start = i
                while i < n and field[i] != '}':
                    i = i + 1
                name = field[start:i]
                i = i + 1
                res = res + findparam(name, plist)
            else:
                res = res + '%' + c
    return res

def findparam(name, plist):
    name = name.lower() + '='
    n = len(name)
    for p in plist:
        if p[:n].lower() == name:
            return p[n:]
    return ''

def test():
    import sys
    caps = getcaps()
    if not sys.argv[1:]:
        show(caps)
        return
    for i in range(1, len(sys.argv), 2):
        args = sys.argv[i:i + 2]
        if len(args) < 2:
            print('usage: mailcap [MIMEtype file] ...')
            return
        MIMEtype = args[0]
        file = args[1]
        (command, e) = findmatch(caps, MIMEtype, 'view', file)
        if not command:
            print('No viewer found for', type)
        else:
            print('Executing:', command)
            sts = os.system(command)
            if sts:
                print('Exit status:', sts)

def show(caps):
    print('Mailcap files:')
    for fn in listmailcapfiles():
        print('\t' + fn)
    print()
    if not caps:
        caps = getcaps()
    print('Mailcap entries:')
    print()
    ckeys = sorted(caps)
    for type in ckeys:
        print(type)
        entries = caps[type]
        for e in entries:
            keys = sorted(e)
            for k in keys:
                print('  %-15s' % k, e[k])
            print()
if __name__ == '__main__':
    test()