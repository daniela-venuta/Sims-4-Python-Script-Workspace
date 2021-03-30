from bucks.bucks_enums import BucksType, BucksTrackerTypeimport servicesfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, OptionalTunable, TunableEnumSet, TunableReferencefrom sims4.tuning.tunable_base import ExportModes, EnumBinaryExportTypeimport sims4
class BucksUtils:
    BUCK_TYPE_TO_TRACKER_MAP = TunableMapping(description='\n        Maps a buck type to the tracker that uses that bucks type.\n        ', key_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=BucksType.INVALID, pack_safe=True), key_name='Bucks Type', value_type=BucksTrackerType, value_name='Bucks Tracker')
    BUCK_TYPE_TO_DISPLAY_DATA = TunableMapping(description='\n        For each supplied Bucks, a set of UI display data to be used when displaying\n        information related to this bucks in the UI.\n        ', key_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=BucksType.INVALID, pack_safe=True), key_name='Bucks Type', value_type=TunableTuple(description='\n            A set of UI display data for one bucks type.\n            ', ui_name=TunableLocalizedStringFactory(), cost_string=OptionalTunable(description='\n                Format for displaying interaction names on interactions that\n                have this buck as a cost. 0.String is the interaction name. 1 will be the the cost\n                amount.\n                ', tunable=TunableLocalizedStringFactory()), gain_string=OptionalTunable(description='\n                Format for displaying interaction names on interactions that\n                have this buck as a gain. 0.String is the interaction name. 1 will be the the gain\n                amount.\n                ', tunable=TunableLocalizedStringFactory()), value_string=OptionalTunable(description='\n                A string like "{0.Money}" that will be used in UI to display a\n                value of this currency.\n                ', tunable=TunableLocalizedStringFactory()), headline=OptionalTunable(description='\n                If enabled when this buck updates we will display\n                a headline update to the UI for selectable sims.\n                ', tunable=TunableReference(description='\n                    The headline that we want to send down.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.HEADLINE)))), value_name='Bucks UI Data')
    WALLET_BUCK_TYPES = TunableEnumSet(description='\n        A list of buck types whose values will be displayed in the wallet\n        tooltip.\n        ', enum_type=BucksType, invalid_enums=BucksType.INVALID, pack_safe=True, export_modes=ExportModes.ClientBinary, binary_type=EnumBinaryExportType.EnumUint32)

    @classmethod
    def get_tracker_for_bucks_type(cls, bucks_type, owner_id=None, add_if_none=False):
        bucks_tracker_type = BucksUtils.BUCK_TYPE_TO_TRACKER_MAP.get(bucks_type)
        if owner_id is None:
            active_household = services.active_household()
            return active_household.bucks_tracker
        if bucks_tracker_type == BucksTrackerType.HOUSEHOLD:
            sim_info = services.sim_info_manager().get(owner_id)
            if sim_info is None:
                active_household = services.active_household()
                return active_household.bucks_tracker
            if sim_info.household is None:
                return
            return sim_info.household.bucks_tracker
        if bucks_tracker_type == BucksTrackerType.CLUB:
            club_service = services.get_club_service()
            if club_service is None:
                return
            club = club_service.get_club_by_id(owner_id)
            if club is not None:
                return club.bucks_tracker
        elif bucks_tracker_type == BucksTrackerType.SIM:
            sim_info = services.sim_info_manager().get(owner_id)
            if sim_info is not None:
                return sim_info.get_bucks_tracker(add_if_none=add_if_none)
