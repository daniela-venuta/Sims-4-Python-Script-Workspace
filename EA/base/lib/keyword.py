__all__ = ['iskeyword', 'kwlist']kwlist = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']iskeyword = frozenset(kwlist).__contains__
def main():
    import sys
    import re
    args = sys.argv[1:]
    if args:
        pass
    iptfile = 'Python/graminit.c'
    if len(args) > 1:
        optfile = args[1]
    else:
        optfile = 'Lib/keyword.py'
    with open(optfile, newline='') as fp:
        format = fp.readlines()
    nl = format[0][len(format[0].strip()):] if format else '\n'
    with open(iptfile) as fp:
        strprog = re.compile('"([^"]+)"')
        lines = []
        for line in fp:
            if '{1, "' in line:
                match = strprog.search(line)
                if match:
                    lines.append("        '" + match.group(1) + "'," + nl)
    lines.sort()
    try:
        start = format.index('#--start keywords--' + nl) + 1
        end = format.index('#--end keywords--' + nl)
        format[start:end] = lines
    except ValueError:
        sys.stderr.write('target does not contain format markers\n')
        sys.exit(1)
    with open(optfile, 'w', newline='') as fp:
        fp.writelines(format)
if __name__ == '__main__':
    main()