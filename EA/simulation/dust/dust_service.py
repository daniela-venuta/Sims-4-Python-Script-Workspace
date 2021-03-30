import build_buyimport servicesimport sims4from event_testing.resolver import GlobalResolverfrom interactions.utils.tested_variant import TunableGlobalTestListfrom objects.components.types import STATISTIC_COMPONENTfrom plex.plex_enums import INVALID_PLEX_IDfrom sims4.common import Packfrom sims4.geometry import Polygonfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableReference, TunableSet, TunableRangefrom sims4.utils import classpropertyfrom statistics.commodity import Commodityfrom tag import TunableTagslogger = sims4.log.Logger('DustService', default_owner='jmorrow')
class DustService(Service):
    DUST_STATE_COMMODITY = Commodity.TunablePackSafeReference(description='\n        The lot-level commodity that controls dust state.\n        ')
    TESTS_TO_ENABLE = TunableGlobalTestList(description='\n        Tests that must pass for the dust system to become active on a zone.\n        ')
    OBJECT_TAGS_TO_RECLAIM = TunableTags(description='\n        Tags of dust-related objects that need to be reclaimed by the dust\n        service or else they will be destroyed. This helps ensure that\n        dust-related objects are destroyed when loading a save after the dust\n        system game option has been disabled.\n        ', filter_prefixes=('Func',))
    ZONE_MODIFIERS = TunableSet(description='\n        A set of default zone modifiers to apply when the Dust System is enabled. These zone \n        modifiers will be "hidden" from the UI and will not appear as lot traits in the \n        lot trait molecule or manage worlds.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), pack_safe=True))
    MIN_AREA_REQUIRED_TO_ADD_DUST_COMMODITY = TunableRange(description='\n        The minimum area required to add a dust commodity on a level. If the\n        level has a dust commodity and becomes smaller than the minimum\n        area, then the dust commodity will be culled.\n        ', tunable_type=float, default=0.0, minimum=0.0)

    @classproperty
    def required_packs(cls):
        return (Pack.SP22,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_on_zone = False
        self._game_option_enabled = False

    def on_zone_load(self):
        self._active_on_zone = self._test_zone()
        if self._active_on_zone:
            self._enable(from_load=True)
        else:
            self._disable(from_load=True)

    def _enable(self, from_load):
        zone = services.current_zone()
        zone_modifier_service = services.get_zone_modifier_service()
        zone_modifier_service.check_for_and_apply_new_zone_modifiers(services.current_zone_id())
        self._setup_lot_levels()
        if not from_load:
            return
        obj_man = services.object_manager()
        for obj in obj_man.get_objects_with_tags_gen(*self.OBJECT_TAGS_TO_RECLAIM):
            obj.claim()

    def _disable(self, from_load):
        self._active_on_zone = False
        lot = services.active_lot()
        for lot_level in lot.lot_levels.values():
            if not lot_level.has_component(STATISTIC_COMPONENT):
                pass
            else:
                lot_level.commodity_tracker.remove_statistic(self.DUST_STATE_COMMODITY)
        if from_load:
            return
        zone_modifier_service = services.get_zone_modifier_service()
        zone_modifier_service.check_for_and_apply_new_zone_modifiers(services.current_zone_id())
        obj_man = services.object_manager()
        for obj in obj_man.get_objects_with_tags_gen(*self.OBJECT_TAGS_TO_RECLAIM):
            obj.destroy()

    def on_zone_unload(self):
        if not self._active_on_zone:
            return
        self._active_on_zone = False

    def on_build_buy_exit(self):
        if not self._active_on_zone:
            return
        self._setup_lot_levels()

    def _setup_lot_levels(self):
        if self.DUST_STATE_COMMODITY is None:
            logger.error('dust.dust_service.Dust State Commodity is unexpectedly None. This can happen if the tuning instance is in a pack other than SP22.')
            return
        plex_service = services.get_plex_service()
        plex_id = plex_service.get_active_zone_plex_id() or INVALID_PLEX_ID
        block_polys = build_buy.get_all_block_polygons(plex_id).values()

        def _get_level_area(level_index):
            area = 0
            for (poly_data, block_level_index) in block_polys:
                if block_level_index != level_index:
                    pass
                else:
                    for p in poly_data:
                        polygon = Polygon(list(reversed(p)))
                        polygon.normalize()
                        area += polygon.area()
            return area

        lot = services.active_lot()
        for lot_level in lot.lot_levels.values():
            should_have_dust_statistic = _get_level_area(lot_level.level_index) > self.MIN_AREA_REQUIRED_TO_ADD_DUST_COMMODITY
            if lot_level.commodity_tracker.has_statistic(self.DUST_STATE_COMMODITY):
                if not should_have_dust_statistic:
                    lot_level.commodity_tracker.remove_statistic(self.DUST_STATE_COMMODITY)
                    if not should_have_dust_statistic:
                        pass
                    else:
                        lot_level.commodity_tracker.add_statistic(self.DUST_STATE_COMMODITY)
            elif not should_have_dust_statistic:
                pass
            else:
                lot_level.commodity_tracker.add_statistic(self.DUST_STATE_COMMODITY)

    def _test_zone(self):
        if not self._game_option_enabled:
            return False
        household = services.owning_household_of_active_lot()
        if household is None:
            return False
        if not household.is_played_household:
            return False
        return self.TESTS_TO_ENABLE.run_tests(GlobalResolver())

    def get_zone_modifiers(self):
        if self._active_on_zone:
            return DustService.ZONE_MODIFIERS
        return ()

    def save_options(self, options_proto):
        options_proto.dust_system_enabled = self._game_option_enabled

    def load_options(self, options_proto):
        self._game_option_enabled = options_proto.dust_system_enabled

    @property
    def game_option_enabled(self):
        return self._game_option_enabled

    def set_enabled(self, value):
        self._game_option_enabled = value
        self._active_on_zone = self._test_zone()
        if self._active_on_zone:
            self._enable(from_load=False)
        else:
            self._disable(from_load=False)
