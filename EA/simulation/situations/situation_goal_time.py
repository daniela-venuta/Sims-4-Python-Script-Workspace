from clock import interval_in_sim_hoursfrom date_and_time import TimeSpanfrom sims4.tuning.tunable import TunableRangefrom situations.situation_goal import SituationGoalimport alarmsimport services
class SituationGoalTime(SituationGoal):
    DURATION_RUN = 'duration_run'
    REMOVE_INSTANCE_TUNABLES = ('_post_tests',)
    INSTANCE_TUNABLES = {'duration': TunableRange(description='\n            The amount of time in Sim Hours that this goal has to run before\n            completing.\n            ', tunable_type=int, default=5, minimum=1)}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._total_time_ran = TimeSpan.ZERO
        self._last_started_time = None
        self._alarm_handle = None
        self._total_duration = interval_in_sim_hours(self.duration)
        if reader is not None:
            duration_run = reader.read_uint64(self.DURATION_RUN, 0)
            self._total_time_ran = TimeSpan(duration_run)

    def setup(self):
        super().setup()
        self._start_alarm()

    def create_seedling(self):
        self._start_alarm()
        seedling = super().create_seedling()
        writer = seedling.writer
        writer.write_uint64(self.DURATION_RUN, self._total_time_ran.in_ticks())
        return seedling

    def _decommision(self):
        self._stop_alarm()
        super()._decommision()

    def _on_hour_reached(self, alarm_handle=None):
        self._stop_alarm()
        if self._total_time_ran >= self._total_duration:
            super()._on_goal_completed()
        else:
            self._on_iteration_completed()
            self._start_alarm()

    def _start_alarm(self):
        self._stop_alarm()
        next_hour = interval_in_sim_hours(int(self._total_time_ran.in_hours()) + 1)
        time_till_completion = next_hour - self._total_time_ran
        self._alarm_handle = alarms.add_alarm(self, time_till_completion, self._on_hour_reached)
        self._last_started_time = services.time_service().sim_now

    def _stop_alarm(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None
            self._total_time_ran += services.time_service().sim_now - self._last_started_time
            self._last_started_time = None

    @property
    def completed_iterations(self):
        return int(self._total_time_ran.in_hours())

    @property
    def max_iterations(self):
        return self.duration
