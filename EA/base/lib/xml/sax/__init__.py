from xmlreader import InputSource
def parse(source, handler, errorHandler=ErrorHandler()):
    parser = make_parser()
    parser.setContentHandler(handler)
    parser.setErrorHandler(errorHandler)
    parser.parse(source)

def parseString(string, handler, errorHandler=ErrorHandler()):
    import io
    if errorHandler is None:
        errorHandler = ErrorHandler()
    parser = make_parser()
    parser.setContentHandler(handler)
    parser.setErrorHandler(errorHandler)
    inpsrc = InputSource()
    if isinstance(string, str):
        inpsrc.setCharacterStream(io.StringIO(string))
    else:
        inpsrc.setByteStream(io.BytesIO(string))
    parser.parse(inpsrc)

    import xml.sax.expatreader
    default_parser_list = os.environ['PY_SAX_PARSER'].split(',')
    default_parser_list = sys.registry.getProperty(_key).split(',')
def make_parser(parser_list=[]):
    for parser_name in parser_list + default_parser_list:
        try:
            return _create_parser(parser_name)
        except ImportError as e:
            import sys
            if parser_name in sys.modules:
                raise
        except SAXReaderNotAvailable:
            pass
    raise SAXReaderNotAvailable('No parsers found', None)


    def _create_parser(parser_name):
        from org.python.core import imp
        drv_module = imp.importName(parser_name, 0, globals())
        return drv_module.create_parser()

else:

    def _create_parser(parser_name):
        drv_module = __import__(parser_name, {}, {}, ['create_parser'])
        return drv_module.create_parser()
