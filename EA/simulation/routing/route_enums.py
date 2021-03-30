from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class RouteEventType(enum.Int, export=False):
    LOW_REPEAT = 1
    LOW_SINGLE = 2
    HIGH_SINGLE = 3
    BROADCASTER = 4
    ENTER_LOT_LEVEL_INDOOR = 5
    INTERACTION_PRE = 6
    INTERACTION_POST = 7
    FIRST_OUTDOOR = 8
    LAST_OUTDOOR = 9
    FIRST_INDOOR = 10
    LAST_INDOOR = 11

class RouteEventPriority(DynamicEnum):
    DEFAULT = 0

class RoutingStageEvent(enum.Int, export=False):
    ROUTE_START = 0
    ROUTE_END = 1
