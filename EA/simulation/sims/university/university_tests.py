from event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeSim, ParticipantType, ParticipantTypeSingle, ParticipantTypeSingleSim, ParticipantTypeActorTargetSimfrom sims.sim_info_tests import MatchTypefrom sims.university.university_enums import EnrollmentStatus, FinalCourseRequirement, Gradefrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, TunableReference, TunableList, OptionalTunable, TunableEnumEntry, TunableTuple, TunableThreshold, Tunable, TunablePackSafeReference, TunableSetfrom traits.trait_type import TraitTypefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport event_testing.test_baseimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('UniversityTests')
class UniversityEnrollmentTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    class _SpecificMajors(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'_majors': TunableWhiteBlackList(description="\n                The sim's enrolled major must match against the whitelist and blacklist\n                to pass.\n                ", tunable=TunableReference(description='\n                    A University major to test against.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY_MAJOR)))}

        def is_valid_major(self, sim_info, tooltip=None):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, '{0} has no degree tracker.', sim_info, tooltip=tooltip)
            major = degree_tracker.get_major()
            if not self._majors.test_item(major):
                return TestResult(False, "{0}'s enrolled majors do not match the tuned whitelist/blacklist.", sim_info, tooltip=tooltip)
            return TestResult.TRUE

    class _AnyMajors(HasTunableSingletonFactory, AutoFactoryInit):

        def is_valid_major(self, sim_info, tooltip=None):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, '{0} has no degree tracker.', sim_info, tooltip=tooltip)
            if degree_tracker.get_enrolled_major() is None:
                return TestResult(False, '{0} is not enrolled in a major.', sim_info, tooltip=tooltip)
            return TestResult.TRUE

    class _NoMajor(HasTunableSingletonFactory, AutoFactoryInit):

        def is_valid_major(self, sim_info, tooltip=None):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is not None and degree_tracker.get_enrolled_major() is not None:
                return TestResult(False, '{0} is enrolled in a major.', sim_info, tooltip=tooltip)
            return TestResult.TRUE

    FACTORY_TUNABLES = {'major': TunableVariant(description='\n            Which major(s) the sim must be pursuing.\n            ', any_majors=_AnyMajors.TunableFactory(), specific_majors=_SpecificMajors.TunableFactory(), no_major=_NoMajor.TunableFactory(), locked_args={'disabled': None}, default='any_majors'), 'university': OptionalTunable(description='\n            University in which the sim must be enrolled.\n            If Disabled, sim can be in any university.\n            ', tunable=TunableReference(description='\n                The university to filter for.\n                ', manager=services.get_instance_manager(Types.UNIVERSITY))), 'enrollment_status': OptionalTunable(description='\n            Enrollment status to test against. \n            If Disabled, sim can have any enrollment status.\n            ', disabled_name="Don't_Test", tunable=TunableWhiteBlackList(description="\n                The sim's enrollment status must match the whitelist and blacklist\n                to pass.\n                ", tunable=TunableEnumEntry(description='\n                    The enrollment status to check against.\n                    ', tunable_type=EnrollmentStatus, default=EnrollmentStatus.NONE))), 'subject': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'match_type': TunableEnumEntry(description='\n            When testing multiple participants if MATCH_ALL is set, then all the\n            participants need to pass the test.\n             \n            If MATCH_ANY is set, test will pass as soon as one of them meet the\n            criteria\n            ', tunable_type=MatchType, default=MatchType.MATCH_ALL)}

    def is_valid(self, sim_info, tooltip=None):
        if self.major is not None:
            valid_major_result = self.major.is_valid_major(sim_info, tooltip=tooltip)
            if not valid_major_result:
                return valid_major_result
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            return TestResult(False, "{0} doesn't have a degree tracker.", sim_info, tooltip=tooltip)
        if self.university is not None:
            current_university = degree_tracker.get_university()
            if current_university is None:
                return TestResult(False, '{0} has no university specified in their degree tracker.', sim_info, tooltip=tooltip)
            if current_university.guid64 != self.university.guid64:
                return TestResult(False, '{0} is not enrolled in the correct university.', sim_info, tooltip=tooltip)
        if self.enrollment_status is not None and not self.enrollment_status.test_item(degree_tracker._enrollment_status):
            return TestResult(False, '{0} does not pass the whitelist/blacklist for university enrollment status', sim_info, tooltip=tooltip)
        return TestResult.TRUE

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets, targets=None, tooltip=None):
        if not test_targets:
            return TestResult(False, 'UniversityEnrollmentTest failed due no targets.', tooltip=self.tooltip)
        if self.match_type == MatchType.MATCH_ALL:
            for target in test_targets:
                result = self.is_valid(target, tooltip=self.tooltip)
                if not result:
                    return result
            return TestResult.TRUE
        for target in test_targets:
            result = self.is_valid(target, tooltip=self.tooltip)
            if result:
                return result
        return result

class UniversityClassroomTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    REFERENCE_SOURCE = 1
    PARTICIPANT_SOURCE = 2
    FACTORY_TUNABLES = {'course': TunableVariant(description='\n            Which course to see if the target is the classroom for\n            ', from_university_course_reference=TunableTuple(description='\n                If selected we determine the course directly from the specified\n                CourseSlot.\n                ', from_university_course_reference=TunableReference(description='\n                    Course slot from which to check proper classroom.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions=('UniversityCourseCareerSlot',), pack_safe=True), locked_args={'course_type': REFERENCE_SOURCE}), from_participant=TunableTuple(description='\n                If selected we get the course slot id from the passed participant\n                i.e. pickedItemId\n                ', from_participant=TunableEnumEntry(description='\n                    The participant from which the course slot ID will be pulled. \n                    Typically should be PickedItemId if this test comes via a \n                    CareerPickerSuperInteraction.\n                    ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId), locked_args={'course_type': PARTICIPANT_SOURCE}), default='from_university_course_reference'), 'subject': TunableEnumEntry(description='\n            The sim who is testing to see if the target is their classroom\n            for the specified course.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target': TunableEnumEntry(description="\n            The object being tested to see if it's the classroom.\n            ", tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'during_office_hours_only': Tunable(description='\n            If checked, the office hour test set must pass for the course for this \n            test to pass.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return_args = {'subjects': self.subject, 'targets': self.target}
        if self.course.course_type == UniversityClassroomTest.PARTICIPANT_SOURCE:
            return_args['career_guids'] = self.course.from_participant
        return return_args

    @cached_test
    def __call__(self, subjects=None, targets=None, career_guids=None, tooltip=None):
        if career_guids is not None:
            career_guid = next(iter(career_guids))
        else:
            career_guid = self.course.from_university_course_reference.guid64
        for sim in subjects:
            sim_info = sim.sim_info
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                logger.error('Trying to test university classroom for sim {} with no degree tracker', sim_info)
                return TestResult(False, "{} doesn't have degree tracker", sim, tooltip=tooltip)
            course_data = degree_tracker.get_course_data(career_guid)
            if course_data is None:
                logger.error("Trying to test university classroom for sim {} who doesn't have course slot {}", sim_info, career_guid)
                return TestResult(False, "{} doesn't have career {}", sim, career_guid, tooltip=tooltip)
            for target in targets:
                if not target.has_any_tag(course_data.classroom_tag[degree_tracker.get_university()]):
                    return TestResult(False, "{} isn't correct classroom", target, tooltip=tooltip)
            if self.during_office_hours_only:
                career_tracker = sim_info.career_tracker
                course_career = career_tracker.get_career_by_uid(career_guid)
                if course_career is not None:
                    career_level_data = course_career.current_level_tuning()
                    resolver = SingleSimResolver(sim_info)
                    result = career_level_data.office_hour_test_set.run_tests(resolver=resolver, search_for_tooltip=True)
                    if not result:
                        return result
        return TestResult.TRUE

class UniversityTests(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    class AcceptedPrestigeDegreeCountTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose degree will be used.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'number_to_test': TunableThreshold(description='\n                The number of accepted prestige degrees to pass this test.\n                ')}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            acc_prestige_degrees = degree_tracker.get_accepted_prestige_degrees()
            num_acc_prestige_degrees = 0
            for degrees in acc_prestige_degrees.values():
                num_acc_prestige_degrees += len(degrees)
            if not self.number_to_test.compare(num_acc_prestige_degrees):
                return TestResult(False, '{} of accepted prestige degrees, failed threshold {}:{}.', num_acc_prestige_degrees, self.number_to_test.comparison, self.number_to_test.value, tooltip=tooltip)
            return TestResult.TRUE

    class CanApplyTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose degree will be used.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            completed_degree_ids = set(degree_tracker.previous_majors)
            not_yet_accepted_degrees = degree_tracker.get_not_yet_accepted_degrees()
            for not_yet_accepted_degree_ids in not_yet_accepted_degrees.values():
                available_degree_ids = not_yet_accepted_degree_ids - completed_degree_ids
                if len(available_degree_ids) > 0:
                    return TestResult.TRUE
            return TestResult(False, "Actor {} can't apply to university.", actor, tooltip=tooltip)

    class CourseCareerSlotTest(HasTunableSingletonFactory, AutoFactoryInit):

        class _CompletedCoursesOnly(HasTunableSingletonFactory, AutoFactoryInit):

            def test(self, actor, course_info):
                if course_info.final_grade == Grade.UNKNOWN:
                    return TestResult(False, "Actor {}'s course {} is not completed.", actor, course_info.course_data)
                return TestResult.TRUE

        class _OngoingCoursesOnly(HasTunableSingletonFactory, AutoFactoryInit):

            def test(self, actor, course_info):
                if course_info.final_grade != Grade.UNKNOWN:
                    return TestResult(False, "Actor {}'s course {} is completed.", actor, course_info.course_data)
                return TestResult.TRUE

        class _CompletedAndOngoingCourses(HasTunableSingletonFactory, AutoFactoryInit):

            def test(self, actor, course_info):
                return TestResult.TRUE

        class _SpecificCourses(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'courses': TunableWhiteBlackList(description='\n                    A list of courses to test the course career slot for. A sim must \n                    have at least one course in their whitelist and none in their \n                    blacklist to pass (by default). \n                    ', tunable=TunablePackSafeReference(description='\n                        A specific course to test the course career slot(s) for.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY_COURSE_DATA)))}

            def test(self, actor, course_slots, invert, course_completion_status, tooltip=None):
                degree_tracker = actor.sim_info.degree_tracker
                if degree_tracker is None:
                    return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
                for career_slot in course_slots:
                    if career_slot is None:
                        pass
                    else:
                        course_info = degree_tracker.course_infos.get(career_slot.guid64)
                        if course_info is None:
                            pass
                        elif course_completion_status.test(actor, course_info):
                            pass
                        else:
                            course_data = course_info.course_data
                            if self.courses.test_item(course_data):
                                if invert:
                                    return TestResult(False, "Actor {}'s course {} is associated with at least one of the specified course career slots", actor, course_data, tooltip=tooltip)
                                return TestResult.TRUE
                if invert:
                    return TestResult.TRUE
                return TestResult(False, "Actor {}'s course career slots and valid course datas do not match.", actor, tooltip=tooltip)

        class _AnyCourse(HasTunableSingletonFactory, AutoFactoryInit):

            def test(self, actor, course_slots, invert, course_completion_status, tooltip=None):
                degree_tracker = actor.sim_info.degree_tracker
                if degree_tracker is None:
                    return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
                for career_slot in course_slots:
                    if career_slot is None:
                        pass
                    else:
                        course_info = degree_tracker.course_infos.get(career_slot.guid64)
                        if course_info is None:
                            pass
                        elif not course_completion_status.test(actor, course_info):
                            pass
                        else:
                            if invert:
                                return TestResult(False, 'Actor {} has valid course data in at least one of the course career slots.', actor, tooltip=tooltip)
                            return TestResult.TRUE
                if invert:
                    return TestResult.TRUE
                return TestResult(False, 'Actor {} has no valid course data in any of the specified course career slots.', actor, tooltip=tooltip)

        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose course career slot we will consider.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'course_career_slots': TunableSet(description='\n                The set of course career slots to test. If the course data is \n                associated with any careers in the list, the test will evaluate to True.\n                ', tunable=TunablePackSafeReference(description='\n                    The course career slot we will test course data for.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions='UniversityCourseCareerSlot')), 'course_data': TunableVariant(description='\n                The course data we will test the course career slot(s) for.\n                ', specific_courses=_SpecificCourses.TunableFactory(), any_course=_AnyCourse.TunableFactory(), default='any_course'), 'invert': Tunable(description='\n                If checked, test will pass if all specified course career slots \n                do NOT match.\n                ', tunable_type=bool, default=False), 'course_completion_status': TunableVariant(description='\n                How we will test completed courses.\n                ', completed_courses_only=_CompletedCoursesOnly.TunableFactory(), ongoing_courses_only=_OngoingCoursesOnly.TunableFactory(), completed_and_ongoing_courses=_CompletedAndOngoingCourses.TunableFactory(), default='ongoing_courses_only')}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            return self.course_data.test(actor, self.course_career_slots, self.invert, self.course_completion_status, tooltip=tooltip)

    class CourseGradeTest(HasTunableSingletonFactory, AutoFactoryInit):

        class _KnownGrade(HasTunableSingletonFactory, AutoFactoryInit):

            def test(self, actor, final_grade, known_grade, grades_to_match, tooltip=None):
                if grades_to_match.test_item(known_grade):
                    return TestResult.TRUE
                return TestResult(False, "Actor {}'s course grade does not pass the white/black list.", actor, tooltip=tooltip)

        class _FinalGrade(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'use_known_as_fallback': Tunable(description="\n                    If enabled, the test will run against the sim's known grade \n                    if the final grade cannot be determined. \n                    ", tunable_type=bool, default=True)}

            def test(self, actor, final_grade, known_grade, grades_to_match, tooltip=None):
                grade = final_grade
                if self.use_known_as_fallback:
                    grade = known_grade
                if grade == Grade.UNKNOWN and grades_to_match.test_item(grade):
                    return TestResult.TRUE
                return TestResult(False, "Actor {}'s course grade does not pass the white/black list.", actor, tooltip=tooltip)

        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose course grade we will test. \n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'course_career_slot': TunablePackSafeReference(description='\n                The course career slot we will test the grade of.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions='UniversityCourseCareerSlot'), 'grades': TunableWhiteBlackList(description="\n                The white/black list of grades that the sim's course grade must\n                match.\n                ", tunable=TunableEnumEntry(description='\n                    A grade to test against.\n                    ', tunable_type=Grade, default=Grade.UNKNOWN)), 'grade_type': TunableVariant(description='\n                The grade type to compare against.\n                ', known_grade=_KnownGrade.TunableFactory(), final_grade=_FinalGrade.TunableFactory(), default='final_grade')}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Sim {} doesn't have degree tracker.", actor, tooltip=tooltip)
            if self.course_career_slot is None:
                return TestResult(False, 'The specified course career slot is None, probably because of packsafeness.', tooltip=tooltip)
            course_data = degree_tracker.course_infos.get(self.course_career_slot.guid64)
            if course_data is None:
                return TestResult(False, "Actor {} doesn't have course data associated with career {}.", actor, self.course_career_slot, tooltip=tooltip)
            final_grade = course_data.final_grade
            known_grade = course_data.known_grade
            return self.grade_type.test(actor, final_grade, known_grade, self.grades, tooltip=tooltip)

    class FinalRequirementTypeTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose course career slot we will consider.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'course_career_slot': TunablePackSafeReference(description='\n                The course career slot we will test the final project type of.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions='UniversityCourseCareerSlot'), 'final_requirement_type': TunableEnumEntry(description='\n                The final requirement type we will compare against.\n                ', tunable_type=FinalCourseRequirement, default=FinalCourseRequirement.EXAM)}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            if self.course_career_slot is None:
                return TestResult(False, 'Course Career Slot is None, probably because of PackSafeness.', tooltip=tooltip)
            course_data = degree_tracker.get_course_data(self.course_career_slot.guid64)
            if course_data is None:
                return TestResult(False, "Actor {} doesn't have course data associated with career {}.", actor, self.course_career_slot, tooltip=tooltip)
            final_requirement_type = course_data.final_requirement_type
            if final_requirement_type is self.final_requirement_type:
                return TestResult.TRUE
            return TestResult(False, "Actor {}'s course {} has a final requirement type of {} but needed a final requirement type of {}", actor, course_data, course_data.final_requirement_type, self.final_requirement_type, tooltip=tooltip)

    class FinalRequirementCompletedTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose course career slot we will consider.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'course_career_slot': TunablePackSafeReference(description='\n                The course career slot we will test the final project completion of.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions='UniversityCourseCareerSlot'), 'invert': Tunable(description="\n                If checked, the test will be inverted. In other words, a \n                sim will pass the test if they have NOT completed their \n                course's final requirement.\n                ", tunable_type=bool, default=False)}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            if self.course_career_slot is None:
                return TestResult(False, 'Course Career Slot is None, probably because of PackSafeness.', tooltip=tooltip)
            course_data = degree_tracker.course_infos.get(self.course_career_slot.guid64)
            if course_data is None:
                return TestResult(False, "Actor {} doesn't have course data associated with career {}.", actor, self.course_career_slot, tooltip=tooltip)
            if course_data.final_requirement_completed:
                if self.invert:
                    return TestResult(False, 'Actor {} has not completed the final requirement for course {}.', actor, course_data, tooltip=tooltip)
            elif not self.invert:
                return TestResult(False, 'Actor {} has completed the final requirement for course {}.', actor, course_data, tooltip=tooltip)
            return TestResult.TRUE

    class GPATest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose GPA will be used. Must have a GPA greater than \n                or equal to the tuned GPA to pass the test.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'gpa': TunableThreshold(description='\n                The GPA to compare against.\n                ', value=Tunable(description='\n                    The value of the threshold that the gpa is compared\n                    against.\n                    ', tunable_type=float, default=3.5))}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            gpa = degree_tracker.get_gpa()
            if gpa is not None and self.gpa.compare(gpa):
                return TestResult.TRUE
            return TestResult(False, 'Actor {} has a GPA of {}, but needs to have a GPA of {} or higher.', actor, gpa, self.gpa, tooltip=tooltip)

    class HasDegreeToEnrollTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor whose degree will be used.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

        def get_expected_args(self):
            return {'actors': self.actor}

        def test(self, tooltip=None, actors=()):
            actor = next(iter(actors), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            degree_tracker = actor.sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            available_degrees = degree_tracker.get_available_degrees_to_enroll()
            if not available_degrees:
                return TestResult(False, 'No available degree to enroll for Actor {}.', actor, tooltip=tooltip)
            return TestResult.TRUE

    class HasSameMajorTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor to compare the major of.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'target': TunableEnumEntry(description='\n                The target to compare the major of.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim)}

        def get_expected_args(self):
            return {'actors': self.actor, 'targets': self.target}

        def test(self, tooltip=None, actors=(), targets=()):
            actor = next(iter(actors), None)
            target = next(iter(targets), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            if target is None:
                return TestResult(False, "Target {} doesn't exist.", self.target, tooltip=tooltip)
            actor_degree_tracker = actor.sim_info.degree_tracker
            if actor_degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            target_degree_tracker = target.sim_info.degree_tracker
            if target_degree_tracker is None:
                return TestResult(False, "Target {} doesn't have degree tracker.", target, tooltip=tooltip)
            actor_major = actor_degree_tracker.get_major()
            target_major = target_degree_tracker.get_major()
            if actor_major is target_major:
                return TestResult.TRUE
            return TestResult(False, 'Actor {} has major {} , but Target {} has major {}.', actor, actor_major, target, target_major, tooltip=tooltip)

    class HasSameUniversityTest(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n                The actor to compare the university of.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'target': TunableEnumEntry(description='\n                The target to compare the university of.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim), 'invert': Tunable(description='\n                If checked, the test will be inverted. In other words, this \n                test will pass if the two Sims are from rival (different) \n                universities.\n                ', tunable_type=bool, default=False)}

        def get_expected_args(self):
            return {'actors': self.actor, 'targets': self.target}

        def test(self, tooltip=None, actors=(), targets=()):
            actor = next(iter(actors), None)
            target = next(iter(targets), None)
            if actor is None:
                return TestResult(False, "Actor {} doesn't exist.", self.actor, tooltip=tooltip)
            if target is None:
                return TestResult(False, "Target {} doesn't exist.", self.target, tooltip=tooltip)
            actor_degree_tracker = actor.sim_info.degree_tracker
            if actor_degree_tracker is None:
                return TestResult(False, "Actor {} doesn't have degree tracker.", actor, tooltip=tooltip)
            target_degree_tracker = target.sim_info.degree_tracker
            if target_degree_tracker is None:
                return TestResult(False, "Target {} doesn't have degree tracker.", target, tooltip=tooltip)
            actor_university = actor_degree_tracker.get_university()
            target_university = target_degree_tracker.get_university()
            if actor_university is not target_university and not self.invert:
                return TestResult(False, 'Checking for same universities: Actor {} has university {} , but Target {} has university {}.', actor, actor_university, target, target_university, tooltip=tooltip)
            if actor_university is target_university and self.invert:
                return TestResult(False, 'Checking for different universities: Actor {} and Target {} both have university {}.', actor, target, target_university, tooltip=tooltip)
            return TestResult.TRUE

    FACTORY_TUNABLES = {'test': TunableVariant(description='\n            The university test to perform.\n            ', accepted_prestige_degree_count_test=AcceptedPrestigeDegreeCountTest.TunableFactory(), can_apply_test=CanApplyTest.TunableFactory(), course_career_slot_test=CourseCareerSlotTest.TunableFactory(), course_grade_test=CourseGradeTest.TunableFactory(), final_requirement_completed_test=FinalRequirementCompletedTest.TunableFactory(), final_requirement_type_test=FinalRequirementTypeTest.TunableFactory(), gpa_test=GPATest.TunableFactory(), has_degree_to_enroll_test=HasDegreeToEnrollTest.TunableFactory(), has_same_degree_test=HasSameMajorTest.TunableFactory(), has_same_university_test=HasSameUniversityTest.TunableFactory(), default='has_degree_to_enroll_test')}

    def get_expected_args(self):
        return self.test.get_expected_args()

    @cached_test
    def __call__(self, **kwargs):
        return self.test.test(tooltip=self.tooltip, **kwargs)

class UniversityProfessorTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    class _ByStudent(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'student': TunableEnumEntry(description='\n                The participant type to find the student in.\n                ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)}

        def get_expected_args(self):
            return {'students': self.student}

        def __call__(self, targets, students, course, tooltip):
            for target in targets:
                for student in students:
                    degree_tracker = student.degree_tracker
                    if degree_tracker is None:
                        return TestResult(False, '{} does not have a degree tracker.', student, tooltip=tooltip)
                    student_university = degree_tracker.get_university()
                    if student_university is None:
                        return TestResult(False, '{} is not enrolled in university.', student, tooltip=tooltip)
                    courses = student.degree_tracker.get_courses()
                    for enrolled_course in courses:
                        if target.has_trait(enrolled_course.professor_assignment_trait[student_university]):
                            break
                    return TestResult(False, "{} is not a professor for any of {}'s classes", target, student, tooltip=tooltip)
            return TestResult.TRUE

    class _ByParticipantType(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'course': OptionalTunable(description='\n                If enabled, the target Sim must be the professor of the\n                specified course. If not enabled the professor can be professor\n                of any course.\n                ', tunable=TunableTuple(description='\n                    A pair of participant type and student to use for your checks.\n                    Since you need some reference as to whos class and what\n                    university we have to specify the student.\n                    ', course_participant=TunableEnumEntry(description='\n                        The participant type to find the course specification in.\n                        ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId), student=TunableEnumEntry(description='\n                        The participant type to find the student in.\n                        ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)))}

        def get_expected_args(self):
            if self.course is not None:
                return {'course': self.course.course_participant, 'students': self.course.student}
            return {}

        def __call__(self, targets, students, course, tooltip):
            for target in targets:
                if course:
                    career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
                    career = career_manager.get(course[0])
                    if career is None:
                        return TestResult(False, "Didn't choose a valid career slot to look for the course in.", tooltip=tooltip)
                    for student in students:
                        degree_tracker = student.degree_tracker
                        if degree_tracker is None:
                            return TestResult(False, '{} does not have a degree tracker.', student, tooltip=tooltip)
                        course_data = degree_tracker.get_course_data(career.guid64)
                        if course_data is None:
                            return TestResult(False, "Career Slot being checked against isn't actually an active slot for an enrolled course.", tooltip=tooltip)
                        student_university = degree_tracker.get_university()
                        professor_trait = course_data.professor_assignment_trait[student_university]
                        if not target.has_trait(professor_trait):
                            return TestResult(False, '{} is not the professor for {} in slot {}', target, course_data, career, tooltip=tooltip)
                else:
                    traits = target.trait_tracker.get_traits_of_type(TraitType.PROFESSOR)
                    if not traits:
                        return TestResult(False, "{} doesn't have any PROFESSOR type traits.", target, tooltip=tooltip)
            return TestResult.TRUE

    class _ByCareerSlot(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'student': TunableEnumEntry(description='\n                The participant type to find the student in.\n                ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'career_slot': TunableReference(description='\n                The career slot to find the course to check whether or not\n                the target is the professor of.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions=('UniversityCourseCareerSlot',))}

        def get_expected_args(self):
            return {'students': self.student}

        def __call__(self, targets, students, course, tooltip):
            for target in targets:
                for student in students:
                    degree_tracker = student.degree_tracker
                    if degree_tracker is None:
                        return TestResult(False, '{} is not a student', student, tooltip=tooltip)
                    course_data = degree_tracker.get_course_data(self.career_slot.guid64)
                    if course_data is None:
                        return TestResult(False, "{} doesn't have any enrolled classed in {}", student, self.career_slot, tooltip=tooltip)
                    student_university = student.degree_tracker.get_university()
                    if not target.trait_tracker.has_trait(course_data.professor_assignment_trait[student_university]):
                        return TestResult(False, "{} is not in {}'s class for {}", student, target, self.career_slot, tooltip=tooltip)
            return TestResult.TRUE

    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The Sim to test the professorness of. If student is not specified\n            then test whether or not this Sim is the professor of ANY course.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.TargetSim), 'test': TunableVariant(description='\n            The test used to see if the target is a professor or not.\n            ', student=_ByStudent.TunableFactory(), participant=_ByParticipantType.TunableFactory(), career_slot=_ByCareerSlot.TunableFactory(), default='student'), 'negate': Tunable(description='\n            If checked then the value of the test result will be reversed.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        args = {'targets': self.target}
        args.update(self.test.get_expected_args())
        return args

    def __call__(self, targets, students=None, course=None):
        result = self.test(targets, students, course, self.tooltip)
        if result or self.negate:
            return TestResult.TRUE
        elif result and self.negate:
            return TestResult(False, 'Negated True result to False. The settings are target:{}, students:{}, course:{}, test:{}, negate:{}', targets, students, course, self.test, self.negate, tooltip=self.tooltip)
        return result

class UniversityHousingConfigurationTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'university': OptionalTunable(description='\n            Checks for a specific university requirement.\n            ', tunable=TunablePackSafeReference(description='\n                Which university to check for.\n                ', manager=services.get_instance_manager(Types.UNIVERSITY)))}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self, tooltip=None):
        zone_id = services.current_zone_id()
        if zone_id is None:
            return TestResult(False, 'No current ZoneId found', tooltip=tooltip)
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is None:
            return TestResult(False, 'No zone data found for ZoneID:{}', zone_id, tooltip=tooltip)
        if zone_data.HasField('university_housing_configuration') and zone_data.university_housing_configuration is None:
            return TestResult(False, 'No university housing configuration data found', tooltip=tooltip)
        config_data = zone_data.university_housing_configuration
        if self.university is not None:
            if not config_data.HasField('university_id'):
                return TestResult(False, 'No university university id found in configuration data', tooltip=tooltip)
            university_id = config_data.university_id
            if self.university.guid64 != university_id:
                return TestResult(False, "University id:{} doesn't match the venue configuration's university id:{}", self.university.guid64, university_id, tooltip=tooltip)
            return TestResult.TRUE
        return TestResult(False, 'No requirements tuned on test', tooltip=tooltip)
