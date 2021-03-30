from event_testing.test_base import BaseTestfrom event_testing.results import TestResultfrom sims4.tuning.tunable import TunableMapping, TunableList, TunableTuple, TunableEnumEntry, Tunable, TunableReference, TunablePercent, OptionalTunable, TunableRange, AutoFactoryInit, HasTunableSingletonFactory, TunablePackSafeReferencefrom sims4.tuning import dynamic_enumfrom tunable_time import TunableTimeOfDayfrom collections import defaultdictfrom objects.components import typesimport servicesimport sims4.logimport randomimport alarmsimport date_and_timelogger = sims4.log.Logger('WildlifeEncounterDirector', default_owner='uviswavasu')
class WildlifeEncounterGroups(dynamic_enum.DynamicEnum):
    INVALID = 0
WILDLIFE_LAST_ROLL_DATE = 'wildlife_last_roll_date'ACTIVE_ENCOUNTER_AREAS = 'active_encounter_areas'ACTIVE_GROUP_COUNTS = 'active_group_counts'ACTIVE_GROUP_NAMES = 'active_group_names'
class WildlifeEncounterDirectorMixin:
    ACTIVE_STATE = TunablePackSafeReference(description='\n        State to set wildlife broadcasters when active\n        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))
    INACTIVE_STATE = TunablePackSafeReference(description='\n        State to set wildlife broadcasters when inactive\n        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))
    DAILY_ROLL_TIME = TunableTimeOfDay(description='\n        The time each day to re-roll the encounters for the day\n        ', default_hour=4, default_minute=0)
    WILDLIFE_ENCOUNTER_GROUPS = TunableMapping(description='\n        Mapping of Group enum to max instances of active broadcasters per group\n        ', key_type=TunableEnumEntry(tunable_type=WildlifeEncounterGroups, default=WildlifeEncounterGroups.INVALID, invalid_enums=(WildlifeEncounterGroups.INVALID,)), value_type=TunableRange(tunable_type=int, minimum=0, default=1, display_name='max_active_instances'))
    INSTANCE_TUNABLES = {'wildlife_encounter_tuning': OptionalTunable(tunable=TunableList(description='\n                List of details for each encounter area wildlife broadcaster\n                ', tunable=TunableTuple(encounter_object=TunableReference(description='\n                        Reference to wildlife broadcaster object\n                        ', manager=services.definition_manager(), pack_safe=True), chance_of_activation=TunablePercent(description='\n                        Percent chance that this broadcaster will be activated.\n                        ', default=0.0), group_name=TunableEnumEntry(tunable_type=WildlifeEncounterGroups, default=WildlifeEncounterGroups.INVALID))), enabled_name='encounter_area_list')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_encounter_list = []
        self._last_encounter_roll_date = None
        self._alarm_handler = None
        self._wildlife_group_count = defaultdict(int)

    def get_active_encounter_list(self):
        return self._active_encounter_list

    def get_active_group_counts(self):
        return self._wildlife_group_count

    def on_startup(self):
        super().on_startup()
        if self.wildlife_encounter_tuning:
            if self.ACTIVE_STATE is None or self.INACTIVE_STATE is None:
                return
            now = services.time_service().sim_now
            current_day = now.absolute_days()
            if current_day != self._last_encounter_roll_date:
                self.roll_active_encounters()
                self._last_encounter_roll_date = current_day
                time_span = now.time_till_next_day_time(self.DAILY_ROLL_TIME)
                repeating_time_span = date_and_time.create_time_span(days=1)
                self._alarm_handler = alarms.add_alarm(self, time_span, self.roll_active_encounters_callback, repeating=True, repeating_time_span=repeating_time_span)

    def on_shutdown(self):
        if self._alarm_handler is not None:
            alarms.cancel_alarm(self._alarm_handler)
            self._alarm_handler = None
        super.on_shutdown()

    def roll_active_encounters_callback(self, _alarm_handle):
        self.roll_active_encounters()
        self._last_encounter_roll_date = services.time_service().sim_now.absolute_days()

    def roll_active_encounters(self):
        self._active_encounter_list.clear()
        if self.wildlife_encounter_tuning:
            wildlife_encounter_data_list = random.sample(self.wildlife_encounter_tuning, len(self.wildlife_encounter_tuning))
            self._wildlife_group_count.clear()
            for encounter_data in wildlife_encounter_data_list:
                area_objects = list(services.object_manager().get_objects_of_def_id_gen(encounter_data.encounter_object.id))
                for area_object in area_objects:
                    if not area_object.has_component(types.STATE_COMPONENT):
                        pass
                    elif self._wildlife_group_count[encounter_data.group_name] > self.WILDLIFE_ENCOUNTER_GROUPS[encounter_data.group_name]:
                        area_object.set_state(self.INACTIVE_STATE.state, self.INACTIVE_STATE)
                    elif random.random() < encounter_data.chance_of_activation:
                        self._wildlife_group_count[encounter_data.group_name] += 1
                        area_object.set_state(self.ACTIVE_STATE.state, self.ACTIVE_STATE)
                        self._active_encounter_list.append(area_object.guid64)
                    else:
                        area_object.set_state(self.INACTIVE_STATE.state, self.INACTIVE_STATE)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        if self.wildlife_encounter_tuning:
            writer.write_uint64s(ACTIVE_ENCOUNTER_AREAS, self._active_encounter_list)
            writer.write_uint64s(ACTIVE_GROUP_NAMES, self._wildlife_group_count.keys())
            writer.write_uint64s(ACTIVE_GROUP_COUNTS, self._wildlife_group_count.values())
            writer.write_uint64(WILDLIFE_LAST_ROLL_DATE, self._last_encounter_roll_date)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if self.wildlife_encounter_tuning:
            self._active_encounter_list = reader.read_uint64s(ACTIVE_ENCOUNTER_AREAS, [])
            wildlife_group_keys = reader.read_uint64s(ACTIVE_GROUP_NAMES, [])
            wildlife_group_values = reader.read_uint64s(ACTIVE_GROUP_COUNTS, [])
            self._last_encounter_roll_date = reader.read_uint64(WILDLIFE_LAST_ROLL_DATE, 0)
            self._wildlife_group_count = dict(zip(wildlife_group_keys, wildlife_group_values))
        super()._load_custom_zone_director(zone_director_proto, reader)

class WildlifeEncounterTestByGroup(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'wildlife_encounter_group': TunableEnumEntry(description='\n            The wildlife encounter group to test against.\n            ', tunable_type=WildlifeEncounterGroups, default=WildlifeEncounterGroups.INVALID, invalid_enums=(WildlifeEncounterGroups.INVALID,)), 'invert': Tunable(description='\n            If checked, this test will return the opposite of what it\'s tuned to\n            return. For instance, if "invert" is set and group count is 0,\n            the test will return true.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {}

    def __call__(self):
        walkby_director = services.current_zone().ambient_service.get_walkby_director()
        if walkby_director is None:
            return TestResult(False, 'Wildlife encounter -- Walkby director not active.')
        group_count = walkby_director.get_active_group_counts()
        test_group_count = group_count.get(self.wildlife_encounter_group, 0)
        if self.invert:
            if test_group_count > 0:
                return TestResult(False, 'Wildlife encounter active, but test inverted.')
        elif test_group_count == 0:
            return TestResult(False, 'Wildlife encounter inactive.')
        return TestResult.TRUE
