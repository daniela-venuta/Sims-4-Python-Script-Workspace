try:
    import _areaops
except ImportError:

    class _areaops:

        @staticmethod
        def op_request(*_, **__):
            pass

        @staticmethod
        def save_gsi(*_, **__):
            pass

        @staticmethod
        def load_gsi(*_, **__):
            pass

        @staticmethod
        def trigger_assert(*_, **__):
            pass
op_request = _areaops.op_requestsave_gsi = _areaops.save_gsiload_gsi = _areaops.load_gsitrigger_native_assert = _areaops.trigger_assert