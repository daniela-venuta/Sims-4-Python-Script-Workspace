from careers.career_story_progression import CareerStoryProgressionParametersfrom careers.career_tuning import Career, TunableCareerTrack, CareerLevelfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import CompoundTestList, TunableTestSetWithTooltipfrom interactions.context import QueueInsertStrategyfrom sims.university.university_enums import FinalCourseRequirement, HomeworkCheatingStatusfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, TunableReference, OptionalTunablefrom sims4.utils import classproperty, constpropertyfrom tunable_multiplier import TunableMultiplier, TestedSumimport interactions.contextimport servicesimport sims4.loglogger = sims4.log.Logger('UniversityTuning', default_owner='nabaker')
class UniversityCourseCareerSlot(Career):
    INSTANCE_TUNABLES = {'caught_cheating_loot': TunableReference(description='\n            Loot action applied on a sim who has been caught cheating\n            on homework. It is applied at the time that homework is processed.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION)), 'successful_cheating_loot': TunableReference(description='\n            Loot action applied on a sim who has cheated on homework but\n            was not caught. It is applied at the time that homework is processed.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION)), 'prelecture_affordance': OptionalTunable(tunable=TunableReference(description='\n                The affordance that is pushed onto the Sim prior to going to \n                class.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))), 'end_of_course_loot': TunableReference(description='\n            Loot action applied on a sim when all work has been completed for \n            a course. \n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION))}

    def put_sim_in_career_rabbit_hole(self):
        sim = self._get_sim()
        if self.prelecture_affordance is not None and sim is not None:
            context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.LAST)
            sim.push_super_affordance(self.prelecture_affordance, sim, context, career_uid=self.guid64)
        return super().put_sim_in_career_rabbit_hole()

    def end_career_session(self):
        super().end_career_session()
        degree_tracker = self._sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('ending career session for {} with no degree tracker', self._sim_info)
            return
        degree_tracker.finish_lecture(self.guid64)
        self._process_cheating()

    def _process_cheating(self):
        degree_tracker = self._sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('Applying performance change for {} with no degree tracker', self._sim_info)
            return
        course_info = degree_tracker.course_infos.get(self.guid64)
        if course_info is None:
            logger.error('Applying performance change for {} on course career slot {}, but no course info was found.', self._sim_info, self)
            return
        resolver = SingleSimResolver(self._sim_info)
        cheating_status = course_info.homework_cheated
        degree_tracker.update_homework_cheating_status(self, HomeworkCheatingStatus.NONE)
        if cheating_status == HomeworkCheatingStatus.CHEATING_FAIL:
            self.caught_cheating_loot.apply_to_resolver(resolver)
        elif cheating_status == HomeworkCheatingStatus.CHEATING_SUCCESS:
            self.successful_cheating_loot.apply_to_resolver(resolver)

    def process_homework(self):
        metrics = self.current_level_tuning.performance_metrics
        gain = 0
        loss = 0

        def add_metric(value):
            nonlocal gain, loss
            if value >= 0:
                gain += value
            else:
                loss -= value

        for metric in metrics.statistic_metrics:
            if metric.performance_curve is not None:
                stat = self._sim_info.get_statistic(metric.statistic, add=False)
                if stat is not None:
                    stat_value = stat.get_value()
                    performance_mod = metric.performance_curve.get(stat_value)
                    add_metric(performance_mod)
        statistic_tracker = self._sim_info.statistic_tracker
        time_elapsed = self._current_work_end - self._current_work_start
        if statistic_tracker is not None:
            total = gain - loss
            delta = total*time_elapsed.in_ticks()/self._current_work_duration.in_ticks()
            self.add_work_performance(delta)
            session_stat = statistic_tracker.get_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE, add=True)
            session_stat.add_value(delta)
        self.resend_career_data()
        self._process_cheating()

    def complete_course(self):
        resolver = SingleSimResolver(self._sim_info)
        self.end_of_course_loot.apply_to_resolver(resolver)

    @classproperty
    def allow_multiple_careers(cls):
        return True

    @classmethod
    def get_spawn_point_tags(cls, sim_info):
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('Trying to get UniversityCourse spawn point from sim {} with no degree tracker', sim_info)
            return set()
        course_data = degree_tracker.get_course_data(cls.guid64)
        if course_data is None:
            logger.error('sim {} has no course for slot {} when getting spawn_point_tags.', sim_info, cls)
            return set()
        university = degree_tracker.get_university()
        if university not in course_data.spawn_point_tag:
            return set()
        return course_data.spawn_point_tag[university]

    @constproperty
    def is_course_slot():
        return True

    def can_change_level(self, demote=False):
        return False
lock_instance_tunables(UniversityCourseCareerSlot, available_for_club_criteria=False, can_be_fired=False, career_availablity_tests=CompoundTestList(), career_story_progression=CareerStoryProgressionParameters(joining=None, retiring=None, quitting=None), days_to_level_loss=0, demotion_buff=None, demotion_chance_modifiers=TunableMultiplier(base_value=0, multipliers=()), early_promotion_chance=TunableMultiplier(base_value=0, multipliers=()), early_promotion_modifiers=TunableMultiplier(base_value=0, multipliers=()), fired_buff=None, initial_pto=0, is_active=False, levels_lost_on_leave=0, promotion_buff=None, quittable_data=None, start_level_modifiers=TestedSum(base_value=0, modifiers=()), disable_pto=True, show_career_in_join_career_picker=False)
class UniversityCourseTrack(TunableCareerTrack):

    @classmethod
    def get_career_description(cls, sim):
        sim_info = sim.sim_info
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('Getting career_description for {} with no degree tracker', sim_info)
            return
        for (career_guid, course_info) in degree_tracker.course_infos.items():
            course_slot = sim_info.career_tracker.get_career_by_uid(career_guid)
            if course_slot is not None and course_slot.start_track == cls:
                return degree_tracker.get_course_description(course_info.course_data)
        logger.error('sim {} has no course for Track {} when getting career_description.', sim_info, cls)

    @classmethod
    def get_career_name(cls, sim):
        sim_info = sim.sim_info
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('Getting career_name for {} with no degree tracker', sim_info)
            return
        for (career_guid, course_info) in degree_tracker.course_infos.items():
            course_slot = sim_info.career_tracker.get_career_by_uid(career_guid)
            if course_slot is not None and course_slot.start_track == cls:
                return degree_tracker.get_course_name(course_info.course_data)
        logger.error('sim {} has no course for Track {} when getting career_name.', sim_info, cls)
lock_instance_tunables(UniversityCourseTrack, overmax=None)
class UniversityCourseSchedule(CareerLevel):
    INSTANCE_TUNABLES = {'final_requirement_type': TunableEnumEntry(description='\n            The final course requirement type for this schedule.  This \n            schedule can only be assigned to a course that has the same final\n            course requirement\n            ', tunable_type=FinalCourseRequirement, default=FinalCourseRequirement.NONE), 'office_hour_test_set': TunableTestSetWithTooltip(description='\n            Set of tests to determine if office hours are available for this course\n            ')}

    @classmethod
    def get_title(cls, sim):
        sim_info = sim.sim_info
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('Getting title for {} with no degree tracker', sim_info)
            return
        course_slot = cls.career
        course_data = degree_tracker.get_course_data(course_slot.guid64)
        if course_data is None:
            logger.error('sim {} has no course for slot {} when getting title.', sim_info, cls)
            return
        return degree_tracker.get_course_name(course_data)
lock_instance_tunables(UniversityCourseSchedule, promotion_audio_sting=None, ageup_branch_career=None, promotion_reward=None, screen_slam=None, simolean_trait_bonus=[], simoleons_for_assignments_per_day=0, demotion_performance_level=-100, fired_performance_level=-100, promote_performance_level=100)