try:
    import _pythonutils
except ImportError:

    class _pythonutils:

        @staticmethod
        def try_highwater_gc():
            return False
