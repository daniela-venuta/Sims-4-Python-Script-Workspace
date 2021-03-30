import enumfrom sims4.tuning.dynamic_enum import DynamicEnum
class AdditionalBillSource(DynamicEnum):
    Miscellaneous = 0

class UtilityEndOfBillAction(enum.Int, export=False):
    SELL = 0
    STORE = 1
