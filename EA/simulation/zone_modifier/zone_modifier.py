from event_testing.tests_with_data import InteractionTestEventsfrom interactions.utils.loot import LootActionsfrom objects import ALL_HIDDEN_REASONSfrom sims.household_utilities.utility_types import Utilitiesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableSet, TunableList, Tunable, OptionalTunable, TunableReference, TunableVariant, TunableMapping, TunableEnumEntryfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import classpropertyfrom situations.situation_curve import SituationCurvefrom tag import TunableTag, Tagfrom tunable_utils.taggables_tests import SituationIdentityTestfrom zone_modifier.zone_modifier_actions import ZoneInteractionTriggers, ZoneModifierWeeklySchedule, ZoneModifierUpdateActionfrom zone_modifier.zone_modifier_from_objects_actions import ZoneModifierFromObjectsActionVariants, ZoneModifierFromObjectsActionTypefrom zone_modifier.zone_modifier_household_actions import ZoneModifierHouseholdActionVariantsimport collectionsimport servicesimport sims4.resourceslogger = sims4.log.Logger('ZoneModifier', default_owner='bnguyen')
class ZoneModifier(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER)):
    INSTANCE_TUNABLES = {'zone_modifier_locked': Tunable(description='\n            Whether this is a locked trait that cannot be assigned/removed\n            through build/buy.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'enter_lot_loot': TunableSet(description='\n            Loot applied to Sims when they enter or spawn in on the lot while\n            this zone modifier is active.\n            \n            NOTE: The corresponding exit loot is not guaranteed to be given.\n            For example, if the Sim walks onto the lot, player switches to a\n            different zone, then summons that Sim, that Sim will bypass\n            getting the exit loot.\n            A common use case for exit lot loot is to remove buffs granted\n            by this zone_mod.  This case is already covered as buffs are \n            automatically removed if they are non-persistable (have no associated commodity)\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'exit_lot_loot': TunableSet(description='\n            Loot applied to Sims when they exit or spawn off of the lot while\n            this zone modifier is active.\n            \n            NOTE: This loot is not guaranteed to be given after the enter loot.\n            For example, if the Sim walks onto the lot, player switches to a\n            different zone, then summons that Sim, that Sim will bypass\n            getting the exit loot.\n            A common use case for exit lot loot is to remove buffs granted\n            by this zone_mod.  This case is already covered as buffs are \n            automatically removed if they are non-persistable (have no associated commodity)\n            ', tunable=LootActions.TunableReference(pack_safe=True), tuning_group=GroupNames.LOOT), 'interaction_triggers': TunableList(description='\n            A mapping of interactions to possible loots that can be applied\n            when an on-lot Sim executes them if this zone modifier is set.\n            ', tunable=ZoneInteractionTriggers.TunableFactory()), 'schedule': ZoneModifierWeeklySchedule.TunableFactory(description='\n            Schedule to be activated for this particular zone modifier.\n            '), 'household_actions': TunableList(description='\n            Actions to apply to the household that owns this lot when this zone\n            modifier is set.\n            ', tunable=ZoneModifierHouseholdActionVariants(description='\n                The action to apply to the household.\n                ')), 'object_tag_to_actions': TunableMapping(description='\n            Mapping of object tag to zone modifier from object actions. Objects \n            in this tuning can be buy objects, build objects (column, window, pool),\n            and materials (floor tiles, roof tiles, wallpaper).\n            \n            This is primarily intended for architectural elements such as wallpaper, \n            roof materials, windows will give effect to utilities and eco footprint.\n            \n            All actions will always be applied to the current lot.\n            \n            NOTE: The actions will only be applied if user enables the \n            "Architecture Affects Eco Living" option under Game Options.\n            ', key_type=TunableTag(description='\n                The object tag that will be used to do actions.\n                '), value_type=TunableList(description='\n                The list of action to apply.\n                ', tunable=ZoneModifierFromObjectsActionVariants())), 'prohibited_situations': OptionalTunable(description='\n            Optionally define if this zone should prevent certain situations\n            from running or getting scheduled.\n            ', tunable=SituationIdentityTest.TunableFactory(description='\n                Prevent a situation from running if it is one of the specified \n                situations or if it contains one of the specified tags.\n                ')), 'venue_requirements': TunableVariant(description='\n            Whether or not we use a blacklist or white list for the venue\n            requirements on this zone modifier.\n            ', allowed_venue_types=TunableSet(description='\n                A list of venue types that this Zone Modifier can be placed on.\n                All other venue types are not allowed.\n                ', tunable=TunableReference(description='\n                    A venue type that this Zone Modifier can be placed on.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True)), prohibited_venue_types=TunableSet(description='\n                A list of venue types that this Zone Modifier cannot be placed on.\n                ', tunable=TunableReference(description='\n                    A venue type that this Zone Modifier cannot be placed on.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True)), export_modes=ExportModes.All), 'conflicting_zone_modifiers': TunableSet(description='\n            Conflicting zone modifiers for this zone modifier. If the lot has any of the\n            specified zone modifiers, then it is not allowed to be equipped with this\n            one.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), pack_safe=True), export_modes=ExportModes.All), 'additional_situations': SituationCurve.TunableFactory(description="\n            An additional schedule of situations that can be added in addition\n            a situation scheduler's source tuning.\n            ", get_create_params={'user_facing': False}), 'zone_wide_loot': ZoneModifierUpdateAction.TunableFactory(description='\n            Loots applied when spawning into a zone with \n            this zone modifier. This loot is also applied to all sims, \n            objects, etc. in the zone when this zone modifier is added to a lot.\n            ', tuning_group=GroupNames.LOOT), 'cleanup_loot': ZoneModifierUpdateAction.TunableFactory(description='\n            Loots applied when this zone modifier is removed.\n            ', tuning_group=GroupNames.LOOT), 'on_add_loot': ZoneModifierUpdateAction.TunableFactory(description='\n            Loots applied when this zone modifier is added.\n            ', tuning_group=GroupNames.LOOT), 'spin_up_lot_loot': ZoneModifierUpdateAction.TunableFactory(description='\n            Loots applied when the zone spins up.\n            ', tuning_group=GroupNames.LOOT), 'utility_supply_surplus_loot': TunableMapping(description='\n            Loots applied when utility supply statistic change\n            from deficit to surplus.\n            ', key_type=TunableEnumEntry(description='\n                The utility that we want to listen for supply change.\n                ', tunable_type=Utilities, default=Utilities.POWER), value_type=ZoneModifierUpdateAction.TunableFactory(description='\n                Loots to apply.\n                '), tuning_group=GroupNames.LOOT), 'utility_supply_deficit_loot': TunableMapping(description='\n            Loots applied when utility supply statistic change\n            from surplus to deficit.\n            ', key_type=TunableEnumEntry(description='\n                The utility that we want to listen for supply change.\n                ', tunable_type=Utilities, default=Utilities.POWER), value_type=ZoneModifierUpdateAction.TunableFactory(description='\n                Loots to apply.\n                '), tuning_group=GroupNames.LOOT), 'ignore_route_events_during_zone_spin_up': Tunable(description="\n            Don't handle sim route events during zone spin up.  Useful for preventing\n            unwanted loot from being applied when enter_lot_loot runs situation blacklist tests.\n            If we require sims to retrieve loot on zone spin up, we can tune spin_up_lot_loot. \n            ", tunable_type=bool, default=False), 'hide_screen_slam': Tunable(description='\n            If checked, this zone modifier will not show the usual screen slam\n            when first applied.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.UI)}
    _obj_tag_id_to_count = None

    @classproperty
    def obj_tag_id_to_count(cls):
        return cls._obj_tag_id_to_count

    @classmethod
    def on_start_actions(cls):
        cls.register_interaction_triggers()

    @classmethod
    def on_spin_up_actions(cls, is_build_eco_effects_enabled):
        sim_spawner_service = services.sim_spawner_service()
        if not sim_spawner_service.is_registered_sim_spawned_callback(cls.zone_wide_loot.apply_to_sim):
            sim_spawner_service.register_sim_spawned_callback(cls.zone_wide_loot.apply_to_sim)
        cls.spin_up_lot_loot.apply_all_actions()
        cls.zone_wide_loot.apply_all_actions()
        cls.apply_object_actions(is_build_eco_effects_enabled)

    @classmethod
    def on_add_actions(cls, is_build_eco_effects_enabled):
        sim_spawner_service = services.sim_spawner_service()
        if not sim_spawner_service.is_registered_sim_spawned_callback(cls.zone_wide_loot.apply_to_sim):
            sim_spawner_service.register_sim_spawned_callback(cls.zone_wide_loot.apply_to_sim)
        cls.register_interaction_triggers()
        cls.start_household_actions()
        cls.on_add_loot.apply_all_actions()
        cls.zone_wide_loot.apply_all_actions()
        cls.apply_object_actions(is_build_eco_effects_enabled)

    @classmethod
    def on_stop_actions(cls):
        services.sim_spawner_service().unregister_sim_spawned_callback(cls.zone_wide_loot.apply_to_sim)
        cls.unregister_interaction_triggers()
        cls.stop_household_actions()
        cls.revert_object_actions()

    @classmethod
    def on_remove_actions(cls):
        services.sim_spawner_service().unregister_sim_spawned_callback(cls.zone_wide_loot.apply_to_sim)
        cls.unregister_interaction_triggers()
        cls.stop_household_actions()
        cls.cleanup_loot.apply_all_actions()
        cls.revert_object_actions()

    @classmethod
    def on_utility_supply_surplus(cls, utility):
        if utility in cls.utility_supply_surplus_loot:
            cls.utility_supply_surplus_loot[utility].apply_all_actions()

    @classmethod
    def on_utility_supply_deficit(cls, utility):
        if utility in cls.utility_supply_deficit_loot:
            cls.utility_supply_deficit_loot[utility].apply_all_actions()

    @classmethod
    def handle_event(cls, sim_info, event, resolver):
        if event not in InteractionTestEvents:
            return
        sim = sim_info.get_sim_instance()
        if sim is None or not sim.is_on_active_lot():
            return
        for trigger in cls.interaction_triggers:
            trigger.handle_interaction_event(sim_info, event, resolver)

    @classmethod
    def start_household_actions(cls):
        if not cls.household_actions:
            return
        household_id = services.owning_household_id_of_active_lot()
        if household_id is not None:
            for household_action in cls.household_actions:
                household_action.start_action(household_id)

    @classmethod
    def stop_household_actions(cls):
        if not cls.household_actions:
            return
        household_id = services.owning_household_id_of_active_lot()
        if household_id is not None:
            for household_action in cls.household_actions:
                household_action.stop_action(household_id)

    @classmethod
    def _on_build_objects_environment_score_update(cls):
        household = services.active_household()
        if household is None:
            return
        for sim in household.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
            sim.on_build_objects_environment_score_update()

    @classmethod
    def apply_object_actions(cls, is_build_eco_effects_enabled):
        if not is_build_eco_effects_enabled:
            return
        if not cls.object_tag_to_actions:
            return
        object_tags = list(cls.object_tag_to_actions.keys())
        curr_obj_tag_id_to_count = services.active_lot().get_object_count_by_tags(object_tags)
        if cls._obj_tag_id_to_count is None:
            delta_obj_tag_id_to_count = curr_obj_tag_id_to_count
        else:
            delta_obj_tag_id_to_count = {key: curr_obj_tag_id_to_count[key] - cls._obj_tag_id_to_count[key] for key in curr_obj_tag_id_to_count}
        zone = services.current_zone()
        total_architectural_stat_effects = collections.defaultdict(int)
        for (obj_tag_id, delta_obj_count) in delta_obj_tag_id_to_count.items():
            for action in cls.object_tag_to_actions[Tag(obj_tag_id)]:
                if action.action_type == ZoneModifierFromObjectsActionType.STATISTIC_CHANGE:
                    if action.stat is not None:
                        obj_count = curr_obj_tag_id_to_count[obj_tag_id]
                        total_architectural_stat_effects[action.stat.guid64] += action.get_value(obj_count)
                        if delta_obj_count != 0:
                            action.apply(delta_obj_count)
                elif delta_obj_count != 0:
                    action.apply(delta_obj_count)
        zone.revert_zone_architectural_stat_effects()
        statistic_manager = services.statistic_manager()
        for (stat_id, value) in total_architectural_stat_effects.items():
            stat = statistic_manager.get(stat_id)
            if stat is None:
                logger.error('B/B Gameplay Effect stat with ID {} expected, but not found.', stat_id, owner='amwu')
            elif zone.lot is None:
                logger.error('Trying to add architectural stat effects onto zone {} without lot', zone.id, owner='amwu')
            else:
                tracker = zone.lot.get_tracker(stat)
                if tracker is None:
                    logger.error('Tracker for B/B Gameplay Effect stat {} expected, but not found.', stat_id, owner='amwu')
                else:
                    original_value = tracker.get_value(stat)
                    tracker.add_value(stat, value)
                    new_value = tracker.get_value(stat)
                    zone.zone_architectural_stat_effects[stat_id] += new_value - original_value
        cls._on_build_objects_environment_score_update()
        cls._obj_tag_id_to_count = curr_obj_tag_id_to_count

    @classmethod
    def revert_object_actions(cls):
        if not cls._obj_tag_id_to_count:
            return
        zone = services.current_zone()
        for (obj_tag_id, obj_count) in cls._obj_tag_id_to_count.items():
            if obj_count != 0:
                for action in cls.object_tag_to_actions[Tag(obj_tag_id)]:
                    if action.action_type != ZoneModifierFromObjectsActionType.STATISTIC_CHANGE:
                        action.revert(obj_count)
        zone.revert_zone_architectural_stat_effects()
        cls._on_build_objects_environment_score_update()
        cls._obj_tag_id_to_count = None

    @classmethod
    def register_interaction_triggers(cls):
        services.get_event_manager().register_tests(cls, cls._get_trigger_tests())

    @classmethod
    def unregister_interaction_triggers(cls):
        services.get_event_manager().unregister_tests(cls, cls._get_trigger_tests())

    @classmethod
    def _get_trigger_tests(cls):
        tests = list()
        for trigger in cls.interaction_triggers:
            tests.extend(trigger.get_trigger_tests())
        return tests

    @classmethod
    def is_situation_prohibited(cls, situation_type):
        if cls.prohibited_situations is None:
            return False
        return cls.prohibited_situations(situation=situation_type)
