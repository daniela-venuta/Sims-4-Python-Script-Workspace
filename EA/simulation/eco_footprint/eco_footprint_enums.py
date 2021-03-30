import enum
class EcoFootprintStateType(enum.Int):
    GREEN = 0
    NEUTRAL = 1
    INDUSTRIAL = 2

class EcoFootprintDirection(enum.Int):
    TOWARD_GREEN = 0
    AT_CONVERGENCE = 1
    TOWARD_INDUSTRIAL = 2
