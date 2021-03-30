if __name__ == '__main__':
    import os
    import sys
    (cythonpath, _) = os.path.split(os.path.realpath(__file__))
    sys.path.insert(0, cythonpath)
    from Cython.Compiler.Main import main
    main(command_line=1)
else:
    from Cython.Shadow import *
    from Cython import __version__
    from Cython import load_ipython_extension