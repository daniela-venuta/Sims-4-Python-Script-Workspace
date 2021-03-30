import reimport urllibfrom string import hexdigitsfrom collections import OrderedDictfrom operator import itemgetterfrom email import _encoded_words as _ewfrom email import errorsfrom email import utilsWSP = set(' \t')CFWS_LEADER = WSP | set('(')SPECIALS = set('()<>@,:;.\\"[]')ATOM_ENDS = SPECIALS | WSPDOT_ATOM_ENDS = ATOM_ENDS - set('.')PHRASE_ENDS = SPECIALS - set('."(')TSPECIALS = (SPECIALS | set('/?=')) - set('.')TOKEN_ENDS = TSPECIALS | WSPASPECIALS = TSPECIALS | set("*'%")ATTRIBUTE_ENDS = ASPECIALS | WSPEXTENDED_ATTRIBUTE_ENDS = ATTRIBUTE_ENDS - set('%')
def quote_string(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'

class TokenList(list):
    token_type = None
    syntactic_break = True
    ew_combine_allowed = True

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.defects = []

    def __str__(self):
        return ''.join(str(x) for x in self)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super().__repr__())

    @property
    def value(self):
        return ''.join(x.value for x in self if x.value)

    @property
    def all_defects(self):
        return sum((x.all_defects for x in self), self.defects)

    def startswith_fws(self):
        return self[0].startswith_fws()

    @property
    def as_ew_allowed(self):
        return all(part.as_ew_allowed for part in self)

    @property
    def comments(self):
        comments = []
        for token in self:
            comments.extend(token.comments)
        return comments

    def fold(self, *, policy):
        return _refold_parse_tree(self, policy=policy)

    def pprint(self, indent=''):
        print(self.ppstr(indent=indent))

    def ppstr(self, indent=''):
        return '\n'.join(self._pp(indent=indent))

    def _pp(self, indent=''):
        yield '{}{}/{}('.format(indent, self.__class__.__name__, self.token_type)
        for token in self:
            if not hasattr(token, '_pp'):
                yield indent + '    !! invalid element in token list: {!r}'.format(token)
            else:
                yield from token._pp(indent + '    ')
        if self.defects:
            extra = ' Defects: {}'.format(self.defects)
        else:
            extra = ''
        yield '{}){}'.format(indent, extra)

class WhiteSpaceTokenList(TokenList):

    @property
    def value(self):
        return ' '

    @property
    def comments(self):
        return [x.content for x in self if x.token_type == 'comment']

class UnstructuredTokenList(TokenList):
    token_type = 'unstructured'

class Phrase(TokenList):
    token_type = 'phrase'

class Word(TokenList):
    token_type = 'word'

class CFWSList(WhiteSpaceTokenList):
    token_type = 'cfws'

class Atom(TokenList):
    token_type = 'atom'

class Token(TokenList):
    token_type = 'token'
    encode_as_ew = False

class EncodedWord(TokenList):
    token_type = 'encoded-word'
    cte = None
    charset = None
    lang = None

class QuotedString(TokenList):
    token_type = 'quoted-string'

    @property
    def content(self):
        for x in self:
            if x.token_type == 'bare-quoted-string':
                return x.value

    @property
    def quoted_value(self):
        res = []
        for x in self:
            if x.token_type == 'bare-quoted-string':
                res.append(str(x))
            else:
                res.append(x.value)
        return ''.join(res)

    @property
    def stripped_value(self):
        for token in self:
            if token.token_type == 'bare-quoted-string':
                return token.value

class BareQuotedString(QuotedString):
    token_type = 'bare-quoted-string'

    def __str__(self):
        return quote_string(''.join(str(x) for x in self))

    @property
    def value(self):
        return ''.join(str(x) for x in self)

class Comment(WhiteSpaceTokenList):
    token_type = 'comment'

    def __str__(self):
        return ''.join(sum([['('], [self.quote(x) for x in self], [')']], []))

    def quote(self, value):
        if value.token_type == 'comment':
            return str(value)
        return str(value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    @property
    def content(self):
        return ''.join(str(x) for x in self)

    @property
    def comments(self):
        return [self.content]

class AddressList(TokenList):
    token_type = 'address-list'

    @property
    def addresses(self):
        return [x for x in self if x.token_type == 'address']

    @property
    def mailboxes(self):
        return sum((x.mailboxes for x in self if x.token_type == 'address'), [])

    @property
    def all_mailboxes(self):
        return sum((x.all_mailboxes for x in self if x.token_type == 'address'), [])

class Address(TokenList):
    token_type = 'address'

    @property
    def display_name(self):
        if self[0].token_type == 'group':
            return self[0].display_name

    @property
    def mailboxes(self):
        if self[0].token_type == 'mailbox':
            return [self[0]]
        if self[0].token_type == 'invalid-mailbox':
            return []
        return self[0].mailboxes

    @property
    def all_mailboxes(self):
        if self[0].token_type == 'mailbox':
            return [self[0]]
        if self[0].token_type == 'invalid-mailbox':
            return [self[0]]
        return self[0].all_mailboxes

class MailboxList(TokenList):
    token_type = 'mailbox-list'

    @property
    def mailboxes(self):
        return [x for x in self if x.token_type == 'mailbox']

    @property
    def all_mailboxes(self):
        return [x for x in self if x.token_type in ('mailbox', 'invalid-mailbox')]

class GroupList(TokenList):
    token_type = 'group-list'

    @property
    def mailboxes(self):
        if self and self[0].token_type != 'mailbox-list':
            return []
        return self[0].mailboxes

    @property
    def all_mailboxes(self):
        if self and self[0].token_type != 'mailbox-list':
            return []
        return self[0].all_mailboxes

class Group(TokenList):
    token_type = 'group'

    @property
    def mailboxes(self):
        if self[2].token_type != 'group-list':
            return []
        return self[2].mailboxes

    @property
    def all_mailboxes(self):
        if self[2].token_type != 'group-list':
            return []
        return self[2].all_mailboxes

    @property
    def display_name(self):
        return self[0].display_name

class NameAddr(TokenList):
    token_type = 'name-addr'

    @property
    def display_name(self):
        if len(self) == 1:
            return
        return self[0].display_name

    @property
    def local_part(self):
        return self[-1].local_part

    @property
    def domain(self):
        return self[-1].domain

    @property
    def route(self):
        return self[-1].route

    @property
    def addr_spec(self):
        return self[-1].addr_spec

class AngleAddr(TokenList):
    token_type = 'angle-addr'

    @property
    def local_part(self):
        for x in self:
            if x.token_type == 'addr-spec':
                return x.local_part

    @property
    def domain(self):
        for x in self:
            if x.token_type == 'addr-spec':
                return x.domain

    @property
    def route(self):
        for x in self:
            if x.token_type == 'obs-route':
                return x.domains

    @property
    def addr_spec(self):
        for x in self:
            if x.token_type == 'addr-spec':
                if x.local_part:
                    return x.addr_spec
                return quote_string(x.local_part) + x.addr_spec
        return '<>'

class ObsRoute(TokenList):
    token_type = 'obs-route'

    @property
    def domains(self):
        return [x.domain for x in self if x.token_type == 'domain']

class Mailbox(TokenList):
    token_type = 'mailbox'

    @property
    def display_name(self):
        if self[0].token_type == 'name-addr':
            return self[0].display_name

    @property
    def local_part(self):
        return self[0].local_part

    @property
    def domain(self):
        return self[0].domain

    @property
    def route(self):
        if self[0].token_type == 'name-addr':
            return self[0].route

    @property
    def addr_spec(self):
        return self[0].addr_spec

class InvalidMailbox(TokenList):
    token_type = 'invalid-mailbox'

    @property
    def display_name(self):
        pass

    local_part = domain = route = addr_spec = display_name

class Domain(TokenList):
    token_type = 'domain'
    as_ew_allowed = False

    @property
    def domain(self):
        return ''.join(super().value.split())

class DotAtom(TokenList):
    token_type = 'dot-atom'

class DotAtomText(TokenList):
    token_type = 'dot-atom-text'
    as_ew_allowed = True

class AddrSpec(TokenList):
    token_type = 'addr-spec'
    as_ew_allowed = False

    @property
    def local_part(self):
        return self[0].local_part

    @property
    def domain(self):
        if len(self) < 3:
            return
        return self[-1].domain

    @property
    def value(self):
        if len(self) < 3:
            return self[0].value
        return self[0].value.rstrip() + self[1].value + self[2].value.lstrip()

    @property
    def addr_spec(self):
        nameset = set(self.local_part)
        if len(nameset) > len(nameset - DOT_ATOM_ENDS):
            lp = quote_string(self.local_part)
        else:
            lp = self.local_part
        if self.domain is not None:
            return lp + '@' + self.domain
        return lp

class ObsLocalPart(TokenList):
    token_type = 'obs-local-part'
    as_ew_allowed = False

class DisplayName(Phrase):
    token_type = 'display-name'
    ew_combine_allowed = False

    @property
    def display_name(self):
        res = TokenList(self)
        if res[0].token_type == 'cfws':
            res.pop(0)
        elif res[0][0].token_type == 'cfws':
            res[0] = TokenList(res[0][1:])
        if res[-1].token_type == 'cfws':
            res.pop()
        elif res[-1][-1].token_type == 'cfws':
            res[-1] = TokenList(res[-1][:-1])
        return res.value

    @property
    def value(self):
        quote = False
        if self.defects:
            quote = True
        else:
            for x in self:
                if x.token_type == 'quoted-string':
                    quote = True
        if quote:
            pre = post = ''
            if self[0].token_type == 'cfws' or self[0][0].token_type == 'cfws':
                pre = ' '
            if self[-1].token_type == 'cfws' or self[-1][-1].token_type == 'cfws':
                post = ' '
            return pre + quote_string(self.display_name) + post
        else:
            return super().value

class LocalPart(TokenList):
    token_type = 'local-part'
    as_ew_allowed = False

    @property
    def value(self):
        if self[0].token_type == 'quoted-string':
            return self[0].quoted_value
        else:
            return self[0].value

    @property
    def local_part(self):
        res = [DOT]
        last = DOT
        last_is_tl = False
        for tok in self[0] + [DOT]:
            if tok.token_type == 'cfws':
                pass
            else:
                if last[-1].token_type == 'cfws':
                    res[-1] = TokenList(last[:-1])
                is_tl = isinstance(tok, TokenList)
                if last_is_tl and tok.token_type == 'dot' and is_tl and last.token_type == 'dot' and tok[0].token_type == 'cfws':
                    res.append(TokenList(tok[1:]))
                else:
                    res.append(tok)
                last = res[-1]
                last_is_tl = is_tl
        res = TokenList(res[1:-1])
        return res.value

class DomainLiteral(TokenList):
    token_type = 'domain-literal'
    as_ew_allowed = False

    @property
    def domain(self):
        return ''.join(super().value.split())

    @property
    def ip(self):
        for x in self:
            if x.token_type == 'ptext':
                return x.value

class MIMEVersion(TokenList):
    token_type = 'mime-version'
    major = None
    minor = None

class Parameter(TokenList):
    token_type = 'parameter'
    sectioned = False
    extended = False
    charset = 'us-ascii'

    @property
    def section_number(self):
        if self.sectioned:
            return self[1].number
        return 0

    @property
    def param_value(self):
        for token in self:
            if token.token_type == 'value':
                return token.stripped_value
            if token.token_type == 'quoted-string':
                for token in token:
                    if token.token_type == 'bare-quoted-string':
                        for token in token:
                            if token.token_type == 'value':
                                return token.stripped_value
        return ''

class InvalidParameter(Parameter):
    token_type = 'invalid-parameter'

class Attribute(TokenList):
    token_type = 'attribute'

    @property
    def stripped_value(self):
        for token in self:
            if token.token_type.endswith('attrtext'):
                return token.value

class Section(TokenList):
    token_type = 'section'
    number = None

class Value(TokenList):
    token_type = 'value'

    @property
    def stripped_value(self):
        token = self[0]
        if token.token_type == 'cfws':
            token = self[1]
        if token.token_type.endswith(('quoted-string', 'attribute', 'extended-attribute')):
            return token.stripped_value
        return self.value

class MimeParameters(TokenList):
    token_type = 'mime-parameters'
    syntactic_break = False

    @property
    def params(self):
        params = OrderedDict()
        for token in self:
            if not token.token_type.endswith('parameter'):
                pass
            elif token[0].token_type != 'attribute':
                pass
            else:
                name = token[0].value.strip()
                params[name] = []
                params[name].append((token.section_number, token))
        for (name, parts) in params.items():
            parts = sorted(parts, key=itemgetter(0))
            first_param = parts[0][1]
            charset = first_param.charset
            parts[1][1].defects.append(errors.InvalidHeaderDefect('duplicate parameter name; duplicate(s) ignored'))
            parts = parts[:1]
            value_parts = []
            i = 0
            for (section_number, param) in parts:
                if section_number != i:
                    if not param.extended:
                        param.defects.append(errors.InvalidHeaderDefect('duplicate parameter name; duplicate ignored'))
                    else:
                        param.defects.append(errors.InvalidHeaderDefect('inconsistent RFC2231 parameter numbering'))
                i += 1
                value = param.param_value
                if param.extended:
                    try:
                        value = urllib.parse.unquote_to_bytes(value)
                    except UnicodeEncodeError:
                        value = urllib.parse.unquote(value, encoding='latin-1')
                    try:
                        value = value.decode(charset, 'surrogateescape')
                    except LookupError:
                        value = value.decode('us-ascii', 'surrogateescape')
                    if utils._has_surrogates(value):
                        param.defects.append(errors.UndecodableBytesDefect())
                value_parts.append(value)
            value = ''.join(value_parts)
            yield (name, value)

    def __str__(self):
        params = []
        for (name, value) in self.params:
            if value:
                params.append('{}={}'.format(name, quote_string(value)))
            else:
                params.append(name)
        params = '; '.join(params)
        if params:
            return ' ' + params
        return ''

class ParameterizedHeaderValue(TokenList):
    syntactic_break = False

    @property
    def params(self):
        for token in reversed(self):
            if token.token_type == 'mime-parameters':
                return token.params
        return {}

class ContentType(ParameterizedHeaderValue):
    token_type = 'content-type'
    as_ew_allowed = False
    maintype = 'text'
    subtype = 'plain'

class ContentDisposition(ParameterizedHeaderValue):
    token_type = 'content-disposition'
    as_ew_allowed = False
    content_disposition = None

class ContentTransferEncoding(TokenList):
    token_type = 'content-transfer-encoding'
    as_ew_allowed = False
    cte = '7bit'

class HeaderLabel(TokenList):
    token_type = 'header-label'
    as_ew_allowed = False

class Header(TokenList):
    token_type = 'header'

class Terminal(str):
    as_ew_allowed = True
    ew_combine_allowed = True
    syntactic_break = True

    def __new__(cls, value, token_type):
        self = super().__new__(cls, value)
        self.token_type = token_type
        self.defects = []
        return self

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super().__repr__())

    def pprint(self):
        print(self.__class__.__name__ + '/' + self.token_type)

    @property
    def all_defects(self):
        return list(self.defects)

    def _pp(self, indent=''):
        return ['{}{}/{}({}){}'.format(indent, self.__class__.__name__, self.token_type, super().__repr__(), '' if not self.defects else ' {}'.format(self.defects))]

    def pop_trailing_ws(self):
        pass

    @property
    def comments(self):
        return []

    def __getnewargs__(self):
        return (str(self), self.token_type)

class WhiteSpaceTerminal(Terminal):

    @property
    def value(self):
        return ' '

    def startswith_fws(self):
        return True

class ValueTerminal(Terminal):

    @property
    def value(self):
        return self

    def startswith_fws(self):
        return False

class EWWhiteSpaceTerminal(WhiteSpaceTerminal):

    @property
    def value(self):
        return ''

    def __str__(self):
        return ''
DOT = ValueTerminal('.', 'dot')ListSeparator = ValueTerminal(',', 'list-separator')RouteComponentMarker = ValueTerminal('@', 'route-component-marker')_wsp_splitter = re.compile('([{}]+)'.format(''.join(WSP))).split_non_atom_end_matcher = re.compile('[^{}]+'.format(re.escape(''.join(ATOM_ENDS)))).match_non_printable_finder = re.compile('[\\x00-\\x20\\x7F]').findall_non_token_end_matcher = re.compile('[^{}]+'.format(re.escape(''.join(TOKEN_ENDS)))).match_non_attribute_end_matcher = re.compile('[^{}]+'.format(re.escape(''.join(ATTRIBUTE_ENDS)))).match_non_extended_attribute_end_matcher = re.compile('[^{}]+'.format(re.escape(''.join(EXTENDED_ATTRIBUTE_ENDS)))).match
def _validate_xtext(xtext):
    non_printables = _non_printable_finder(xtext)
    if non_printables:
        xtext.defects.append(errors.NonPrintableDefect(non_printables))
    if utils._has_surrogates(xtext):
        xtext.defects.append(errors.UndecodableBytesDefect('Non-ASCII characters found in header token'))

def _get_ptext_to_endchars(value, endchars):
    (fragment, *remainder) = _wsp_splitter(value, 1)
    vchars = []
    escape = False
    had_qp = False
    for pos in range(len(fragment)):
        if fragment[pos] == '\\':
            if escape:
                escape = False
                had_qp = True
            else:
                escape = True
        else:
            if escape:
                escape = False
            elif fragment[pos] in endchars:
                break
            vchars.append(fragment[pos])
    pos = pos + 1
    return (''.join(vchars), ''.join([fragment[pos:]] + remainder), had_qp)

def get_fws(value):
    newvalue = value.lstrip()
    fws = WhiteSpaceTerminal(value[:len(value) - len(newvalue)], 'fws')
    return (fws, newvalue)

def get_encoded_word(value):
    ew = EncodedWord()
    if not value.startswith('=?'):
        raise errors.HeaderParseError('expected encoded word but found {}'.format(value))
    (tok, *remainder) = value[2:].split('?=', 1)
    if tok == value[2:]:
        raise errors.HeaderParseError('expected encoded word but found {}'.format(value))
    remstr = ''.join(remainder)
    if remstr[1] in hexdigits:
        (rest, *remainder) = remstr.split('?=', 1)
        tok = tok + '?=' + rest
    if len(remstr) > 1 and remstr[0] in hexdigits and len(tok.split()) > 1:
        ew.defects.append(errors.InvalidHeaderDefect('whitespace inside encoded word'))
    ew.cte = value
    value = ''.join(remainder)
    try:
        (text, charset, lang, defects) = _ew.decode('=?' + tok + '?=')
    except ValueError:
        raise errors.HeaderParseError("encoded word format invalid: '{}'".format(ew.cte))
    ew.charset = charset
    ew.lang = lang
    ew.defects.extend(defects)
    if text:
        if text[0] in WSP:
            (token, text) = get_fws(text)
            ew.append(token)
        else:
            (chars, *remainder) = _wsp_splitter(text, 1)
            vtext = ValueTerminal(chars, 'vtext')
            _validate_xtext(vtext)
            ew.append(vtext)
            text = ''.join(remainder)
    return (ew, value)

def get_unstructured(value):
    unstructured = UnstructuredTokenList()
    if value:
        if value[0] in WSP:
            (token, value) = get_fws(value)
            unstructured.append(token)
        elif value.startswith('=?'):
            try:
                (token, value) = get_encoded_word(value)
            except errors.HeaderParseError:
                pass
            have_ws = True
            if unstructured[-1].token_type != 'fws':
                unstructured.defects.append(errors.InvalidHeaderDefect('missing whitespace before encoded word'))
                have_ws = False
            if unstructured[-2].token_type == 'encoded-word':
                unstructured[-1] = EWWhiteSpaceTerminal(unstructured[-1], 'fws')
            unstructured.append(token)
        else:
            (tok, *remainder) = _wsp_splitter(value, 1)
            vtext = ValueTerminal(tok, 'vtext')
            _validate_xtext(vtext)
            unstructured.append(vtext)
            value = ''.join(remainder)
    return unstructured

def get_qp_ctext(value):
    (ptext, value, _) = _get_ptext_to_endchars(value, '()')
    ptext = WhiteSpaceTerminal(ptext, 'ptext')
    _validate_xtext(ptext)
    return (ptext, value)

def get_qcontent(value):
    (ptext, value, _) = _get_ptext_to_endchars(value, '"')
    ptext = ValueTerminal(ptext, 'ptext')
    _validate_xtext(ptext)
    return (ptext, value)

def get_atext(value):
    m = _non_atom_end_matcher(value)
    if not m:
        raise errors.HeaderParseError("expected atext but found '{}'".format(value))
    atext = m.group()
    value = value[len(atext):]
    atext = ValueTerminal(atext, 'atext')
    _validate_xtext(atext)
    return (atext, value)

def get_bare_quoted_string(value):
    if value[0] != '"':
        raise errors.HeaderParseError('expected \'"\' but found \'{}\''.format(value))
    bare_quoted_string = BareQuotedString()
    value = value[1:]
    if value[0] == '"':
        (token, value) = get_qcontent(value)
        bare_quoted_string.append(token)
    if value[0] != '"':
        if value[0] in WSP:
            (token, value) = get_fws(value)
        elif value[:2] == '=?':
            try:
                (token, value) = get_encoded_word(value)
                bare_quoted_string.defects.append(errors.InvalidHeaderDefect('encoded word inside quoted string'))
            except errors.HeaderParseError:
                (token, value) = get_qcontent(value)
        else:
            (token, value) = get_qcontent(value)
        bare_quoted_string.append(token)
    if not (value and value):
        bare_quoted_string.defects.append(errors.InvalidHeaderDefect('end of header inside quoted string'))
        return (bare_quoted_string, value)
    return (bare_quoted_string, value[1:])

def get_comment(value):
    if value and value[0] != '(':
        raise errors.HeaderParseError("expected '(' but found '{}'".format(value))
    comment = Comment()
    value = value[1:]
    if value[0] != ')':
        if value[0] in WSP:
            (token, value) = get_fws(value)
        elif value[0] == '(':
            (token, value) = get_comment(value)
        else:
            (token, value) = get_qp_ctext(value)
        comment.append(token)
    if not (value and value):
        comment.defects.append(errors.InvalidHeaderDefect('end of header inside comment'))
        return (comment, value)
    return (comment, value[1:])

def get_cfws(value):
    cfws = CFWSList()
    if value[0] in CFWS_LEADER:
        if value[0] in WSP:
            (token, value) = get_fws(value)
        else:
            (token, value) = get_comment(value)
        cfws.append(token)
    return (cfws, value)

def get_quoted_string(value):
    quoted_string = QuotedString()
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        quoted_string.append(token)
    (token, value) = get_bare_quoted_string(value)
    quoted_string.append(token)
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        quoted_string.append(token)
    return (quoted_string, value)

def get_atom(value):
    atom = Atom()
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        atom.append(token)
    if value and value[0] in ATOM_ENDS:
        raise errors.HeaderParseError("expected atom but found '{}'".format(value))
    if value.startswith('=?'):
        try:
            (token, value) = get_encoded_word(value)
        except errors.HeaderParseError:
            (token, value) = get_atext(value)
    else:
        (token, value) = get_atext(value)
    atom.append(token)
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        atom.append(token)
    return (atom, value)

def get_dot_atom_text(value):
    dot_atom_text = DotAtomText()
    if value and value[0] in ATOM_ENDS:
        raise errors.HeaderParseError("expected atom at a start of dot-atom-text but found '{}'".format(value))
    while value and value[0] not in ATOM_ENDS:
        (token, value) = get_atext(value)
        dot_atom_text.append(token)
        if value and value[0] == '.':
            dot_atom_text.append(DOT)
            value = value[1:]
    if dot_atom_text[-1] is DOT:
        raise errors.HeaderParseError("expected atom at end of dot-atom-text but found '{}'".format('.' + value))
    return (dot_atom_text, value)

def get_dot_atom(value):
    dot_atom = DotAtom()
    if value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        dot_atom.append(token)
    if value.startswith('=?'):
        try:
            (token, value) = get_encoded_word(value)
        except errors.HeaderParseError:
            (token, value) = get_dot_atom_text(value)
    else:
        (token, value) = get_dot_atom_text(value)
    dot_atom.append(token)
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        dot_atom.append(token)
    return (dot_atom, value)

def get_word(value):
    if value[0] in CFWS_LEADER:
        (leader, value) = get_cfws(value)
    else:
        leader = None
    if value[0] == '"':
        (token, value) = get_quoted_string(value)
    elif value[0] in SPECIALS:
        raise errors.HeaderParseError("Expected 'atom' or 'quoted-string' but found '{}'".format(value))
    else:
        (token, value) = get_atom(value)
    if leader is not None:
        token[:0] = [leader]
    return (token, value)

def get_phrase(value):
    phrase = Phrase()
    try:
        (token, value) = get_word(value)
        phrase.append(token)
    except errors.HeaderParseError:
        phrase.defects.append(errors.InvalidHeaderDefect('phrase does not start with word'))
    if value[0] not in PHRASE_ENDS:
        if value[0] == '.':
            phrase.append(DOT)
            phrase.defects.append(errors.ObsoleteHeaderDefect("period in 'phrase'"))
            value = value[1:]
        else:
            try:
                (token, value) = get_word(value)
            except errors.HeaderParseError:
                if value[0] in CFWS_LEADER:
                    (token, value) = get_cfws(value)
                    phrase.defects.append(errors.ObsoleteHeaderDefect('comment found without atom'))
                else:
                    raise
            phrase.append(token)
    return (phrase, value)

def get_local_part(value):
    local_part = LocalPart()
    leader = None
    if value[0] in CFWS_LEADER:
        (leader, value) = get_cfws(value)
    if not value:
        raise errors.HeaderParseError("expected local-part but found '{}'".format(value))
    try:
        (token, value) = get_dot_atom(value)
    except errors.HeaderParseError:
        try:
            (token, value) = get_word(value)
        except errors.HeaderParseError:
            if value[0] != '\\' and value[0] in PHRASE_ENDS:
                raise
            token = TokenList()
    if leader is not None:
        token[:0] = [leader]
    local_part.append(token)
    if value[0] == '\\' or value[0] not in PHRASE_ENDS:
        (obs_local_part, value) = get_obs_local_part(str(local_part) + value)
        if obs_local_part.token_type == 'invalid-obs-local-part':
            local_part.defects.append(errors.InvalidHeaderDefect('local-part is not dot-atom, quoted-string, or obs-local-part'))
        else:
            local_part.defects.append(errors.ObsoleteHeaderDefect('local-part is not a dot-atom (contains CFWS)'))
        local_part[0] = obs_local_part
    try:
        local_part.value.encode('ascii')
    except UnicodeEncodeError:
        local_part.defects.append(errors.NonASCIILocalPartDefect('local-part contains non-ASCII characters)'))
    return (local_part, value)

def get_obs_local_part(value):
    obs_local_part = ObsLocalPart()
    last_non_ws_was_dot = False
    if value[0] == '\\' or value[0] not in PHRASE_ENDS:
        if value[0] == '.':
            if last_non_ws_was_dot:
                obs_local_part.defects.append(errors.InvalidHeaderDefect("invalid repeated '.'"))
            obs_local_part.append(DOT)
            last_non_ws_was_dot = True
            value = value[1:]
        elif value[0] == '\\':
            obs_local_part.append(ValueTerminal(value[0], 'misplaced-special'))
            value = value[1:]
            obs_local_part.defects.append(errors.InvalidHeaderDefect("'\\' character outside of quoted-string/ccontent"))
            last_non_ws_was_dot = False
        else:
            if obs_local_part and obs_local_part[-1].token_type != 'dot':
                obs_local_part.defects.append(errors.InvalidHeaderDefect("missing '.' between words"))
            try:
                (token, value) = get_word(value)
                last_non_ws_was_dot = False
            except errors.HeaderParseError:
                if value[0] not in CFWS_LEADER:
                    raise
                (token, value) = get_cfws(value)
            obs_local_part.append(token)
        if obs_local_part and obs_local_part[-1].token_type != 'dot':
            obs_local_part.defects.append(errors.InvalidHeaderDefect("missing '.' between words"))
        try:
            (token, value) = get_word(value)
            last_non_ws_was_dot = False
        except errors.HeaderParseError:
            if value[0] not in CFWS_LEADER:
                raise
            (token, value) = get_cfws(value)
        obs_local_part.append(token)
    if value and obs_local_part[0].token_type == 'dot' or obs_local_part[0].token_type == 'cfws' and obs_local_part[1].token_type == 'dot':
        obs_local_part.defects.append(errors.InvalidHeaderDefect("Invalid leading '.' in local part"))
    if obs_local_part[-1].token_type == 'dot' or obs_local_part[-1].token_type == 'cfws' and obs_local_part[-2].token_type == 'dot':
        obs_local_part.defects.append(errors.InvalidHeaderDefect("Invalid trailing '.' in local part"))
    if obs_local_part.defects:
        obs_local_part.token_type = 'invalid-obs-local-part'
    return (obs_local_part, value)

def get_dtext(value):
    (ptext, value, had_qp) = _get_ptext_to_endchars(value, '[]')
    ptext = ValueTerminal(ptext, 'ptext')
    if had_qp:
        ptext.defects.append(errors.ObsoleteHeaderDefect('quoted printable found in domain-literal'))
    _validate_xtext(ptext)
    return (ptext, value)

def _check_for_early_dl_end(value, domain_literal):
    if value:
        return False
    domain_literal.append(errors.InvalidHeaderDefect('end of input inside domain-literal'))
    domain_literal.append(ValueTerminal(']', 'domain-literal-end'))
    return True

def get_domain_literal(value):
    domain_literal = DomainLiteral()
    if value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        domain_literal.append(token)
    if not value:
        raise errors.HeaderParseError('expected domain-literal')
    if value[0] != '[':
        raise errors.HeaderParseError("expected '[' at start of domain-literal but found '{}'".format(value))
    value = value[1:]
    if _check_for_early_dl_end(value, domain_literal):
        return (domain_literal, value)
    domain_literal.append(ValueTerminal('[', 'domain-literal-start'))
    if value[0] in WSP:
        (token, value) = get_fws(value)
        domain_literal.append(token)
    (token, value) = get_dtext(value)
    domain_literal.append(token)
    if _check_for_early_dl_end(value, domain_literal):
        return (domain_literal, value)
    if value[0] in WSP:
        (token, value) = get_fws(value)
        domain_literal.append(token)
    if _check_for_early_dl_end(value, domain_literal):
        return (domain_literal, value)
    if value[0] != ']':
        raise errors.HeaderParseError("expected ']' at end of domain-literal but found '{}'".format(value))
    domain_literal.append(ValueTerminal(']', 'domain-literal-end'))
    value = value[1:]
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        domain_literal.append(token)
    return (domain_literal, value)

def get_domain(value):
    domain = Domain()
    leader = None
    if value[0] in CFWS_LEADER:
        (leader, value) = get_cfws(value)
    if not value:
        raise errors.HeaderParseError("expected domain but found '{}'".format(value))
    if value[0] == '[':
        (token, value) = get_domain_literal(value)
        if leader is not None:
            token[:0] = [leader]
        domain.append(token)
        return (domain, value)
    try:
        (token, value) = get_dot_atom(value)
    except errors.HeaderParseError:
        (token, value) = get_atom(value)
    if leader is not None:
        token[:0] = [leader]
    domain.append(token)
    if value[0] == '.':
        domain.defects.append(errors.ObsoleteHeaderDefect('domain is not a dot-atom (contains CFWS)'))
        if domain[0].token_type == 'dot-atom':
            domain[:] = domain[0]
        while value and value[0] == '.':
            domain.append(DOT)
            (token, value) = get_atom(value[1:])
            domain.append(token)
    return (domain, value)

def get_addr_spec(value):
    addr_spec = AddrSpec()
    (token, value) = get_local_part(value)
    addr_spec.append(token)
    if value and value[0] != '@':
        addr_spec.defects.append(errors.InvalidHeaderDefect('add-spec local part with no domain'))
        return (addr_spec, value)
    addr_spec.append(ValueTerminal('@', 'address-at-symbol'))
    (token, value) = get_domain(value[1:])
    addr_spec.append(token)
    return (addr_spec, value)

def get_obs_route(value):
    obs_route = ObsRoute()
    if value[0] == ',' or value[0] in CFWS_LEADER:
        if value[0] in CFWS_LEADER:
            (token, value) = get_cfws(value)
            obs_route.append(token)
        elif value[0] == ',':
            obs_route.append(ListSeparator)
            value = value[1:]
    if value and value and value[0] != '@':
        raise errors.HeaderParseError("expected obs-route domain but found '{}'".format(value))
    obs_route.append(RouteComponentMarker)
    (token, value) = get_domain(value[1:])
    obs_route.append(token)
    while value and value[0] == ',':
        obs_route.append(ListSeparator)
        value = value[1:]
        if not value:
            break
        if value[0] in CFWS_LEADER:
            (token, value) = get_cfws(value)
            obs_route.append(token)
        if value[0] == '@':
            obs_route.append(RouteComponentMarker)
            (token, value) = get_domain(value[1:])
            obs_route.append(token)
    if not value:
        raise errors.HeaderParseError('end of header while parsing obs-route')
    if value[0] != ':':
        raise errors.HeaderParseError("expected ':' marking end of obs-route but found '{}'".format(value))
    obs_route.append(ValueTerminal(':', 'end-of-obs-route-marker'))
    return (obs_route, value[1:])

def get_angle_addr(value):
    angle_addr = AngleAddr()
    if value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        angle_addr.append(token)
    if value and value[0] != '<':
        raise errors.HeaderParseError("expected angle-addr but found '{}'".format(value))
    angle_addr.append(ValueTerminal('<', 'angle-addr-start'))
    value = value[1:]
    if value[0] == '>':
        angle_addr.append(ValueTerminal('>', 'angle-addr-end'))
        angle_addr.defects.append(errors.InvalidHeaderDefect('null addr-spec in angle-addr'))
        value = value[1:]
        return (angle_addr, value)
    try:
        (token, value) = get_addr_spec(value)
    except errors.HeaderParseError:
        try:
            (token, value) = get_obs_route(value)
            angle_addr.defects.append(errors.ObsoleteHeaderDefect('obsolete route specification in angle-addr'))
        except errors.HeaderParseError:
            raise errors.HeaderParseError("expected addr-spec or obs-route but found '{}'".format(value))
        angle_addr.append(token)
        (token, value) = get_addr_spec(value)
    angle_addr.append(token)
    if value and value[0] == '>':
        value = value[1:]
    else:
        angle_addr.defects.append(errors.InvalidHeaderDefect("missing trailing '>' on angle-addr"))
    angle_addr.append(ValueTerminal('>', 'angle-addr-end'))
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        angle_addr.append(token)
    return (angle_addr, value)

def get_display_name(value):
    display_name = DisplayName()
    (token, value) = get_phrase(value)
    display_name.extend(token[:])
    display_name.defects = token.defects[:]
    return (display_name, value)

def get_name_addr(value):
    name_addr = NameAddr()
    leader = None
    if value[0] in CFWS_LEADER:
        (leader, value) = get_cfws(value)
        if not value:
            raise errors.HeaderParseError("expected name-addr but found '{}'".format(leader))
    if value[0] != '<':
        if value[0] in PHRASE_ENDS:
            raise errors.HeaderParseError("expected name-addr but found '{}'".format(value))
        (token, value) = get_display_name(value)
        if not value:
            raise errors.HeaderParseError("expected name-addr but found '{}'".format(token))
        if leader is not None:
            token[0][:0] = [leader]
            leader = None
        name_addr.append(token)
    (token, value) = get_angle_addr(value)
    if leader is not None:
        token[:0] = [leader]
    name_addr.append(token)
    return (name_addr, value)

def get_mailbox(value):
    mailbox = Mailbox()
    try:
        (token, value) = get_name_addr(value)
    except errors.HeaderParseError:
        try:
            (token, value) = get_addr_spec(value)
        except errors.HeaderParseError:
            raise errors.HeaderParseError("expected mailbox but found '{}'".format(value))
    if any(isinstance(x, errors.InvalidHeaderDefect) for x in token.all_defects):
        mailbox.token_type = 'invalid-mailbox'
    mailbox.append(token)
    return (mailbox, value)

def get_invalid_mailbox(value, endchars):
    invalid_mailbox = InvalidMailbox()
    if value[0] not in endchars:
        if value[0] in PHRASE_ENDS:
            invalid_mailbox.append(ValueTerminal(value[0], 'misplaced-special'))
            value = value[1:]
        else:
            (token, value) = get_phrase(value)
            invalid_mailbox.append(token)
    return (invalid_mailbox, value)

def get_mailbox_list(value):
    mailbox_list = MailboxList()
    while value and value[0] != ';':
        try:
            (token, value) = get_mailbox(value)
            mailbox_list.append(token)
        except errors.HeaderParseError:
            leader = None
            if value[0] in CFWS_LEADER:
                (leader, value) = get_cfws(value)
                if value and value[0] in ',;':
                    mailbox_list.append(leader)
                    mailbox_list.defects.append(errors.ObsoleteHeaderDefect('empty element in mailbox-list'))
                else:
                    (token, value) = get_invalid_mailbox(value, ',;')
                    if leader is not None:
                        token[:0] = [leader]
                    mailbox_list.append(token)
                    mailbox_list.defects.append(errors.InvalidHeaderDefect('invalid mailbox in mailbox-list'))
            elif value[0] == ',':
                mailbox_list.defects.append(errors.ObsoleteHeaderDefect('empty element in mailbox-list'))
            else:
                (token, value) = get_invalid_mailbox(value, ',;')
                if leader is not None:
                    token[:0] = [leader]
                mailbox_list.append(token)
                mailbox_list.defects.append(errors.InvalidHeaderDefect('invalid mailbox in mailbox-list'))
        if value and value[0] not in ',;':
            mailbox = mailbox_list[-1]
            mailbox.token_type = 'invalid-mailbox'
            (token, value) = get_invalid_mailbox(value, ',;')
            mailbox.extend(token)
            mailbox_list.defects.append(errors.InvalidHeaderDefect('invalid mailbox in mailbox-list'))
        if value and value[0] == ',':
            mailbox_list.append(ListSeparator)
            value = value[1:]
    return (mailbox_list, value)

def get_group_list(value):
    group_list = GroupList()
    if not value:
        group_list.defects.append(errors.InvalidHeaderDefect('end of header before group-list'))
        return (group_list, value)
    leader = None
    if value and value[0] in CFWS_LEADER:
        (leader, value) = get_cfws(value)
        if not value:
            group_list.defects.append(errors.InvalidHeaderDefect('end of header in group-list'))
            group_list.append(leader)
            return (group_list, value)
        if value[0] == ';':
            group_list.append(leader)
            return (group_list, value)
    (token, value) = get_mailbox_list(value)
    if len(token.all_mailboxes) == 0:
        if leader is not None:
            group_list.append(leader)
        group_list.extend(token)
        group_list.defects.append(errors.ObsoleteHeaderDefect('group-list with empty entries'))
        return (group_list, value)
    if leader is not None:
        token[:0] = [leader]
    group_list.append(token)
    return (group_list, value)

def get_group(value):
    group = Group()
    (token, value) = get_display_name(value)
    if value and value[0] != ':':
        raise errors.HeaderParseError("expected ':' at end of group display name but found '{}'".format(value))
    group.append(token)
    group.append(ValueTerminal(':', 'group-display-name-terminator'))
    value = value[1:]
    if value and value[0] == ';':
        group.append(ValueTerminal(';', 'group-terminator'))
        return (group, value[1:])
    (token, value) = get_group_list(value)
    group.append(token)
    if not value:
        group.defects.append(errors.InvalidHeaderDefect('end of header in group'))
    if value[0] != ';':
        raise errors.HeaderParseError("expected ';' at end of group but found {}".format(value))
    group.append(ValueTerminal(';', 'group-terminator'))
    value = value[1:]
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        group.append(token)
    return (group, value)

def get_address(value):
    address = Address()
    try:
        (token, value) = get_group(value)
    except errors.HeaderParseError:
        try:
            (token, value) = get_mailbox(value)
        except errors.HeaderParseError:
            raise errors.HeaderParseError("expected address but found '{}'".format(value))
    address.append(token)
    return (address, value)

def get_address_list(value):
    address_list = AddressList()
    while value:
        try:
            (token, value) = get_address(value)
            address_list.append(token)
        except errors.HeaderParseError as err:
            leader = None
            if value[0] in CFWS_LEADER:
                (leader, value) = get_cfws(value)
                if value and value[0] == ',':
                    address_list.append(leader)
                    address_list.defects.append(errors.ObsoleteHeaderDefect('address-list entry with no content'))
                else:
                    (token, value) = get_invalid_mailbox(value, ',')
                    if leader is not None:
                        token[:0] = [leader]
                    address_list.append(Address([token]))
                    address_list.defects.append(errors.InvalidHeaderDefect('invalid address in address-list'))
            elif value[0] == ',':
                address_list.defects.append(errors.ObsoleteHeaderDefect('empty element in address-list'))
            else:
                (token, value) = get_invalid_mailbox(value, ',')
                if leader is not None:
                    token[:0] = [leader]
                address_list.append(Address([token]))
                address_list.defects.append(errors.InvalidHeaderDefect('invalid address in address-list'))
        if value and value[0] != ',':
            mailbox = address_list[-1][0]
            mailbox.token_type = 'invalid-mailbox'
            (token, value) = get_invalid_mailbox(value, ',')
            mailbox.extend(token)
            address_list.defects.append(errors.InvalidHeaderDefect('invalid address in address-list'))
        if value:
            address_list.append(ValueTerminal(',', 'list-separator'))
            value = value[1:]
    return (address_list, value)

def parse_mime_version(value):
    mime_version = MIMEVersion()
    if not value:
        mime_version.defects.append(errors.HeaderMissingRequiredValue('Missing MIME version number (eg: 1.0)'))
        return mime_version
    if value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        mime_version.append(token)
        if not value:
            mime_version.defects.append(errors.HeaderMissingRequiredValue('Expected MIME version number but found only CFWS'))
    digits = ''
    while value and value[0] != '.' and value[0] not in CFWS_LEADER:
        digits += value[0]
        value = value[1:]
    if not digits.isdigit():
        mime_version.defects.append(errors.InvalidHeaderDefect('Expected MIME major version number but found {!r}'.format(digits)))
        mime_version.append(ValueTerminal(digits, 'xtext'))
    else:
        mime_version.major = int(digits)
        mime_version.append(ValueTerminal(digits, 'digits'))
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        mime_version.append(token)
    if value and value[0] != '.':
        if mime_version.major is not None:
            mime_version.defects.append(errors.InvalidHeaderDefect('Incomplete MIME version; found only major number'))
        if value:
            mime_version.append(ValueTerminal(value, 'xtext'))
        return mime_version
    mime_version.append(ValueTerminal('.', 'version-separator'))
    value = value[1:]
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        mime_version.append(token)
    if not value:
        if mime_version.major is not None:
            mime_version.defects.append(errors.InvalidHeaderDefect('Incomplete MIME version; found only major number'))
        return mime_version
    digits = ''
    while value and value[0] not in CFWS_LEADER:
        digits += value[0]
        value = value[1:]
    if not digits.isdigit():
        mime_version.defects.append(errors.InvalidHeaderDefect('Expected MIME minor version number but found {!r}'.format(digits)))
        mime_version.append(ValueTerminal(digits, 'xtext'))
    else:
        mime_version.minor = int(digits)
        mime_version.append(ValueTerminal(digits, 'digits'))
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        mime_version.append(token)
    if value:
        mime_version.defects.append(errors.InvalidHeaderDefect('Excess non-CFWS text after MIME version'))
        mime_version.append(ValueTerminal(value, 'xtext'))
    return mime_version

def get_invalid_parameter(value):
    invalid_parameter = InvalidParameter()
    if value[0] != ';':
        if value[0] in PHRASE_ENDS:
            invalid_parameter.append(ValueTerminal(value[0], 'misplaced-special'))
            value = value[1:]
        else:
            (token, value) = get_phrase(value)
            invalid_parameter.append(token)
    return (invalid_parameter, value)

def get_ttext(value):
    m = _non_token_end_matcher(value)
    if not m:
        raise errors.HeaderParseError("expected ttext but found '{}'".format(value))
    ttext = m.group()
    value = value[len(ttext):]
    ttext = ValueTerminal(ttext, 'ttext')
    _validate_xtext(ttext)
    return (ttext, value)

def get_token(value):
    mtoken = Token()
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        mtoken.append(token)
    if value and value[0] in TOKEN_ENDS:
        raise errors.HeaderParseError("expected token but found '{}'".format(value))
    (token, value) = get_ttext(value)
    mtoken.append(token)
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        mtoken.append(token)
    return (mtoken, value)

def get_attrtext(value):
    m = _non_attribute_end_matcher(value)
    if not m:
        raise errors.HeaderParseError('expected attrtext but found {!r}'.format(value))
    attrtext = m.group()
    value = value[len(attrtext):]
    attrtext = ValueTerminal(attrtext, 'attrtext')
    _validate_xtext(attrtext)
    return (attrtext, value)

def get_attribute(value):
    attribute = Attribute()
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        attribute.append(token)
    if value and value[0] in ATTRIBUTE_ENDS:
        raise errors.HeaderParseError("expected token but found '{}'".format(value))
    (token, value) = get_attrtext(value)
    attribute.append(token)
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        attribute.append(token)
    return (attribute, value)

def get_extended_attrtext(value):
    m = _non_extended_attribute_end_matcher(value)
    if not m:
        raise errors.HeaderParseError('expected extended attrtext but found {!r}'.format(value))
    attrtext = m.group()
    value = value[len(attrtext):]
    attrtext = ValueTerminal(attrtext, 'extended-attrtext')
    _validate_xtext(attrtext)
    return (attrtext, value)

def get_extended_attribute(value):
    attribute = Attribute()
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        attribute.append(token)
    if value and value[0] in EXTENDED_ATTRIBUTE_ENDS:
        raise errors.HeaderParseError("expected token but found '{}'".format(value))
    (token, value) = get_extended_attrtext(value)
    attribute.append(token)
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        attribute.append(token)
    return (attribute, value)

def get_section(value):
    section = Section()
    if value and value[0] != '*':
        raise errors.HeaderParseError('Expected section but found {}'.format(value))
    section.append(ValueTerminal('*', 'section-marker'))
    value = value[1:]
    if not (value and value[0].isdigit()):
        raise errors.HeaderParseError('Expected section number but found {}'.format(value))
    digits = ''
    while value and value[0].isdigit():
        digits += value[0]
        value = value[1:]
    if digits[0] == '0' and digits != '0':
        section.defects.append(errors.InvalidHeaderError('section numberhas an invalid leading 0'))
    section.number = int(digits)
    section.append(ValueTerminal(digits, 'digits'))
    return (section, value)

def get_value(value):
    v = Value()
    if not value:
        raise errors.HeaderParseError('Expected value but found end of string')
    leader = None
    if value[0] in CFWS_LEADER:
        (leader, value) = get_cfws(value)
    if not value:
        raise errors.HeaderParseError('Expected value but found only {}'.format(leader))
    if value[0] == '"':
        (token, value) = get_quoted_string(value)
    else:
        (token, value) = get_extended_attribute(value)
    if leader is not None:
        token[:0] = [leader]
    v.append(token)
    return (v, value)

def get_parameter(value):
    param = Parameter()
    (token, value) = get_attribute(value)
    param.append(token)
    if value and value[0] == ';':
        param.defects.append(errors.InvalidHeaderDefect('Parameter contains name ({}) but no value'.format(token)))
        return (param, value)
    if value[0] == '*':
        try:
            (token, value) = get_section(value)
            param.sectioned = True
            param.append(token)
        except errors.HeaderParseError:
            pass
        if not value:
            raise errors.HeaderParseError('Incomplete parameter')
        if value[0] == '*':
            param.append(ValueTerminal('*', 'extended-parameter-marker'))
            value = value[1:]
            param.extended = True
    if value[0] != '=':
        raise errors.HeaderParseError("Parameter not followed by '='")
    param.append(ValueTerminal('=', 'parameter-separator'))
    value = value[1:]
    leader = None
    if value and value[0] in CFWS_LEADER:
        (token, value) = get_cfws(value)
        param.append(token)
    remainder = None
    appendto = param
    if param.extended and value and value[0] == '"':
        (qstring, remainder) = get_quoted_string(value)
        inner_value = qstring.stripped_value
        semi_valid = False
        if param.section_number == 0:
            if inner_value and inner_value[0] == "'":
                semi_valid = True
            else:
                (token, rest) = get_attrtext(inner_value)
                if rest[0] == "'":
                    semi_valid = True
        try:
            (token, rest) = get_extended_attrtext(inner_value)
        except:
            pass
        if not rest:
            semi_valid = True
        if semi_valid:
            param.defects.append(errors.InvalidHeaderDefect('Quoted string value for extended parameter is invalid'))
            param.append(qstring)
            for t in qstring:
                if t.token_type == 'bare-quoted-string':
                    t[:] = []
                    appendto = t
                    break
            value = inner_value
        else:
            remainder = None
            param.defects.append(errors.InvalidHeaderDefect('Parameter marked as extended but appears to have a quoted string value that is non-encoded'))
    if value and value[0] == "'":
        token = None
    else:
        (token, value) = get_value(value)
    if param.extended and param.section_number > 0:
        if value and value[0] != "'":
            appendto.append(token)
            if remainder is not None:
                value = remainder
            return (param, value)
        param.defects.append(errors.InvalidHeaderDefect('Apparent initial-extended-value but attribute was not marked as extended or was not initial section'))
    if not value:
        param.defects.append(errors.InvalidHeaderDefect('Missing required charset/lang delimiters'))
        appendto.append(token)
        if remainder is None:
            return (param, value)
    else:
        if token is not None:
            for t in token:
                if t.token_type == 'extended-attrtext':
                    break
            t.token_type == 'attrtext'
            appendto.append(t)
            param.charset = t.value
        if value[0] != "'":
            raise errors.HeaderParseError('Expected RFC2231 char/lang encoding delimiter, but found {!r}'.format(value))
        appendto.append(ValueTerminal("'", 'RFC2231-delimiter'))
        value = value[1:]
        if value and value[0] != "'":
            (token, value) = get_attrtext(value)
            appendto.append(token)
            param.lang = token.value
            if value and value[0] != "'":
                raise errors.HeaderParseError('Expected RFC2231 char/lang encoding delimiter, but found {}'.format(value))
        appendto.append(ValueTerminal("'", 'RFC2231-delimiter'))
        value = value[1:]
    if remainder is not None:
        v = Value()
        if value:
            if value[0] in WSP:
                (token, value) = get_fws(value)
            else:
                (token, value) = get_qcontent(value)
            v.append(token)
        token = v
    else:
        (token, value) = get_value(value)
    appendto.append(token)
    if remainder is not None:
        value = remainder
    return (param, value)

def parse_mime_parameters(value):
    mime_parameters = MimeParameters()
    while value:
        try:
            (token, value) = get_parameter(value)
            mime_parameters.append(token)
        except errors.HeaderParseError as err:
            leader = None
            if value[0] in CFWS_LEADER:
                (leader, value) = get_cfws(value)
            if not value:
                mime_parameters.append(leader)
                return mime_parameters
            if value[0] == ';':
                if leader is not None:
                    mime_parameters.append(leader)
                mime_parameters.defects.append(errors.InvalidHeaderDefect('parameter entry with no content'))
            else:
                (token, value) = get_invalid_parameter(value)
                if leader:
                    token[:0] = [leader]
                mime_parameters.append(token)
                mime_parameters.defects.append(errors.InvalidHeaderDefect('invalid parameter {!r}'.format(token)))
        if value and value[0] != ';':
            param = mime_parameters[-1]
            param.token_type = 'invalid-parameter'
            (token, value) = get_invalid_parameter(value)
            param.extend(token)
            mime_parameters.defects.append(errors.InvalidHeaderDefect('parameter with invalid trailing text {!r}'.format(token)))
        if value:
            mime_parameters.append(ValueTerminal(';', 'parameter-separator'))
            value = value[1:]
    return mime_parameters

def _find_mime_parameters(tokenlist, value):
    while value:
        if value[0] != ';':
            if value[0] in PHRASE_ENDS:
                tokenlist.append(ValueTerminal(value[0], 'misplaced-special'))
                value = value[1:]
            else:
                (token, value) = get_phrase(value)
                tokenlist.append(token)
    if not value:
        return
    tokenlist.append(ValueTerminal(';', 'parameter-separator'))
    tokenlist.append(parse_mime_parameters(value[1:]))

def parse_content_type_header(value):
    ctype = ContentType()
    recover = False
    if not value:
        ctype.defects.append(errors.HeaderMissingRequiredValue('Missing content type specification'))
        return ctype
    try:
        (token, value) = get_token(value)
    except errors.HeaderParseError:
        ctype.defects.append(errors.InvalidHeaderDefect('Expected content maintype but found {!r}'.format(value)))
        _find_mime_parameters(ctype, value)
        return ctype
    ctype.append(token)
    if value and value[0] != '/':
        ctype.defects.append(errors.InvalidHeaderDefect('Invalid content type'))
        if value:
            _find_mime_parameters(ctype, value)
        return ctype
    ctype.maintype = token.value.strip().lower()
    ctype.append(ValueTerminal('/', 'content-type-separator'))
    value = value[1:]
    try:
        (token, value) = get_token(value)
    except errors.HeaderParseError:
        ctype.defects.append(errors.InvalidHeaderDefect('Expected content subtype but found {!r}'.format(value)))
        _find_mime_parameters(ctype, value)
        return ctype
    ctype.append(token)
    ctype.subtype = token.value.strip().lower()
    if not value:
        return ctype
    if value[0] != ';':
        ctype.defects.append(errors.InvalidHeaderDefect('Only parameters are valid after content type, but found {!r}'.format(value)))
        del ctype.maintype
        del ctype.subtype
        _find_mime_parameters(ctype, value)
        return ctype
    ctype.append(ValueTerminal(';', 'parameter-separator'))
    ctype.append(parse_mime_parameters(value[1:]))
    return ctype

def parse_content_disposition_header(value):
    disp_header = ContentDisposition()
    if not value:
        disp_header.defects.append(errors.HeaderMissingRequiredValue('Missing content disposition'))
        return disp_header
    try:
        (token, value) = get_token(value)
    except errors.HeaderParseError:
        disp_header.defects.append(errors.InvalidHeaderDefect('Expected content disposition but found {!r}'.format(value)))
        _find_mime_parameters(disp_header, value)
        return disp_header
    disp_header.append(token)
    disp_header.content_disposition = token.value.strip().lower()
    if not value:
        return disp_header
    if value[0] != ';':
        disp_header.defects.append(errors.InvalidHeaderDefect('Only parameters are valid after content disposition, but found {!r}'.format(value)))
        _find_mime_parameters(disp_header, value)
        return disp_header
    disp_header.append(ValueTerminal(';', 'parameter-separator'))
    disp_header.append(parse_mime_parameters(value[1:]))
    return disp_header

def parse_content_transfer_encoding_header(value):
    cte_header = ContentTransferEncoding()
    if not value:
        cte_header.defects.append(errors.HeaderMissingRequiredValue('Missing content transfer encoding'))
        return cte_header
    try:
        (token, value) = get_token(value)
    except errors.HeaderParseError:
        cte_header.defects.append(errors.InvalidHeaderDefect('Expected content transfer encoding but found {!r}'.format(value)))
    cte_header.append(token)
    cte_header.cte = token.value.strip().lower()
    if not value:
        return cte_header
    while value:
        cte_header.defects.append(errors.InvalidHeaderDefect('Extra text after content transfer encoding'))
        if value[0] in PHRASE_ENDS:
            cte_header.append(ValueTerminal(value[0], 'misplaced-special'))
            value = value[1:]
        else:
            (token, value) = get_phrase(value)
            cte_header.append(token)
    return cte_header

def _steal_trailing_WSP_if_exists(lines):
    wsp = ''
    if lines[-1][-1] in WSP:
        wsp = lines[-1][-1]
        lines[-1] = lines[-1][:-1]
    return wsp

def _refold_parse_tree(parse_tree, *, policy):
    maxlen = policy.max_line_length or float('+inf')
    encoding = 'utf-8' if policy.utf8 else 'us-ascii'
    lines = ['']
    last_ew = None
    wrap_as_ew_blocked = 0
    want_encoding = False
    end_ew_not_allowed = Terminal('', 'wrap_as_ew_blocked')
    parts = list(parse_tree)
    while parts:
        part = parts.pop(0)
        if part is end_ew_not_allowed:
            wrap_as_ew_blocked -= 1
        else:
            tstr = str(part)
            try:
                tstr.encode(encoding)
                charset = encoding
            except UnicodeEncodeError:
                if any(isinstance(x, errors.UndecodableBytesDefect) for x in part.all_defects):
                    charset = 'unknown-8bit'
                else:
                    charset = 'utf-8'
                want_encoding = True
            if part.token_type == 'mime-parameters':
                _fold_mime_parameters(part, lines, maxlen, encoding)
            elif want_encoding and not wrap_as_ew_blocked:
                if not part.as_ew_allowed:
                    want_encoding = False
                    last_ew = None
                    if part.syntactic_break:
                        encoded_part = part.fold(policy=policy)[:-1]
                        if policy.linesep not in encoded_part:
                            if len(encoded_part) > maxlen - len(lines[-1]):
                                newline = _steal_trailing_WSP_if_exists(lines)
                                lines.append(newline)
                            lines[-1] += encoded_part
                        else:
                            if not hasattr(part, 'encode'):
                                parts = list(part) + parts
                            else:
                                last_ew = _fold_as_ew(tstr, lines, maxlen, last_ew, part.ew_combine_allowed, charset)
                            want_encoding = False
                            if len(tstr) <= maxlen - len(lines[-1]):
                                lines[-1] += tstr
                            elif part.syntactic_break and len(tstr) + 1 <= maxlen:
                                newline = _steal_trailing_WSP_if_exists(lines)
                                if newline or part.startswith_fws():
                                    lines.append(newline + tstr)
                                elif not hasattr(part, 'encode'):
                                    newparts = list(part)
                                    if not part.as_ew_allowed:
                                        wrap_as_ew_blocked += 1
                                        newparts.append(end_ew_not_allowed)
                                    parts = newparts + parts
                                elif part.as_ew_allowed and not wrap_as_ew_blocked:
                                    parts.insert(0, part)
                                    want_encoding = True
                                else:
                                    newline = _steal_trailing_WSP_if_exists(lines)
                                    if newline or part.startswith_fws():
                                        lines.append(newline + tstr)
                                    else:
                                        lines[-1] += tstr
                            elif not hasattr(part, 'encode'):
                                newparts = list(part)
                                if not part.as_ew_allowed:
                                    wrap_as_ew_blocked += 1
                                    newparts.append(end_ew_not_allowed)
                                parts = newparts + parts
                            elif part.as_ew_allowed and not wrap_as_ew_blocked:
                                parts.insert(0, part)
                                want_encoding = True
                            else:
                                newline = _steal_trailing_WSP_if_exists(lines)
                                if newline or part.startswith_fws():
                                    lines.append(newline + tstr)
                                else:
                                    lines[-1] += tstr
                    else:
                        if not hasattr(part, 'encode'):
                            parts = list(part) + parts
                        else:
                            last_ew = _fold_as_ew(tstr, lines, maxlen, last_ew, part.ew_combine_allowed, charset)
                        want_encoding = False
                        if len(tstr) <= maxlen - len(lines[-1]):
                            lines[-1] += tstr
                        elif part.syntactic_break and len(tstr) + 1 <= maxlen:
                            newline = _steal_trailing_WSP_if_exists(lines)
                            if newline or part.startswith_fws():
                                lines.append(newline + tstr)
                            elif not hasattr(part, 'encode'):
                                newparts = list(part)
                                if not part.as_ew_allowed:
                                    wrap_as_ew_blocked += 1
                                    newparts.append(end_ew_not_allowed)
                                parts = newparts + parts
                            elif part.as_ew_allowed and not wrap_as_ew_blocked:
                                parts.insert(0, part)
                                want_encoding = True
                            else:
                                newline = _steal_trailing_WSP_if_exists(lines)
                                if newline or part.startswith_fws():
                                    lines.append(newline + tstr)
                                else:
                                    lines[-1] += tstr
                        elif not hasattr(part, 'encode'):
                            newparts = list(part)
                            if not part.as_ew_allowed:
                                wrap_as_ew_blocked += 1
                                newparts.append(end_ew_not_allowed)
                            parts = newparts + parts
                        elif part.as_ew_allowed and not wrap_as_ew_blocked:
                            parts.insert(0, part)
                            want_encoding = True
                        else:
                            newline = _steal_trailing_WSP_if_exists(lines)
                            if newline or part.startswith_fws():
                                lines.append(newline + tstr)
                            else:
                                lines[-1] += tstr
                else:
                    if not hasattr(part, 'encode'):
                        parts = list(part) + parts
                    else:
                        last_ew = _fold_as_ew(tstr, lines, maxlen, last_ew, part.ew_combine_allowed, charset)
                    want_encoding = False
                    if len(tstr) <= maxlen - len(lines[-1]):
                        lines[-1] += tstr
                    elif part.syntactic_break and len(tstr) + 1 <= maxlen:
                        newline = _steal_trailing_WSP_if_exists(lines)
                        if newline or part.startswith_fws():
                            lines.append(newline + tstr)
                        elif not hasattr(part, 'encode'):
                            newparts = list(part)
                            if not part.as_ew_allowed:
                                wrap_as_ew_blocked += 1
                                newparts.append(end_ew_not_allowed)
                            parts = newparts + parts
                        elif part.as_ew_allowed and not wrap_as_ew_blocked:
                            parts.insert(0, part)
                            want_encoding = True
                        else:
                            newline = _steal_trailing_WSP_if_exists(lines)
                            if newline or part.startswith_fws():
                                lines.append(newline + tstr)
                            else:
                                lines[-1] += tstr
                    elif not hasattr(part, 'encode'):
                        newparts = list(part)
                        if not part.as_ew_allowed:
                            wrap_as_ew_blocked += 1
                            newparts.append(end_ew_not_allowed)
                        parts = newparts + parts
                    elif part.as_ew_allowed and not wrap_as_ew_blocked:
                        parts.insert(0, part)
                        want_encoding = True
                    else:
                        newline = _steal_trailing_WSP_if_exists(lines)
                        if newline or part.startswith_fws():
                            lines.append(newline + tstr)
                        else:
                            lines[-1] += tstr
            elif len(tstr) <= maxlen - len(lines[-1]):
                lines[-1] += tstr
            elif part.syntactic_break and len(tstr) + 1 <= maxlen:
                newline = _steal_trailing_WSP_if_exists(lines)
                if newline or part.startswith_fws():
                    lines.append(newline + tstr)
                elif not hasattr(part, 'encode'):
                    newparts = list(part)
                    if not part.as_ew_allowed:
                        wrap_as_ew_blocked += 1
                        newparts.append(end_ew_not_allowed)
                    parts = newparts + parts
                elif part.as_ew_allowed and not wrap_as_ew_blocked:
                    parts.insert(0, part)
                    want_encoding = True
                else:
                    newline = _steal_trailing_WSP_if_exists(lines)
                    if newline or part.startswith_fws():
                        lines.append(newline + tstr)
                    else:
                        lines[-1] += tstr
            elif not hasattr(part, 'encode'):
                newparts = list(part)
                if not part.as_ew_allowed:
                    wrap_as_ew_blocked += 1
                    newparts.append(end_ew_not_allowed)
                parts = newparts + parts
            elif part.as_ew_allowed and not wrap_as_ew_blocked:
                parts.insert(0, part)
                want_encoding = True
            else:
                newline = _steal_trailing_WSP_if_exists(lines)
                if newline or part.startswith_fws():
                    lines.append(newline + tstr)
                else:
                    lines[-1] += tstr
    return policy.linesep.join(lines) + policy.linesep

def _fold_as_ew(to_encode, lines, maxlen, last_ew, ew_combine_allowed, charset):
    if ew_combine_allowed:
        to_encode = str(get_unstructured(lines[-1][last_ew:] + to_encode))
        lines[-1] = lines[-1][:last_ew]
    if last_ew is not None and to_encode[0] in WSP:
        leading_wsp = to_encode[0]
        to_encode = to_encode[1:]
        if len(lines[-1]) == maxlen:
            lines.append(_steal_trailing_WSP_if_exists(lines))
        lines[-1] += leading_wsp
    trailing_wsp = ''
    if to_encode[-1] in WSP:
        trailing_wsp = to_encode[-1]
        to_encode = to_encode[:-1]
    new_last_ew = len(lines[-1]) if last_ew is None else last_ew
    while to_encode:
        remaining_space = maxlen - len(lines[-1])
        encode_as = 'utf-8' if charset == 'us-ascii' else charset
        text_space = remaining_space - len(encode_as) - 7
        if text_space <= 0:
            lines.append(' ')
        else:
            first_part = to_encode[:text_space]
            ew = _ew.encode(first_part, charset=encode_as)
            excess = len(ew) - remaining_space
            if excess > 0:
                first_part = first_part[:-excess]
                ew = _ew.encode(first_part)
            lines[-1] += ew
            to_encode = to_encode[len(first_part):]
            if to_encode:
                lines.append(' ')
                new_last_ew = len(lines[-1])
    lines[-1] += trailing_wsp
    if ew_combine_allowed:
        return new_last_ew

def _fold_mime_parameters(part, lines, maxlen, encoding):
    for (name, value) in part.params:
        if not lines[-1].rstrip().endswith(';'):
            lines[-1] += ';'
        charset = encoding
        error_handler = 'strict'
        try:
            value.encode(encoding)
            encoding_required = False
        except UnicodeEncodeError:
            encoding_required = True
            if utils._has_surrogates(value):
                charset = 'unknown-8bit'
                error_handler = 'surrogateescape'
            else:
                charset = 'utf-8'
        if encoding_required:
            encoded_value = urllib.parse.quote(value, safe='', errors=error_handler)
            tstr = "{}*={}''{}".format(name, charset, encoded_value)
        else:
            tstr = '{}={}'.format(name, quote_string(value))
        if len(lines[-1]) + len(tstr) + 1 < maxlen:
            lines[-1] = lines[-1] + ' ' + tstr
        elif len(tstr) + 2 <= maxlen:
            lines.append(' ' + tstr)
        else:
            section = 0
            extra_chrome = charset + "''"
            while value:
                chrome_len = len(name) + len(str(section)) + 3 + len(extra_chrome)
                if maxlen <= chrome_len + 3:
                    maxlen = 78
                splitpoint = maxchars = maxlen - chrome_len - 2
                while True:
                    partial = value[:splitpoint]
                    encoded_value = urllib.parse.quote(partial, safe='', errors=error_handler)
                    if len(encoded_value) <= maxchars:
                        break
                    splitpoint -= 1
                lines.append(' {}*{}*={}{}'.format(name, section, extra_chrome, encoded_value))
                extra_chrome = ''
                section += 1
                value = value[splitpoint:]
                if value:
                    lines[-1] += ';'
        section = 0
        extra_chrome = charset + "''"
        while value:
            chrome_len = len(name) + len(str(section)) + 3 + len(extra_chrome)
            if maxlen <= chrome_len + 3:
                maxlen = 78
            splitpoint = maxchars = maxlen - chrome_len - 2
            while True:
                partial = value[:splitpoint]
                encoded_value = urllib.parse.quote(partial, safe='', errors=error_handler)
                if len(encoded_value) <= maxchars:
                    break
                splitpoint -= 1
            lines.append(' {}*{}*={}{}'.format(name, section, extra_chrome, encoded_value))
            extra_chrome = ''
            section += 1
            value = value[splitpoint:]
            if value:
                lines[-1] += ';'
