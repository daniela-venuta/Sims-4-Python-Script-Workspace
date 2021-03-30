__all__ = ['Parser', 'HeaderParser', 'BytesParser', 'BytesHeaderParser', 'FeedParser', 'BytesFeedParser']from io import StringIO, TextIOWrapperfrom email.feedparser import FeedParser, BytesFeedParserfrom email._policybase import compat32
class Parser:

    def __init__(self, _class=None, *, policy=compat32):
        self._class = _class
        self.policy = policy

    def parse(self, fp, headersonly=False):
        feedparser = FeedParser(self._class, policy=self.policy)
        if headersonly:
            feedparser._set_headersonly()
        while True:
            data = fp.read(8192)
            if not data:
                break
            feedparser.feed(data)
        return feedparser.close()

    def parsestr(self, text, headersonly=False):
        return self.parse(StringIO(text), headersonly=headersonly)

class HeaderParser(Parser):

    def parse(self, fp, headersonly=True):
        return Parser.parse(self, fp, True)

    def parsestr(self, text, headersonly=True):
        return Parser.parsestr(self, text, True)

class BytesParser:

    def __init__(self, *args, **kw):
        self.parser = Parser(*args, **kw)

    def parse(self, fp, headersonly=False):
        fp = TextIOWrapper(fp, encoding='ascii', errors='surrogateescape')
        try:
            return self.parser.parse(fp, headersonly)
        finally:
            fp.detach()

    def parsebytes(self, text, headersonly=False):
        text = text.decode('ASCII', errors='surrogateescape')
        return self.parser.parsestr(text, headersonly)

class BytesHeaderParser(BytesParser):

    def parse(self, fp, headersonly=True):
        return BytesParser.parse(self, fp, headersonly=True)

    def parsebytes(self, text, headersonly=True):
        return BytesParser.parsebytes(self, text, headersonly=True)
