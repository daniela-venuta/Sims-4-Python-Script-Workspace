import servicesfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom interactions.utils.line_utils import LineUtilsfrom objects.components.types import WAITING_LINE_COMPONENTfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonInteractionCompletedSituationState, SituationStateWAITING_IN_LINE_ID_TOKEN = 'waiting_in_line_id'WAITING_NEAR_LINE_IDS_TOKEN = 'waiting_near_line_ids'LINE_KEY_TOKEN = 'line_key'LINE_SIM_TARGET_ID_TOKEN = 'line_sim_target_id'
class GetSimsState(SituationState):
    pass

class _WaitingInLineState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if services.current_zone().is_zone_running or reader is not None:
            self.owner._change_state(self.owner._route_to_waiting_line_state())
            return
        self._register_custom_events()
        self.owner.try_to_push_routing_formation()

    def _register_custom_events(self):
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)
        self._test_event_register(TestEvent.RoutingFormationStarted)
        if self.owner.route_nearby_affordance is not None:
            self._test_event_register(TestEvent.InteractionExitedPipeline, self.owner.route_nearby_affordance)

    def _on_routing_formation_started(self, resolver):
        self.owner._on_routing_formation_started(slave=resolver.event_kwargs.get('slave'))

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.InteractionExitedPipeline:
            self._on_interaction_of_interest_complete(sim_info=sim_info, resolver=resolver)
        if event == TestEvent.RoutingFormationStarted:
            self._on_routing_formation_started(resolver)

    def _on_interaction_of_interest_complete(self, sim_info=None, resolver=None):
        if self.owner.is_sim_in_situation(sim_info.get_sim_instance()) and resolver.interaction.has_been_canceled:
            self.owner._self_destruct()

class _RouteToWaitingLineState(_WaitingInLineState):

    def on_activate(self, reader=None):
        if services.current_zone().is_zone_running or reader is not None:
            self.owner._self_destruct()
            return
        super().on_activate()

    def _on_interaction_of_interest_complete(self, sim_info=None, resolver=None):
        if not self.owner.is_sim_in_situation(sim_info.get_sim_instance()):
            return
        if resolver.interaction.has_been_canceled:
            self.owner._self_destruct()
        else:
            self.owner._change_state(self.owner._waiting_in_line_state())

class _RunStoredInteractionState(_WaitingInLineState):

    def _on_interaction_of_interest_complete(self, sim_info=None, resolver=None, **kwargs):
        if self.owner.is_sim_in_situation(sim_info.get_sim_instance()) and resolver.interaction.has_been_canceled:
            self.owner._self_destruct()

class WaitInLineTogether(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_route_to_waiting_line_state': _RouteToWaitingLineState.TunableFactory(description='\n            The state where sims route to the waiting line together.\n            ', display_name='1. Route to Line State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': False, 'time_out': None}), '_waiting_in_line_state': _WaitingInLineState.TunableFactory(description='\n            The wait in line state, which has the sims wait in the line after\n            routing there.\n            ', display_name='2. Waiting In Line State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': False, 'time_out': None}), '_run_stored_interaction_state': _RunStoredInteractionState.TunableFactory(description='\n            The run stored interaction state, which encapsulates the host sim \n            running the interaction they were lined up for after becoming\n            first in line.\n            ', display_name='3. Run Stored Interaction State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': False, 'time_out': None}), 'waiting_in_line_sim_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the sim waiting in the line.\n            ', tuning_group=GroupNames.ROLES), 'waiting_near_line_sim_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for a sim waiting near the sim waiting in \n            the line.\n            ', tuning_group=GroupNames.ROLES)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            self.line_key = reader.read_string16(LINE_KEY_TOKEN, None)
            self.line_interaction_target_id = reader.read_uint64(LINE_SIM_TARGET_ID_TOKEN, None)
            waiting_in_line_sim_id = reader.read_uint64(WAITING_IN_LINE_ID_TOKEN, None)
            self.waiting_in_line_sim = services.object_manager().get(waiting_in_line_sim_id)
            self.waiting_nearby_sim_ids = list(reader.read_uint64s(WAITING_NEAR_LINE_IDS_TOKEN, ()))
        else:
            self.line_key = self._seed.extra_kwargs.get('line_key', None)
            self.line_interaction_target_id = self._seed.extra_kwargs.get('target_id', None)
            self.waiting_in_line_sim = None
            self.waiting_nearby_sim_ids = []
        self._pushed_routing_formation = False
        self._stored_interaction = None
        self.route_nearby_fn = None
        self.route_nearby_affordance = None
        self._following_nearby_sim_ids = []

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GetSimsState), SituationStateData(2, _RouteToWaitingLineState, factory=cls._route_to_waiting_line_state), SituationStateData(3, _WaitingInLineState, factory=cls._waiting_in_line_state), SituationStateData(4, _RunStoredInteractionState, factory=cls._run_stored_interaction_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.waiting_in_line_sim_job_and_role_state.job, cls.waiting_in_line_sim_job_and_role_state.role_state), (cls.waiting_near_line_sim_job_and_role_state.job, cls.waiting_near_line_sim_job_and_role_state.role_state)]

    def _destroy(self):
        for sim_id in self.waiting_nearby_sim_ids:
            sim = services.object_manager().get(sim_id)
            if sim is None:
                pass
            else:
                for interaction in sim.get_all_running_and_queued_interactions():
                    if interaction.affordance is LineUtils.WAIT_IN_LINE_TOGETHER_ROUTING_FORMATION:
                        interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='WaitInLineTogetherSituation destroyed.')
        reserve_object = services.object_manager().get(self.line_interaction_target_id)
        if reserve_object.has_component(WAITING_LINE_COMPONENT):
            waiting_line = reserve_object.waiting_line_component.get_waiting_line(self.line_key)
            if waiting_line:
                for interaction in waiting_line._line:
                    if interaction.sim is self.waiting_in_line_sim:
                        interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='WaitInLineTogetherSituation destroyed')
                        break
        if reserve_object is not None and self.route_nearby_affordance is not None:
            if self.waiting_in_line_sim is None:
                return
            for interaction in self.waiting_in_line_sim.get_all_running_and_queued_interactions():
                if interaction.affordance is self.route_nearby_affordance:
                    interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='WaitInLineTogetherSituation destroyed.')
        if self._stored_interaction:
            self._stored_interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='WaitInLineTogetherSituation destroyed.')
        self.route_nearby_fn = None
        super()._destroy()

    def start_situation(self):
        super().start_situation()
        self._change_state(GetSimsState())

    def change_to_run_stored_interaction_state(self):
        self._change_state(self._run_stored_interaction_state())

    def change_to_route_to_waiting_line_state(self):
        self._change_state(self._route_to_waiting_line_state())

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if sim is self._guest_list.host_sim:
            self.waiting_in_line_sim = sim
            return
        if sim.id not in self.waiting_nearby_sim_ids:
            self.waiting_nearby_sim_ids.append(sim.id)
        if self.num_of_sims >= self.num_invited_sims and services.current_zone().is_zone_running:
            self._change_state(self._route_to_waiting_line_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self.waiting_in_line_sim is not None:
            writer.write_uint64(WAITING_IN_LINE_ID_TOKEN, self.waiting_in_line_sim.id)
        if self.waiting_nearby_sim_ids is not None:
            writer.write_uint64s(WAITING_NEAR_LINE_IDS_TOKEN, self.waiting_nearby_sim_ids)
        if self.line_key is not None:
            writer.write_string16(LINE_KEY_TOKEN, self.line_key)
        if self.line_interaction_target_id is not None:
            writer.write_uint64(LINE_SIM_TARGET_ID_TOKEN, self.line_interaction_target_id)

    def _on_routing_formation_started(self, slave=None):
        if self.is_sim_in_situation(slave) and slave is None:
            return
        self._following_nearby_sim_ids.append(slave.id)
        if len(self._following_nearby_sim_ids) >= len(self.waiting_nearby_sim_ids):
            if self.route_nearby_fn is not None:
                self.route_nearby_fn()
            else:
                self._self_destruct()

    def set_route_nearby_affordance(self, route_nearby_affordance):
        self.route_nearby_affordance = route_nearby_affordance
        if self.num_of_sims < self.num_invited_sims:
            return
        self._cur_state._test_event_register(TestEvent.InteractionExitedPipeline, route_nearby_affordance)
        self.try_to_push_routing_formation()

    def try_to_push_routing_formation(self):
        if self._pushed_routing_formation or self.route_nearby_affordance is None:
            return
        self._pushed_routing_formation = True
        waiting_in_line_sim = self.waiting_in_line_sim
        if waiting_in_line_sim is None:
            self._self_destruct()
            return
        for nearby_sim_id in self.waiting_nearby_sim_ids:
            nearby_sim = services.object_manager().get(nearby_sim_id)
            if nearby_sim is None:
                self._self_destruct()
                return
            wait_near_context = InteractionContext(nearby_sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST)
            success = nearby_sim.push_super_affordance(LineUtils.WAIT_IN_LINE_TOGETHER_ROUTING_FORMATION, waiting_in_line_sim, wait_near_context, allow_posture_changes=True, must_run_next=True, name_override='WaitNearSimInLineRoutingFormation')
            if not success:
                self._self_destruct()
