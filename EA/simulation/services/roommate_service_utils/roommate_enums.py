from sims4.tuning.dynamic_enum import DynamicEnumLockedimport enum
class RoommateLeaveReason(DynamicEnumLocked):
    INVALID = 0
    OVERCAPACITY = 1

class LeaveReasonTestingTime(enum.Int):
    UNTESTED = 0
    HOUSEHOLD_ROOMMATES_ALL_LOTS = 1
    HOUSEHOLD_ROOMMATES_HOME_LOT = 2
    ALL_ROOMMATES = 3
