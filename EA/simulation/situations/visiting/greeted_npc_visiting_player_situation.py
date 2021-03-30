from event_testing.resolver import DoubleSimResolverfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom situations.visiting.visiting_situation_common import VisitingNPCSituationimport role.role_stateimport sims4.tuning.tunableimport situations.bouncer.bouncer_typesimport situations.situation_complex
class GreetedNPCVisitingPlayerSituation(VisitingNPCSituation):
    INSTANCE_TUNABLES = {'greeted_npc_sims': sims4.tuning.tunable.TunableTuple(situation_job=situations.situation_job.SituationJob.TunableReference(description='\n                    The job given to NPC sims in the visiting situation.\n                    '), role_state=role.role_state.RoleState.TunableReference(description='\n                    The role state given to NPC sims in the visiting situation.\n                    '), tuning_group=GroupNames.ROLES)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GreetedNPCVisitingPlayerState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.greeted_npc_sims.situation_job, cls.greeted_npc_sims.role_state)]

    @classmethod
    def default_job(cls):
        return cls.greeted_npc_sims.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(GreetedNPCVisitingPlayerState())

    def _resolve_sim_job_headline(self, sim, sim_job):
        resolver = DoubleSimResolver(sim.sim_info, self._guest_list.host_sim_info)
        tokens = sim_job.tooltip_name_text_tokens.get_tokens(resolver)
        if self.is_user_facing and self.manager.is_distributed(self) or sim_job.user_facing_sim_headline_display_override:
            sim.sim_info.sim_headline = sim_job.tooltip_name(*tokens)
        return tokens
lock_instance_tunables(GreetedNPCVisitingPlayerSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.VISIT, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=True)
class GreetedNPCVisitingPlayerState(situations.situation_complex.SituationState):
    pass
