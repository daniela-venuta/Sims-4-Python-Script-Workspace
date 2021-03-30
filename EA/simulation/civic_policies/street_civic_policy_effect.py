from protocolbuffers import GameplaySaveData_pb2, Consts_pb2, Lot_pb2import alarmsimport build_buyimport game_servicesimport worldfrom date_and_time import DateAndTime, TimeSpan, create_time_spanfrom interactions.utils.tested_variant import TunableGlobalTestListfrom scheduler import WeeklySchedulefrom seasons.season_ops import SeasonParameterUpdateOpfrom sims.household_utilities.utility_types import Utilities, UtilityShutoffReasonPriorityfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import HasTunableFactory, TunableList, TunableEnumEntry, TunableHouseDescription, TunableMapping, TunableLotDescription, OptionalTunable, TunableSimMinute, TunableVariant, Tunable, AutoFactoryInit, TunableReferencefrom ui.ui_dialog_notification import UiDialogNotificationfrom weather.weather_enums import WeatherEffectType, CloudTypeimport sims4from distributor.system import Distributorfrom event_testing.resolver import SingleSimResolver, GlobalResolver, StreetResolver, LotResolverfrom interactions.utils.loot import LootActionsfrom open_street_director.open_street_conditional_layer_change import DirectManipulateConditionalLayerfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog_labeled_icons import TunableUiDialogVariantfrom ui.ui_tuning import MapOverlayEnumfrom world.street import get_zone_ids_from_street, get_lot_id_to_zone_ids_dictimport serviceslogger = sims4.log.Logger('StreetEffect', default_owner='shouse')
class StreetEffect(metaclass=sims4.tuning.instances.HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SNIPPET)):
    INSTANCE_SUBCLASSES_ONLY = True

    def __init__(self):
        self._policy = None
        self._street = None

    def finalize_startup(self, policy):
        self._policy = policy
        street_service = services.street_service()
        self._street = None if street_service is None else street_service.get_street(self.policy.provider)
        if self._street is None:
            logger.error('{} failed to get street from {}', self, self.policy.provider)

    @property
    def policy(self):
        return self._policy

    def get_save_state_msg(self):
        pass

    def set_load_state_from_msg(self, effect_data):
        pass

    def enact(self):
        raise NotImplementedError

    def repeal(self):
        raise NotImplementedError

class StreetConditionalLayerEffect(StreetEffect, DirectManipulateConditionalLayer):
    INSTANCE_TUNABLES = {'layer': DirectManipulateConditionalLayer.TunableFactory(), 'tests': TunableGlobalTestList(description="\n            The tests that must pass in order for this conditional layer\n            to be changed. The test will be evaluated at the time the change\n            is to be made, for both repeal and enact changes.\n            The Street Participant is set to this effect's street.\n            "), 'always_show_dialog': Tunable(description='\n            By default, if tests fail and no change in the layer is done, any\n            dialog will be shown anyway.  To stop the dialog unless the layer\n            is actually changed, uncheck this option.\n            ', tunable_type=bool, default=True), 'delay_from_change': OptionalTunable(description='\n            If enabled, a delay time from the time the policy is \n            enacted or repealed before changing the conditional layer.\n            ', tunable=TunableTimeSpan(description='\n                A delay duration.\n                ')), 'active_street_enact_dialog': OptionalTunable(description="\n            If enabled and this policy's street is the active street,\n            tune what dialog to show to notify the player of the enact change.\n            If used, the delay time is applied.\n            ", tunable=TunableUiDialogVariant()), 'active_street_repeal_dialog': OptionalTunable(description="\n            If enabled and this policy's street is the active street,\n            tune what dialog to show to notify the player of the enact change.\n            If used, the delay time is applied.\n            ", tunable=TunableUiDialogVariant())}
    CHANGE_PENDING_SENTINEL_VALUE = 18446744073709551615

    def __init__(self):
        super().__init__()
        self._change_alarm = None
        self._last_change_start_time = None
        self._change_pending = False
        self.layer = self.layer()

    def _is_on_active_street(self):
        zone_ids = world.street.get_zone_ids_from_street(self._street)
        return services.current_zone_id() in zone_ids

    def _do_change(self, from_finalize=False):
        if not self._is_on_active_street():
            if not from_finalize:
                self._change_pending = True
            return
        self._change_pending = False
        change_layer = not self.tests or self.tests.run_tests(StreetResolver(self._street))
        if change_layer:
            self.layer.change_conditional_layer(invert_show=not self.policy.enacted)
        if from_finalize:
            return
        if change_layer or not self.always_show_dialog:
            return
        dialog = self.active_street_enact_dialog if self.policy.enacted else self.active_street_repeal_dialog
        if dialog is not None:
            dialog = dialog(None, resolver=GlobalResolver())
            dialog.show_dialog()

    def _do_change_when_appropriate(self, from_finalize=False):
        if self._change_alarm is not None:
            alarms.cancel_alarm(self._change_alarm)
            self._change_alarm = None
        if self._last_change_start_time is None:
            logger.error('Attempt to (re)start conditional layer without start time set for {}', self)
            return
        if self.delay_from_change is not None:
            time_of_change = self._last_change_start_time + self.delay_from_change()
        else:
            time_of_change = self._last_change_start_time
        now = services.time_service().sim_now
        time_until_change = time_of_change - now
        if time_until_change == TimeSpan.ZERO:
            self._do_change(from_finalize=from_finalize)
        elif time_until_change > TimeSpan.ZERO:
            self._change_alarm = alarms.add_alarm(self, time_until_change, lambda _: self._do_change(), cross_zone=True)
        elif self.layer.conditional_layer.client_only and self._is_on_active_street():
            conditional_layer_service = services.conditional_layer_service()
            show_layer = self.layer.show_conditional_layer
            invert_show = not self.policy.enacted
            if invert_show:
                show_layer = not show_layer
            if show_layer != conditional_layer_service.is_layer_loaded(self.layer.conditional_layer):
                self.layer.change_conditional_layer(invert_show=invert_show)

    def _mark_policy_change(self):
        self._change_pending = False
        self._last_change_start_time = services.time_service().sim_now

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if self._street is None:
            return
        if self._change_pending:
            self._do_change(from_finalize=True)
            return
        if self._last_change_start_time is not None and self._change_alarm is None:
            self._do_change_when_appropriate(from_finalize=True)

    def get_save_state_msg(self):
        if self._last_change_start_time is None:
            return
        effect_msg = GameplaySaveData_pb2.PersistableCivicPolicyStreetConditionalLayerEffectData()
        if self._change_pending:
            effect_msg.start_tick = self.CHANGE_PENDING_SENTINEL_VALUE
        else:
            effect_msg.start_tick = self._last_change_start_time.absolute_ticks()
        return effect_msg.SerializeToString()

    def set_load_state_from_msg(self, effect_data):
        if effect_data is not None:
            effect_msg = GameplaySaveData_pb2.PersistableCivicPolicyStreetConditionalLayerEffectData()
            effect_msg.ParseFromString(effect_data)
            if effect_msg.start_tick == self.CHANGE_PENDING_SENTINEL_VALUE:
                self._change_pending = True
                self._last_change_start_time = DateAndTime(0)
            else:
                self._last_change_start_time = DateAndTime(effect_msg.start_tick)

    def enact(self):
        self._mark_policy_change()
        self._do_change_when_appropriate()

    def repeal(self):
        self._mark_policy_change()
        self._do_change_when_appropriate()

class StreetMapOverlayEffect(StreetEffect):
    INSTANCE_TUNABLES = {'map_overlay': TunableEnumEntry(description='\n            The map overlay to add when enacted.\n            ', tunable_type=MapOverlayEnum, default=MapOverlayEnum.NONE, invalid_enums=(MapOverlayEnum.NONE,))}

    @classmethod
    def _verify_tuning_callback(cls):
        pass

    def _send_update_msg(self, neighborhood_proto):
        distributor = Distributor.instance()
        distributor.add_event(Consts_pb2.MSG_NS_NEIGHBORHOOD_UPDATE, neighborhood_proto)

    def enact(self):
        street_service = services.street_service()
        if street_service is None:
            return
        (neighborhood_proto, street_data) = street_service.get_neighborhood_proto(self._street)
        if neighborhood_proto is None:
            logger.error('{} failed to find neighborhood data street info', self)
            return
        if self.map_overlay not in street_data.map_overlays:
            street_data.map_overlays.append(self.map_overlay)
            self._send_update_msg(neighborhood_proto)

    def repeal(self):
        if self.map_overlay == MapOverlayEnum.NONE:
            logger.warn('{} tuned to an invalid map overlay {}', self, self.map_overlay)
            return
        street_service = services.street_service()
        if street_service is None:
            return
        (neighborhood_proto, street_data) = street_service.get_neighborhood_proto(self._street, add=False)
        if neighborhood_proto is None:
            return
        if self.map_overlay in street_data.map_overlays:
            street_data.map_overlays.remove(self.map_overlay)
            self._send_update_msg(neighborhood_proto)

class StreetPlexExteriorChangeEffect(StreetEffect):
    INSTANCE_TUNABLES = {'enact_exterior_house_descriptions': TunableMapping(description="\n            When enacted, a reference to the HouseDescription resource to use to \n            select the Lot Template.  Leaving unset makes no change on enact.\n            The Street's Zones are matched to find which House Descriptions should\n            be applied.  Only Zones that have matching Lot Descriptions and are on\n            the current Street will be modified.\n            ", key_type=TunableLotDescription(pack_safe=True), value_type=TunableHouseDescription(pack_safe=True)), 'repeal_exterior_house_descriptions': TunableMapping(description="\n            When repealed, a reference to the HouseDescription resource to use to \n            select the Lot Template.  Leaving unset makes no change on repeal.\n            The Street's Zones are matched to find which House Descriptions should\n            be applied.  Only Zones that have matching Lot Descriptions and are on\n            the current Street will be modified.\n            ", key_type=TunableLotDescription(pack_safe=True), value_type=TunableHouseDescription(pack_safe=True))}

    def _set_exterior_house_description(self, house_descriptions):
        if not house_descriptions:
            return
        zone_ids = get_zone_ids_from_street(self._street)
        if not zone_ids:
            return
        distributor = Distributor.instance()
        persistence_service = services.get_persistence_service()
        for zone_id in zone_ids:
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            zone_world_description_id = services.get_world_description_id(zone_data.world_id)
            zone_lot_description_id = services.get_lot_description_id(zone_data.lot_id, zone_world_description_id)
            for (lot_description_id, house_description_id) in house_descriptions.items():
                if lot_description_id == zone_lot_description_id:
                    zone_data.pending_plex_exterior_house_desc_id = house_description_id
                    plex_update_msg = Lot_pb2.LotPlexExteriorUpdate()
                    plex_update_msg.zone_id = zone_id
                    plex_update_msg.plex_exterior_house_desc_id = house_description_id
                    distributor.add_event(Consts_pb2.MSG_SET_PLEX_EXTERIOR_HOUSE_DESC, plex_update_msg)
                    break

    def enact(self):
        self._set_exterior_house_description(self.enact_exterior_house_descriptions)

    def repeal(self):
        self._set_exterior_house_description(self.repeal_exterior_house_descriptions)

class ScheduledLoot(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'loot': TunableList(description='\n            Loot applied when the effect is enacted.\n            ', tunable=LootActions.TunableReference(description='\n                Loot applied when the effect is enacted.\n                ', pack_safe=True)), 'schedule_data': WeeklySchedule.TunableFactory(description='\n            The information to schedule points during the week that\n            the Street Policy Effect, if enacted, will award loot.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loot_schedule = None
        self._resolver_gen = None

    def set_resolver_gen(self, resolver_gen):
        self._resolver_gen = resolver_gen

    def start_loot_schedule(self):
        if self._loot_schedule is not None:
            self._loot_schedule.destroy()
        self._loot_schedule = self.schedule_data(start_callback=self._handle_scheduled_loot_action, schedule_immediate=True)

    def stop_loot_schedule(self):
        if self._loot_schedule is not None:
            self._loot_schedule.destroy()
            self._loot_schedule = None

    def _handle_scheduled_loot_action(self, scheduler, alarm_data, extra_data):
        if self._resolver_gen is None:
            return
        for resolver in self._resolver_gen():
            for loot in self.loot:
                loot.apply_to_resolver(resolver)

class StreetBaseLootEffect(StreetEffect):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'enact_loot': TunableList(description='\n            If enabled, Loot applied when the effect is enacted\n            ', tunable=LootActions.TunableReference(description='\n                Loot applied when the effect is enacted.\n                ', pack_safe=True)), 'repeal_loot': TunableList(description='\n            If enabled, Loot applied when the effect is repealed\n            ', tunable=LootActions.TunableReference(description='\n                Loot applied when the effect is repealed.\n                ', pack_safe=True)), 'scheduled_loot': OptionalTunable(description='\n            While enacted, loot to award on a schedule.\n            ', tunable=ScheduledLoot.TunableFactory())}

    @classmethod
    def _verify_tuning_callback(cls):
        pass

    @classmethod
    def _tuning_loaded_callback(cls):
        if cls.scheduled_loot is not None:
            cls.scheduled_loot = cls.scheduled_loot()

    def _collect_resolvers(self):
        raise NotImplementedError

    def _enact_for_resolver(self, resolver):
        for loot in self.enact_loot:
            loot.apply_to_resolver(resolver)

    def _repeal_for_resolver(self, resolver):
        for loot in self.repeal_loot:
            loot.apply_to_resolver(resolver)

    def _start_schedule(self):
        if self.scheduled_loot is not None:
            self.scheduled_loot.set_resolver_gen(self._collect_resolvers)
            self.scheduled_loot.start_loot_schedule()

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if self._street is not None and self.policy.enacted:
            self._start_schedule()

    def enact(self):
        if self.enact_loot is None:
            return
        for resolver in self._collect_resolvers():
            self._enact_for_resolver(resolver)
        self._start_schedule()

    def repeal(self):
        if self.repeal_loot is None:
            return
        for resolver in self._collect_resolvers():
            self._repeal_for_resolver(resolver)
        if self.scheduled_loot is not None:
            self.scheduled_loot.set_resolver_gen(None)
            self.scheduled_loot.stop_loot_schedule()

class StreetLootEffect(StreetBaseLootEffect):

    def _collect_resolvers(self):
        return (StreetResolver(self._street),)

class StreetActiveSimLootEffect(StreetBaseLootEffect):

    def _collect_resolvers(self):
        active_sim = services.get_active_sim()
        if active_sim is None:
            return ()
        return (SingleSimResolver(active_sim.sim_info),)

class StreetLotsLootEffect(StreetBaseLootEffect):

    def _collect_resolvers(self):
        resolvers = []
        zone_manager = services.get_zone_manager()
        lot_id_to_zone_id_dict = get_lot_id_to_zone_ids_dict(self._street)
        for (lot_id, zone_ids) in lot_id_to_zone_id_dict.items():
            if not zone_ids:
                pass
            else:
                zone_id = zone_ids[0]
                zone = zone_manager.get(zone_id, allow_uninstantiated_zones=True)
                if zone is not None:
                    resolvers.append(LotResolver(zone.lot))
        return resolvers

class StreetResidentSimLootEffect(StreetEffect):
    INSTANCE_TUNABLES = {'enact_loot': TunableList(description="\n            If enabled, Loot applied on a Street's resident Sims when the effect is enacted\n            ", tunable=LootActions.TunableReference(description="\n                Loot applied on a Street's resident Sims when the effect is enacted.\n                ", pack_safe=True)), 'repeal_loot': TunableList(description="\n            If enabled, Loot applied on a Street's resident Sims when the effect is repealed\n            ", tunable=LootActions.TunableReference(description="\n                Loot applied on a Street's resident Sims when the effect is repealed.\n                ", pack_safe=True)), 'scheduled_loot': OptionalTunable(description='\n            While enacted, loot to award on a schedule.\n            ', tunable=ScheduledLoot.TunableFactory())}

    @classmethod
    def _verify_tuning_callback(cls):
        pass

    @classmethod
    def _tuning_loaded_callback(cls):
        if cls.scheduled_loot is not None:
            cls.scheduled_loot = cls.scheduled_loot()

    def _start_schedule(self):
        if self.scheduled_loot is not None:
            self.scheduled_loot.set_resolver_gen(lambda : [SingleSimResolver(sim_info) for sim_info in self.policy.provider.get_resident_sim_infos()])
            self.scheduled_loot.start_loot_schedule()

    def _enact_for_sim_info(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot in self.enact_loot:
            loot.apply_to_resolver(resolver)

    def _repeal_for_sim_info(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot in self.repeal_loot:
            loot.apply_to_resolver(resolver)

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if self._street is None:
            return

        def handle_moved_sim_info(sim_info, old_street, new_street):
            if not self.policy.enacted:
                return
            if old_street is self._street and self.repeal_loot is not None:
                self._repeal_for_sim_info(sim_info)
            if new_street is self._street and self.enact_loot is not None:
                self._enact_for_sim_info(sim_info)

        services.street_service().register_sim_info_home_street_change_callback(self._street, handle_moved_sim_info)
        if self.policy.enacted:
            self._start_schedule()

    def enact(self):
        if self.enact_loot is not None:
            for sim_info in self.policy.provider.get_resident_sim_infos():
                self._enact_for_sim_info(sim_info)
        self._start_schedule()

    def repeal(self):
        if self.repeal_loot is not None:
            for sim_info in self.policy.provider.get_resident_sim_infos():
                self._repeal_for_sim_info(sim_info)
        if self.scheduled_loot is not None:
            self.scheduled_loot.set_resolver_gen(None)
            self.scheduled_loot.stop_loot_schedule()

class StreetInstancedSimLootEffect(StreetEffect):
    INSTANCE_TUNABLES = {'enact_loot': TunableList(description='\n            Loots applied when a sim is instanced on a street where this effect\n            is enacted.\n            ', tunable=LootActions.TunableReference(pack_safe=True)), 'repeal_loot': TunableList(description='\n            Loots applied when a sim is de-instanced on a street where this\n            effect is enacted. \n            ', tunable=LootActions.TunableReference(pack_safe=True)), 'scheduled_loot': OptionalTunable(description='\n            While enacted, loot to award on a schedule.\n            ', tunable=ScheduledLoot.TunableFactory())}

    @classmethod
    def _verify_tuning_callback(cls):
        pass

    @classmethod
    def _tuning_loaded_callback(cls):
        if cls.scheduled_loot is not None:
            cls.scheduled_loot = cls.scheduled_loot()

    def _register_callbacks(self):
        street_service = services.street_service()
        street_service.register_sim_added_callback(self._street, self._enact_for_sim_info)
        street_service.register_sim_removed_callback(self._street, self._repeal_for_sim_info)

    def _unregister_callbacks(self):
        street_service = services.street_service()
        street_service.unregister_sim_added_callback(self._street, self._enact_for_sim_info)
        street_service.unregister_sim_removed_callback(self._street, self._repeal_for_sim_info)

    def _enact_for_sim_info(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot in self.enact_loot:
            loot.apply_to_resolver(resolver)

    def _repeal_for_sim_info(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot in self.repeal_loot:
            loot.apply_to_resolver(resolver)

    def _start_schedule(self):
        if self.scheduled_loot is not None:
            self.scheduled_loot.set_resolver_gen(lambda : [SingleSimResolver(sim.sim_info) for sim in services.sim_info_manager().instanced_sims_gen()])
            self.scheduled_loot.start_loot_schedule()

    def _stop_schedule(self):
        if self.scheduled_loot is not None:
            self.scheduled_loot.set_resolver_gen(None)
            self.scheduled_loot.stop_loot_schedule()

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if self._street is None:
            return
        if self.policy.enacted:
            if self._street is services.current_street():
                for sim in services.sim_info_manager().instanced_sims_gen():
                    self._enact_for_sim_info(sim.sim_info)
                self._register_callbacks()
                self._start_schedule()
            else:
                self._unregister_callbacks()
                self._stop_schedule()

    def enact(self):
        if self._street is services.current_street():
            if self.enact_loot is not None:
                for sim in services.sim_info_manager().instanced_sims_gen():
                    self._enact_for_sim_info(sim.sim_info)
            self._start_schedule()
            self._register_callbacks()

    def repeal(self):
        if self._street is services.current_street():
            if self.repeal_loot is not None:
                for sim in services.sim_info_manager().instanced_sims_gen():
                    self._repeal_for_sim_info(sim.sim_info)
            self._stop_schedule()
            self._unregister_callbacks()

class StreetUtilityShutoffEffect(StreetEffect):
    INSTANCE_TUNABLES = {'utility': TunableEnumEntry(Utilities, None), 'shutoff_reason': TunableEnumEntry(description='\n            The utility shutoff reason for bills. This determines how important the\n            bills tooltip is when we shutoff the utility for delinquent bills\n            relative to other shutoff reasons.\n            ', tunable_type=UtilityShutoffReasonPriority, default=UtilityShutoffReasonPriority.NO_REASON), 'shutoff_tooltip': OptionalTunable(description='\n            A tooltip to show when an interaction cannot be run due to this\n            utility being shutoff.\n            ', tunable=TunableLocalizedStringFactory(description='\n                A tooltip to show when an interaction cannot be run due to this\n                utility being shutoff.\n                ')), 'start_notification': OptionalTunable(description='\n            A TNS that is displayed when the active lot is losing the utility.\n            ', tunable=UiDialogNotification.TunableFactory()), 'end_notification': OptionalTunable(description='\n            A TNS that is displayed when the active lot utility is restored.\n            ', tunable=UiDialogNotification.TunableFactory()), 'schedule_data': WeeklySchedule.TunableFactory(description='\n            The information to schedule points during the week that\n            the Street Policy Effect, if enacted, will turn off the tuned\n            utility.\n            ')}

    def __init__(self):
        super().__init__()
        self._schedule = None
        self._end_alarm = None
        self._zone_ids_impacted = None

    def _activate_schedule(self):
        if self._street is None or self.policy is None or self.policy.enacted and self._schedule is not None:
            return
        self._schedule = self.schedule_data(start_callback=self._scheduled_start_action, schedule_immediate=True, cross_zone=True)

    @staticmethod
    def _should_have_utility_shut_off(venue_tuning):
        return venue_tuning is not None and (venue_tuning.is_residential or venue_tuning.is_university_housing)

    def _collect_residential_zones(self):
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        residential_zone_ids = []
        for zone_id in get_zone_ids_from_street(self._street):
            venue_key = build_buy.get_current_venue(zone_id, allow_ineligible=True)
            venue_tuning = venue_manager.get(venue_key)
            if StreetUtilityShutoffEffect._should_have_utility_shut_off(venue_tuning):
                residential_zone_ids.append(zone_id)
        return residential_zone_ids

    def _scheduled_start_action(self, scheduler, alarm_data, extra_data):
        if self._end_alarm is not None:
            if self._end_alarm.finishing_time < alarm_data.end_time:
                alarms.cancel_alarm(self._end_alarm)
                self._end_alarm = None
            else:
                return
        now = services.time_service().sim_now
        time_to_end = alarm_data.end_time - now.time_since_beginning_of_week()
        self._end_alarm = alarms.add_alarm(self, time_to_end, lambda _: self._scheduled_end_action(), cross_zone=True)
        self._zone_ids_impacted = self._collect_residential_zones()
        for zone_id in self._zone_ids_impacted:
            self._turn_off_utilities_for_zone(zone_id)
        services.venue_game_service().on_venue_type_changed.register(self._on_venue_type_changed)

    def _scheduled_end_action(self):
        if self._end_alarm is None:
            return
        self._end_alarm = None
        services.venue_game_service().on_venue_type_changed.unregister(self._on_venue_type_changed)
        if self._zone_ids_impacted:
            for zone_id in self._zone_ids_impacted:
                self._turn_on_utilities_for_zone(zone_id)
            self._zone_ids_impacted = None

    def _handle_notification(self, notification, zone_id):
        if notification is not None and services.current_zone_id() == zone_id:
            notification = notification(None, resolver=GlobalResolver())
            notification.show_dialog()

    def _on_venue_type_changed(self, zone_id, active_venue_type):
        utility_can_be_shut_off = StreetUtilityShutoffEffect._should_have_utility_shut_off(active_venue_type)
        if zone_id in self._zone_ids_impacted:
            if not utility_can_be_shut_off:
                del self._zone_ids_impacted[zone_id]
                self._turn_on_utilities_for_zone(zone_id)
        elif utility_can_be_shut_off:
            self._zone_ids_impacted.append(zone_id)
            self._turn_off_utilities_for_zone(zone_id)

    def _turn_off_utilities_for_zone(self, zone_id):
        self._handle_notification(self.start_notification, zone_id)
        utilities_manager = game_services.service_manager.utilities_manager.get_manager_for_zone(zone_id)
        utilities_manager.shut_off_utility(self.utility, self.shutoff_reason, self.shutoff_tooltip)

    def _turn_on_utilities_for_zone(self, zone_id):
        self._handle_notification(self.end_notification, zone_id)
        utilities_manager = game_services.service_manager.utilities_manager.get_manager_for_zone(zone_id)
        utilities_manager.restore_utility(self.utility, self.shutoff_reason)

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if self._street is None:
            return
        self._activate_schedule()

    def enact(self):
        self._activate_schedule()

    def repeal(self):
        if self._schedule is not None:
            self._schedule.destroy()
            self._schedule = None
            self._scheduled_end_action()

class _WeatherParamData(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'interpolation_time': TunableSimMinute(description='\n            The time in sim minutes over which to transition to the new value,\n            if this occurs during simulation.\n            ', minimum=0.0, default=15.0), 'new_value': Tunable(description='\n            The value that we will set this parameter to.\n            ', tunable_type=float, default=1.0)}

class StreetWeatherEffect(StreetEffect):
    INSTANCE_TUNABLES = {'enact_data': _WeatherParamData.TunableFactory(description='\n            The value of the parameter that will be sent when this effect is enacted.\n            '), 'repeal_data': _WeatherParamData.TunableFactory(description='\n            The value of the parameter that will be sent when this effect is repealed.\n            '), 'weather_parameter_type': TunableVariant(description='\n            The parameter that we wish to change.\n            ', weather_effect_type=TunableEnumEntry(tunable_type=WeatherEffectType, default=WeatherEffectType.ECO_FOOTPRINT), cloud_type=TunableEnumEntry(tunable_type=CloudType, default=CloudType.SKYBOX_INDUSTRIAL))}

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if self.policy.enacted and self._street is services.current_street():
            self._send_parameter_update_op(self.enact_data, from_load=True)

    def enact(self):
        self._send_parameter_update_op(self.enact_data)

    def repeal(self):
        self._send_parameter_update_op(self.repeal_data)

    def _send_parameter_update_op(self, data, from_load=False):
        start_time = services.time_service().sim_now
        end_value = data.new_value
        if from_load:
            start_value = end_value
            end_time = start_time
        else:
            start_value = self.repeal_data.new_value if data is self.enact_data else self.enact_data.new_value
            end_time = start_time + create_time_span(minutes=data.interpolation_time)
        op = SeasonParameterUpdateOp(self.weather_parameter_type, start_value, start_time, end_value, end_time)
        Distributor.instance().add_op_with_no_owner(op)

class StreetCreateSituationEffect(StreetEffect):
    INSTANCE_TUNABLES = {'situation': TunableReference(description='\n            The situation to start.\n            ', manager=services.situation_manager())}

    def finalize_startup(self, policy):
        super().finalize_startup(policy)
        if not self.policy.enacted:
            return
        if self._street is not services.current_street():
            return
        situation_manager = services.get_zone_situation_manager()
        if not situation_manager.get_situations_by_type(self.situation):
            self.enact()

    def enact(self):
        situation_manager = services.get_zone_situation_manager()
        situation_manager.create_situation(self.situation, user_facing=False)

    def repeal(self):
        pass
