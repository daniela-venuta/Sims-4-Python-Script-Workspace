from situations.situation_goal import SituationGoal
class SituationGoalProxy(SituationGoal):
    REMOVE_INSTANCE_TUNABLES = ('_post_tests',)

    def setup(self):
        super().setup()
        if self._situation is None:
            return
        self._situation._on_proxy_situation_goal_setup(self)

    def set_count(self, value):
        self._count = int(value)
        if self._count >= self._iterations:
            super()._on_goal_completed()
        else:
            self._on_iteration_completed()
