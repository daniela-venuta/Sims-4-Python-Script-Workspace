from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableReferenceimport enumimport servicesimport sims4.resources
class ZoneDirectorRequestType(enum.Int, export=False):
    CAREER_EVENT = ...
    GO_DANCING = ...
    DRAMA_SCHEDULER = ...
    AMBIENT_SUB_VENUE = ...
    AMBIENT_VENUE = ...

class NPCSummoningPurpose(DynamicEnum):
    DEFAULT = 0
    PLAYER_BECOMES_GREETED = 1
    BRING_PLAYER_SIM_TO_LOT = 2
    ZONE_FIXUP = 3
