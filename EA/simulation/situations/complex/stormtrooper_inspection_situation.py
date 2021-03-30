import randomfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonInteractionCompletedSituationStateimport servicesimport sims4logger = sims4.log.Logger('Stormtrooper Inspection Situation', default_owner='madang')
class _FleeState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Suspect Sim is fleeing from the Inspector Sim.')
        super().on_activate(reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.surrender_state())

    def timer_expired(self):
        suspect_sim = self.owner.get_suspect()
        if suspect_sim.sim_info.is_npc:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(suspect_sim)
        self._change_state(self.owner.fallback_state())

class _SurrenderState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Suspect Sim is surrendering to the Inspector Sim.')
        super().on_activate(reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.fight_state())

    def timer_expired(self):
        self._change_state(self.owner.fight_state())

class _FightState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Inspector and Suspect Sims are fighting.')
        super().on_activate(reader=reader)

    def _on_interaction_of_interest_complete(self, resolver=None, **kwargs):
        if resolver is not None and resolver.interaction is not None:
            ko_sim = resolver.interaction.target
            inspector_sim = self.owner.get_inspector()
            suspect_sim = self.owner.get_suspect()
            if ko_sim is not None and (inspector_sim is not None and (suspect_sim is not None and ko_sim.sim_id == inspector_sim.sim_id)) and suspect_sim.sim_info.is_npc:
                services.get_zone_situation_manager().make_sim_leave_now_must_run(suspect_sim)
        self._change_state(self.owner.fallback_state())

    def timer_expired(self):
        self.owner._self_destruct()

class _FallbackState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Stormtrooper Inspection is ending.')
        super().on_activate(reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def timer_expired(self):
        self.owner._self_destruct()

class StormtrooperInspectionSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'flee_state': _FleeState.TunableFactory(description='\n            The flee state for the stormtrooper inspection situation.  This \n            will be the starting situation state only if both suspect and \n            inspector are NPCs.  In this state, the inspector will fire warning \n            shots and the suspect will run away.\n            ', display_name='1. Flee State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'surrender_state': _SurrenderState.TunableFactory(description='\n            The surrender state for the stormtrooper inspection situation. \n            This will be the starting state if either suspect or inspector is\n            a player Sim.  Otherwise, the Flee State can lead into this one.  \n            In this state, the suspect will put their hands up and the \n            inspector will run over to the suspect.\n            ', display_name='2. Surrender State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'fight_state': _FightState.TunableFactory(description='\n            The fight state for the stormtrooper inspection situation.  In this \n            state, the inspector will fight the suspect.\n            ', display_name='3. Fight State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'fallback_state': _FallbackState.TunableFactory(description='\n            The final/fallback state for the stormtrooper inspection \n            situation.  This state may be reached from either the flee or \n            fight states, thus ending the situation.\n            ', display_name='4. Fallback State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'suspect_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the suspect Sim.\n            ', tuning_group=GroupNames.ROLES), 'inspector_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the inspector Sim.\n            ', tuning_group=GroupNames.ROLES), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI)}
    REMOVE_INSTANCE_TUNABLES = Situation.SITUATION_SCORING_REMOVE_INSTANCE_TUNABLES + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _FleeState, factory=cls.flee_state), SituationStateData(2, _SurrenderState, factory=cls.surrender_state), SituationStateData(3, _FightState, factory=cls.fight_state), SituationStateData(4, _FallbackState, factory=cls.fallback_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.suspect_job_and_role_state.job, cls.suspect_job_and_role_state.role_state), (cls.inspector_job_and_role_state.job, cls.inspector_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def _destroy(self):
        super()._destroy()
        persistance_service = services.get_persistence_service()
        if persistance_service.is_save_locked():
            persistance_service.unlock_save(self)

    def start_situation(self):
        super().start_situation()
        inspector_sim = self.get_inspector()
        suspect_sim = self.get_suspect()
        if inspector_sim is not None and suspect_sim is not None:
            if inspector_sim.sim_info.is_npc and suspect_sim.sim_info.is_npc:
                start_state = random.choice([self.flee_state, self.fight_state])
                self._change_state(start_state())
            else:
                services.get_persistence_service().lock_save(self)
                self._change_state(self.fight_state())

    def get_lock_save_reason(self):
        return self.save_lock_tooltip

    def get_inspector(self):
        inspector = next(iter(self._guest_list.get_guest_infos_for_job(self.inspector_job_and_role_state.job)), None)
        if inspector is not None:
            return services.object_manager().get(inspector.sim_id)

    def get_suspect(self):
        suspect = next(iter(self._guest_list.get_guest_infos_for_job(self.suspect_job_and_role_state.job)), None)
        if suspect is not None:
            return services.object_manager().get(suspect.sim_id)
