import osimport reimport sysfrom collections import dequefrom io import StringIO__all__ = ['shlex', 'split', 'quote']
class shlex:

    def __init__(self, instream=None, infile=None, posix=False, punctuation_chars=False):
        if isinstance(instream, str):
            instream = StringIO(instream)
        if instream is not None:
            self.instream = instream
            self.infile = infile
        else:
            self.instream = sys.stdin
            self.infile = None
        self.posix = posix
        if posix:
            self.eof = None
        else:
            self.eof = ''
        self.commenters = '#'
        self.wordchars = 'abcdfeghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
        if self.posix:
            self.wordchars += 'ßàáâãäåæçèéêëìíîïğñòóôõöøùúûüışÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏĞÑÒÓÔÕÖØÙÚÛÜİŞ'
        self.whitespace = ' \t\r\n'
        self.whitespace_split = False
        self.quotes = '\'"'
        self.escape = '\\'
        self.escapedquotes = '"'
        self.state = ' '
        self.pushback = deque()
        self.lineno = 1
        self.debug = 0
        self.token = ''
        self.filestack = deque()
        self.source = None
        if not punctuation_chars:
            punctuation_chars = ''
        elif punctuation_chars is True:
            punctuation_chars = '();<>|&'
        self.punctuation_chars = punctuation_chars
        if punctuation_chars:
            self._pushback_chars = deque()
            self.wordchars += '~-./*?='
            t = self.wordchars.maketrans(dict.fromkeys(punctuation_chars))
            self.wordchars = self.wordchars.translate(t)

    def push_token(self, tok):
        if self.debug >= 1:
            print('shlex: pushing token ' + repr(tok))
        self.pushback.appendleft(tok)

    def push_source(self, newstream, newfile=None):
        if isinstance(newstream, str):
            newstream = StringIO(newstream)
        self.filestack.appendleft((self.infile, self.instream, self.lineno))
        self.infile = newfile
        self.instream = newstream
        self.lineno = 1
        if self.debug:
            if newfile is not None:
                print('shlex: pushing to file %s' % (self.infile,))
            else:
                print('shlex: pushing to stream %s' % (self.instream,))

    def pop_source(self):
        self.instream.close()
        (self.infile, self.instream, self.lineno) = self.filestack.popleft()
        if self.debug:
            print('shlex: popping to %s, line %d' % (self.instream, self.lineno))
        self.state = ' '

    def get_token(self):
        if self.pushback:
            tok = self.pushback.popleft()
            if self.debug >= 1:
                print('shlex: popping token ' + repr(tok))
            return tok
        raw = self.read_token()
        if self.source is not None:
            while raw == self.source:
                spec = self.sourcehook(self.read_token())
                if spec:
                    (newfile, newstream) = spec
                    self.push_source(newstream, newfile)
                raw = self.get_token()
        if raw == self.eof:
            if not self.filestack:
                return self.eof
            self.pop_source()
            raw = self.get_token()
        if self.debug >= 1:
            if raw != self.eof:
                print('shlex: token=' + repr(raw))
            else:
                print('shlex: token=EOF')
        return raw

    def read_token(self):
        quoted = False
        escapedstate = ' '
        while True:
            if self.punctuation_chars and self._pushback_chars:
                nextchar = self._pushback_chars.pop()
            else:
                nextchar = self.instream.read(1)
            if nextchar == '\n':
                self.lineno += 1
            if self.debug >= 3:
                print('shlex: in state %r I see character: %r' % (self.state, nextchar))
            if self.state is None:
                self.token = ''
                break
            elif self.state == ' ':
                if not nextchar:
                    self.state = None
                    break
                else:
                    if nextchar in self.whitespace:
                        if self.debug >= 2:
                            print('shlex: I see whitespace in whitespace state')
                        if not self.token:
                            if self.posix and quoted:
                                break
                                if self.state in self.quotes:
                                    quoted = True
                                    if not nextchar:
                                        if self.debug >= 2:
                                            print('shlex: I see EOF in quotes state')
                                        raise ValueError('No closing quotation')
                                    if nextchar == self.state:
                                        if not self.posix:
                                            self.token += nextchar
                                            self.state = ' '
                                            break
                                        else:
                                            self.state = 'a'
                                    elif self.posix and nextchar in self.escape and self.state in self.escapedquotes:
                                        escapedstate = self.state
                                        self.state = nextchar
                                    else:
                                        self.token += nextchar
                                elif self.state in self.escape:
                                    if not nextchar:
                                        if self.debug >= 2:
                                            print('shlex: I see EOF in escape state')
                                        raise ValueError('No escaped character')
                                    if nextchar != escapedstate:
                                        self.token += self.state
                                    self.token += nextchar
                                    self.state = escapedstate
                                elif self.state in ('a', 'c'):
                                    if not nextchar:
                                        self.state = None
                                        break
                                    elif nextchar in self.whitespace:
                                        if self.debug >= 2:
                                            print('shlex: I see whitespace in word state')
                                        self.state = ' '
                                        if not self.token:
                                            if self.posix and quoted:
                                                break
                                                if nextchar in self.commenters:
                                                    self.instream.readline()
                                                    self.lineno += 1
                                                    if self.posix:
                                                        self.state = ' '
                                                        if not self.token:
                                                            if self.posix and quoted:
                                                                break
                                                                if self.state == 'c':
                                                                    if nextchar in self.punctuation_chars:
                                                                        self.token += nextchar
                                                                    else:
                                                                        if nextchar not in self.whitespace:
                                                                            self._pushback_chars.append(nextchar)
                                                                        self.state = ' '
                                                                        break
                                                                elif self.posix and nextchar in self.quotes:
                                                                    self.state = nextchar
                                                                elif self.posix and nextchar in self.escape:
                                                                    escapedstate = 'a'
                                                                    self.state = nextchar
                                                                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                                    self.token += nextchar
                                                                else:
                                                                    if self.punctuation_chars:
                                                                        self._pushback_chars.append(nextchar)
                                                                    else:
                                                                        self.pushback.appendleft(nextchar)
                                                                    if self.debug >= 2:
                                                                        print('shlex: I see punctuation in word state')
                                                                    self.state = ' '
                                                                    if (self.token or self.posix) and quoted:
                                                                        break
                                                        break
                                                        if self.state == 'c':
                                                            if nextchar in self.punctuation_chars:
                                                                self.token += nextchar
                                                            else:
                                                                if nextchar not in self.whitespace:
                                                                    self._pushback_chars.append(nextchar)
                                                                self.state = ' '
                                                                break
                                                        elif self.posix and nextchar in self.quotes:
                                                            self.state = nextchar
                                                        elif self.posix and nextchar in self.escape:
                                                            escapedstate = 'a'
                                                            self.state = nextchar
                                                        elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                            self.token += nextchar
                                                        else:
                                                            if self.punctuation_chars:
                                                                self._pushback_chars.append(nextchar)
                                                            else:
                                                                self.pushback.appendleft(nextchar)
                                                            if self.debug >= 2:
                                                                print('shlex: I see punctuation in word state')
                                                            self.state = ' '
                                                            if (self.token or self.posix) and quoted:
                                                                break
                                                elif self.state == 'c':
                                                    if nextchar in self.punctuation_chars:
                                                        self.token += nextchar
                                                    else:
                                                        if nextchar not in self.whitespace:
                                                            self._pushback_chars.append(nextchar)
                                                        self.state = ' '
                                                        break
                                                elif self.posix and nextchar in self.quotes:
                                                    self.state = nextchar
                                                elif self.posix and nextchar in self.escape:
                                                    escapedstate = 'a'
                                                    self.state = nextchar
                                                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                    self.token += nextchar
                                                else:
                                                    if self.punctuation_chars:
                                                        self._pushback_chars.append(nextchar)
                                                    else:
                                                        self.pushback.appendleft(nextchar)
                                                    if self.debug >= 2:
                                                        print('shlex: I see punctuation in word state')
                                                    self.state = ' '
                                                    if (self.token or self.posix) and quoted:
                                                        break
                                        break
                                    elif nextchar in self.commenters:
                                        self.instream.readline()
                                        self.lineno += 1
                                        if self.posix:
                                            self.state = ' '
                                            if not self.token:
                                                if self.posix and quoted:
                                                    break
                                                    if self.state == 'c':
                                                        if nextchar in self.punctuation_chars:
                                                            self.token += nextchar
                                                        else:
                                                            if nextchar not in self.whitespace:
                                                                self._pushback_chars.append(nextchar)
                                                            self.state = ' '
                                                            break
                                                    elif self.posix and nextchar in self.quotes:
                                                        self.state = nextchar
                                                    elif self.posix and nextchar in self.escape:
                                                        escapedstate = 'a'
                                                        self.state = nextchar
                                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                        self.token += nextchar
                                                    else:
                                                        if self.punctuation_chars:
                                                            self._pushback_chars.append(nextchar)
                                                        else:
                                                            self.pushback.appendleft(nextchar)
                                                        if self.debug >= 2:
                                                            print('shlex: I see punctuation in word state')
                                                        self.state = ' '
                                                        if (self.token or self.posix) and quoted:
                                                            break
                                            break
                                            if self.state == 'c':
                                                if nextchar in self.punctuation_chars:
                                                    self.token += nextchar
                                                else:
                                                    if nextchar not in self.whitespace:
                                                        self._pushback_chars.append(nextchar)
                                                    self.state = ' '
                                                    break
                                            elif self.posix and nextchar in self.quotes:
                                                self.state = nextchar
                                            elif self.posix and nextchar in self.escape:
                                                escapedstate = 'a'
                                                self.state = nextchar
                                            elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                self.token += nextchar
                                            else:
                                                if self.punctuation_chars:
                                                    self._pushback_chars.append(nextchar)
                                                else:
                                                    self.pushback.appendleft(nextchar)
                                                if self.debug >= 2:
                                                    print('shlex: I see punctuation in word state')
                                                self.state = ' '
                                                if (self.token or self.posix) and quoted:
                                                    break
                                    elif self.state == 'c':
                                        if nextchar in self.punctuation_chars:
                                            self.token += nextchar
                                        else:
                                            if nextchar not in self.whitespace:
                                                self._pushback_chars.append(nextchar)
                                            self.state = ' '
                                            break
                                    elif self.posix and nextchar in self.quotes:
                                        self.state = nextchar
                                    elif self.posix and nextchar in self.escape:
                                        escapedstate = 'a'
                                        self.state = nextchar
                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                        self.token += nextchar
                                    else:
                                        if self.punctuation_chars:
                                            self._pushback_chars.append(nextchar)
                                        else:
                                            self.pushback.appendleft(nextchar)
                                        if self.debug >= 2:
                                            print('shlex: I see punctuation in word state')
                                        self.state = ' '
                                        if (self.token or self.posix) and quoted:
                                            break
                        break
                    elif nextchar in self.commenters:
                        self.instream.readline()
                        self.lineno += 1
                    elif self.posix and nextchar in self.escape:
                        escapedstate = 'a'
                        self.state = nextchar
                    elif nextchar in self.wordchars:
                        self.token = nextchar
                        self.state = 'a'
                    elif nextchar in self.punctuation_chars:
                        self.token = nextchar
                        self.state = 'c'
                    elif nextchar in self.quotes:
                        if not self.posix:
                            self.token = nextchar
                        self.state = nextchar
                    elif self.whitespace_split:
                        self.token = nextchar
                        self.state = 'a'
                    else:
                        self.token = nextchar
                        if not self.token:
                            if self.posix and quoted:
                                break
                                if self.state in self.quotes:
                                    quoted = True
                                    if not nextchar:
                                        if self.debug >= 2:
                                            print('shlex: I see EOF in quotes state')
                                        raise ValueError('No closing quotation')
                                    if nextchar == self.state:
                                        if not self.posix:
                                            self.token += nextchar
                                            self.state = ' '
                                            break
                                        else:
                                            self.state = 'a'
                                    elif self.posix and nextchar in self.escape and self.state in self.escapedquotes:
                                        escapedstate = self.state
                                        self.state = nextchar
                                    else:
                                        self.token += nextchar
                                elif self.state in self.escape:
                                    if not nextchar:
                                        if self.debug >= 2:
                                            print('shlex: I see EOF in escape state')
                                        raise ValueError('No escaped character')
                                    if nextchar != escapedstate:
                                        self.token += self.state
                                    self.token += nextchar
                                    self.state = escapedstate
                                elif self.state in ('a', 'c'):
                                    if not nextchar:
                                        self.state = None
                                        break
                                    elif nextchar in self.whitespace:
                                        if self.debug >= 2:
                                            print('shlex: I see whitespace in word state')
                                        self.state = ' '
                                        if not self.token:
                                            if self.posix and quoted:
                                                break
                                                if nextchar in self.commenters:
                                                    self.instream.readline()
                                                    self.lineno += 1
                                                    if self.posix:
                                                        self.state = ' '
                                                        if not self.token:
                                                            if self.posix and quoted:
                                                                break
                                                                if self.state == 'c':
                                                                    if nextchar in self.punctuation_chars:
                                                                        self.token += nextchar
                                                                    else:
                                                                        if nextchar not in self.whitespace:
                                                                            self._pushback_chars.append(nextchar)
                                                                        self.state = ' '
                                                                        break
                                                                elif self.posix and nextchar in self.quotes:
                                                                    self.state = nextchar
                                                                elif self.posix and nextchar in self.escape:
                                                                    escapedstate = 'a'
                                                                    self.state = nextchar
                                                                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                                    self.token += nextchar
                                                                else:
                                                                    if self.punctuation_chars:
                                                                        self._pushback_chars.append(nextchar)
                                                                    else:
                                                                        self.pushback.appendleft(nextchar)
                                                                    if self.debug >= 2:
                                                                        print('shlex: I see punctuation in word state')
                                                                    self.state = ' '
                                                                    if (self.token or self.posix) and quoted:
                                                                        break
                                                        break
                                                        if self.state == 'c':
                                                            if nextchar in self.punctuation_chars:
                                                                self.token += nextchar
                                                            else:
                                                                if nextchar not in self.whitespace:
                                                                    self._pushback_chars.append(nextchar)
                                                                self.state = ' '
                                                                break
                                                        elif self.posix and nextchar in self.quotes:
                                                            self.state = nextchar
                                                        elif self.posix and nextchar in self.escape:
                                                            escapedstate = 'a'
                                                            self.state = nextchar
                                                        elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                            self.token += nextchar
                                                        else:
                                                            if self.punctuation_chars:
                                                                self._pushback_chars.append(nextchar)
                                                            else:
                                                                self.pushback.appendleft(nextchar)
                                                            if self.debug >= 2:
                                                                print('shlex: I see punctuation in word state')
                                                            self.state = ' '
                                                            if (self.token or self.posix) and quoted:
                                                                break
                                                elif self.state == 'c':
                                                    if nextchar in self.punctuation_chars:
                                                        self.token += nextchar
                                                    else:
                                                        if nextchar not in self.whitespace:
                                                            self._pushback_chars.append(nextchar)
                                                        self.state = ' '
                                                        break
                                                elif self.posix and nextchar in self.quotes:
                                                    self.state = nextchar
                                                elif self.posix and nextchar in self.escape:
                                                    escapedstate = 'a'
                                                    self.state = nextchar
                                                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                    self.token += nextchar
                                                else:
                                                    if self.punctuation_chars:
                                                        self._pushback_chars.append(nextchar)
                                                    else:
                                                        self.pushback.appendleft(nextchar)
                                                    if self.debug >= 2:
                                                        print('shlex: I see punctuation in word state')
                                                    self.state = ' '
                                                    if (self.token or self.posix) and quoted:
                                                        break
                                        break
                                    elif nextchar in self.commenters:
                                        self.instream.readline()
                                        self.lineno += 1
                                        if self.posix:
                                            self.state = ' '
                                            if not self.token:
                                                if self.posix and quoted:
                                                    break
                                                    if self.state == 'c':
                                                        if nextchar in self.punctuation_chars:
                                                            self.token += nextchar
                                                        else:
                                                            if nextchar not in self.whitespace:
                                                                self._pushback_chars.append(nextchar)
                                                            self.state = ' '
                                                            break
                                                    elif self.posix and nextchar in self.quotes:
                                                        self.state = nextchar
                                                    elif self.posix and nextchar in self.escape:
                                                        escapedstate = 'a'
                                                        self.state = nextchar
                                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                        self.token += nextchar
                                                    else:
                                                        if self.punctuation_chars:
                                                            self._pushback_chars.append(nextchar)
                                                        else:
                                                            self.pushback.appendleft(nextchar)
                                                        if self.debug >= 2:
                                                            print('shlex: I see punctuation in word state')
                                                        self.state = ' '
                                                        if (self.token or self.posix) and quoted:
                                                            break
                                            break
                                            if self.state == 'c':
                                                if nextchar in self.punctuation_chars:
                                                    self.token += nextchar
                                                else:
                                                    if nextchar not in self.whitespace:
                                                        self._pushback_chars.append(nextchar)
                                                    self.state = ' '
                                                    break
                                            elif self.posix and nextchar in self.quotes:
                                                self.state = nextchar
                                            elif self.posix and nextchar in self.escape:
                                                escapedstate = 'a'
                                                self.state = nextchar
                                            elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                self.token += nextchar
                                            else:
                                                if self.punctuation_chars:
                                                    self._pushback_chars.append(nextchar)
                                                else:
                                                    self.pushback.appendleft(nextchar)
                                                if self.debug >= 2:
                                                    print('shlex: I see punctuation in word state')
                                                self.state = ' '
                                                if (self.token or self.posix) and quoted:
                                                    break
                                    elif self.state == 'c':
                                        if nextchar in self.punctuation_chars:
                                            self.token += nextchar
                                        else:
                                            if nextchar not in self.whitespace:
                                                self._pushback_chars.append(nextchar)
                                            self.state = ' '
                                            break
                                    elif self.posix and nextchar in self.quotes:
                                        self.state = nextchar
                                    elif self.posix and nextchar in self.escape:
                                        escapedstate = 'a'
                                        self.state = nextchar
                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                        self.token += nextchar
                                    else:
                                        if self.punctuation_chars:
                                            self._pushback_chars.append(nextchar)
                                        else:
                                            self.pushback.appendleft(nextchar)
                                        if self.debug >= 2:
                                            print('shlex: I see punctuation in word state')
                                        self.state = ' '
                                        if (self.token or self.posix) and quoted:
                                            break
                        break
                    if self.state in self.quotes:
                        quoted = True
                        if not nextchar:
                            if self.debug >= 2:
                                print('shlex: I see EOF in quotes state')
                            raise ValueError('No closing quotation')
                        if nextchar == self.state:
                            if not self.posix:
                                self.token += nextchar
                                self.state = ' '
                                break
                            else:
                                self.state = 'a'
                        elif self.posix and nextchar in self.escape and self.state in self.escapedquotes:
                            escapedstate = self.state
                            self.state = nextchar
                        else:
                            self.token += nextchar
                    elif self.state in self.escape:
                        if not nextchar:
                            if self.debug >= 2:
                                print('shlex: I see EOF in escape state')
                            raise ValueError('No escaped character')
                        if nextchar != escapedstate:
                            self.token += self.state
                        self.token += nextchar
                        self.state = escapedstate
                    elif self.state in ('a', 'c'):
                        if not nextchar:
                            self.state = None
                            break
                        elif nextchar in self.whitespace:
                            if self.debug >= 2:
                                print('shlex: I see whitespace in word state')
                            self.state = ' '
                            if not self.token:
                                if self.posix and quoted:
                                    break
                                    if nextchar in self.commenters:
                                        self.instream.readline()
                                        self.lineno += 1
                                        if self.posix:
                                            self.state = ' '
                                            if not self.token:
                                                if self.posix and quoted:
                                                    break
                                                    if self.state == 'c':
                                                        if nextchar in self.punctuation_chars:
                                                            self.token += nextchar
                                                        else:
                                                            if nextchar not in self.whitespace:
                                                                self._pushback_chars.append(nextchar)
                                                            self.state = ' '
                                                            break
                                                    elif self.posix and nextchar in self.quotes:
                                                        self.state = nextchar
                                                    elif self.posix and nextchar in self.escape:
                                                        escapedstate = 'a'
                                                        self.state = nextchar
                                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                        self.token += nextchar
                                                    else:
                                                        if self.punctuation_chars:
                                                            self._pushback_chars.append(nextchar)
                                                        else:
                                                            self.pushback.appendleft(nextchar)
                                                        if self.debug >= 2:
                                                            print('shlex: I see punctuation in word state')
                                                        self.state = ' '
                                                        if (self.token or self.posix) and quoted:
                                                            break
                                            break
                                            if self.state == 'c':
                                                if nextchar in self.punctuation_chars:
                                                    self.token += nextchar
                                                else:
                                                    if nextchar not in self.whitespace:
                                                        self._pushback_chars.append(nextchar)
                                                    self.state = ' '
                                                    break
                                            elif self.posix and nextchar in self.quotes:
                                                self.state = nextchar
                                            elif self.posix and nextchar in self.escape:
                                                escapedstate = 'a'
                                                self.state = nextchar
                                            elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                self.token += nextchar
                                            else:
                                                if self.punctuation_chars:
                                                    self._pushback_chars.append(nextchar)
                                                else:
                                                    self.pushback.appendleft(nextchar)
                                                if self.debug >= 2:
                                                    print('shlex: I see punctuation in word state')
                                                self.state = ' '
                                                if (self.token or self.posix) and quoted:
                                                    break
                                    elif self.state == 'c':
                                        if nextchar in self.punctuation_chars:
                                            self.token += nextchar
                                        else:
                                            if nextchar not in self.whitespace:
                                                self._pushback_chars.append(nextchar)
                                            self.state = ' '
                                            break
                                    elif self.posix and nextchar in self.quotes:
                                        self.state = nextchar
                                    elif self.posix and nextchar in self.escape:
                                        escapedstate = 'a'
                                        self.state = nextchar
                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                        self.token += nextchar
                                    else:
                                        if self.punctuation_chars:
                                            self._pushback_chars.append(nextchar)
                                        else:
                                            self.pushback.appendleft(nextchar)
                                        if self.debug >= 2:
                                            print('shlex: I see punctuation in word state')
                                        self.state = ' '
                                        if (self.token or self.posix) and quoted:
                                            break
                            break
                        elif nextchar in self.commenters:
                            self.instream.readline()
                            self.lineno += 1
                            if self.posix:
                                self.state = ' '
                                if not self.token:
                                    if self.posix and quoted:
                                        break
                                        if self.state == 'c':
                                            if nextchar in self.punctuation_chars:
                                                self.token += nextchar
                                            else:
                                                if nextchar not in self.whitespace:
                                                    self._pushback_chars.append(nextchar)
                                                self.state = ' '
                                                break
                                        elif self.posix and nextchar in self.quotes:
                                            self.state = nextchar
                                        elif self.posix and nextchar in self.escape:
                                            escapedstate = 'a'
                                            self.state = nextchar
                                        elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                            self.token += nextchar
                                        else:
                                            if self.punctuation_chars:
                                                self._pushback_chars.append(nextchar)
                                            else:
                                                self.pushback.appendleft(nextchar)
                                            if self.debug >= 2:
                                                print('shlex: I see punctuation in word state')
                                            self.state = ' '
                                            if (self.token or self.posix) and quoted:
                                                break
                                break
                                if self.state == 'c':
                                    if nextchar in self.punctuation_chars:
                                        self.token += nextchar
                                    else:
                                        if nextchar not in self.whitespace:
                                            self._pushback_chars.append(nextchar)
                                        self.state = ' '
                                        break
                                elif self.posix and nextchar in self.quotes:
                                    self.state = nextchar
                                elif self.posix and nextchar in self.escape:
                                    escapedstate = 'a'
                                    self.state = nextchar
                                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                    self.token += nextchar
                                else:
                                    if self.punctuation_chars:
                                        self._pushback_chars.append(nextchar)
                                    else:
                                        self.pushback.appendleft(nextchar)
                                    if self.debug >= 2:
                                        print('shlex: I see punctuation in word state')
                                    self.state = ' '
                                    if (self.token or self.posix) and quoted:
                                        break
                        elif self.state == 'c':
                            if nextchar in self.punctuation_chars:
                                self.token += nextchar
                            else:
                                if nextchar not in self.whitespace:
                                    self._pushback_chars.append(nextchar)
                                self.state = ' '
                                break
                        elif self.posix and nextchar in self.quotes:
                            self.state = nextchar
                        elif self.posix and nextchar in self.escape:
                            escapedstate = 'a'
                            self.state = nextchar
                        elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                            self.token += nextchar
                        else:
                            if self.punctuation_chars:
                                self._pushback_chars.append(nextchar)
                            else:
                                self.pushback.appendleft(nextchar)
                            if self.debug >= 2:
                                print('shlex: I see punctuation in word state')
                            self.state = ' '
                            if (self.token or self.posix) and quoted:
                                break
            elif self.state in self.quotes:
                quoted = True
                if not nextchar:
                    if self.debug >= 2:
                        print('shlex: I see EOF in quotes state')
                    raise ValueError('No closing quotation')
                if nextchar == self.state:
                    if not self.posix:
                        self.token += nextchar
                        self.state = ' '
                        break
                    else:
                        self.state = 'a'
                elif self.posix and nextchar in self.escape and self.state in self.escapedquotes:
                    escapedstate = self.state
                    self.state = nextchar
                else:
                    self.token += nextchar
            elif self.state in self.escape:
                if not nextchar:
                    if self.debug >= 2:
                        print('shlex: I see EOF in escape state')
                    raise ValueError('No escaped character')
                if nextchar != escapedstate:
                    self.token += self.state
                self.token += nextchar
                self.state = escapedstate
            elif self.state in ('a', 'c'):
                if not nextchar:
                    self.state = None
                    break
                elif nextchar in self.whitespace:
                    if self.debug >= 2:
                        print('shlex: I see whitespace in word state')
                    self.state = ' '
                    if not self.token:
                        if self.posix and quoted:
                            break
                            if nextchar in self.commenters:
                                self.instream.readline()
                                self.lineno += 1
                                if self.posix:
                                    self.state = ' '
                                    if not self.token:
                                        if self.posix and quoted:
                                            break
                                            if self.state == 'c':
                                                if nextchar in self.punctuation_chars:
                                                    self.token += nextchar
                                                else:
                                                    if nextchar not in self.whitespace:
                                                        self._pushback_chars.append(nextchar)
                                                    self.state = ' '
                                                    break
                                            elif self.posix and nextchar in self.quotes:
                                                self.state = nextchar
                                            elif self.posix and nextchar in self.escape:
                                                escapedstate = 'a'
                                                self.state = nextchar
                                            elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                                self.token += nextchar
                                            else:
                                                if self.punctuation_chars:
                                                    self._pushback_chars.append(nextchar)
                                                else:
                                                    self.pushback.appendleft(nextchar)
                                                if self.debug >= 2:
                                                    print('shlex: I see punctuation in word state')
                                                self.state = ' '
                                                if (self.token or self.posix) and quoted:
                                                    break
                                    break
                                    if self.state == 'c':
                                        if nextchar in self.punctuation_chars:
                                            self.token += nextchar
                                        else:
                                            if nextchar not in self.whitespace:
                                                self._pushback_chars.append(nextchar)
                                            self.state = ' '
                                            break
                                    elif self.posix and nextchar in self.quotes:
                                        self.state = nextchar
                                    elif self.posix and nextchar in self.escape:
                                        escapedstate = 'a'
                                        self.state = nextchar
                                    elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                        self.token += nextchar
                                    else:
                                        if self.punctuation_chars:
                                            self._pushback_chars.append(nextchar)
                                        else:
                                            self.pushback.appendleft(nextchar)
                                        if self.debug >= 2:
                                            print('shlex: I see punctuation in word state')
                                        self.state = ' '
                                        if (self.token or self.posix) and quoted:
                                            break
                            elif self.state == 'c':
                                if nextchar in self.punctuation_chars:
                                    self.token += nextchar
                                else:
                                    if nextchar not in self.whitespace:
                                        self._pushback_chars.append(nextchar)
                                    self.state = ' '
                                    break
                            elif self.posix and nextchar in self.quotes:
                                self.state = nextchar
                            elif self.posix and nextchar in self.escape:
                                escapedstate = 'a'
                                self.state = nextchar
                            elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                self.token += nextchar
                            else:
                                if self.punctuation_chars:
                                    self._pushback_chars.append(nextchar)
                                else:
                                    self.pushback.appendleft(nextchar)
                                if self.debug >= 2:
                                    print('shlex: I see punctuation in word state')
                                self.state = ' '
                                if (self.token or self.posix) and quoted:
                                    break
                    break
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno += 1
                    if self.posix:
                        self.state = ' '
                        if not self.token:
                            if self.posix and quoted:
                                break
                                if self.state == 'c':
                                    if nextchar in self.punctuation_chars:
                                        self.token += nextchar
                                    else:
                                        if nextchar not in self.whitespace:
                                            self._pushback_chars.append(nextchar)
                                        self.state = ' '
                                        break
                                elif self.posix and nextchar in self.quotes:
                                    self.state = nextchar
                                elif self.posix and nextchar in self.escape:
                                    escapedstate = 'a'
                                    self.state = nextchar
                                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                                    self.token += nextchar
                                else:
                                    if self.punctuation_chars:
                                        self._pushback_chars.append(nextchar)
                                    else:
                                        self.pushback.appendleft(nextchar)
                                    if self.debug >= 2:
                                        print('shlex: I see punctuation in word state')
                                    self.state = ' '
                                    if (self.token or self.posix) and quoted:
                                        break
                        break
                        if self.state == 'c':
                            if nextchar in self.punctuation_chars:
                                self.token += nextchar
                            else:
                                if nextchar not in self.whitespace:
                                    self._pushback_chars.append(nextchar)
                                self.state = ' '
                                break
                        elif self.posix and nextchar in self.quotes:
                            self.state = nextchar
                        elif self.posix and nextchar in self.escape:
                            escapedstate = 'a'
                            self.state = nextchar
                        elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                            self.token += nextchar
                        else:
                            if self.punctuation_chars:
                                self._pushback_chars.append(nextchar)
                            else:
                                self.pushback.appendleft(nextchar)
                            if self.debug >= 2:
                                print('shlex: I see punctuation in word state')
                            self.state = ' '
                            if (self.token or self.posix) and quoted:
                                break
                elif self.state == 'c':
                    if nextchar in self.punctuation_chars:
                        self.token += nextchar
                    else:
                        if nextchar not in self.whitespace:
                            self._pushback_chars.append(nextchar)
                        self.state = ' '
                        break
                elif self.posix and nextchar in self.quotes:
                    self.state = nextchar
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif nextchar in self.wordchars or nextchar in self.quotes or self.whitespace_split:
                    self.token += nextchar
                else:
                    if self.punctuation_chars:
                        self._pushback_chars.append(nextchar)
                    else:
                        self.pushback.appendleft(nextchar)
                    if self.debug >= 2:
                        print('shlex: I see punctuation in word state')
                    self.state = ' '
                    if (self.token or self.posix) and quoted:
                        break
        result = self.token
        self.token = ''
        if result == '':
            result = None
        if self.posix and (quoted or self.debug > 1):
            if result:
                print('shlex: raw token=' + repr(result))
            else:
                print('shlex: raw token=EOF')
        return result

    def sourcehook(self, newfile):
        if newfile[0] == '"':
            newfile = newfile[1:-1]
        if not os.path.isabs(newfile):
            newfile = os.path.join(os.path.dirname(self.infile), newfile)
        return (newfile, open(newfile, 'r'))

    def error_leader(self, infile=None, lineno=None):
        if infile is None:
            infile = self.infile
        if lineno is None:
            lineno = self.lineno
        return '"%s", line %d: ' % (infile, lineno)

    def __iter__(self):
        return self

    def __next__(self):
        token = self.get_token()
        if token == self.eof:
            raise StopIteration
        return token

def split(s, comments=False, posix=True):
    lex = shlex(s, posix=posix)
    lex.whitespace_split = True
    if not comments:
        lex.commenters = ''
    return list(lex)
_find_unsafe = re.compile('[^\\w@%+=:,./-]', re.ASCII).search
def quote(s):
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s
    return "'" + s.replace("'", '\'"\'"\'') + "'"

def _print_tokens(lexer):
    while True:
        tt = lexer.get_token()
        if not tt:
            break
        print('Token: ' + repr(tt))
if __name__ == '__main__':
    if len(sys.argv) == 1:
        _print_tokens(shlex())
    else:
        fn = sys.argv[1]
        with open(fn) as f:
            _print_tokens(shlex(f, fn))