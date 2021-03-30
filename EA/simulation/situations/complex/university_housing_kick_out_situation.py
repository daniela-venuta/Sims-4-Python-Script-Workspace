from event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom server_commands.household_commands import household_split, trigger_move_in_move_out, is_zone_occupiedfrom sims.university.university_commands import get_target_household_id_for_zonefrom sims.university.university_enums import UniversityHousingKickOutReasonfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationUserFacingType, SituationDisplayPriorityfrom ui.ui_dialog import UiDialogOkfrom world.travel_service import travel_sim_to_zoneimport servicesimport sims4logger = sims4.log.Logger('UniversityHousingKickOutSituation', default_owner='bnguyen')
class PreparationState(CommonSituationState):
    pass

class UniversityHousingKickOutSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'preparation_state': PreparationState.TunableFactory(description='\n            The state in which the sim prepares before being kicked out.\n            ', display_name='01_preparation_state', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'start_dialog_map': TunableMapping(description='\n            Map of kick out reason to tunable dialog that will display when\n            the situation begins.\n            ', key_type=TunableEnumEntry(tunable_type=UniversityHousingKickOutReason, default=UniversityHousingKickOutReason.NONE, invalid_enums=UniversityHousingKickOutReason.NONE, pack_safe=False), key_name='Kick Out Reason', value_type=UiDialogOk.TunableFactory(), value_name='Start Dialog', tuning_group=GroupNames.UI), 'timeout_dialog': UiDialogOk.TunableFactory(description='\n            Dialog that appears when the situation times out.\n            ', tuning_group=GroupNames.UI), 'save_lock_tooltip_message': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI)}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._kick_out_reason = self._seed.extra_kwargs.get('kick_out_reason', None)
        self._additional_sim_ids = self._seed.extra_kwargs.get('additional_sim_ids', None)
        self._university_housing_destination_zone_id = self._seed.extra_kwargs.get('university_housing_destination_zone_id', 0)
        self._host_sim_id = self._seed._guest_list._host_sim_id

    def start_situation(self):
        end_situation = True
        if self._kick_out_reason in self.start_dialog_map:
            sim_info = services.sim_info_manager().get(self._host_sim_id)
            map_entry = self.start_dialog_map[self._kick_out_reason]
            if map_entry is not None:
                resolver = SingleSimResolver(sim_info)
                dialog = map_entry(None, resolver)
                dialog.show_dialog()
                end_situation = False
        if self._kick_out_reason == UniversityHousingKickOutReason.BABY and not self._additional_sim_ids:
            logger.error('Attempting to kick sim out of university housing for {} without a valid parent', self._kick_out_reason, owner='bnguyen')
        if end_situation:
            self._self_destruct()
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(self.preparation_state())
        services.get_event_manager().register(self, (TestEvent.HouseholdSplitPanelClosed,))
        services.get_event_manager().register(self, (TestEvent.SimEnrolledInUniversity,))

    def _destroy(self):
        super()._destroy()
        services.get_event_manager().unregister(self, (TestEvent.HouseholdSplitPanelClosed,))
        services.get_event_manager().unregister(self, (TestEvent.SimEnrolledInUniversity,))

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.HouseholdSplitPanelClosed:
            self._self_destruct()
        elif event == TestEvent.SimEnrolledInUniversity:
            enrolled_sim_id = resolver.event_kwargs['enrolled_sim_id']
            if enrolled_sim_id is self._host_sim_id:
                self._self_destruct()

    def _show_household_split_dialog(self, source_household_id):
        selected_sim_ids = [self._host_sim_id]
        if self._additional_sim_ids is not None:
            selected_sim_ids += self._additional_sim_ids
        account = services.client_manager().get_first_client().account
        target_household_id = get_target_household_id_for_zone(self._university_housing_destination_zone_id, account)
        allow_sim_transfer = self._kick_out_reason != UniversityHousingKickOutReason.MOVED
        household_split(sourceHouseholdId=source_household_id, targetHouseholdId=target_household_id, cancelable=False, allow_sim_transfer=allow_sim_transfer, selected_sim_ids=selected_sim_ids, destination_zone_id=self._university_housing_destination_zone_id, callback_command_name='university.end_kickout_situation')

    def _kickout_single_sim(self):
        sim_info = services.sim_info_manager().get(self._host_sim_id)
        household = sim_info.household if sim_info is not None else None
        if household is None:
            return
        zone_id = self._university_housing_destination_zone_id
        household.set_household_lot_ownership(zone_id=zone_id)
        if zone_id == 0:
            trigger_move_in_move_out(is_in_game_evict=True)
        else:
            travel_sim_to_zone(sim_info.id, zone_id)

    def pre_destroy(self):
        if not services.get_persistence_service().is_save_locked_exclusively_by_holder(self):
            self._self_destruct()
            return
        services.get_persistence_service().unlock_save(self)
        sim_info = services.sim_info_manager().get(self._host_sim_id)
        if sim_info is not None:
            sim_info.degree_tracker.clear_kickout_info()
        household = sim_info.household if sim_info is not None else None
        if household is None:
            self._self_destruct()
            return
        active_household = services.active_household()
        if active_household is None or sim_info not in active_household:
            self._self_destruct()
            return
        self_destruct = True
        destination_zone_occupied = is_zone_occupied(self._university_housing_destination_zone_id)
        if len(household) > 1 or destination_zone_occupied:
            self._show_household_split_dialog(household.id)
            self_destruct = False
        else:
            self._kickout_single_sim()
        services.venue_service().set_university_housing_kick_out_completed()
        if self_destruct:
            self._self_destruct()

    def _situation_timed_out(self, *args, **kwargs):

        def on_response(dialog):
            self.pre_destroy()

        sim_info = services.sim_info_manager().get(self._host_sim_id)
        if sim_info is not None:
            resolver = SingleSimResolver(sim_info)
            dialog = self.timeout_dialog(None, resolver)
            if dialog is not None:
                dialog.show_dialog(on_response=on_response)

    def get_lock_save_reason(self):
        return self.save_lock_tooltip_message

    @property
    def user_facing_type(self):
        return SituationUserFacingType.UNIVERSITY_HOUSING_KICK_OUT_EVENT

    @property
    def situation_display_priority(self):
        return SituationDisplayPriority.HIGH

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(1, cls.preparation_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list()

    @classmethod
    def default_job(cls):
        pass
