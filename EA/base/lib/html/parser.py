import reimport warningsimport _markupbasefrom html import unescape__all__ = ['HTMLParser']interesting_normal = re.compile('[&<]')incomplete = re.compile('&[a-zA-Z#]')entityref = re.compile('&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]')charref = re.compile('&#(?:[0-9]+|[xX][0-9a-fA-F]+)[^0-9a-fA-F]')starttagopen = re.compile('<[a-zA-Z]')piclose = re.compile('>')commentclose = re.compile('--\\s*>')tagfind_tolerant = re.compile('([a-zA-Z][^\\t\\n\\r\\f />\\x00]*)(?:\\s|/(?!>))*')attrfind_tolerant = re.compile('((?<=[\\\'"\\s/])[^\\s/>][^\\s/=>]*)(\\s*=+\\s*(\\\'[^\\\']*\\\'|"[^"]*"|(?![\\\'"])[^>\\s]*))?(?:\\s|/(?!>))*')locatestarttagend_tolerant = re.compile('\n  <[a-zA-Z][^\\t\\n\\r\\f />\\x00]*       # tag name\n  (?:[\\s/]*                          # optional whitespace before attribute name\n    (?:(?<=[\'"\\s/])[^\\s/>][^\\s/=>]*  # attribute name\n      (?:\\s*=+\\s*                    # value indicator\n        (?:\'[^\']*\'                   # LITA-enclosed value\n          |"[^"]*"                   # LIT-enclosed value\n          |(?![\'"])[^>\\s]*           # bare value\n         )\n         (?:\\s*,)*                   # possibly followed by a comma\n       )?(?:\\s|/(?!>))*\n     )*\n   )?\n  \\s*                                # trailing whitespace\n', re.VERBOSE)endendtag = re.compile('>')endtagfind = re.compile('</\\s*([a-zA-Z][-.a-zA-Z0-9:_]*)\\s*>')