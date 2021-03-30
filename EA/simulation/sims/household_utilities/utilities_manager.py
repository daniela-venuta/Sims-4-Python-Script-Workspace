import operatorimport simsfrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom interactions.interaction_finisher import FinishingTypefrom sims.household_utilities.utility_types import UtilityShutoffReasonPriority, Utilitiesfrom sims4.service_manager import Serviceimport objects.components.typesimport servicesimport sims4.loglogger = sims4.log.Logger('UtilitiesManager', default_owner='rmccord')
class UtilityInfo:

    def __init__(self, utility):
        self._utility = utility
        self._surplus = None
        self._surplus_listeners_info = None
        self._shutoff_reasons = {}

    @property
    def utility(self):
        return self._utility

    @property
    def active(self):
        return self._surplus or len(self._shutoff_reasons) == 0

    @property
    def surplus(self):
        return self._surplus

    @surplus.setter
    def surplus(self, value):
        self._surplus = value

    @property
    def is_surplus_updates_initialized(self):
        return self._surplus is not None and self._surplus_listeners_info is not None

    def set_surplus_listeners_info(self, tracker, surplus_listener, deficit_listener):
        self._surplus_listeners_info = (tracker, surplus_listener, deficit_listener)

    def clear_surplus_listeners_info(self):
        if self.is_surplus_updates_initialized:
            (tracker, surplus_listener, deficit_listener) = self._surplus_listeners_info
            tracker.remove_listener(surplus_listener)
            tracker.remove_listener(deficit_listener)
        self._surplus_listeners_info = None
        self.surplus = None

    def get_priority_shutoff_tooltip(self, shutoff_tooltip_override):
        if self.active:
            return
        reason = max(UtilityShutoffReasonPriority.NO_REASON, [reason for reason in self._shutoff_reasons if reason is not None])
        tooltip = None
        if reason != UtilityShutoffReasonPriority.NO_REASON:
            if shutoff_tooltip_override and reason in shutoff_tooltip_override:
                tooltip = shutoff_tooltip_override[reason]
            else:
                tooltip = self._shutoff_reasons[reason]
        return tooltip

    def add_shutoff_reason(self, shutoff_reason, tooltip=None):
        if shutoff_reason in self._shutoff_reasons:
            return False
        self._shutoff_reasons[shutoff_reason] = tooltip
        return True

    def remove_shutoff_reason(self, shutoff_reason):
        if shutoff_reason not in self._shutoff_reasons:
            return False
        del self._shutoff_reasons[shutoff_reason]
        return True

class UtilitiesManager(Service):

    def __init__(self):
        self._utilities_managers = dict()

    def get_manager_for_household(self, household_id):
        if not household_id:
            logger.error('Trying to get utilities manager but the household id is {}.', household_id)
            return
        household = services.household_manager().get(household_id)
        if household is None:
            logger.error('Trying to get utilities manager for an unknown household {}', household_id)
            return
        return self.get_manager_for_zone(household.home_zone_id)

    def get_manager_for_zone(self, zone_id):
        if not zone_id:
            logger.error('Trying to get utilities manager but the zone id is {}.', zone_id)
            return
        if zone_id not in self._utilities_managers:
            self._utilities_managers[zone_id] = ZoneUtilitiesManager(zone_id)
        return self._utilities_managers[zone_id]

    def on_zone_unload(self):
        for manager in self._utilities_managers.values():
            manager.on_zone_unload()

    def on_all_households_and_sim_infos_loaded(self, client):
        for manager in self._utilities_managers.values():
            manager.on_all_households_and_sim_infos_loaded()

class ZoneUtilitiesManager:
    SURPLUS_DEAD_ZONE_LOWER_BOUND = 0.0
    SURPLUS_DEAD_ZONE_UPPER_BOUND_DELTA = 0.25
    utility_surplus_threshold = None

    def __init__(self, zone_id):
        self._utilities = {u: UtilityInfo(u) for u in Utilities}
        self._zone_id = zone_id
        if ZoneUtilitiesManager.utility_surplus_threshold is None:
            ZoneUtilitiesManager.utility_surplus_threshold = dict()
            for utility in Utilities:
                utility_tuning = sims.bills.Bills.get_utility_info(utility)
                if utility_tuning is None:
                    logger.error('Failed to find utility tuning for {}, this will cause errors later.', utility)
                    ZoneUtilitiesManager.utility_surplus_threshold[utility] = (ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_LOWER_BOUND, ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_UPPER_BOUND_DELTA)
                else:
                    sell_value = utility_tuning.statistic_sell_value
                    upper_bound = sell_value - ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_UPPER_BOUND_DELTA
                    upper_bound_lower_limit = ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_UPPER_BOUND_DELTA - ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_LOWER_BOUND
                    if upper_bound < upper_bound_lower_limit:
                        logger.error('Ignoring Utilities Manager Dead Zone values ({}, {}) due to conflict with Statistic Sell Value {}.', ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_LOWER_BOUND, upper_bound, sell_value)
                        upper_bound = upper_bound_lower_limit
                    ZoneUtilitiesManager.utility_surplus_threshold[utility] = (ZoneUtilitiesManager.SURPLUS_DEAD_ZONE_LOWER_BOUND, upper_bound)

    def on_zone_unload(self):
        if not self.is_manager_on_current_lot():
            return
        for utility_info in self._utilities.values():
            utility_info.clear_surplus_listeners_info()

    def on_all_households_and_sim_infos_loaded(self):
        if not self.is_manager_on_current_lot():
            return
        for utility_info in self._utilities.values():
            if not utility_info.is_surplus_updates_initialized:
                self._update_surplus(utility_info)

    def is_manager_on_current_lot(self):
        return self._zone_id == services.current_zone_id()

    def is_affected_object(self, obj):
        return obj.is_on_active_lot()

    def get_utility_info(self, utility):
        utility_info = self._utilities[utility]
        if not utility_info.is_surplus_updates_initialized:
            self._update_surplus(utility_info)
        return utility_info

    def is_utility_active(self, utility):
        return self.get_utility_info(utility).active

    def test_utility_info(self, utilities, target, resolver, skip_safe_tests=False):
        if utilities is None:
            return TestResult.TRUE
        for (utility, utility_data) in utilities.items():
            utility_info = self.get_utility_info(utility)
            if utility_info is not None and not utility_info.active:
                tests = None
                if not target.is_terrain:
                    tests = target.tests_to_bypass_utility_requirement.get(utility, None)
                if tests:
                    if not tests.run_tests(resolver, skip_safe_tests=skip_safe_tests):
                        return TestResult(False, 'Bills: Interaction requires a utility that is shut off.', tooltip=utility_info.get_priority_shutoff_tooltip(utility_data.shutoff_tooltip_override))
                return TestResult(False, 'Bills: Interaction requires a utility that is shut off.', tooltip=utility_info.get_priority_shutoff_tooltip(utility_data.shutoff_tooltip_override))
        return TestResult.TRUE

    def shut_off_utility(self, utility, reason, tooltip=None, from_load=False):
        utility_info = self.get_utility_info(utility)
        utility_info_was_active = utility_info.active
        if not utility_info.add_shutoff_reason(reason, tooltip=tooltip):
            return
        if not self.is_manager_on_current_lot():
            return
        if utility_info_was_active and not utility_info.active:
            self._shutoff_utilities(utility, from_load=from_load)

    def restore_utility(self, utility, reason):
        utility_info = self.get_utility_info(utility)
        utility_info_was_active = utility_info.active
        if not utility_info.remove_shutoff_reason(reason):
            return
        if not self.is_manager_on_current_lot():
            return
        if utility_info_was_active or utility_info.active:
            self._startup_utilities(utility)

    def on_build_buy_exit(self):
        if not self.is_manager_on_current_lot():
            return
        for utility in Utilities:
            if self.get_utility_info(utility).active:
                pass
            else:
                if utility == Utilities.POWER:
                    self._shutoff_power_utilities()
                self._apply_delinquent_states(utility)

    def _apply_delinquent_states(self, delinquent_utility):
        for obj in services.object_manager().valid_objects():
            if not self.is_affected_object(obj):
                pass
            else:
                state_component = obj.state_component
                if state_component is None:
                    pass
                else:
                    state_component.apply_delinquent_states(utility=delinquent_utility)

    def _clear_delinquent_states(self, delinquent_utility):
        for obj in services.object_manager().valid_objects():
            if not self.is_affected_object(obj):
                pass
            else:
                state_component = obj.state_component
                if state_component is None:
                    pass
                else:
                    state_component.clear_delinquent_states(utility=delinquent_utility)

    def _cancel_delinquent_interactions(self, delinquent_utility):
        for sim in services.sim_info_manager().instanced_sims_gen():
            for interaction in sim.si_state:
                utility_info = interaction.utility_info
                if utility_info is None:
                    pass
                elif delinquent_utility in utility_info:
                    interaction.cancel(FinishingType.FAILED_TESTS, 'Utilities Manager. Interaction violates current delinquency state.')

    def _startup_utilities(self, utility):
        if utility == Utilities.POWER:
            self._startup_power_utilities()
        self._exec_on_objects_in_inventory(lambda component: component.on_utility_on(utility))
        self._clear_delinquent_states(utility)
        commodity = self._get_utility_statistic(utility)
        if commodity is not None:
            commodity.remove_min_value_override()
        services.get_event_manager().process_events_for_household(TestEvent.UtilityStatusChanged, services.active_household())

    def _shutoff_utilities(self, utility, from_load=False):
        if utility == Utilities.POWER:
            self._shutoff_power_utilities(from_load=from_load)
        self._exec_on_objects_in_inventory(lambda component: component.on_utility_off(utility))
        self._cancel_delinquent_interactions(utility)
        self._apply_delinquent_states(utility)
        commodity = self._get_utility_statistic(utility)
        if commodity is not None:
            commodity.set_min_value_override(commodity.get_value())
        services.get_event_manager().process_events_for_household(TestEvent.UtilityStatusChanged, services.active_household())

    def _startup_power_utilities(self):
        self._exec_on_objects_with_component(objects.components.types.LIGHTING_COMPONENT, lambda component: component.update_lighting_enabled_state())

    def _shutoff_power_utilities(self, from_load=False):
        self._exec_on_objects_with_component(objects.components.types.LIGHTING_COMPONENT, lambda component: component.update_lighting_enabled_state())

    def _exec_on_objects_in_inventory(self, func):
        inventory_manager = services.inventory_manager()
        for obj in inventory_manager.objects:
            if not self.is_affected_object(obj):
                pass
            else:
                func(obj.get_component(objects.components.types.INVENTORY_ITEM_COMPONENT))

    def _exec_on_objects_with_component(self, component_type, func):
        object_manager = services.object_manager()
        plex_service = services.get_plex_service()
        for obj in object_manager.get_all_objects_with_component_gen(component_type):
            if not self.is_affected_object(obj):
                pass
            elif plex_service.is_active_zone_a_plex() and plex_service.get_plex_zone_at_position(obj.position, obj.level) is None:
                pass
            else:
                func(obj.get_component(component_type))

    def _on_utility_supply_surplus(self, utility_info, zone_id):
        currently_active = utility_info.active
        utility_info.surplus = True
        if currently_active != utility_info.active:
            self._startup_utilities(utility_info.utility)
        zone_modifiers = services.get_zone_modifier_service().get_zone_modifiers(zone_id)
        for zone_modifier in zone_modifiers:
            zone_modifier.on_utility_supply_surplus(utility_info.utility)

    def _on_utility_supply_deficit(self, utility_info, zone_id):
        currently_active = utility_info.active
        utility_info.surplus = False
        if currently_active != utility_info.active:
            self._shutoff_utilities(utility_info.utility)
        zone_modifiers = services.get_zone_modifier_service().get_zone_modifiers(zone_id)
        for zone_modifier in zone_modifiers:
            zone_modifier.on_utility_supply_deficit(utility_info.utility)

    def _get_lot_commodity_tracker(self):
        zone = services.get_zone_manager().get(self._zone_id)
        if zone is None:
            return
        statistic_component = zone.lot.get_component(objects.components.types.STATISTIC_COMPONENT)
        if statistic_component is None:
            return
        return statistic_component.get_commodity_tracker()

    def _get_utility_statistic_type(self, utility):
        utility_info = sims.bills.Bills.get_utility_info(utility)
        if utility_info is None:
            return
        return utility_info.statistic

    def _get_utility_statistic(self, utility):
        tracker = self._get_lot_commodity_tracker()
        if tracker is None:
            return
        stat_type = self._get_utility_statistic_type(utility)
        if stat_type is None:
            return
        return tracker.get_statistic(stat_type)

    def _update_surplus(self, utility_info):
        if not self.is_manager_on_current_lot():
            return
        utility_stat_type = self._get_utility_statistic_type(utility_info.utility)
        if utility_stat_type is None:
            return
        commodity_tracker = self._get_lot_commodity_tracker()
        if commodity_tracker is None:
            return
        utility_info.surplus = commodity_tracker.get_value(utility_stat_type) > 0
        (lower_bound, upper_bound) = ZoneUtilitiesManager.utility_surplus_threshold[utility_info.utility]
        positive_threshold = sims4.math.Threshold(upper_bound, operator.gt)
        surplus_listener = commodity_tracker.create_and_add_listener(utility_stat_type, positive_threshold, lambda _, info=utility_info, zone_id=self._zone_id: self._on_utility_supply_surplus(info, zone_id))
        negative_threshold = sims4.math.Threshold(lower_bound, operator.le)
        deficit_listener = commodity_tracker.create_and_add_listener(utility_stat_type, negative_threshold, lambda _, info=utility_info, zone_id=self._zone_id: self._on_utility_supply_deficit(info, zone_id))
        utility_info.set_surplus_listeners_info(commodity_tracker, surplus_listener, deficit_listener)
