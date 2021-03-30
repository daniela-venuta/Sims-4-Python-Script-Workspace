import localeimport osimport reimport sys__all__ = ['NullTranslations', 'GNUTranslations', 'Catalog', 'find', 'translation', 'install', 'textdomain', 'bindtextdomain', 'bind_textdomain_codeset', 'dgettext', 'dngettext', 'gettext', 'lgettext', 'ldgettext', 'ldngettext', 'lngettext', 'ngettext']_default_localedir = os.path.join(sys.base_prefix, 'share', 'locale')_token_pattern = re.compile('\n        (?P<WHITESPACES>[ \\t]+)                    | # spaces and horizontal tabs\n        (?P<NUMBER>[0-9]+\\b)                       | # decimal integer\n        (?P<NAME>n\\b)                              | # only n is allowed\n        (?P<PARENTHESIS>[()])                      |\n        (?P<OPERATOR>[-*/%+?:]|[><!]=?|==|&&|\\|\\|) | # !, *, /, %, +, -, <, >,\n                                                     # <=, >=, ==, !=, &&, ||,\n                                                     # ? :\n                                                     # unary and bitwise ops\n                                                     # not allowed\n        (?P<INVALID>\\w+|.)                           # invalid token\n    ', re.VERBOSE | re.DOTALL)
def _tokenize(plural):
    for mo in re.finditer(_token_pattern, plural):
        kind = mo.lastgroup
        if kind == 'WHITESPACES':
            pass
        else:
            value = mo.group(kind)
            if kind == 'INVALID':
                raise ValueError('invalid token in plural form: %s' % value)
            yield value
    yield ''

def _error(value):
    if value:
        return ValueError('unexpected token in plural form: %s' % value)
    else:
        return ValueError('unexpected end of plural form')
_binary_ops = (('||',), ('&&',), ('==', '!='), ('<', '>', '<=', '>='), ('+', '-'), ('*', '/', '%'))_binary_ops = {op: i for (i, ops) in enumerate(_binary_ops, 1) for op in ops}_c2py_ops = {'||': 'or', '&&': 'and', '/': '//'}