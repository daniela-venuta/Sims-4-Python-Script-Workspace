import randomfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableSimMinutefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOption
class _LoungerSituationState(SituationState):
    pass

class PoolVenueLoungerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'lounger_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role for Pool Venue lounger.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _LoungerSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.lounger_job_and_role.job, cls.lounger_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        return cls.lounger_job_and_role.job

    def start_situation(self):
        super().start_situation()
        self._change_state(_LoungerSituationState())
lock_instance_tunables(PoolVenueLoungerSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)