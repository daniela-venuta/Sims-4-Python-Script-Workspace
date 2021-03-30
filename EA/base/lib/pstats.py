import sysimport osimport timeimport marshalimport refrom enum_lib import Enumfrom functools import cmp_to_key__all__ = ['Stats', 'SortKey']
class SortKey(str, Enum):
    CALLS = ('calls', 'ncalls')
    CUMULATIVE = ('cumulative', 'cumtime')
    FILENAME = ('filename', 'module')
    LINE = 'line'
    NAME = 'name'
    NFL = 'nfl'
    PCALLS = 'pcalls'
    STDNAME = 'stdname'
    TIME = ('time', 'tottime')

    def __new__(cls, *values):
        obj = str.__new__(cls)
        obj._value_ = values[0]
        for other_value in values[1:]:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj
