from date_and_time import create_time_span, create_date_and_time, DateAndTimefrom math import floorfrom sims.university.university_housing_tuning import UniversityHousingTuningfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import Tunable, TunableInterval, TunableList, TunableTuple, TunableRangefrom sims.university.university_enums import EnrollmentStatusfrom story_progression.story_progression_action import _StoryProgressionActionfrom tunable_time import TunableTimeOfDayimport servicesimport sims4logger = sims4.log.Logger('StoryProgressionActionUniversity', default_owner='jmorrow')
class StoryProgressionActionUniversity(_StoryProgressionAction):
    UNSET = 0
    FACTORY_TUNABLES = {'time_to_update_progress': TunableTimeOfDay(description='\n            The approximate time of day when the action should update story \n            progress.\n            ', default_hour=20), 'performance_gain_per_day': TunableInterval(description='\n            The amount of work performance to give a university student per day.\n            ', tunable_type=float, default_lower=70, default_upper=90, minimum=0), 'number_of_classes_to_take_on_reenrollment': TunableList(description='\n            A list of weighted numbers of classes to take when this story\n            progression action re-enrolls a sim.\n            ', tunable=TunableTuple(weight=Tunable(description='\n                    The relative chance of taking this number of classes.\n                    ', tunable_type=int, default=1), number_of_classes=TunableRange(description='\n                    The number of classes to take.\n                    ', tunable_type=int, default=3, minimum=1)))}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._next_update_time = None
        self._weighted_class_counts = []
        for pair in self.number_of_classes_to_take_on_reenrollment:
            self._weighted_class_counts.append((pair.weight, pair.number_of_classes))

    def save(self, data):
        if self._next_update_time is None:
            data.university_action.next_update_time = StoryProgressionActionUniversity.UNSET
        else:
            data.university_action.next_update_time = self._next_update_time.absolute_ticks()

    def load(self, data):
        university_data = data.university_action
        if university_data.next_update_time == StoryProgressionActionUniversity.UNSET:
            self._next_update_time = None
        else:
            self._next_update_time = DateAndTime(university_data.next_update_time)

    def should_process(self, options):
        now = services.time_service().sim_now
        if self._next_update_time is None:
            self._next_update_time = create_date_and_time(days=floor(now.absolute_days()), hours=self.time_to_update_progress.hour())
            if self._next_update_time < now:
                self._next_update_time += create_time_span(days=1)
        if now >= self._next_update_time:
            self._next_update_time += create_time_span(days=1)
            return True
        return False

    def process_action(self, story_progression_flags):
        for sim_info in services.sim_info_manager().get_all():
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                pass
            elif sim_info in services.active_household():
                pass
            else:
                enrollment_status = degree_tracker.get_enrollment_status()
                if enrollment_status == EnrollmentStatus.ENROLLED:
                    if degree_tracker.term_started_time is None:
                        pass
                    else:
                        course_slots = degree_tracker.get_career_course_slots()
                        for course_slot in course_slots:
                            performance = self.performance_gain_per_day.random_float()
                            course_slot.add_work_performance(performance)
                        if enrollment_status == EnrollmentStatus.NOT_ENROLLED:
                            if not sim_info.is_played_sim:
                                self._reenroll(sim_info)
                                if enrollment_status == EnrollmentStatus.GRADUATED and sim_info.zone_id in UniversityHousingTuning.get_university_housing_zone_ids() and not sim_info.is_played_sim:
                                    household = sim_info.household
                                    if household.household_size == 1:
                                        household.clear_household_lot_ownership()
                                    household_manager = services.household_manager()
                                    target_household = household_manager.create_household(sim_info.account)
                                    household_manager.switch_sim_from_household_to_target_household(sim_info, household, target_household)
                        elif enrollment_status == EnrollmentStatus.GRADUATED and sim_info.zone_id in UniversityHousingTuning.get_university_housing_zone_ids() and not sim_info.is_played_sim:
                            household = sim_info.household
                            if household.household_size == 1:
                                household.clear_household_lot_ownership()
                            household_manager = services.household_manager()
                            target_household = household_manager.create_household(sim_info.account)
                            household_manager.switch_sim_from_household_to_target_household(sim_info, household, target_household)
                elif enrollment_status == EnrollmentStatus.NOT_ENROLLED:
                    if not sim_info.is_played_sim:
                        self._reenroll(sim_info)
                        if enrollment_status == EnrollmentStatus.GRADUATED and sim_info.zone_id in UniversityHousingTuning.get_university_housing_zone_ids() and not sim_info.is_played_sim:
                            household = sim_info.household
                            if household.household_size == 1:
                                household.clear_household_lot_ownership()
                            household_manager = services.household_manager()
                            target_household = household_manager.create_household(sim_info.account)
                            household_manager.switch_sim_from_household_to_target_household(sim_info, household, target_household)
                elif enrollment_status == EnrollmentStatus.GRADUATED and sim_info.zone_id in UniversityHousingTuning.get_university_housing_zone_ids() and not sim_info.is_played_sim:
                    household = sim_info.household
                    if household.household_size == 1:
                        household.clear_household_lot_ownership()
                    household_manager = services.household_manager()
                    target_household = household_manager.create_household(sim_info.account)
                    household_manager.switch_sim_from_household_to_target_household(sim_info, household, target_household)

    def _reenroll(self, sim_info):
        degree_tracker = sim_info.degree_tracker
        degree_tracker.enroll(degree_tracker.get_major(), degree_tracker.get_university(), weighted_random_item(self._weighted_class_counts), [])
