from sims4.tuning.dynamic_enum import DynamicEnumLocked
class OrganizationStatusEnum(DynamicEnumLocked):
    ACTIVE = 0
    INACTIVE = 1
    NONMEMBER = 2

class OrganizationMembershipActionEnum(DynamicEnumLocked):
    JOIN = 0
    LEAVE = 1
    UPDATE = 2
