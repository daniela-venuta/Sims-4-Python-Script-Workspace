from role.role_state import RoleState
class StayTheNightSituation(VisitingNPCSituation):
    INSTANCE_TUNABLES = {'invited_job': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                          The situation job for the sim spending the night.\n                          '), staying_role_state=RoleState.TunableReference(description='\n                          The role state for the sim spending the night.\n                          ')), 'when_to_leave': tunable_time.TunableTimeOfDay(description='\n            The time of day for the invited sim to leave.\n            ', default_hour=7)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _StayState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.invited_job.situation_job, cls.invited_job.staying_role_state)]

    @classmethod
    def default_job(cls):
        return cls.invited_job.situation_job

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_time = None

    def start_situation(self):
        super().start_situation()
        self._start_time = services.time_service().sim_now
        self._change_state(_StayState())

    def _get_duration(self):
        if self._seed.duration_override is not None:
            return self._seed.duration_override
        time_span = self._start_time.time_till_next_day_time(self.when_to_leave)
        return time_span.in_minutes()

class _StayState(SituationState):
    pass
