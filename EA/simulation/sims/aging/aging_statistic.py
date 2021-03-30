from sims.sim_info_lod import SimInfoLODLevelfrom sims4.utils import classpropertyfrom statistics.continuous_statistic import ContinuousStatisticimport date_and_timeimport sims4.math
class AgeProgressContinuousStatistic(ContinuousStatistic):
    _default_convergence_value = sims4.math.POS_INFINITY
    decay_modifier = 1
    delayed_decay_rate = None

    def __init__(self, tracker, initial_value):
        self.min_lod_value = SimInfoLODLevel.BACKGROUND
        super().__init__(tracker, initial_value)

    @classproperty
    def max_value(cls):
        return cls.default_value

    @classproperty
    def min_value(cls):
        return 0.0

    @classproperty
    def best_value(cls):
        return cls.max_value

    @classproperty
    def persisted(cls):
        return True

    @classmethod
    def set_modifier(cls, modifier):
        cls.decay_modifier = modifier

    @property
    def base_decay_rate(self):
        return self.decay_modifier/(date_and_time.HOURS_PER_DAY*date_and_time.MINUTES_PER_HOUR)
