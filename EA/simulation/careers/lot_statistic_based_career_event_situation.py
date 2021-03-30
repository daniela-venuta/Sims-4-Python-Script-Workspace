from careers.career_event_situation import CareerEventSituationfrom distributor.rollback import ProtocolBufferRollbackfrom sims4.tuning.tunable import TunableReferencefrom situations.situation_meter import StatBasedSituationMeterDatafrom situations.situation_types import SituationDisplayFlagsimport servicesimport sims4
class LotStatisticBasedCareerEventSituation(CareerEventSituation):
    PROGRESS_METER_ID = 1
    INSTANCE_TUNABLES = {'progress_statistic': TunableReference(description='\n            The statistic that will be used to determine the progress of the situation.\n            This will be added to the lot when situation starts and will be removed when situation ends.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'progress_meter_settings': StatBasedSituationMeterData.TunableFactory(description='\n            The meter used to track the progress of the situation.\n            ', locked_args={'_meter_id': PROGRESS_METER_ID})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress_tracking_situation_goal = None
        self._statistic_watcher_handle = None
        self._progress_meter = None

    def on_goal_completed(self, goal):
        super().on_goal_completed(goal)
        self._self_destruct()

    def _on_statistic_updated(self, stat_type, old_value, new_value):
        if stat_type is self.progress_statistic:
            self._progress_tracking_situation_goal.set_count(new_value)
            self._progress_meter.send_update_if_dirty()

    def start_situation(self):
        super().start_situation()
        self._setup_situation_meters()

    def load_situation(self):
        result = super().load_situation()
        if result:
            self._setup_situation_meters()
        return result

    def _setup_situation_meters(self):
        statistic_tracker = services.active_lot().statistic_tracker
        statistic_tracker.add_statistic(self.progress_statistic)
        self._statistic_watcher_handle = statistic_tracker.add_watcher(self._on_statistic_updated)
        self._progress_meter = self.progress_meter_settings.create_meter_with_statistic_tracker(self, statistic_tracker)

    def _on_proxy_situation_goal_setup(self, goal):
        self._progress_tracking_situation_goal = goal

    def build_situation_start_message(self):
        msg = super().build_situation_start_message()
        with ProtocolBufferRollback(msg.meter_data) as meter_data_msg:
            self.progress_meter_settings.build_data_message(meter_data_msg)
        msg.situation_display_flags |= SituationDisplayFlags.STAT_BASED
        return msg

    def get_level(self, score=None):
        effective_score = self._progress_tracking_situation_goal.completed_iterations if self._progress_tracking_situation_goal is not None else 0
        for level in self.level_data_gen():
            if effective_score < level.min_score_threshold:
                break
            last_level = level
        return last_level.level_data.medal

    def _destroy(self):
        super()._destroy()
        if self._progress_meter is not None:
            self._progress_meter.destroy()
        statistic_tracker = services.active_lot().statistic_tracker
        if statistic_tracker.has_watcher(self._statistic_watcher_handle):
            statistic_tracker.remove_watcher(self._statistic_watcher_handle)
        statistic_tracker.remove_statistic(self.progress_statistic)
