import collectionsimport urllib.parseimport urllib.request__all__ = ['RobotFileParser']RequestRate = collections.namedtuple('RequestRate', 'requests seconds')
class RobotFileParser:

    def __init__(self, url=''):
        self.entries = []
        self.default_entry = None
        self.disallow_all = False
        self.allow_all = False
        self.set_url(url)
        self.last_checked = 0

    def mtime(self):
        return self.last_checked

    def modified(self):
        import time
        self.last_checked = time.time()

    def set_url(self, url):
        self.url = url
        (self.host, self.path) = urllib.parse.urlparse(url)[1:3]

    def read(self):
        try:
            f = urllib.request.urlopen(self.url)
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                self.disallow_all = True
            elif err.code < 500:
                self.allow_all = True
        raw = f.read()
        self.parse(raw.decode('utf-8').splitlines())

    def _add_entry(self, entry):
        if '*' in entry.useragents:
            if self.default_entry is None:
                self.default_entry = entry
        else:
            self.entries.append(entry)

    def parse(self, lines):
        state = 0
        entry = Entry()
        self.modified()
        for line in lines:
            if not line:
                if state == 1:
                    entry = Entry()
                    state = 0
                elif state == 2:
                    self._add_entry(entry)
                    entry = Entry()
                    state = 0
            i = line.find('#')
            if i >= 0:
                line = line[:i]
            line = line.strip()
            if not line:
                pass
            else:
                line = line.split(':', 1)
                if len(line) == 2:
                    line[0] = line[0].strip().lower()
                    line[1] = urllib.parse.unquote(line[1].strip())
                    if line[0] == 'user-agent':
                        if state == 2:
                            self._add_entry(entry)
                            entry = Entry()
                        entry.useragents.append(line[1])
                        state = 1
                    elif line[0] == 'disallow':
                        if state != 0:
                            entry.rulelines.append(RuleLine(line[1], False))
                            state = 2
                            if line[0] == 'allow':
                                if state != 0:
                                    entry.rulelines.append(RuleLine(line[1], True))
                                    state = 2
                                    if line[0] == 'crawl-delay':
                                        if state != 0:
                                            if line[1].strip().isdigit():
                                                entry.delay = int(line[1])
                                            state = 2
                                            if line[0] == 'request-rate' and state != 0:
                                                numbers = line[1].split('/')
                                                if numbers[1].strip().isdigit():
                                                    entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                                state = 2
                                    elif line[0] == 'request-rate' and state != 0:
                                        numbers = line[1].split('/')
                                        if numbers[1].strip().isdigit():
                                            entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                        state = 2
                            elif line[0] == 'crawl-delay':
                                if state != 0:
                                    if line[1].strip().isdigit():
                                        entry.delay = int(line[1])
                                    state = 2
                                    if line[0] == 'request-rate' and state != 0:
                                        numbers = line[1].split('/')
                                        if numbers[1].strip().isdigit():
                                            entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                        state = 2
                            elif line[0] == 'request-rate' and state != 0:
                                numbers = line[1].split('/')
                                if numbers[1].strip().isdigit():
                                    entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                state = 2
                    elif line[0] == 'allow':
                        if state != 0:
                            entry.rulelines.append(RuleLine(line[1], True))
                            state = 2
                            if line[0] == 'crawl-delay':
                                if state != 0:
                                    if line[1].strip().isdigit():
                                        entry.delay = int(line[1])
                                    state = 2
                                    if line[0] == 'request-rate' and state != 0:
                                        numbers = line[1].split('/')
                                        if numbers[1].strip().isdigit():
                                            entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                        state = 2
                            elif line[0] == 'request-rate' and state != 0:
                                numbers = line[1].split('/')
                                if numbers[1].strip().isdigit():
                                    entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                state = 2
                    elif line[0] == 'crawl-delay':
                        if state != 0:
                            if line[1].strip().isdigit():
                                entry.delay = int(line[1])
                            state = 2
                            if line[0] == 'request-rate' and state != 0:
                                numbers = line[1].split('/')
                                if numbers[1].strip().isdigit():
                                    entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                                state = 2
                    elif line[0] == 'request-rate' and state != 0:
                        numbers = line[1].split('/')
                        if numbers[1].strip().isdigit():
                            entry.req_rate = RequestRate(int(numbers[0]), int(numbers[1]))
                        state = 2
        if state == 2:
            self._add_entry(entry)

    def can_fetch(self, useragent, url):
        if self.disallow_all:
            return False
        if self.allow_all:
            return True
        if not self.last_checked:
            return False
        parsed_url = urllib.parse.urlparse(urllib.parse.unquote(url))
        url = urllib.parse.urlunparse(('', '', parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))
        url = urllib.parse.quote(url)
        if not url:
            url = '/'
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.allowance(url)
        if self.default_entry:
            return self.default_entry.allowance(url)
        return True

    def crawl_delay(self, useragent):
        if not self.mtime():
            return
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.delay
        return self.default_entry.delay

    def request_rate(self, useragent):
        if not self.mtime():
            return
        for entry in self.entries:
            if entry.applies_to(useragent):
                return entry.req_rate
        return self.default_entry.req_rate

    def __str__(self):
        entries = self.entries
        if self.default_entry is not None:
            entries = entries + [self.default_entry]
        return '\n'.join(map(str, entries)) + '\n'

class RuleLine:

    def __init__(self, path, allowance):
        if not allowance:
            allowance = True
        path = urllib.parse.urlunparse(urllib.parse.urlparse(path))
        self.path = urllib.parse.quote(path)
        self.allowance = allowance

    def applies_to(self, filename):
        return self.path == '*' or filename.startswith(self.path)

    def __str__(self):
        return ('Allow' if self.allowance else 'Disallow') + ': ' + self.path

class Entry:

    def __init__(self):
        self.useragents = []
        self.rulelines = []
        self.delay = None
        self.req_rate = None

    def __str__(self):
        ret = []
        for agent in self.useragents:
            ret.append(f'User-agent: {agent}')
        if self.delay is not None:
            ret.append(f'Crawl-delay: {self.delay}')
        if self.req_rate is not None:
            rate = self.req_rate
            ret.append(f'Request-rate: {rate.requests}/{rate.seconds}')
        ret.extend(map(str, self.rulelines))
        ret.append('')
        return '\n'.join(ret)

    def applies_to(self, useragent):
        useragent = useragent.split('/')[0].lower()
        for agent in self.useragents:
            if agent == '*':
                return True
            agent = agent.lower()
            if agent in useragent:
                return True
        return False

    def allowance(self, filename):
        for line in self.rulelines:
            if line.applies_to(filename):
                return line.allowance
        return True
