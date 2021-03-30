from interactions.interaction_finisher import FinishingTypefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonInteractionCompletedSituationStateimport servicesimport sims4logger = sims4.log.Logger('Prisoner Escort Situation', default_owner='madang')
class _EscortState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Escort Sim and the Prisoner Sim are routing to a spawn point.')
        super().on_activate(reader=reader)
        self.owner.break_routing_formations()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.despawn_state())

    def timer_expired(self):
        self._change_state(self.owner.despawn_state())

class _DespawnState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Sims have completed the escort routing.')
        super().on_activate(reader=reader)
        self.owner.break_routing_formations()

    def _despawn_sims(self):
        escort_sim = self.owner.get_escort()
        prisoner_sim = self.owner.get_prisoner()
        if escort_sim is not None and escort_sim.sim_info.is_npc:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(escort_sim)
        if prisoner_sim is not None and prisoner_sim.sim_info.is_npc:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(prisoner_sim)

    def _on_interaction_of_interest_complete(self, **kwargs):
        if self.owner.npc_despawn:
            self._despawn_sims()
        self.owner._self_destruct()

    def timer_expired(self):
        if self.owner.npc_despawn:
            self._despawn_sims()
        self.owner._self_destruct()

class PrisonerEscortSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'escort_state': _EscortState.TunableFactory(description='\n            The escort state for the prisoner escort situation, where an escort\n            Sim and prisoner Sim route to a spawn point.\n            ', display_name='1. Escorting State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'despawn_state': _DespawnState.TunableFactory(description='\n            The post-routing state for the prisoner escort situation.  The Sims \n            will break the routing formation, and then either despawn (if NPC)\n            or continue on additional behavior before the situation ends.\n            ', display_name='2. Despawn State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'escort_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the escort Sim.\n            ', tuning_group=GroupNames.ROLES), 'prisoner_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the prisoner Sim.\n            ', tuning_group=GroupNames.ROLES), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI), 'npc_despawn': Tunable(description='\n            If checked, any NPC sims at the end of the situation will despawn.\n            ', tunable_type=bool, default=True)}
    REMOVE_INSTANCE_TUNABLES = Situation.SITUATION_SCORING_REMOVE_INSTANCE_TUNABLES + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _EscortState, factory=cls.escort_state), SituationStateData(2, _DespawnState, factory=cls.despawn_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.escort_job_and_role_state.job, cls.escort_job_and_role_state.role_state), (cls.prisoner_job_and_role_state.job, cls.prisoner_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def _destroy(self):
        super()._destroy()
        persistance_service = services.get_persistence_service()
        if persistance_service.is_save_locked():
            persistance_service.unlock_save(self)

    def start_situation(self):
        escort_sim = self.get_escort()
        prisoner_sim = self.get_prisoner()
        if not (escort_sim is not None and (prisoner_sim is not None and escort_sim.sim_info.is_npc) and prisoner_sim.sim_info.is_npc):
            services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(self.escort_state())

    def get_lock_save_reason(self):
        return self.save_lock_tooltip

    def get_escort(self):
        escort = next(iter(self._guest_list.get_guest_infos_for_job(self.escort_job_and_role_state.job)), None)
        if escort is not None:
            return services.object_manager().get(escort.sim_id)

    def get_prisoner(self):
        prisoner = next(iter(self._guest_list.get_guest_infos_for_job(self.prisoner_job_and_role_state.job)), None)
        if prisoner is not None:
            return services.object_manager().get(prisoner.sim_id)

    def break_routing_formations(self):
        escort_sim = self.get_escort()
        prisoner_sim = self.get_prisoner()
        if escort_sim is not None:
            for slave_data in escort_sim.routing_component.get_routing_slave_data():
                slave_data.interaction.cancel(FinishingType.SITUATIONS, 'Routing formation interaction on escort Sim canceled due to PrisonerEscortSituation.')
        if prisoner_sim is not None:
            for slave_data in prisoner_sim.routing_component.get_routing_slave_data():
                slave_data.interaction.cancel(FinishingType.SITUATIONS, 'Routing formation interaction on prisoner Sim canceled due to PrisonerEscortSituation.')
