import collectionsimport functoolsimport randomfrom careers.career_enums import CareerShiftTypefrom date_and_time import TimeSpan, create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import GlobalResolverfrom event_testing.tests import TunableTestSetfrom scheduler_utils import TunableDayAvailabilityfrom sims4.tuning.tunable import TunableList, Tunable, TunableFactory, TunableReference, AutoFactoryInit, HasTunableSingletonFactory, HasTunableFactory, TunableEnumEntry, TunableTuple, TunableVariant, TunableRangefrom tunable_multiplier import TunableMultiplierfrom tunable_time import TunableTimeOfDayimport alarmsimport date_and_timeimport servicesimport sims4.resourceslogger = sims4.log.Logger('Scheduler')AlarmData = collections.namedtuple('AlarmData', ('start_time', 'end_time', 'entry', 'is_random'))
class ScheduleEntry(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'days_available': TunableDayAvailability(), 'start_time': TunableTimeOfDay(default_hour=9), 'duration': Tunable(description='\n            Duration of this work session in hours.\n            ', tunable_type=float, default=1.0), 'random_start': Tunable(description='\n            If checked, this schedule will have a random start time in the tuned\n            window each time.\n            ', tunable_type=bool, default=False), 'schedule_shift_type': TunableEnumEntry(description='\n            Shift Type for the schedule, this will be used for validations.\n            ', tunable_type=CareerShiftType, default=CareerShiftType.ALL_DAY)}

    @TunableFactory.factory_option
    def schedule_entry_data(tuning_name='schedule_entry_tuning', tuning_type=None, additional_tuning_name='additional_tuning', additional_tuning_type=None):
        value = {}
        if tuning_type is not None:
            value[tuning_name] = tuning_type
        if additional_tuning_type is not None:
            value[additional_tuning_name] = additional_tuning_type
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_and_end_times = set()
        for (day, day_enabled) in self.days_available.items():
            if day_enabled:
                days_as_time_span = date_and_time.create_time_span(days=day)
                start_time = self.start_time + days_as_time_span
                end_time = start_time + date_and_time.create_time_span(hours=self.duration)
                self._start_and_end_times.add((start_time, end_time))

    def get_start_and_end_times(self):
        return self._start_and_end_times

class WeeklySchedule(HasTunableFactory):

    @TunableFactory.factory_option
    def schedule_entry_data(**kwargs):
        return {'schedule_entries': TunableList(description='\n                A list of event schedules. Each event is a mapping of days of\n                the week to a start_time and duration.\n                ', tunable=ScheduleEntry.TunableFactory(schedule_entry_data=kwargs))}

    def __init__(self, schedule_entries, start_callback=None, schedule_immediate=True, min_alarm_time_span=None, min_duration_remaining=None, early_warning_callback=None, early_warning_time_span=None, extra_data=None, init_only=False, required_start_time=None, schedule_shift_type=CareerShiftType.ALL_DAY, cross_zone=False):
        self._schedule_entry_tuning = schedule_entries
        self._schedule_entries = set()
        now = services.time_service().sim_now
        will_not_be_empty = any(entry.schedule_shift_type == schedule_shift_type for entry in self._schedule_entry_tuning)
        for entry in self._schedule_entry_tuning:
            if will_not_be_empty and entry.schedule_shift_type != schedule_shift_type:
                pass
            else:
                for (start_time, end_time) in entry.get_start_and_end_times():
                    is_random = entry.random_start
                    if required_start_time is not None and now.time_to_week_time(required_start_time) != now.time_to_week_time(start_time):
                        pass
                    else:
                        self._schedule_entries.add(AlarmData(start_time, end_time, entry, is_random))
        self._start_callback = start_callback
        self._alarm_handle = None
        self._random_alarm_handles = []
        self._alarm_data = {}
        self._min_alarm_time_span = min_alarm_time_span
        self.extra_data = extra_data
        self._early_warning_callback = early_warning_callback
        self._early_warning_time_span = early_warning_time_span
        self._early_warning_alarm_handle = None
        self._cross_zone = cross_zone
        self._cooldown_time = None
        if not init_only:
            self.schedule_next_alarm(schedule_immediate=schedule_immediate, min_duration_remaining=min_duration_remaining)

    def __iter__(self):
        yield from self._schedule_entries

    def populate_scheduler_msg(self, schedule_msg, schedule_shift_type=None):
        for schedule_entry in self._schedule_entry_tuning:
            if schedule_shift_type is not None and schedule_entry.schedule_shift_type != schedule_shift_type:
                pass
            else:
                with ProtocolBufferRollback(schedule_msg.schedule_entries) as schedule_entry_msg:
                    schedule_entry_msg.days.extend(day for (day, is_day_available) in schedule_entry.days_available.items() if is_day_available)
                    schedule_entry_msg.start_hour = schedule_entry.start_time.hour()
                    schedule_entry_msg.start_minute = schedule_entry.start_time.minute()
                    schedule_entry_msg.duration = schedule_entry.duration
                    schedule_entry_msg.schedule_shift_type = schedule_entry.schedule_shift_type

    def schedule_next_alarm(self, schedule_immediate=False, min_duration_remaining=None):
        if self._alarm_handle is not None:
            logger.error('Trying to schedule the next alarm which has already been created.', owner='rmccord')
        now = services.time_service().sim_now
        (time_span, best_work_data) = self.time_until_next_scheduled_event(now, schedule_immediate=schedule_immediate, min_duration_remaining=min_duration_remaining)
        if time_span is not None:
            if time_span < self._min_alarm_time_span:
                time_span = self._min_alarm_time_span
            if schedule_immediate:
                time_span = date_and_time.TimeSpan.ONE
            self._alarm_handle = alarms.add_alarm(self, time_span, self._alarm_callback, cross_zone=self._cross_zone)
            self._alarm_data[self._alarm_handle] = best_work_data
            if self._early_warning_time_span > date_and_time.TimeSpan.ZERO:
                warning_time_span = time_span - self._early_warning_time_span
                if warning_time_span > date_and_time.TimeSpan.ZERO:
                    logger.assert_log(self._early_warning_alarm_handle is None, 'Scheduler is setting an early warning alarm when the previous one has not fired.', owner='tingyul')
                    self._early_warning_alarm_handle = alarms.add_alarm(self, warning_time_span, self._early_warning_alarm_callback, cross_zone=self._cross_zone)

    def _random_alarm_callback(self, handle, alarm_data):
        self._random_alarm_handles.remove(handle)
        if not self.is_on_cooldown():
            self._start_callback(self, alarm_data, self.extra_data)

    def _early_warning_alarm_callback(self, handle, alarm_data=None):
        self._early_warning_alarm_handle = None
        self._early_warning_callback()

    def _alarm_callback(self, handle, alarm_datas=None):
        if alarm_datas is None:
            alarm_datas = self._alarm_data.pop(self._alarm_handle)
            self._alarm_handle = None
        if self._start_callback is not None:
            for alarm_data in alarm_datas:
                if alarm_data.is_random:
                    current_time = services.time_service().sim_now
                    current_time = current_time.time_since_beginning_of_week()
                    available_time_span = alarm_data.end_time - current_time
                    random_time_span = TimeSpan(random.randint(0, available_time_span.in_ticks()))
                    random_callback = functools.partial(self._random_alarm_callback, alarm_data=alarm_data)
                    cur_handle = alarms.add_alarm(self, random_time_span, random_callback, cross_zone=self._cross_zone)
                    self._random_alarm_handles.append(cur_handle)
                else:
                    self._start_callback(self, alarm_data, self.extra_data)
        self.schedule_next_alarm(schedule_immediate=False)

    def time_since_last_scheduled_event(self, cur_time):
        cur_time_of_week = cur_time.absolute_days() % date_and_time.DAYS_PER_WEEK

        def get_elapsed_time(event_end_time):
            if event_end_time <= cur_time_of_week:
                return cur_time_of_week - event_end_time
            else:
                return cur_time_of_week + date_and_time.DAYS_PER_WEEK - event_end_time

        if len(self._schedule_entries) == 0:
            return
        shortest_elapsed_time = min(get_elapsed_time(e.end_time.absolute_days()) for e in self._schedule_entries)
        return create_time_span(days=shortest_elapsed_time)

    def time_until_next_scheduled_event(self, current_date_and_time, schedule_immediate=False, min_duration_remaining=None):
        best_time = None
        best_work_data = []
        for alarm_data in self._schedule_entries:
            start_time = alarm_data.start_time
            end_time = alarm_data.end_time
            cur_time = current_date_and_time.time_till_timespan_of_week(start_time, optional_end_time=end_time if schedule_immediate else None, min_duration_remaining=min_duration_remaining)
            if best_time is None or cur_time < best_time:
                best_time = cur_time
                best_work_data = []
                best_work_data.append(alarm_data)
            elif cur_time == best_time:
                best_work_data.append(alarm_data)
        return (best_time, best_work_data)

    def is_scheduled_time(self, current_date_and_time):
        (best_time, _) = self.time_until_next_scheduled_event(current_date_and_time, schedule_immediate=True)
        if best_time <= TimeSpan.ZERO:
            return True
        return False

    def add_cooldown(self, time_span):
        if self._cooldown_time is None:
            now = services.time_service().sim_now
            self._cooldown_time = now + time_span
        else:
            self._cooldown_time = self._cooldown_time + time_span

    def is_on_cooldown(self):
        if self._cooldown_time is None:
            return False
        now = services.time_service().sim_now
        if self._cooldown_time >= now:
            return True
        self._cooldown_time = None
        return False

    def get_schedule_times(self):
        busy_times = []
        for (start_time, end_time, _, _) in self._schedule_entries:
            busy_times.append((start_time.absolute_ticks(), end_time.absolute_ticks()))
        return busy_times

    def get_schedule_entries(self):
        return tuple((start_time, end_time) for (start_time, end_time, _, _) in self._schedule_entries)

    def check_for_conflict(self, other_schedule):
        START = 0
        END = 1
        busy_times = self.get_schedule_times()
        other_busy_times = other_schedule.get_schedule_times()
        for this_time in busy_times:
            for other_time in other_busy_times:
                starting_time_delta = this_time[START] - other_time[START]
                if starting_time_delta >= 0:
                    earlier_career_duration = other_time[END] - other_time[START]
                else:
                    earlier_career_duration = this_time[END] - this_time[START]
                if earlier_career_duration >= abs(starting_time_delta):
                    return True
        return False

    def merge_schedule(self, other_schedule):
        self._schedule_entries |= other_schedule._schedule_entries

    def destroy(self):
        for alarm_handle in self._random_alarm_handles:
            alarms.cancel_alarm(alarm_handle)
        self._random_alarm_handles = []
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None
        if self._early_warning_alarm_handle is not None:
            alarms.cancel_alarm(self._early_warning_alarm_handle)
            self._early_warning_alarm_handle = None
        self._alarm_data = {}

    def get_alarm_finishing_time(self):
        if self._alarm_handle is not None:
            return self._alarm_handle.finishing_time

class SituationWeeklySchedule(WeeklySchedule):

    @TunableFactory.factory_option
    def schedule_entry_data(pack_safe=False, affected_object_cap=False):
        schedule_entry_tuning = {'tuning_name': 'situation', 'tuning_type': TunableReference(description='\n                The situation to start according to the tuned schedule.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=pack_safe)}
        if affected_object_cap:
            schedule_entry_tuning['additional_tuning_name'] = 'affected_object_cap'
            schedule_entry_tuning['additional_tuning_type'] = TunableRange(description='\n                Specify the maximum number of objects on the zone lot that \n                can schedule the situations.\n                ', tunable_type=int, minimum=1, default=1)
        return {'schedule_entries': TunableList(description='\n                A list of event schedules. Each event is a mapping of days of the\n                week to a start_time and duration.\n                ', tunable=ScheduleEntry.TunableFactory(schedule_entry_data=schedule_entry_tuning))}

class WeightedSituationsWeeklySchedule(WeeklySchedule):

    @TunableFactory.factory_option
    def schedule_entry_data(pack_safe=False, affected_object_cap=False):
        schedule_entry_tuning = {'tuning_name': 'weighted_situations', 'tuning_type': TunableList(description='\n                A weighted list of situations to be used at the scheduled time.\n                ', tunable=TunableTuple(situation=TunableReference(description='\n                        The situation to start according to the tuned schedule.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=pack_safe), params=TunableTuple(description='\n                        Situation creation parameters.\n                        ', user_facing=Tunable(description="\n                            If enabled, we will start the situation as user facing.\n                            Note: We can only have one user facing situation at a time,\n                            so make sure you aren't tuning multiple user facing\n                            situations to occur at once.\n                            ", tunable_type=bool, default=False)), weight_multipliers=TunableMultiplier.TunableFactory(description="\n                        Tunable tested multiplier to apply to weight.\n                        \n                        *IMPORTANT* The only participants that work are ones\n                        available globally, such as Lot and ActiveHousehold. Only\n                        use these participant types or use tests that don't rely\n                        on any, such as testing all objects via Object Criteria\n                        test or testing active zone with the Zone test.\n                        "), tests=TunableTestSet(description="\n                        A set of tests that must pass for the situation and weight\n                        pair to be available for selection.\n                        \n                        *IMPORTANT* The only participants that work are ones\n                        available globally, such as Lot and ActiveHousehold. Only\n                        use these participant types or use tests that don't rely\n                        on any, such as testing all objects via Object Criteria\n                        test or testing active zone with the Zone test.\n                        ")))}
        if affected_object_cap:
            schedule_entry_tuning['additional_tuning_name'] = 'affected_object_cap'
            schedule_entry_tuning['additional_tuning_type'] = TunableRange(description='\n                Specify the maximum number of objects on the zone lot that \n                can schedule the situations.\n                ', tunable_type=int, minimum=1, default=1)
        return {'schedule_entries': TunableList(description='\n                A list of event schedules. Each event is a mapping of days of the\n                week to a start_time and duration.\n                ', tunable=ScheduleEntry.TunableFactory(schedule_entry_data=schedule_entry_tuning))}

    @staticmethod
    def get_weighted_situations(cls, predicate=lambda _: True):
        resolver = GlobalResolver()

        def get_weight(item):
            if not predicate(item.situation):
                return 0
            if not item.tests.run_tests(resolver):
                return 0
            return item.weight_multipliers.get_multiplier(resolver)*item.situation.weight_multipliers.get_multiplier(resolver)

        weighted_situations = tuple((get_weight(item), (item.situation, dict(item.params.items()))) for item in cls.weighted_situations)
        return weighted_situations

    @staticmethod
    def get_situation_and_params(cls, predicate=lambda _: True, additional_situations=None):
        weighted_situations = WeightedSituationsWeeklySchedule.get_weighted_situations(cls, predicate=predicate)
        if additional_situations is not None:
            weighted_situations = tuple(weighted_situations) + tuple(additional_situations)
        situation_and_params = sims4.random.weighted_random_item(weighted_situations)
        if situation_and_params is not None:
            return situation_and_params
        return (None, {})

class SituationWeeklyScheduleVariant(TunableVariant):

    def __init__(self, *args, pack_safe=False, affected_object_cap=False, **kwargs):
        schedule_entry_data = {'pack_safe': pack_safe, 'affected_object_cap': affected_object_cap}
        super().__init__(*args, situation=SituationWeeklySchedule.TunableFactory(schedule_entry_data=schedule_entry_data), weighted_situations=WeightedSituationsWeeklySchedule.TunableFactory(schedule_entry_data=schedule_entry_data), default='situation', **kwargs)

class ObjectLayerWeeklySchedule(WeeklySchedule):

    @TunableFactory.factory_option
    def schedule_entry_data(pack_safe=False):
        return {'schedule_entries': TunableList(description='\n                A list of schedule entries. Each entry is a mapping of days of the\n                week to a start_time and duration.\n                ', tunable=ScheduleEntry.TunableFactory(schedule_entry_data={'tuning_name': 'conditional_layer', 'tuning_type': TunableReference(description='\n                            The Conditional Layer that will be loaded.\n                            ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER))}))}
