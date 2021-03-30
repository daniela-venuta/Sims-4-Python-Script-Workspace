import itertoolsimport weakreffrom protocolbuffers import Consts_pb2, UI_pb2, InteractionOps_pb2from clock import ClockSpeedModefrom date_and_time import TimeSpanfrom distributor import shared_messagesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom drama_scheduler.drama_node import DramaNodeUiDisplayTypefrom event_testing.resolver import SingleSimResolverfrom households.household_object_preference_tracker import HouseholdObjectPreferenceTrackerfrom objects import ALL_HIDDEN_REASONSfrom sims.household import Householdfrom sims.sim_spawner import SimSpawnerfrom sims4.tuning.tunable import TunableList, TunableReferencefrom travel_group.travel_group_telemetry import write_travel_group_telemetry, TELEMETRY_HOOK_TRAVEL_GROUP_EXTENDfrom world.region import get_region_description_id_from_zone_id, RegionTypefrom world.travel_group_tuning import TravelGroupTuningimport alarmsimport clockimport date_and_timeimport distributorimport servicesimport sims4.loglogger = sims4.log.Logger('TravelGroup')
class TravelGroup:
    ON_LEAVE_TRAVEL_GROUP_LOOT = TunableList(description='\n        A list of loot to apply to a Sim when they leave a travel\n        group.\n        ', tunable=TunableReference(description='\n            The loot to apply when the Sim leaves a travel group.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))

    def __init__(self, zone_id=0, played=False, create_timestamp=None, end_timestamp=None, setup_alarms=False):
        self.id = 0
        self.manager = None
        self.primitives = ()
        self._zone_id = zone_id
        self.played = played
        self.create_timestamp = create_timestamp
        self.end_timestamp = end_timestamp
        self._sim_infos = []
        self._end_vacation_alarm = None
        self._days_left_notification_alarm = None
        self._hours_left_notification_alarm = None
        if end_timestamp is not None and setup_alarms:
            self.setup_rented_zone_alarms()
        self.object_preference_tracker = HouseholdObjectPreferenceTracker(self)

    def __repr__(self):
        sim_strings = []
        for sim_info in self._sim_infos:
            sim_strings.append(str(sim_info))
        return 'Travel Group {} : {}'.format(self.id, '; '.join(sim_strings))

    def __len__(self):
        return len(self._sim_infos)

    def __iter__(self):
        return iter(self._sim_infos)

    def ref(self, callback=None):
        return weakref.ref(self, callback)

    def get_create_op(self, *args, **kwargs):
        return distributor.ops.TravelGroupCreate(self, *args, zone_id=self.zone_id, **kwargs)

    def get_delete_op(self):
        return distributor.ops.TravelGroupDelete()

    def get_create_after_objs(self):
        return ()

    @property
    def valid_for_distribution(self):
        return True

    @property
    def zone_id(self):
        return self._zone_id

    @property
    def uid(self):
        return self.id

    @property
    def ui_display_type(self):
        return DramaNodeUiDisplayType.VACATION

    @property
    def travel_group_size(self):
        return len(self)

    @property
    def duration_time_span(self):
        return self.end_timestamp - self.create_timestamp

    @property
    def duration_time_in_minutes(self):
        if self.end_timestamp is None:
            return 0
        return self.duration_time_span.in_minutes()

    def create_calendar_entry(self):
        calendar_entry = UI_pb2.CalendarEntry()
        calendar_entry.entry_id = self.id
        calendar_entry.entry_type = self.ui_display_type
        calendar_entry.start_time = self.create_timestamp.absolute_ticks()
        calendar_entry.end_time = self.end_timestamp.absolute_ticks()
        calendar_entry.scoring_enabled = False
        calendar_entry.deletable = False
        calendar_entry.zone_id = self._zone_id
        for sim_info in self:
            calendar_entry.household_sim_ids.append(sim_info.id)
        return calendar_entry

    def instanced_sims_gen(self, allow_hidden_flags=0):
        for sim_info in self._sim_infos:
            if sim_info.is_instanced(allow_hidden_flags=allow_hidden_flags):
                yield sim_info.get_sim_instance(allow_hidden_flags=allow_hidden_flags)

    def sim_info_gen(self):
        for sim_info in self._sim_infos:
            yield sim_info

    @property
    def free_slot_count(self):
        used_slot_count = len(self)
        return Household.MAXIMUM_SIZE - used_slot_count

    def can_add_to_travel_group(self, sim_info):
        for household_sim_info in sim_info.household:
            if household_sim_info.travel_group_id != 0:
                if household_sim_info.travel_group_id != self.id:
                    return False
                break
        if sim_info in self:
            return False
        return self.free_slot_count >= 1

    def add_sim_info(self, sim_info):
        if sim_info in self._sim_infos:
            logger.error('Attempted to add {} to a same travel group.', sim_info)
            return False
        if sim_info.household.any_member_in_travel_group():
            for hh_sim_info in sim_info.household:
                if not hh_sim_info.is_in_travel_group():
                    pass
                elif hh_sim_info.travel_group is not self:
                    logger.error('Attempted to add a second travel group to household of {}. This is not allowed.', sim_info)
                    return False
        self._sim_infos.append(sim_info)
        sim_info.assign_to_travel_group(self)
        sim_info.career_tracker.resend_at_work_infos()
        if sim_info.is_selectable:
            services.get_first_client().send_selectable_sims_update()
        if self.is_selectable_sim_in_travel_group:
            calendar_service = services.calendar_service()
            if calendar_service is not None:
                calendar_service.update_on_calendar(self)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            self.give_instanced_sim_loot(sim_info)
            sim.update_intended_position_on_active_lot(update_ui=True)
        return True

    def give_instanced_sim_loot(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot in TravelGroupTuning.INSTANCED_SIM_LOOT:
            loot.apply_to_resolver(resolver)

    def remove_sim_info(self, sim_info, destroy_on_empty=True):
        if sim_info not in self._sim_infos:
            logger.error('Trying to remove a sim from a travel group they do not belong to. Sim: {}, Travel Group: {}', sim_info, self)
        was_active_household_group = self.is_selectable_sim_in_travel_group
        client = services.get_first_client()
        if sim_info is services.active_sim_info():
            client.set_next_sim()
        sim_info.remove_from_travel_group(self)
        self._sim_infos.remove(sim_info)
        sim_info.career_tracker.resend_at_work_infos()
        if sim_info.is_selectable:
            client.send_selectable_sims_update()
        resolver = SingleSimResolver(sim_info)
        for loot_action in TravelGroup.ON_LEAVE_TRAVEL_GROUP_LOOT:
            loot_action.apply_to_resolver(resolver)
        if all(travel_sim_info.household.home_zone_id == 0 for travel_sim_info in self._sim_infos):
            self.played = False
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            sim.update_intended_position_on_active_lot(update_ui=True)
        if was_active_household_group:
            calendar_service = services.calendar_service()
            if calendar_service is not None:
                if self.is_selectable_sim_in_travel_group:
                    calendar_service.update_on_calendar(self)
                else:
                    calendar_service.remove_on_calendar(self.uid)
        if self._sim_infos or destroy_on_empty:
            services.travel_group_manager().destroy_travel_group_and_release_zone(self, last_sim_info=sim_info, return_objects=True)

    def rent_zone(self, zone_id):
        self._zone_id = zone_id

    @property
    def is_vacation_over(self):
        if self.end_timestamp is None:
            return False
        return self.end_timestamp - self.create_timestamp > TimeSpan.ZERO

    @property
    def is_active_sim_in_travel_group(self):
        active_sim_info = services.active_sim_info()
        return active_sim_info is not None and active_sim_info in self

    @property
    def is_selectable_sim_in_travel_group(self):
        return any(sim_info.is_selectable for sim_info in self)

    def extend_vacation(self, duration_days, cost=0):
        extension = clock.interval_in_sim_days(duration_days)
        self.end_timestamp = self.end_timestamp + extension
        self.setup_rented_zone_alarms()
        services.active_household().funds.try_remove(cost, reason=Consts_pb2.FUNDS_MONEY_VACATION, sim=services.get_active_sim())
        leader_sim_info = services.active_sim_info()
        if leader_sim_info not in self:
            leader_sim_info = self._sim_infos[0]
        if self.is_selectable_sim_in_travel_group:
            calendar_service = services.calendar_service()
            if calendar_service is not None:
                calendar_service.update_on_calendar(self)
        write_travel_group_telemetry(self, TELEMETRY_HOOK_TRAVEL_GROUP_EXTEND, sim_info=leader_sim_info)

    def end_vacation(self):
        active_household = services.active_household()
        current_zone_id = services.current_zone_id()
        current_region_id = get_region_description_id_from_zone_id(current_zone_id)
        rental_region_id = get_region_description_id_from_zone_id(self._zone_id)
        if current_region_id != rental_region_id or not active_household.any_member_belong_to_travel_group_id(self.id):
            at_home = current_zone_id == active_household.home_zone_id
            for sim_info in self:
                if active_household.id == sim_info.household_id and at_home:
                    if not sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                        SimSpawner.spawn_sim(sim_info)
                        if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS))
                        else:
                            sim_info.inject_into_inactive_zone(sim_info.household.home_zone_id)
                elif sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                    services.get_zone_situation_manager().make_sim_leave_now_must_run(sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS))
                else:
                    sim_info.inject_into_inactive_zone(sim_info.household.home_zone_id)
            services.travel_group_manager().destroy_travel_group_and_release_zone(self, return_objects=True)
            return
        for instanced_sim in active_household.instanced_sims_gen():
            instanced_sim.queue.cancel_all()
        travel_info = InteractionOps_pb2.TravelSimsToZone()
        travel_info.zone_id = active_household.home_zone_id
        active_sims_on_zone = [active_sim_info for active_sim_info in active_household if active_sim_info.zone_id == current_zone_id]
        for sim_info in itertools.chain(self, active_sims_on_zone):
            if active_household.id == sim_info.household_id:
                if sim_info.sim_id not in travel_info.sim_ids:
                    travel_info.sim_ids.append(sim_info.sim_id)
            else:
                sim_info.inject_into_inactive_zone(sim_info.household.home_zone_id, skip_instanced_check=True)
        distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_TRAVEL_SIMS_TO_ZONE, travel_info)
        services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)
        services.travel_group_manager().destroy_travel_group_and_release_zone(self)

    def _travel_group_end_callback(self, _):
        if not self.is_active_sim_in_travel_group:
            self.end_vacation()
            return
        self.show_extend_vacation_dialog()

    def _days_left_notification_callback(self, _):
        if not self.is_active_sim_in_travel_group:
            return
        notification = TravelGroupTuning.VACATION_ENDING_DAYS_TNS.notification_to_show(self)
        notification.show_dialog()

    def _hours_left_notification_callback(self, _):
        if not self.is_active_sim_in_travel_group:
            return
        time_left = self.end_timestamp - services.time_service().sim_now
        hours_left = int(time_left.in_hours())
        notification = TravelGroupTuning.VACATION_ENDING_HOURS_TNS.notification_to_show(self)
        notification.show_dialog(additional_tokens=(hours_left,))

    def setup_rented_zone_alarms(self):
        if self.end_timestamp is None:
            return
        if self._end_vacation_alarm is not None:
            alarms.cancel_alarm(self._end_vacation_alarm)
        time_now = services.time_service().sim_now
        self._end_vacation_alarm = alarms.add_alarm(self, self.end_timestamp - time_now, self._travel_group_end_callback, repeating=False)
        if self._days_left_notification_alarm is not None:
            alarms.cancel_alarm(self._days_left_notification_alarm)
        days_before_vacation_ends = clock.interval_in_sim_days(TravelGroupTuning.VACATION_ENDING_DAYS_TNS.days_before_vacation_ends)
        days_left_timestamp = self.end_timestamp + -days_before_vacation_ends
        if days_left_timestamp > time_now:
            self._days_left_notification_alarm = alarms.add_alarm(self, days_left_timestamp - time_now, self._days_left_notification_callback, repeating=False)
        if self._hours_left_notification_alarm is not None:
            alarms.cancel_alarm(self._hours_left_notification_alarm)
        hours_before_vacation_ends = clock.interval_in_sim_hours(TravelGroupTuning.VACATION_ENDING_HOURS_TNS.hours_before_vacation_ends)
        hours_left_timestamp = self.end_timestamp + -hours_before_vacation_ends
        if hours_left_timestamp > time_now:
            self._hours_left_notification_alarm = alarms.add_alarm(self, hours_left_timestamp - time_now, self._hours_left_notification_callback, repeating=False)

    def show_extend_vacation_dialog(self):
        if services.current_zone().ui_dialog_service.auto_respond:
            self.end_vacation()
        else:
            msg = UI_pb2.ExtendVacation()
            msg.travel_group_id = self.id
            msg.zone_id = self.zone_id
            for sim_info in self:
                msg.sim_ids.append(sim_info.id)
            delta_time = self.end_timestamp - services.time_service().sim_now
            delta_time = delta_time if delta_time > TimeSpan.ZERO else TimeSpan.ZERO
            days_remaining = float(delta_time.in_days())
            msg.days_remaining = days_remaining
            persistence_service = services.get_persistence_service()
            zone_data = persistence_service.get_zone_proto_buff(self.zone_id)
            msg.household_description_id = persistence_service.get_house_description_id(self.zone_id)
            msg.lot_name = zone_data.name
            msg.lot_daily_cost = services.current_zone().lot.furnished_lot_value
            op = shared_messages.create_message_op(msg, Consts_pb2.MSG_EXTEND_VACATION)
            Distributor.instance().add_op_with_no_owner(op)

    def load_data(self, travel_group_proto):
        self.id = travel_group_proto.travel_group_id
        self._zone_id = travel_group_proto.zone_id
        self.played = travel_group_proto.played
        self.create_timestamp = date_and_time.DateAndTime(travel_group_proto.create_time)
        if travel_group_proto.HasField('end_time'):
            self.end_timestamp = date_and_time.DateAndTime(travel_group_proto.end_time)
        sim_info_manager = services.sim_info_manager()
        for household_sim_ids in travel_group_proto.household_sim_ids:
            for sim_id in household_sim_ids.sim_ids:
                sim_info = sim_info_manager.get(sim_id)
                if sim_info is None:
                    logger.warn('Sim: {} who belonged to travel group {} no longer exists.', sim_id, self.id)
                else:
                    self._sim_infos.append(sim_info)
                    sim_info.assign_to_travel_group(self)
        if not self._sim_infos:
            return
        self.object_preference_tracker.load_data(travel_group_proto.object_preference_tracker, is_household=False)
        self.setup_rented_zone_alarms()
        active_sim_info = services.active_sim_info()
        if active_sim_info is not None and active_sim_info in self:
            now = services.time_service().sim_now
            if self.create_timestamp == now:
                if services.current_region().region_type == RegionType.REGIONTYPE_RESIDENTIAL:
                    notification = TravelGroupTuning.RESIDENTIAL_WELCOME_NOTIFICATION(active_sim_info)
                    notification.show_dialog()
            elif self.end_timestamp and not services.game_services.service_manager.is_traveling:
                notification = TravelGroupTuning.VACATION_CONTINUE_NOTIFICATION(active_sim_info)
                notification.show_dialog(additional_tokens=(active_sim_info.household.name, self.end_timestamp - now))
        if self.end_timestamp and self.is_selectable_sim_in_travel_group:
            calendar_service = services.calendar_service()
            if calendar_service is not None:
                calendar_service.mark_on_calendar(self)

    def save_data(self, travel_group_proto):
        travel_group_proto.travel_group_id = self.id
        travel_group_proto.zone_id = self.zone_id
        travel_group_proto.played = self.played
        travel_group_proto.create_time = self.create_timestamp.absolute_ticks()
        if self.end_timestamp:
            travel_group_proto.end_time = self.end_timestamp.absolute_ticks()
        travel_group_proto.ClearField('household_sim_ids')
        household_sims = {}
        for sim_info in self._sim_infos:
            household_sim_entry = household_sims.get(sim_info.household_id)
            if household_sim_entry is not None:
                household_sim_entry.append(sim_info.id)
            else:
                household_sims[sim_info.household_id] = [sim_info.id]
        for (household_id, sim_ids) in household_sims.items():
            with ProtocolBufferRollback(travel_group_proto.household_sim_ids) as household_sim_data:
                household_sim_data.household_id = household_id
                household_sim_data.sim_ids.extend(sim_ids)
        self.object_preference_tracker.save_data(travel_group_proto)
