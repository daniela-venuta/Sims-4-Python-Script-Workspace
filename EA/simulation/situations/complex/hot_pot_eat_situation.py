import servicesimport sims4.resourcesfrom indexed_manager import CallbackTypesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReferencefrom sims.sim_info_types import Agefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom situations.situation_job import SituationJobTARGET_OBJECT_TOKEN = 'target_object'
class _GatherAtHotPot(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        self.owner.cleanup_expired_sims()
        if self.owner is None:
            return
        self._change_state(self.owner.start_hot_pot_state())

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.target_object)

    def handle_event(self, sim_info, event, resolver):
        try:
            self._sim_info = sim_info
            super().handle_event(sim_info, event, resolver)
        finally:
            self._sim_info = None

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.set_sim_as_ready(self._sim_info)
        if not self.owner.gathering_sim_ids:
            self._change_state(self.owner.start_hot_pot_state())

class _StartHotPot(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        self.owner.assign_host_if_neccesary()
        super().on_activate(reader=reader)

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.target_object)

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.wait_for_meal_ready_state())

class _WaitForMealReady(CommonSituationState):
    FACTORY_TUNABLES = {'hot_pot_ready_state': TunableReference(description='\n            The object state value that represents the hot pot becoming ready\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True)}

    def __init__(self, hot_pot_ready_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hot_pot_ready_state = hot_pot_ready_state

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self.owner.target_object.add_state_changed_callback(self._hot_pot_ready_state_change)

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.target_object)

    def _hot_pot_ready_state_change(self, owner, state, old_value, new_value):
        if new_value == self.hot_pot_ready_state:
            self._change_state(self.owner.eat_hot_pot_state())

    def timer_expired(self):
        self._change_state(self.owner.eat_hot_pot_state())

    def on_deactivate(self):
        self.owner.target_object.remove_state_changed_callback(self._hot_pot_ready_state_change)
        super().on_deactivate()

class _EatHotPot(CommonSituationState):
    FACTORY_TUNABLES = {'hot_pot_done_state': TunableReference(description='\n            The object state value that represents the hot pot becomes empty\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True)}

    def __init__(self, hot_pot_done_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hot_pot_done_state = hot_pot_done_state

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self.owner.target_object.add_state_changed_callback(self._hot_pot_empty_state_change)

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.target_object)

    def _hot_pot_empty_state_change(self, owner, state, old_value, new_value):
        if new_value == self.hot_pot_done_state:
            self._change_state(self.owner.eat_hot_pot_state())

    def timer_expired(self):
        self.owner._self_destruct()

    def on_deactivate(self):
        self.owner.target_object.remove_state_changed_callback(self._hot_pot_empty_state_change)
        super().on_deactivate()

class HotPotEatSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'guest_job': SituationJob.TunableReference(description='\n            The situation job for those gathering to eat\n            '), 'host_job': SituationJob.TunableReference(description='\n            The situation job for the Sim responsible for starting the hot pot\n            '), 'gather_at_hot_pot_state': _GatherAtHotPot.TunableFactory(description='\n            The state to bring all picked Sims to gather at the hot pot.\n            ', display_name='1. Gather at Hot Pot State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'start_hot_pot_state': _StartHotPot.TunableFactory(description='\n            The state to have an actor start the hot pot cooking.\n            ', display_name='2. Start Hot Pot State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'wait_for_meal_ready_state': _WaitForMealReady.TunableFactory(description='\n            The state that will have all picked Sims waiting around the hot pot, talking.\n            ', display_name='3. Wait for Meal Ready State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'eat_hot_pot_state': _EatHotPot.TunableFactory(description='\n            The state that will have all Sims consume from the hot pot.\n            ', display_name='4. Eat Hot Pot', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'hot_pot_empty_state': TunableReference(description="\n            The object state value that represents the hot pot becoming emptied of all food,\n            This occurs when a Sim uses 'Empty Hot Pot'\n            ", manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gathering_sim_ids = set()
        self._ready_sim_ids = set()
        self.target_object = self._get_target_object()
        object_manager = services.object_manager()
        object_manager.register_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_object_removed)
        if self.target_object:
            self.target_object.add_state_changed_callback(self._hot_pot_state_change)
            self.target_object.register_on_location_changed(self._on_hot_pot_location_changed)

    def _destroy(self):
        object_manager = services.object_manager()
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_object_removed)
        if self.target_object:
            self.target_object.remove_state_changed_callback(self._hot_pot_state_change)
            self.target_object.unregister_on_location_changed(self._on_hot_pot_location_changed)
        super()._destroy()

    def start_situation(self):
        super().start_situation()
        self._change_state(self.gather_at_hot_pot_state())

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override)
        self.gathering_sim_ids.add(sim.id)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self.gathering_sim_ids.discard(sim.id)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GatherAtHotPot, factory=cls.gather_at_hot_pot_state), SituationStateData(2, _StartHotPot, factory=cls.start_hot_pot_state), SituationStateData(3, _WaitForMealReady, factory=cls.wait_for_meal_ready_state), SituationStateData(4, _EatHotPot, factory=cls.eat_hot_pot_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.gather_at_hot_pot_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        return cls.guest_job

    def get_target_object(self):
        return self.target_object

    def _get_target_object(self):
        reader = self._seed.custom_init_params_reader
        if reader is None:
            target_object_id = self._seed.extra_kwargs.get('default_target_id', None)
        else:
            target_object_id = reader.read_uint64(TARGET_OBJECT_TOKEN, None)
        if target_object_id:
            return services.object_manager().get(target_object_id)
        else:
            return

    def cleanup_expired_sims(self):
        sim_info_manager = services.sim_info_manager()
        for sim_id in tuple(self.gathering_sim_ids):
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            else:
                sim = sim_info.get_sim_instance()
                if sim is not None and self.is_sim_in_situation(sim):
                    self.remove_sim_from_situation(sim)

    def set_sim_as_ready(self, sim_info):
        if sim_info is None:
            return
        self.gathering_sim_ids.discard(sim_info.id)
        self._ready_sim_ids.add(sim_info.id)

    def assign_host_if_neccesary(self):
        if self.get_num_sims_in_job(job_type=self.host_job) > 0:
            return
        for sim in self.all_sims_in_situation_gen():
            if sim.age >= Age.TEEN:
                self._set_job_for_sim(sim, self.host_job)
                return

    def _hot_pot_state_change(self, owner, state, old_value, new_value):
        if new_value == self.hot_pot_empty_state:
            self._self_destruct()

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self.target_object is not None:
            writer.write_uint64(TARGET_OBJECT_TOKEN, self.target_object.id)

    def _on_object_removed(self, obj):
        if obj.id == self.target_object.id:
            self._self_destruct()

    def _on_hot_pot_location_changed(self, obj, *args, **kwargs):
        if obj.id == self.target_object.id and obj.is_in_inventory():
            self._self_destruct()
lock_instance_tunables(HotPotEatSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)