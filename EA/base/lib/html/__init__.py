import re as _refrom html.entities import html5 as _html5__all__ = ['escape', 'unescape']
def escape(s, quote=True):
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    if quote:
        s = s.replace('"', '&quot;')
        s = s.replace("'", '&#x27;')
    return s
