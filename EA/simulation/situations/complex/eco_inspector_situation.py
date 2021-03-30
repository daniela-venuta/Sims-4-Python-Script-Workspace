from eco_footprint import eco_footprint_tuningfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable import Tunable, OptionalTunable, TunableRangefrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationState, SituationStateData, TunableInteractionOfInterest, TunableReferencefrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4import mathlogger = sims4.log.Logger('EcoInspectorSituation', default_owner='amohananey')
class _WaitState(SituationState):
    pass

class _EcoInspectState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if self.owner.arrival_notification is not None:
            notification = self.owner.arrival_notification(services.active_sim_info(), resolver=SingleSimResolver(services.active_sim_info()))
            notification.show_dialog()
        for custom_key in self.owner.expel_smog.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        for custom_key in self.owner.leave.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete:
            if resolver(self.owner.expel_smog):
                self._change_state(self.owner.expelling_smog_state())
            elif resolver(self.owner.leave):
                if self.owner.leave_notification is not None:
                    notification = self.owner.leave_notification(services.active_sim_info(), resolver=SingleSimResolver(services.active_sim_info()))
                    notification.show_dialog()
                self._change_state(self.owner.leaving_state())

    def timer_expired(self):
        self._change_state(self.owner.leaving_state())

class _ExpellingSmogState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)

    def timer_expired(self):
        if self.owner.expel_smog_notification is not None:
            notification = self.owner.expel_smog_notification(services.active_sim_info(), resolver=SingleSimResolver(services.active_sim_info()))
            notification.show_dialog()
        EcoInspectorSituation.set_footprint_commodity_value(self.owner.initial_street_value + self.owner.delta_expel)
        self._change_state(self.owner.leaving_state())

class _LeavingState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        inspector = self.owner.inspector_person()
        if inspector is not None:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(inspector)
        service_npc_type = self.owner._service_npc_type
        now = services.time_service().sim_now
        household = self.owner._hiring_household
        service_record = household.get_service_npc_record(service_npc_type.guid64)
        service_record.time_last_finished_service = now
        self._service_npc = None
        self.owner._self_destruct()

class EcoInspectorSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'inspector_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the eco-inspector.\n            ', tuning_group=GroupNames.ROLES), 'eco_inspect_state': _EcoInspectState.TunableFactory(description='\n           Inspection + Vacuuming state\n            ', display_name='1. Eco Inspect', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'expelling_smog_state': _ExpellingSmogState.TunableFactory(description='\n           Expelling state\n            ', display_name='2. Expelling Smog', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leaving_state': _LeavingState.TunableFactory(description='\n            Inspector is leaving after Vacuuming.\n            ', display_name='3. Leaving State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'expel_smog': TunableInteractionOfInterest(description='\n            Social: listen to move to expelling_smog state\n            '), 'delta_expel': Tunable(description='\n            How much to increase the pollution level by?  \n            ', tunable_type=float, default=0.0), 'leave': TunableInteractionOfInterest(description='\n            Listen for this enter the leave state.\n            '), 'expel_smog_notification': OptionalTunable(description='\n            A TNS that is displayed after expelling smog.\n            ', tunable=UiDialogNotification.TunableFactory()), 'arrival_notification': OptionalTunable(description='\n            A TNS that is displayed pm arrival of the eco-inspector.\n            ', tunable=UiDialogNotification.TunableFactory()), 'leave_notification': OptionalTunable(description='\n            A TNS that after the eco-inspector leaves.\n            ', tunable=UiDialogNotification.TunableFactory()), 'service_npc_hireable': TunableReference(description='\n            Service NPC for the eco-inspector.\n            ', manager=services.service_npc_manager(), pack_safe=True), 'fake_perform_pollution_limit': Tunable(description='\n            Limit down to which to change pollution.  \n            ', tunable_type=float, default=0.0), 'fake_perform_vacuum_delta': TunableRange(description='\n            How much to decrease the pollution level by?  \n            ', tunable_type=float, default=1.0, minimum=0.1)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service_npc = None
        self._service_start_time = None
        reader = self._seed.custom_init_params_reader
        self._service_npc_type = self.service_npc_hireable
        self._hiring_household = services.household_manager().get(reader.read_uint64('household_id', 0))
        if self._hiring_household is None:
            raise ValueError('Invalid household for situation: {}'.format(self))
        self.initial_street_value = EcoInspectorSituation.get_footprint_commodity_value()

    @staticmethod
    def get_footprint_commodity_value():
        street_service = services.street_service()
        policy_provider = street_service.get_provider(services.current_street())
        return policy_provider.commodity_tracker.get_value(eco_footprint_tuning.EcoFootprintTunables.STREET_FOOTPRINT, add=True)

    @staticmethod
    def set_footprint_commodity_value(value):
        street_service = services.street_service()
        policy_provider = street_service.get_provider(services.current_street())
        policy_provider.commodity_tracker.set_value(eco_footprint_tuning.EcoFootprintTunables.STREET_FOOTPRINT, value)
        policy_provider.distribute_neighborhood_update()

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _WaitState), SituationStateData(2, _EcoInspectState, factory=cls.eco_inspect_state), SituationStateData(3, _ExpellingSmogState, factory=cls.expelling_smog_state), SituationStateData(4, _LeavingState, factory=cls.leaving_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.inspector_job_and_role_state.job, cls.inspector_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        return cls.inspector_job_and_role_state.job

    @classmethod
    def fake_perform_job(cls):
        _inspector = EcoInspectorSituation
        _commodity_val = _inspector.get_footprint_commodity_value()
        if _commodity_val < cls.fake_perform_pollution_limit:
            return
        no_steps = math.ceil((_commodity_val - cls.fake_perform_pollution_limit)/cls.fake_perform_vacuum_delta)
        _inspector.set_footprint_commodity_value(_commodity_val - no_steps*cls.fake_perform_vacuum_delta)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_uint64('household_id', self._hiring_household.id)

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if self.inspector_person() is not None:
            self._change_state(self.eco_inspect_state())

    def inspector_person(self):
        sim = next(self.all_sims_in_job_gen(self.inspector_job_and_role_state.job), None)
        return sim

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._service_npc = sim
        services.current_zone().service_npc_service.cancel_service(self._hiring_household, self._service_npc_type)

    def start_situation(self):
        super().start_situation()
        self._change_state(_WaitState())
