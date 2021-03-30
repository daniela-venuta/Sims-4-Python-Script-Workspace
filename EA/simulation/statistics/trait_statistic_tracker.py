from collections import defaultdictimport alarmsimport randomimport servicesfrom date_and_time import create_time_span, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableSimMinutefrom statistics.continuous_statistic_tracker import ContinuousStatisticTrackerfrom statistics.trait_statistic import TraitStatistic, TraitStatisticStates, TraitStatisticGroupfrom tunable_time import TunableTimeSpan, TunableTimeOfDay
class TraitStatisticTracker(ContinuousStatisticTracker):
    PERIODIC_TEST_TIMER = TunableTimeSpan(description='\n        A repeating time span of how often we will run the periodic\n        tests on Trait Statistics.\n        ')
    PERIODIC_TEST_TIMER_RANDOMIZER = TunableSimMinute(description='\n        A random amount of time between 0 and this will be added to each Sim when setting up the initial\n        alarm such that all of of the timers will not be triggered at once leading to a potential spike.\n        ', default=30, minimum=0)
    END_OF_DAY_TIME = TunableTimeOfDay(description='\n        The time of day in which we will consider the end of day for the trait statistic end of day\n        behaviors: daily cap, neglect, etc.\n        ')
    periodic_trait_statistics = None

    @classmethod
    def get_periodic_tested_trait_statistics(cls):
        if cls.periodic_trait_statistics is None:
            cls.periodic_trait_statistics = []
            statistics_manager = services.get_instance_manager(Types.STATISTIC)
            for statistic in statistics_manager.types.values():
                if not issubclass(statistic, TraitStatistic):
                    pass
                elif statistic.periodic_tests.modifiers:
                    cls.periodic_trait_statistics.append(statistic)
        return cls.periodic_trait_statistics

    __slots__ = ('_trait_statistic_periodic_test_alarm_handle', '_end_of_day_alarm_handle', 'load_in_progress', '_time_to_next_periodic_test', '_trait_statistic_groups', '__weakref__')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._trait_statistic_periodic_test_alarm_handle = None
        self._time_to_next_periodic_test = None
        self._end_of_day_alarm_handle = None
        self.load_in_progress = False
        self._trait_statistic_groups = None

    def should_suppress_calculations(self):
        return self.load_in_progress

    def _cancel_alarms(self):
        if self._trait_statistic_periodic_test_alarm_handle is not None:
            alarms.cancel_alarm(self._trait_statistic_periodic_test_alarm_handle)
            self._trait_statistic_periodic_test_alarm_handle = None
        if self._end_of_day_alarm_handle is not None:
            alarms.cancel_alarm(self._end_of_day_alarm_handle)
            self._end_of_day_alarm_handle = None

    def destroy(self):
        self._cancel_alarms()
        super().destroy()

    def _periodic_tests_callback(self, _):
        resolver = SingleSimResolver(self.owner)
        statistics_to_test = self.get_periodic_tested_trait_statistics()
        for statistic in statistics_to_test:
            values = statistic.periodic_tests.get_modified_value(resolver)
            if values != 0:
                self.add_value(statistic, values)

    def _load_delayed_active_statistics(self):
        statistic_manager = services.get_instance_manager(Types.STATISTIC)
        for trait_statistic_data in self._delayed_active_lod_statistics:
            statistic_type = statistic_manager.get(trait_statistic_data.trait_statistic_id)
            stat = self.add_statistic(statistic_type, from_load=True)
            if stat is None:
                pass
            else:
                stat.load(trait_statistic_data)
        self._delayed_active_lod_statistics = None

    def _get_stat_data_for_active_lod(self, statistic):
        return statistic.get_save_message(self)

    def on_lod_update(self, old_lod, new_lod):
        super().on_lod_update(old_lod, new_lod)
        if new_lod >= SimInfoLODLevel.ACTIVE:
            if self._trait_statistic_periodic_test_alarm_handle is not None:
                return
            duration = TraitStatisticTracker.PERIODIC_TEST_TIMER()
            if self._time_to_next_periodic_test is None:
                initial_duration = duration + create_time_span(minutes=random.randint(0, self.PERIODIC_TEST_TIMER_RANDOMIZER))
            else:
                initial_duration = TimeSpan(self._time_to_next_periodic_test)
                self._time_to_next_periodic_test = None
            self._trait_statistic_periodic_test_alarm_handle = alarms.add_alarm(self, initial_duration, self._periodic_tests_callback, repeating=True, repeating_time_span=duration, cross_zone=True)
            now = services.time_service().sim_now
            time_till_end_of_day = now.time_till_next_day_time(TraitStatisticTracker.END_OF_DAY_TIME)
            self._end_of_day_alarm_handle = alarms.add_alarm(self, time_till_end_of_day, self.on_day_end, repeating=True, repeating_time_span=create_time_span(days=1), cross_zone=True)
        else:
            self._cancel_alarms()

    def get_trait_state(self, trait):
        trait_statistic = self.get_statistic(trait.trait_statistic)
        if trait_statistic is None:
            return TraitStatisticStates.LOCKED
        if trait_statistic.trait_data.trait is trait:
            return trait_statistic.state
        elif trait_statistic.opposing_trait_data.trait is trait:
            return len(TraitStatisticStates) - trait_statistic.state - 1

    def on_day_end(self, *args, **kwargs):
        if self._statistics is None:
            return
        for statistic in self._statistics.values():
            statistic.perform_end_of_day_actions()

    def reset_daily_caps(self):
        if self._statistics is None:
            return
        for statistic in self._statistics.values():
            statistic.reset_daily_caps()

    def add_statistic(self, stat_type, from_load=False, **kwargs):
        stat = super().add_statistic(stat_type, **kwargs)
        if stat is None:
            return
        if not from_load:
            stat.startup_statistic()
        if stat.group != TraitStatisticGroup.NO_GROUP and (self._trait_statistic_groups is not None and stat.group in self._trait_statistic_groups) and len(self._trait_statistic_groups[stat.group]) >= TraitStatistic.GROUPS[stat.group]:
            stat.add_group_limiter()
        return stat

    def _on_statistic_state_changed(self, changed_statistic):
        group_being_changed = changed_statistic.group
        if group_being_changed == TraitStatisticGroup.NO_GROUP:
            return
        if changed_statistic.trait_unlocked:
            if self._trait_statistic_groups is None:
                self._trait_statistic_groups = defaultdict(set)
            elif type(changed_statistic) in self._trait_statistic_groups[group_being_changed]:
                return
            self._trait_statistic_groups[group_being_changed].add(type(changed_statistic))
            if len(self._trait_statistic_groups[group_being_changed]) < TraitStatistic.GROUPS[group_being_changed]:
                return
            for statistic in self._statistics.values():
                if statistic.group != group_being_changed:
                    pass
                elif statistic.trait_unlocked:
                    pass
                else:
                    statistic.add_group_limiter()
        else:
            if self._trait_statistic_groups is None:
                return
            if group_being_changed not in self._trait_statistic_groups:
                return
            if type(changed_statistic) not in self._trait_statistic_groups[group_being_changed]:
                return
            currently_locked = len(self._trait_statistic_groups[group_being_changed]) >= TraitStatistic.GROUPS[group_being_changed]
            self._trait_statistic_groups[group_being_changed].remove(type(changed_statistic))
            del self._trait_statistic_groups[group_being_changed]
            if not self._trait_statistic_groups:
                self._trait_statistic_groups = None
            if self._trait_statistic_groups[group_being_changed] or currently_locked:
                for statistic in self._statistics.values():
                    if statistic.group != group_being_changed:
                        pass
                    else:
                        statistic.remove_group_limiter()

    def remove_all_statistics_by_group(self, trait_statistic_group):
        if self._statistics is None:
            return
        for stat_type in tuple(self._statistics.keys()):
            if stat_type.group != trait_statistic_group:
                pass
            else:
                self.remove_statistic(stat_type)

    def reset_all_statistics_by_group(self, trait_statistic_group):
        if self._statistics is None:
            return
        for statistic in self._statistics.values():
            if statistic.group != trait_statistic_group:
                pass
            else:
                statistic.set_value(statistic.default_value, ignore_caps=True)
                statistic.reset_daily_caps()

    def save(self, msg):
        saved_data = False
        if self._statistics is not None:
            for statistic in self._statistics.values():
                with ProtocolBufferRollback(msg.trait_statistics) as statistic_msg:
                    statistic.save(statistic_msg)
                    saved_data = True
        if self._delayed_active_lod_statistics is not None:
            msg.trait_statistics.extend(self._delayed_active_lod_statistics)
        if self._trait_statistic_periodic_test_alarm_handle is not None:
            msg.time_to_next_periodic_test = self._trait_statistic_periodic_test_alarm_handle.get_remaining_time().in_ticks()
            saved_data = True
        elif self._time_to_next_periodic_test is not None:
            msg.time_to_next_periodic_test = self._time_to_next_periodic_test
        return saved_data

    def load(self, msg):
        statistic_manager = services.get_instance_manager(Types.STATISTIC)
        for trait_statistic_data in msg.trait_statistics:
            statistic_type = statistic_manager.get(trait_statistic_data.trait_statistic_id)
            if statistic_type is None:
                pass
            elif self.owner.lod >= statistic_type.min_lod_value:
                stat = self.add_statistic(statistic_type, from_load=True)
                if stat is None:
                    pass
                else:
                    stat.load(trait_statistic_data)
                    if statistic_type.min_lod_value == SimInfoLODLevel.ACTIVE:
                        if self._delayed_active_lod_statistics is None:
                            self._delayed_active_lod_statistics = list()
                        self._delayed_active_lod_statistics.append(trait_statistic_data)
            elif statistic_type.min_lod_value == SimInfoLODLevel.ACTIVE:
                if self._delayed_active_lod_statistics is None:
                    self._delayed_active_lod_statistics = list()
                self._delayed_active_lod_statistics.append(trait_statistic_data)
        if msg.HasField('time_to_next_periodic_test'):
            self._time_to_next_periodic_test = msg.time_to_next_periodic_test
