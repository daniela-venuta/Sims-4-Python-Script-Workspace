import enum_lib as enumimport importlib._bootstrap_externalimport importlib.machineryimport importlib.utilimport osimport os.pathimport sysimport traceback__all__ = ['compile', 'main', 'PyCompileError', 'PycInvalidationMode']
class PyCompileError(Exception):

    def __init__(self, exc_type, exc_value, file, msg=''):
        exc_type_name = exc_type.__name__
        if exc_type is SyntaxError:
            tbtext = ''.join(traceback.format_exception_only(exc_type, exc_value))
            errmsg = tbtext.replace('File "<string>"', 'File "%s"' % file)
        else:
            errmsg = 'Sorry: %s: %s' % (exc_type_name, exc_value)
        Exception.__init__(self, msg or errmsg, exc_type_name, exc_value, file)
        self.exc_type_name = exc_type_name
        self.exc_value = exc_value
        self.file = file
        self.msg = msg or errmsg

    def __str__(self):
        return self.msg

class PycInvalidationMode(enum.Enum):
    TIMESTAMP = 1
    CHECKED_HASH = 2
    UNCHECKED_HASH = 3

def compile(file, cfile=None, dfile=None, doraise=False, optimize=-1, invalidation_mode=PycInvalidationMode.TIMESTAMP):
    if os.environ.get('SOURCE_DATE_EPOCH'):
        invalidation_mode = PycInvalidationMode.CHECKED_HASH
    if cfile is None:
        if optimize >= 0:
            optimization = optimize if optimize >= 1 else ''
            cfile = importlib.util.cache_from_source(file, optimization=optimization)
        else:
            cfile = importlib.util.cache_from_source(file)
    if os.path.islink(cfile):
        msg = '{} is a symlink and will be changed into a regular file if import writes a byte-compiled file to it'
        raise FileExistsError(msg.format(cfile))
    elif os.path.exists(cfile) and not os.path.isfile(cfile):
        msg = '{} is a non-regular file and will be changed into a regular one if import writes a byte-compiled file to it'
        raise FileExistsError(msg.format(cfile))
    loader = importlib.machinery.SourceFileLoader('<py_compile>', file)
    source_bytes = loader.get_data(file)
    try:
        code = loader.source_to_code(source_bytes, dfile or file, _optimize=optimize)
    except Exception as err:
        py_exc = PyCompileError(err.__class__, err, dfile or file)
        if doraise:
            raise py_exc
        else:
            sys.stderr.write(py_exc.msg + '\n')
            return
    try:
        dirname = os.path.dirname(cfile)
        if dirname:
            os.makedirs(dirname)
    except FileExistsError:
        pass
    if invalidation_mode == PycInvalidationMode.TIMESTAMP:
        source_stats = loader.path_stats(file)
        bytecode = importlib._bootstrap_external._code_to_timestamp_pyc(code, source_stats['mtime'], source_stats['size'])
    else:
        source_hash = importlib.util.source_hash(source_bytes)
        bytecode = importlib._bootstrap_external._code_to_hash_pyc(code, source_hash, invalidation_mode == PycInvalidationMode.CHECKED_HASH)
    mode = importlib._bootstrap_external._calc_mode(file)
    importlib._bootstrap_external._write_atomic(cfile, bytecode, mode)
    return cfile

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    rv = 0
    if args == ['-']:
        while True:
            filename = sys.stdin.readline()
            if not filename:
                break
            filename = filename.rstrip('\n')
            try:
                compile(filename, doraise=True)
            except PyCompileError as error:
                rv = 1
                sys.stderr.write('%s\n' % error.msg)
            except OSError as error:
                rv = 1
                sys.stderr.write('%s\n' % error)
    else:
        for filename in args:
            try:
                compile(filename, doraise=True)
            except PyCompileError as error:
                rv = 1
                sys.stderr.write('%s\n' % error.msg)
    return rv
if __name__ == '__main__':
    sys.exit(main())