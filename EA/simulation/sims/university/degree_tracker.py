from _collections import defaultdictimport itertoolsimport mathimport randomfrom protocolbuffers import SimObjectAttributes_pb2, UI_pb2, Consts_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom careers.career_enums import CareerPanelType, CareerCategoryfrom date_and_time import DateAndTime, TimeSpanfrom display_snippet_tuning import Scholarship, ScholarshipAmountEnumfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom filters.tunable import TraitFilterTerm, DynamicSimFilterfrom interactions.object_rewards import ObjectRewardsOperationfrom interactions.utils.loot import LootActionsfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.relationship_bit import RelationshipBitfrom scheduler import WeeklySchedulefrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.university.university_career_tuning import UniversityCourseCareerSlotfrom sims.university.university_enums import Grade, EnrollmentStatus, FinalCourseRequirement, UniversityHousingKickOutReason, HomeworkCheatingStatus, UniversityMajorStatusfrom sims.university.university_housing_tuning import UniversityHousingTuningfrom sims.university.university_loot_ops import GetScholarshipStatusLootfrom sims.university.university_scholarship_enums import ScholarshipStatusfrom sims.university.university_scholarship_tuning import ScholarshipMaintenanceEnum, ScholarshipTuningfrom sims.university.university_telemetry import UniversityTelemetryfrom sims.university.university_tuning import Universityfrom sims4.common import is_available_pack, Packfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.resources import Typesfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableMapping, TunableRange, TunableInterval, TunableEnumEntry, TunableTuple, TunableList, TunableReference, TunablePackSafeReferencefrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classpropertyfrom singletons import DEFAULTfrom tunable_time import TunableTimeSpan, Daysfrom tunable_utils.tested_list import TunableTestedListfrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_info_columns import UiDialogInfoInColumnsfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport alarmsimport cachesimport date_and_timeimport id_generatorimport objects.components.typesimport servicesimport sims4.loglogger = sims4.log.Logger('DegreeTracker', default_owner='nabaker')EMPTY_LINE = LocalizationHelperTuning.get_raw_text('')with sims4.reload.protected(globals()):
    GPA_THRESHOLDS = []
class DegreeTracker(SimInfoTracker):
    STARTING_PROFESSOR_REL_GAIN = 1
    PROFESSOR_REL_BIT = RelationshipBit.TunablePackSafeReference(description='\n        The rel bit to add between a professor and a Sim that attends a class\n        assigned to a professor.\n        ')
    CREDITS_REQUIRED = TunableRange(description='\n        Number of credits required to graduate.\n        ', tunable_type=int, default=14, minimum=1, export_modes=ExportModes.All)
    CREDITS_RETAINED = TunableRange(description='\n        Number of credits retained after graduation.\n        ', tunable_type=int, default=2, minimum=0)
    TERM_LENGTH = TunableRange(description='\n        The duration, in number of days, of a university term.  This does not \n        include weekends.\n        ', tunable_type=int, default=5, minimum=1)
    TERM_COURSE_COUNT = TunableInterval(description='\n        The min and max number of courses that a Sim may enroll in per term.\n        ', tunable_type=int, default_lower=1, default_upper=4, export_modes=ExportModes.All)
    COURSE_LECTURE_COUNT = TunableRange(description='\n        The number of lectures a Sim must attend per course.\n        ', tunable_type=int, default=2, minimum=1)
    START_OF_TERM_SCHEDULE = WeeklySchedule.TunableFactory(description='\n        A schedule of the possible days of the week and times where the start\n        of a term may occur.  Does not include weekends.\n        ')
    END_OF_TERM_SCHEDULE = WeeklySchedule.TunableFactory(description='\n        A schedule of the possible days of the week and times where the end of\n        term may occur.  Does not include weekends.\n        ')
    CREDIT_CARRYOVER_PERCENTAGE = TunableRange(description='\n        The percentage of credits that will carry over when a Sim switches \n        majors.\n        ', tunable_type=float, default=0.5, minimum=0)
    SUSPENSION_DURATION = TunableRange(description='\n        The number of days a Sim will stay suspended.  The Sim cannot enroll\n        in courses until the suspension is lifted.\n        ', tunable_type=int, default=5, minimum=1)
    DROPOUT_DURATION = TunableRange(description='\n        The number of days a Sim will be unable to enroll at a university\n        after dropping out.\n        ', tunable_type=int, default=5, minimum=1)
    GPA_PROBATION_THRESHOLD = TunableRange(description='\n        The minimum term GPA that Sims must maintain each term.  If they drop\n        below this threshold, they will be placed on probation, or be \n        suspended if they were already on probation.\n        ', tunable_type=float, default=2.0, minimum=0.0)
    COURSE_GRADE_FAIL_THRESHOLD = TunableRange(description='\n        The minimum course grade Sims need to earn in order to pass a course.\n        If they drop below this threshold, the Sim is considered to have \n        failed the course and will need to re-take it until the earn a passing\n        grade.\n        ', tunable_type=float, default=1.0, minimum=0.0)
    GRADUATION_DRAMA_NODE_MAP = TunableMapping(description='\n        The mapping of each University and the associated situation drama node\n        that schedules the graduation situation. \n        ', key_type=TunableReference(description='\n            A reference to a University for the graduation situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY), pack_safe=True), value_type=TunableReference(description='\n            The graduation situation drama node that will be scheduled.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), pack_safe=True))
    POST_GRADUATION_REWARDS = TunableTuple(description='\n        A tuple of the loots that will be awarded after graduation.\n        ', diploma_loot=LootActions.TunableReference(description='\n            The diploma loot action applied to selectable sims. This loot will\n            also be applied when a graduated sim is added to the skewer. \n            ', pack_safe=True), portrait_loot=LootActions.TunableReference(description='\n            The portrait loot action applied.\n            ', pack_safe=True), diploma_notification=UiDialogNotification.TunableFactory(description='\n            The notification to display when a selectable Sim receives their \n            diploma.\n            '))
    DIPLOMA_MAIL_DELAY = TunableRange(description='\n        The number of days after the graduating (once Sim has completed all \n        degree requirements) when the diploma should be mailed to the Sim.\n        ', tunable_type=int, default=3, minimum=0)

    @staticmethod
    def _populate_gpa_thresholds(*args):
        GPA_THRESHOLDS.clear()
        sorted_grades = []
        if not DegreeTracker.GRADE_INFO:
            logger.error('NO Grade Infos specified in degree tracker')
            return
        for entry in DegreeTracker.GRADE_INFO.values():
            sorted_grades.append((entry.gp_value, entry.text))
        sorted_grades.sort(key=lambda x: x[0], reverse=True)
        length_minus_one = len(sorted_grades) - 1
        for i in range(length_minus_one):
            GPA_THRESHOLDS.append(((sorted_grades[i][0] + sorted_grades[i + 1][0])/2, sorted_grades[i][1]))
        GPA_THRESHOLDS.append((0, sorted_grades[length_minus_one][1]))

    GRADE_INFO = TunableMapping(description='\n        Mapping of grade to info about that grade.\n        ', key_type=TunableEnumEntry(tunable_type=Grade, default=Grade.UNKNOWN, invalid_enums=(Grade.UNKNOWN,)), value_type=TunableTuple(range=TunableInterval(description='\n                Performance range to receive this grade.\n                Lower bound is inclusive, upper bound is exclusive.\n                ', tunable_type=float, default_lower=0, default_upper=101), gp_value=TunableRange(description='\n                GP for this grade.\n                ', tunable_type=float, default=2.0, minimum=0), text=TunableLocalizedStringFactory(description='\n                Text for this grade.\n                ')), callback=_populate_gpa_thresholds)
    GRADE_REPORT_MAPPING = TunableMapping(description='\n        The mapping of all the possible in-progress grade report strings.\n        ', key_type=TunableRange(description='\n            The current day of the term.\n            ', tunable_type=int, default=1, minimum=1), value_type=TunableList(description='\n            A list of grade performance tuples, each containing the performance \n            interval and the associated report strings that will be shown to the \n            user.\n            ', tunable=TunableTuple(description='\n                A tuple of the course performance stat range, the report text,\n                and a map of any additional text that should be appended to \n                the end of the report text.\n                ', performance_range=TunableInterval(description='\n                    The grade performance range for this grade report text.\n                    ', tunable_type=int, default_lower=0, default_upper=100), report_text=TunableLocalizedStringFactory(description='\n                    The grade report text for this specific day of term and grade\n                    progress.\n                    '), final_requirement_text_map=TunableMapping(description='\n                    A mapping of the FinalCourseRequirement enums and the \n                    associated additional text that should be appended to the\n                    report_text.  If this map is empty or if a specific enum is\n                    not defined here, then no further text will be added.\n                    ', key_type=TunableEnumEntry(description='\n                        The FinalCourseRequirement enum.\n                        ', tunable_type=FinalCourseRequirement, default=FinalCourseRequirement.NONE), value_type=TunableLocalizedStringFactory(description='\n                        The additional text for this specific final course\n                        requirements.\n                        ')))))
    GRADE_SKILL_MODIFICATION = TunableCurve(description='\n        A mapping of skill delta to the amount that grade progress will be\n        modified\n        ', x_axis_name='Skill Delta', y_axis_name='Grade modification')
    GRADE_SKILL_MAX_MODIFICATION = TunableRange(description='\n        A boost to grade progress that will be earned if sim has maxed the\n        respective skill.\n        ', tunable_type=int, default=5, minimum=1)
    COURSE_GRADE_REPORT_NOTIFICATION = UiDialogNotification.TunableFactory(description="\n        The notification to display for the Sim's current grade report for \n        a specific course.\n        ")
    NO_GPA_TEXT = TunableLocalizedStringFactory(description="\n        The text that should be displayed if the Sim does not yet have a GPA,\n        because they haven't completed any courses or just switched majors.\n        ")
    TERM_NOT_STARTED_TEXT = TunableLocalizedStringFactory(description='\n        The text that should be displayed for the number of days remaining in \n        a term if the university term has not yet started.\n        ')
    LAST_DAY_TERM_TEXT = TunableLocalizedStringFactory(description='\n        The text that should be displayed for the number of days remaining in\n        a term if today is the last day of the term.\n        ')
    GRADUATED_TERM_TEXT = TunableLocalizedStringFactory(description='\n        The text that should be displayed for the number of days remaining in\n        a term if the Sim has already graduated.\n        ')
    DEGREE_INFO_TEXT = TunableLocalizedStringFactory(description="\n        The text for displaying the Sim's degree information for the Career\n        Panel UI.\n        Major: {0.String}\n        GPA: (1.String}\n        Credit count: {2.Number}\n        Credits needed: {3.Number}\n        ")
    DEGREE_INFO_TOOLTIP_TEXT = TunableLocalizedStringFactory(description="\n        The text for displaying the Sim's degree information for the Career\n        Panel Button Tooltip.\n        ")
    TERM_START_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification to display once a Sim has successfully enrolled in \n        courses for the next term.\n        ')
    TERM_END_DIALOGS = TunableTestedList(description='\n        A list of Dialogs that could appear at the end of the term.\n        ', tunable_type=UiDialogInfoInColumns.TunableFactory(description="\n            The dialog with an info table and an ok button that we will display to \n            the user when a term ends if the sim didn't graduate.\n            \n            Additional text arguments are:\n            Term GPA\n            Enrollment Status\n            "))
    REENROLLMENT_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        The dialog with ok/cancel buttons that will display, asking the user\n        if they want to enroll in classes for the next term.\n        ')
    SUSPENSION_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification to display that the Sim is now suspended and cannot\n        enroll in university courses for some time.\n        ')
    SUSPENSION_END_NOTIFICATION = UiDialogNotification.TunableFactory(description="\n        The notification to display once a Sim's suspension ends and they can\n        enroll in courses again.\n        ")
    PROBATION_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification to display at the start of a term if the sim is on \n        probation.\n        ')
    PROBATION_TEXT = TunableLocalizedStringFactory(description='\n        The text that should be displayed on the end of term dialog\n        if the sim is in probation.\n        ')
    SUSPENSION_TEXT = TunableLocalizedStringFactory(description='\n        The text that should be displayed on the end of term dialog\n        if the sim is suspended.\n        ')
    DROPOUT_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        The dialog with ok/cancel buttons that will display, asking the user\n        if they want to confirm dropping out of their major and university.\n        ')
    DROPOUT_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification to display after a player confirms their Sim dropping\n        out of university.\n        ')
    DROPOUT_COOLDOWN_NOTIFICATION = UiDialogNotification.TunableFactory(description="\n        The notification to display once a Sim's dropout cooldown ends and \n        they can enroll in courses again.\n        ")
    WITHDRAW_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification to display once a Sim has withdrawn from their current\n        term.\n        ')
    GRADUATION_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification to display after graduation has been scheduled.\n        ')
    ENROLLMENT_BENEFITS = TunableList(description='\n        Benefits to give on enrollment to sims who pass a test set.\n        ', tunable=TunableTuple(test=TunableTestSet(description='\n                Test to see if sim is eligible for benefits.\n                '), benefits=TunableTuple(starting_credits=TunableRange(description='\n                    The number of starting credits to give the sim.\n                    ', tunable_type=int, minimum=0, default=0))))
    KNOWLEDGE_NOTIFICATION = TunableUiDialogNotificationSnippet(description="\n        The notification to use when a Sim learns about another Sim's \n        university major.  This should use 2 additional tokens: major name and \n        university name.\n        ")
    ENROLLMENT_STATUS_LOOT_MAP = TunableMapping(description='\n        Mapping of degree enrollment status to loot actions.  Loot will be\n        applied when changing to mapped enrollment status.\n        ', key_type=TunableEnumEntry(tunable_type=EnrollmentStatus, default=EnrollmentStatus.NONE, invalid_enums=(EnrollmentStatus.NONE,)), value_type=TunableList(description='\n            A list of loot actions to apply after changing to the mapped enrollment status.\n            ', tunable=LootActions.TunableReference(pack_safe=True)))
    WITHDRAW_COOLDOWN_BUFF = TunablePackSafeReference(description='\n        The buff applied when withdrawing from university, controls when you are able to re-enroll in university.\n        ', manager=services.get_instance_manager(Types.BUFF))
    IS_REENROLLMENT_DIALOGS_IN_PROCESS = False

    class CourseInfo:

        def __init__(self, course_data, final_grade=Grade.UNKNOWN, known_grade=Grade.UNKNOWN, lectures=0, final_completed=False, homework_cheated=HomeworkCheatingStatus.NONE, initial_skill=0):
            self.course_data = course_data
            self.final_grade = final_grade
            self.known_grade = known_grade
            self.lectures = lectures
            self.final_requirement_completed = final_completed
            self.homework_cheated = homework_cheated
            self.initial_skill = initial_skill

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._course_infos = {}
        self._current_university = None
        self._current_major = None
        self._enrollment_status = EnrollmentStatus.NONE
        self._current_credits = 0
        self._total_gp = 0.0
        self._total_courses = 0
        self._previous_majors = []
        self._previous_courses = []
        self._accepted_degrees = None
        self._elective_courses_map = None
        self._elective_timestamp = None
        self._term_started_time = None
        self._start_of_term_handle = None
        self._end_of_term_handle = None
        self._reenrollment_handle = None
        self._diploma_handle = None
        self._daily_update_handle = None
        self.kickout_destination_zone = 0
        self.kickout_reason = UniversityHousingKickOutReason.NONE
        self.is_immune_to_kickout = False
        self._active_scholarships = []
        self._accepted_scholarships = []
        self._rejected_scholarships = []
        self._pending_scholarship_alarm_handles = {}
        self._show_reenrollment_dialog_on_spin_up = False
        self._show_reenrollment_dialog_on_next_turn = False

    @classproperty
    def required_packs(cls):
        return (Pack.EP08,)

    def save(self):
        data = SimObjectAttributes_pb2.PersistableDegreeTracker()
        data.current_major = self._current_major.guid64 if self._current_major else 0
        data.current_university = self._current_university.guid64 if self._current_university else 0
        data.current_credits = self._current_credits
        data.total_gradepoints = self._total_gp
        data.total_courses = self._total_courses
        data.previous_majors.extend(self._previous_majors)
        data.previous_courses.extend(self._previous_courses)
        data.enrollment_status = self._enrollment_status
        if self._accepted_degrees is not None:
            for (university_guid, accepted_degrees) in self._accepted_degrees.items():
                with ProtocolBufferRollback(data.accepted_degrees) as entry:
                    entry.university_id = university_guid
                    entry.degree_ids.extend(accepted_degrees)
        if self._elective_timestamp is not None:
            data.elective_timestamp = self._elective_timestamp
            for (university_guid, elective_guids) in self._elective_courses_map.items():
                with ProtocolBufferRollback(data.elective_courses) as entry:
                    entry.university_id = university_guid
                    entry.elective_ids.extend(elective_guids)
        for (slot_guid, course_info) in self._course_infos.items():
            with ProtocolBufferRollback(data.current_courses) as entry:
                entry.course_slot = slot_guid
                entry.course_data = course_info.course_data.guid64
                entry.final_grade = course_info.final_grade
                entry.known_grade = course_info.known_grade
                entry.lectures = course_info.lectures
                entry.final_requirement_completed = course_info.final_requirement_completed
                entry.homework_cheated = course_info.homework_cheated
                entry.initial_skill = course_info.initial_skill
        show_on_spin_up = self._show_reenrollment_dialog_on_spin_up or self._show_reenrollment_dialog_on_next_turn
        data.show_reenrollment_dialog_on_spin_up = show_on_spin_up
        if self._end_of_term_handle is not None:
            data.end_of_term_time = self._end_of_term_handle.get_remaining_time().in_ticks()
        if self._reenrollment_handle is not None:
            data.reenrollment_time = self._reenrollment_handle.get_remaining_time().in_ticks()
        if self._start_of_term_handle is not None:
            data.start_term_alarm_time = self._start_of_term_handle.get_remaining_time().in_ticks()
        if self._term_started_time is not None:
            data.term_started_time = self._term_started_time.absolute_ticks()
        if self._diploma_handle is not None:
            data.diploma_mail_time = self._diploma_handle.get_remaining_time().in_ticks()
        data.active_scholarships.extend(self._active_scholarships)
        data.accepted_scholarships.extend(self._accepted_scholarships)
        data.rejected_scholarships.extend(self._rejected_scholarships)
        for (scholarship_id, scholarship_evaluation_alarm_handle) in self._pending_scholarship_alarm_handles.items():
            with ProtocolBufferRollback(data.pending_scholarships) as entry:
                entry.remaining_evaluation_time = scholarship_evaluation_alarm_handle.get_remaining_time().in_ticks()
                entry.scholarship_id = scholarship_id
        data.kickout_destination_zone = self.kickout_destination_zone
        data.kickout_reason = self.kickout_reason
        return data

    def load(self, data):
        major_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY_MAJOR)
        university_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY)
        self._current_major = major_manager.get(data.current_major)
        self._current_university = university_manager.get(data.current_university)
        self._current_credits = data.current_credits
        self._total_gp = data.total_gradepoints
        self._total_courses = data.total_courses
        self._previous_majors.extend(data.previous_majors)
        self._previous_courses.extend(data.previous_courses)
        self._enrollment_status = EnrollmentStatus(data.enrollment_status)
        course_data_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY_COURSE_DATA)
        for accepted_degree in data.accepted_degrees:
            university_guid = accepted_degree.university_id
            if university_manager.get(university_guid) is None:
                pass
            else:
                if self._accepted_degrees is None:
                    self._accepted_degrees = defaultdict(list)
                self._accepted_degrees[university_guid] = [i for i in accepted_degree.degree_ids if major_manager.get(i) is not None]
        if data.HasField('elective_timestamp'):
            for elective_course in data.elective_courses:
                university_guid = elective_course.university_id
                if university_manager.get(university_guid) is None:
                    pass
                else:
                    if self._elective_courses_map is None:
                        self._elective_courses_map = defaultdict(list)
                    self._elective_courses_map[university_guid] = [i for i in elective_course.elective_ids if course_data_manager.get(i) is not None]
            if self._elective_courses_map:
                self._elective_timestamp = data.elective_timestamp
        for course_info in data.current_courses:
            course_data = course_data_manager.get(course_info.course_data)
            self._course_infos[course_info.course_slot] = DegreeTracker.CourseInfo(course_data, final_grade=Grade(course_info.final_grade), known_grade=Grade(course_info.known_grade), lectures=course_info.lectures, final_completed=course_info.final_requirement_completed, homework_cheated=course_info.homework_cheated, initial_skill=course_info.initial_skill)
            if data.HasField('term_started_time') and self._sim_info.career_tracker is not None and course_info.course_slot is not None:
                career = self._sim_info.career_tracker.get_career_by_uid(course_info.course_slot)
                if career is not None:
                    career.career_start()
        self._show_reenrollment_dialog_on_spin_up = data.show_reenrollment_dialog_on_spin_up
        require_daily_update_alarm = False
        if data.HasField('end_of_term_time'):
            self._setup_end_of_term_alarm(time_till_end_term=TimeSpan(data.end_of_term_time))
            require_daily_update_alarm = True
        if data.HasField('reenrollment_time'):
            self._setup_reenrollment_alarm(time_till_reenrollment=TimeSpan(data.reenrollment_time))
        if data.HasField('start_term_alarm_time'):
            self._setup_start_of_term_alarm(time_till_start_term=TimeSpan(data.start_term_alarm_time))
            require_daily_update_alarm = True
        if data.HasField('term_started_time'):
            self._term_started_time = DateAndTime(data.term_started_time)
        if data.HasField('diploma_mail_time'):
            self._setup_mail_diploma_alarm(time_till_mail_diploma=TimeSpan(data.diploma_mail_time))
        if require_daily_update_alarm:
            self._setup_daily_update_alarm()
        scholarship_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for scholarship_id in data.active_scholarships:
            if scholarship_manager.get(scholarship_id) is None:
                pass
            else:
                self._active_scholarships.append(scholarship_id)
        for scholarship_id in data.accepted_scholarships:
            if scholarship_manager.get(scholarship_id) is None:
                pass
            else:
                self._accepted_scholarships.append(scholarship_id)
        for scholarship_id in data.rejected_scholarships:
            if scholarship_manager.get(scholarship_id) is None:
                pass
            else:
                self._rejected_scholarships.append(scholarship_id)
        for scholarship_info in data.pending_scholarships:
            scholarship_guid = scholarship_info.scholarship_id
            scholarship = scholarship_manager.get(scholarship_guid)
            if scholarship is None:
                pass
            else:
                self.process_scholarship_application(scholarship, TimeSpan(scholarship_info.remaining_evaluation_time))
        self.kickout_destination_zone = data.kickout_destination_zone
        if data.HasField('kickout_reason'):
            self.kickout_reason = UniversityHousingKickOutReason(data.kickout_reason)

    def on_sim_added_to_skewer(self):
        if self._previous_majors and self._diploma_handle is None:
            resolver = SingleSimResolver(self._sim_info)
            self.POST_GRADUATION_REWARDS.diploma_loot.apply_to_resolver(resolver)

    def on_cancel_enrollment_dialog(self):
        self.finish_reenrollment_dialog_flow()

    def on_enroll_in_same_housing(self):
        self.finish_reenrollment_dialog_flow()

    def finish_reenrollment_dialog_flow(self):
        self.is_immune_to_kickout = False
        DegreeTracker.IS_REENROLLMENT_DIALOGS_IN_PROCESS = False
        self._sim_info.household.handle_delayed_reenrollment_dialog()

    def show_delayed_reenrollment_dialog(self):
        if DegreeTracker.IS_REENROLLMENT_DIALOGS_IN_PROCESS:
            return False
        if self._show_reenrollment_dialog_on_spin_up or not self._show_reenrollment_dialog_on_next_turn:
            return False
        self._show_reenrollment_dialog_on_spin_up = False
        self._show_reenrollment_dialog_on_next_turn = False
        self._show_reenrollment_dialog()
        return True

    def set_kickout_info(self, kickout_destination_zone, kickout_reason):
        self.kickout_destination_zone = kickout_destination_zone
        self.kickout_reason = kickout_reason

    def clear_kickout_info(self):
        self.kickout_destination_zone = 0
        self.kickout_reason = UniversityHousingKickOutReason.NONE

    def update_homework_cheating_status(self, course_slot, cheating_status):
        course_info = self.course_infos.get(course_slot.guid64)
        if course_info is None:
            logger.error("Attempting to update sim {}'s homework cheating status for course career slot {} but there is no associated course info.", self._sim_info, course_slot)
            return
        course_info.homework_cheated = cheating_status

    @property
    def previous_majors(self):
        return self._previous_majors

    @property
    def accepted_degrees(self):
        return self._accepted_degrees

    @property
    def course_infos(self):
        return self._course_infos

    def get_courses(self):
        return [course_info.course_data for course_info in self._course_infos.values()]

    def show_knowledge_notification(self, sim_info, resolver):
        notification = self.KNOWLEDGE_NOTIFICATION(sim_info, resolver=resolver)
        notification.show_dialog(additional_tokens=(self._current_major.display_name, self._current_university.display_name))

    def remove_sim_knowlege(self):
        tracker = self._sim_info.relationship_tracker
        for target in tracker.get_target_sim_infos():
            if target is None:
                logger.error('\n                    SimInfo {} has a relationship with a None target. The target\n                    has probably been pruned and the data is out of sync. Please\n                    provide a save and GSI dump and file a DT for this.\n                    ', self._sim_info)
            else:
                target.relationship_tracker.remove_knows_major(self._sim_info.id)

    def get_career_course_slots(self):
        active_course_slots = []
        careers = self._sim_info.career_tracker.careers
        if careers:
            for course_info in self._course_infos.keys():
                if course_info in careers:
                    active_course_slots.append(careers[course_info])
        elif self._course_infos:
            logger.error('Careers is none, but course info is present for Sim: {}', self._sim_info, owner='amohananey')
        return active_course_slots

    def get_grade(self, performance):
        for (grade, grade_info) in self.GRADE_INFO.items():
            if grade_info.range.lower_bound <= performance and performance < grade_info.range.upper_bound:
                return grade
        logger.error('Failed to find grade for performance value{}', performance)
        return Grade.UNKNOWN

    @property
    def previous_courses(self):
        return self._previous_courses

    @property
    def current_credits(self):
        return self._current_credits

    def is_core_course(self, course):
        if self._current_major is None:
            return False
        return any(course is core_course for core_course in self._current_major.courses)

    @property
    def term_started_time(self):
        return self._term_started_time

    def update_final_requirement_completion(self, career, completion_status):
        course_info = self._course_infos[career.guid64]
        if course_info is None:
            logger.error('Failed to find course data when attempting to             update the final requirement for corresponding course career slot {} for sim {}', career, self._sim_info)
            return
        course_info.final_requirement_completed = completion_status
        if course_info.lectures >= self.COURSE_LECTURE_COUNT and course_info.final_requirement_completed:
            self.complete_course(career.guid64, self.get_grade_performance(career.guid64))

    def finish_lecture(self, career_guid):
        sim_info = self._sim_info
        if not sim_info.is_selectable:
            return
        if career_guid in self._course_infos.keys():
            course_info = self._course_infos[career_guid]
            course_info.lectures += 1
            self.handle_professor_assignment(course_info)
            if course_info.lectures >= self.COURSE_LECTURE_COUNT and course_info.final_requirement_completed and course_info.final_grade == Grade.UNKNOWN:
                self.complete_course(career_guid, self.get_grade_performance(career_guid))

    def handle_professor_assignment(self, course_info):
        university = self.get_university()
        if university is None:
            return
        professor_assignment_trait = course_info.course_data.professor_assignment_trait.get(university, None)
        if professor_assignment_trait is None:
            return
        professor_filter_term = TraitFilterTerm(invert_score=False, minimum_filter_score=0, trait=professor_assignment_trait, ignore_if_wrong_pack=False)
        dynamic_professor_filter = DynamicSimFilter((professor_filter_term,))
        result = services.sim_filter_service().submit_filter(sim_filter=dynamic_professor_filter, allow_yielding=False, callback=None, gsi_source_fn=lambda : 'DegreeTracker: Check if professor is assigned to {} '.format(str(course_info)))
        if not result:
            result = self.assign_professor_to_course(course_info, professor_assignment_trait)
            if not result:
                return
        professor = result[0]
        if not self._sim_info.relationship_tracker.has_relationship(professor.sim_info.id):
            self._sim_info.relationship_tracker.create_relationship(professor.sim_info.id)
            self._sim_info.relationship_tracker.add_relationship_score(professor.sim_info.id, DegreeTracker.STARTING_PROFESSOR_REL_GAIN)
            self._sim_info.relationship_tracker.add_relationship_bit(professor.sim_info.id, RelationshipGlobalTuning.HAS_MET_RELATIONSHIP_BIT)
        self._sim_info.relationship_tracker.add_relationship_bit(professor.sim_info.id, DegreeTracker.PROFESSOR_REL_BIT)

    def complete_course(self, career_guid, performance_value):
        course_info = self._course_infos[career_guid]
        course_info.final_grade = self.get_grade(performance_value)
        career = self._sim_info.career_tracker.get_career_by_uid(career_guid)
        if career is not None:
            career.complete_course()
        UniversityTelemetry.send_university_course_telemetry(self._sim_info, self._current_major, course_info.course_data, performance_value)

    def _on_end_term_dialog_response(self, dialog):
        if self._enrollment_status == EnrollmentStatus.GRADUATED:
            self.is_immune_to_kickout = False
            self.graduate()
        elif self._enrollment_status == EnrollmentStatus.SUSPENDED:
            self.is_immune_to_kickout = False
            self.suspend()
        else:
            self._show_reenrollment_dialog_on_next_turn = True
            self._sim_info.household.handle_delayed_reenrollment_dialog()

    def _show_reenrollment_dialog(self):
        sim_info = self._sim_info
        resolver = SingleSimResolver(sim_info)
        DegreeTracker.IS_REENROLLMENT_DIALOGS_IN_PROCESS = True
        reenrollment_dialog = self.REENROLLMENT_DIALOG(sim_info, resolver=resolver)
        reenrollment_dialog.show_dialog(additional_tokens=(self._current_university.display_name,), on_response=self._on_reenrollment_dialog_response)

    def _on_reenrollment_dialog_response(self, dialog):
        if dialog.accepted:
            self.generate_enrollment_information(is_reenrollment=True)
        else:
            self.clear_scholarships()
            self.finish_reenrollment_dialog_flow()

    def complete_term(self):
        sim_info = self._sim_info
        resolver = SingleSimResolver(sim_info)
        grade_entries = []
        term_grade_point = 0
        for (career_guid, course_info) in self._course_infos.items():
            if course_info.final_grade == Grade.UNKNOWN:
                performance = self.get_grade_performance(career_guid)
                course_info.final_grade = self.get_grade(performance)
                UniversityTelemetry.send_university_course_telemetry(self._sim_info, self._current_major, course_info.course_data, performance)
            self._total_courses += 1
            grade_value = self.GRADE_INFO[course_info.final_grade].gp_value
            self._total_gp += grade_value
            term_grade_point += grade_value
            course_data = course_info.course_data
            course_icon_info = (course_data.icon, self.get_course_name(course_data), self.get_course_description(course_data))
            course_grade_info = (course_data.icon, self.GRADE_INFO[course_info.final_grade].text(sim_info), self.get_course_description(course_data))
            row = [course_icon_info, course_grade_info]
            grade_entries.append(row)
            if grade_value >= self.COURSE_GRADE_FAIL_THRESHOLD:
                self._previous_courses.append(course_data.guid64)
                self._current_credits += 1
        num_courses = len(self._course_infos)
        term_gpa = 0.0
        if num_courses > 0:
            term_gpa = round(term_grade_point/num_courses, 2)
        if self._current_credits >= self.CREDITS_REQUIRED:
            self._set_enrollment_status(EnrollmentStatus.GRADUATED)
        elif term_gpa < self.GPA_PROBATION_THRESHOLD:
            if self._enrollment_status == EnrollmentStatus.PROBATION:
                self._set_enrollment_status(EnrollmentStatus.SUSPENDED)
            else:
                self._set_enrollment_status(EnrollmentStatus.PROBATION)
        else:
            self._set_enrollment_status(EnrollmentStatus.NOT_ENROLLED, from_complete_term=True)
        self._reset_term_alarm()
        self.drop_enrolled_courses()
        UniversityTelemetry.send_university_term_telemetry(self._sim_info, self._current_major, term_gpa)
        if self._sim_info.is_selectable:
            overall_gpa = self.get_gpa()
            enrollment_status_text = ''
            if self._enrollment_status == EnrollmentStatus.SUSPENDED:
                enrollment_status_text = self.SUSPENSION_TEXT()
            if self._enrollment_status == EnrollmentStatus.PROBATION:
                enrollment_status_text = self.PROBATION_TEXT()
            for term_end_dialog in self.TERM_END_DIALOGS(resolver=resolver):
                self.is_immune_to_kickout = True
                end_term_dialog = term_end_dialog(sim_info, resolver=resolver)
                end_term_dialog.show_dialog(row_data=grade_entries, additional_tokens=(self.get_gpa_string(term_gpa), self.get_gpa_string(overall_gpa), enrollment_status_text), on_response=self._on_end_term_dialog_response)
            self._sim_info.career_tracker.resend_career_data()
            self._sim_info.career_tracker.resend_at_work_infos()
        elif self._enrollment_status == EnrollmentStatus.GRADUATED:
            self.graduate()
        elif self._enrollment_status == EnrollmentStatus.NOT_ENROLLED:
            self._show_reenrollment_dialog_on_spin_up = True

    def _setup_mail_diploma_alarm(self, time_till_mail_diploma=None):
        if self._diploma_handle is not None:
            alarms.cancel_alarm(self._diploma_handle)
            self._diploma_handle = None
        if time_till_mail_diploma is None:
            time_till_mail_diploma = date_and_time.create_time_span(days=self.DIPLOMA_MAIL_DELAY)
        self._diploma_handle = alarms.add_alarm(self, time_till_mail_diploma, self._diploma_callback, cross_zone=True)

    def _remove_organization_membership(self):
        organization_tracker = self._sim_info.organization_tracker
        if organization_tracker is not None and self._current_university is not None:
            organization_tracker.deactivate_organizations(self._current_university)

    def _activate_organization_membership(self):
        organization_tracker = self._sim_info.organization_tracker
        if organization_tracker is not None and self._current_university is not None:
            organization_tracker.reactivate_organizations(self._current_university)

    def _suspension_pre_actions(self):
        self.drop_enrolled_courses()
        self._remove_organization_membership()

    def _unenrollment_pre_actions(self, from_complete_term=False):
        if not from_complete_term:
            self._remove_organization_membership()

    def _diploma_callback(self, _):
        self._set_enrollment_status(EnrollmentStatus.NONE)
        self._remove_degree_info_slot()
        if self._sim_info.is_selectable:
            resolver = SingleSimResolver(self._sim_info)
            self.POST_GRADUATION_REWARDS.diploma_loot.apply_to_resolver(resolver)
            diploma_dialog = self.POST_GRADUATION_REWARDS.diploma_notification(self._sim_info, resolver)
            diploma_dialog.show_dialog()
        self._current_major = None
        self._current_university = None
        self._current_credits = 0
        self._total_gp = 0
        self._total_courses = 0
        if self._diploma_handle is not None:
            alarms.cancel_alarm(self._diploma_handle)
            self._diploma_handle = None

    def graduate(self, gpa=None):
        self._previous_majors.append(self._current_major.guid64)
        self._set_enrollment_status(EnrollmentStatus.GRADUATED)
        if gpa is None:
            gpa = self.get_gpa()
        self._current_major.graduate(self._sim_info, self._current_university, gpa)
        self.clear_scholarships()
        self._setup_mail_diploma_alarm()
        if not self._sim_info.is_selectable:
            return
        uid = id_generator.generate_object_id()
        drama_node = self.GRADUATION_DRAMA_NODE_MAP[self._current_university]
        if drama_node is None:
            logger.error('No graduation drama node found for {}', self._current_university)
        drama_node_inst = drama_node(uid)
        resolver = SingleSimResolver(self._sim_info)
        services.drama_scheduler_service().schedule_node(drama_node, resolver, drama_inst=drama_node_inst)
        graduation_notification_dialog = self.GRADUATION_NOTIFICATION(self._sim_info, SingleSimResolver(self._sim_info))
        graduation_notification_dialog.show_dialog(additional_tokens=(self._current_university.display_name,))

    def drop_enrolled_courses(self):
        for career_guid in self._course_infos.keys():
            self._sim_info.career_tracker.remove_career(career_guid, post_quit_msg=False)
        self._course_infos.clear()

    def _setup_reenrollment_alarm(self, duration_in_days=None, time_till_reenrollment=None):
        if self._reenrollment_handle is not None:
            alarms.cancel_alarm(self._reenrollment_handle)
            self._reenrollment_handle = None
        if duration_in_days is not None:
            time_till_reenrollment = date_and_time.create_time_span(days=duration_in_days)
        self._reenrollment_handle = alarms.add_alarm(self, time_till_reenrollment, self._reenrollment_callback, cross_zone=True)

    def withdraw(self):
        self.drop_enrolled_courses()
        self._set_enrollment_status(EnrollmentStatus.NOT_ENROLLED)
        withdraw_notification_dialog = self.WITHDRAW_NOTIFICATION(self._sim_info, SingleSimResolver(self._sim_info))
        withdraw_notification_dialog.show_dialog(additional_tokens=(self._current_university.display_name,))
        self._reset_term_alarm()

    def _on_dropout_dialog_response(self, dialog):
        if dialog.accepted:
            self.dropout()

    def dropout(self):
        self._remove_degree_info_slot()
        self._set_enrollment_status(EnrollmentStatus.DROPOUT)
        university_name = self._current_university.display_name
        self.drop_enrolled_courses()
        self._previous_courses.clear()
        self._current_university = None
        self._current_major = None
        self._current_credits = 0
        self._total_gp = 0.0
        self._total_courses = 0
        self.remove_sim_knowlege()
        self._setup_reenrollment_alarm(duration_in_days=self.DROPOUT_DURATION)
        self._reset_term_alarm()
        dropout_notification_dialog = self.DROPOUT_NOTIFICATION(self._sim_info, SingleSimResolver(self._sim_info))
        dropout_notification_dialog.show_dialog(additional_tokens=(university_name, self.DROPOUT_DURATION))
        self.clear_scholarships()

    def show_dropout_dialog(self):
        dialog = self.DROPOUT_DIALOG(self._sim_info, SingleSimResolver(self._sim_info))
        dialog.show_dialog(on_response=self._on_dropout_dialog_response, additional_tokens=(self.DROPOUT_DURATION,))

    def suspend(self):
        self._set_enrollment_status(EnrollmentStatus.SUSPENDED)
        self._setup_reenrollment_alarm(duration_in_days=self.SUSPENSION_DURATION)
        suspension_notification_dialog = self.SUSPENSION_NOTIFICATION(self._sim_info, SingleSimResolver(self._sim_info))
        suspension_duration = int(round(self._reenrollment_handle.get_remaining_time().in_days()))
        suspension_notification_dialog.show_dialog(additional_tokens=(suspension_duration,))
        self._sim_info.career_tracker.resend_career_data()
        self._reset_term_alarm()
        self.clear_scholarships()

    def _reenrollment_callback(self, _):
        sim_info = self._sim_info
        resolver = SingleSimResolver(sim_info)
        if self._enrollment_status == EnrollmentStatus.SUSPENDED:
            suspension_end_dialog = self.SUSPENSION_END_NOTIFICATION(sim_info, resolver=resolver)
            suspension_end_dialog.show_dialog()
            self.set_enrollment_status(EnrollmentStatus.NOT_ENROLLED)
        elif self._enrollment_status == EnrollmentStatus.DROPOUT:
            probation_end_dialog = self.DROPOUT_COOLDOWN_NOTIFICATION(sim_info, resolver=resolver)
            probation_end_dialog.show_dialog()
            self.set_enrollment_status(EnrollmentStatus.NONE)
        if self._reenrollment_handle is not None:
            alarms.cancel_alarm(self._reenrollment_handle)
            self._reenrollment_handle = None

    def set_enrollment_status(self, enrollment_status, show_confirmation_dialog=False):
        if enrollment_status == EnrollmentStatus.SUSPENDED:
            self.suspend()
        elif enrollment_status == EnrollmentStatus.DROPOUT:
            if show_confirmation_dialog:
                self.show_dropout_dialog()
            else:
                self.dropout()
        elif enrollment_status == EnrollmentStatus.GRADUATED:
            self.graduate()
        else:
            self._set_enrollment_status(enrollment_status)
        caches.clear_all_caches()
        self._sim_info.career_tracker.resend_career_data()
        self._sim_info.career_tracker.resend_at_work_infos()

    def _set_enrollment_status(self, enrollment_status, from_complete_term=False):
        self._apply_enrollment_status_loot(enrollment_status)
        if enrollment_status == EnrollmentStatus.SUSPENDED:
            self._suspension_pre_actions()
        elif enrollment_status == EnrollmentStatus.NONE or enrollment_status == EnrollmentStatus.DROPOUT or enrollment_status == EnrollmentStatus.NOT_ENROLLED:
            self._unenrollment_pre_actions(from_complete_term=from_complete_term)
        elif enrollment_status == EnrollmentStatus.GRADUATED:
            self.set_kickout_info(0, UniversityHousingKickOutReason.GRADUATED)
        self._enrollment_status = enrollment_status

    def _apply_enrollment_status_loot(self, enrollment_status):
        if enrollment_status in self.ENROLLMENT_STATUS_LOOT_MAP:
            resolver = SingleSimResolver(self._sim_info)
            loot_list = self.ENROLLMENT_STATUS_LOOT_MAP[enrollment_status]
            for loot in loot_list:
                loot.apply_to_resolver(resolver)

    def is_current_student(self):
        is_current_student = self.get_enrollment_status() != EnrollmentStatus.NONE and (self.get_enrollment_status() != EnrollmentStatus.DROPOUT and self.get_enrollment_status() != EnrollmentStatus.GRADUATED)
        return is_current_student

    def get_enrollment_status(self):
        return self._enrollment_status

    def get_enrolled_major(self):
        if self._enrollment_status == EnrollmentStatus.ENROLLED or self._enrollment_status == EnrollmentStatus.PROBATION:
            return self._current_major

    def get_university(self):
        return self._current_university

    def get_major(self):
        return self._current_major

    def get_course_data(self, career_guid):
        if career_guid not in self._course_infos:
            return
        return self._course_infos[career_guid].course_data

    def get_course_name(self, course_data):
        if course_data is not None:
            course_mapping = course_data.university_course_mapping
            if self._current_university is not None and course_mapping is not None and len(course_mapping) > 0:
                if course_mapping[self._current_university] is not None:
                    return course_mapping[self._current_university].course_name(self._sim_info)
                logger.error('University course mapping missing for UniversityCourseData {} and University {}', course_data, self._current_university)
        logger.error('University course data missing for UniversityCourseData {}', course_data)

    def get_course_description(self, course_data):
        if course_data is not None:
            course_mapping = course_data.university_course_mapping
            if self._current_university is not None and course_mapping is not None and len(course_mapping) > 0:
                if course_mapping[self._current_university] is not None:
                    return course_mapping[self._current_university].course_description
                logger.error('University course mapping missing for UniversityCourseData {} and University {}', course_data, self._current_university)
        logger.error('University course data missing for UniversityCourseData {}', course_data)

    def get_previous_courses(self):
        course_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY_COURSE_DATA)
        if course_manager is not None:
            return list(course_manager.get(guid) for guid in self._previous_courses)
        return []

    def get_known_grade(self, career_guid, update=True):
        if career_guid not in self._course_infos:
            logger.error("trying to find grade for a course slot {} we aren't taking", career_guid)
            return
        course_info = self._course_infos[career_guid]
        if not update:
            grade = course_info.known_grade
        else:
            career = self._sim_info.career_tracker.get_career_by_uid(career_guid)
            if career is None:
                grade = course_info.final_grade
                course_info.known_grade = grade
            else:
                performance = self.get_grade_performance(career_guid)
                grade = self.get_grade(performance)
                course_info.known_grade = grade
        if grade not in self.GRADE_INFO:
            return
        return self.GRADE_INFO[grade].text(self._sim_info)

    def get_gpa(self):
        if self._total_courses == 0:
            return
        return round(self._total_gp/self._total_courses, 2)

    def get_gpa_string(self, gpa):
        if gpa is None:
            return gpa
        for (threshold, text) in GPA_THRESHOLDS:
            if gpa >= threshold:
                return text(self._sim_info)
        logger.error('GPA: {} is outside GPA thresholds')

    def get_credits_carryover(self):
        return math.floor(self._current_credits*self.CREDIT_CARRYOVER_PERCENTAGE)

    def get_available_degrees_to_enroll(self):
        if self._accepted_degrees is None:
            return {}
        available_degrees = {}
        previous_major_ids = set(self._previous_majors)
        for (university_id, accepted_degree_ids) in self._accepted_degrees.items():
            available_degree_ids = set(accepted_degree_ids) - previous_major_ids
            if available_degree_ids:
                available_degrees[university_id] = available_degree_ids
        return available_degrees

    def get_accepted_prestige_degrees(self):
        if self._accepted_degrees is None:
            return {}
        university_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY)
        accepted_prestige_degrees = {}
        for (university_id, accepted_degree_ids) in self._accepted_degrees.items():
            university = university_manager.get(university_id)
            prestige_degree_ids = {d.guid64 for d in university.prestige_degrees}
            accepted_prestige_degrees[university_id] = set(accepted_degree_ids) & prestige_degree_ids
        return accepted_prestige_degrees

    def get_not_yet_accepted_degrees(self):
        not_yet_accepted_degrees = {}
        for university in University.ALL_UNIVERSITIES:
            university_id = university.guid64
            if self._accepted_degrees is None or university_id not in self._accepted_degrees:
                not_yet_accepted_degrees[university_id] = set(University.all_degree_ids)
            else:
                accepted_degree_ids = set(self._accepted_degrees[university_id])
                not_yet_accepted_degrees[university_id] = set(University.all_degree_ids) - accepted_degree_ids
        return not_yet_accepted_degrees

    def is_accepted_degree(self, university, degree):
        if self._accepted_degrees is None or university.guid64 not in self._accepted_degrees or degree.guid64 not in self._accepted_degrees[university.guid64]:
            return False
        return True

    def set_accepted_degree(self, university, degree):
        if self._accepted_degrees is None:
            self._accepted_degrees = defaultdict(list)
        self._accepted_degrees[university.guid64].append(degree.guid64)

    def process_acceptance(self, send_telemetry=True):
        if send_telemetry:
            UniversityTelemetry.send_acceptance_telemetry(self._sim_info.age)
        for university in University.ALL_UNIVERSITIES:
            for degree in University.ALL_DEGREES:
                if self.is_accepted_degree(university, degree):
                    pass
                elif degree in university.prestige_degrees:
                    if degree.can_sim_be_accepted(self._sim_info):
                        self.set_accepted_degree(university, degree)
                        self.set_accepted_degree(university, degree)
                else:
                    self.set_accepted_degree(university, degree)

    def switch_majors(self, new_major):
        if new_major is not None:
            self._current_major = new_major
            self._course_infos = {}
            self._total_gp = 0
            self._total_courses = 0
            self._previous_courses = []
            self._current_credits = self.get_credits_carryover()

    def _setup_start_of_term_alarm(self, time_till_start_term=None):
        if self._start_of_term_handle is not None:
            alarms.cancel_alarm(self._start_of_term_handle)
            self._start_of_term_handle = None
        if time_till_start_term is None:
            now = services.time_service().sim_now
            (time_till_start_term, alarm_data) = self.START_OF_TERM_SCHEDULE().time_until_next_scheduled_event(now)
            if time_till_start_term is None or not alarm_data:
                logger.error('Unable to find start term time for Sim {} based on current time {}', self._sim_info, str(now))
                return
            if now.day() == 0 or now.day() == alarm_data[0].start_time.day():
                time_till_start_term = time_till_start_term + date_and_time.create_time_span(days=1)
        self._start_of_term_handle = alarms.add_alarm(self, time_till_start_term, self._start_of_term_callback, cross_zone=True)

    def _start_of_term_callback(self, _):
        if self._start_of_term_handle is not None:
            alarms.cancel_alarm(self._start_of_term_handle)
            self._start_of_term_handle = None
        self._term_started_time = services.time_service().sim_now
        self._setup_end_of_term_alarm()
        for career_guid in self._course_infos.keys():
            course_slot = self._sim_info.career_tracker.get_career_by_uid(career_guid)
            course_slot.career_start()
        if self._sim_info.is_selectable:
            start_term_notification = self.TERM_START_NOTIFICATION(self._sim_info, resolver=SingleSimResolver(self._sim_info))
            start_term_notification.show_dialog()
        self._sim_info.career_tracker.resend_career_data()
        self._sim_info.career_tracker.resend_at_work_infos()

    def _setup_end_of_term_alarm(self, time_till_end_term=None):
        if self._end_of_term_handle is not None:
            alarms.cancel_alarm(self._end_of_term_handle)
            self._end_of_term_handle = None
        if time_till_end_term is None:
            sim_now = services.time_service().sim_now
            remaining_term_days = self.TERM_LENGTH - 1
            prospective_end_of_term = sim_now.day() + remaining_term_days
            if prospective_end_of_term >= len(Days):
                remaining_term_days = remaining_term_days + 2
            term_length_span = TimeSpan(remaining_term_days*date_and_time.sim_ticks_per_day())
            time_at_end_day = services.time_service().sim_now + term_length_span
            (time_till_end_term, _) = self.END_OF_TERM_SCHEDULE().time_until_next_scheduled_event(time_at_end_day)
            time_till_end_term = time_till_end_term + term_length_span
        self._end_of_term_handle = alarms.add_alarm(self, time_till_end_term, self._end_of_term_callback, cross_zone=True)

    def _end_of_term_callback(self, _):
        self.complete_term()
        self._reset_term_alarm()

    def _reset_term_alarm(self):
        self._term_started_time = None
        if self._start_of_term_handle is not None:
            alarms.cancel_alarm(self._start_of_term_handle)
            self._start_of_term_handle = None
        if self._end_of_term_handle is not None:
            alarms.cancel_alarm(self._end_of_term_handle)
            self._end_of_term_handle = None
        if self._daily_update_handle is not None:
            alarms.cancel_alarm(self._daily_update_handle)
            self._daily_update_handle = None

    def _setup_daily_update_alarm(self):
        if self._daily_update_handle is not None:
            alarms.cancel_alarm(self._daily_update_handle)
            self._daily_update_handle = None
        if self._sim_info.is_npc:
            return
        sim_now = services.time_service().sim_now
        next_day = DateAndTime(sim_now).day() + 1
        if next_day == 7:
            next_day = 0
        alarm_time = date_and_time.create_date_and_time(days=next_day)
        time_till_daily_update = sim_now.time_till_next_day_time(alarm_time)
        self._daily_update_handle = alarms.add_alarm(self, time_till_daily_update + TimeSpan.ONE, self._daily_update_callback, cross_zone=True)

    def _daily_update_callback(self, _):
        self._sim_info.career_tracker.resend_career_data()
        self._sim_info.career_tracker.resend_at_work_infos()
        self._setup_daily_update_alarm()

    def get_current_day_of_term(self):
        if self._term_started_time is not None:
            now = services.time_service().sim_now
            diff = now - self._term_started_time
            return math.floor(diff.in_days()) + 1

    def get_remaining_days_in_term(self):
        if self._end_of_term_handle is not None:
            days = math.ceil(self._end_of_term_handle.get_remaining_time().in_days())
            if days == 1:
                current_day = DateAndTime(services.time_service().sim_now).day()
                finishing_day = DateAndTime(self._end_of_term_handle.finishing_time).day()
                if current_day == finishing_day:
                    return 0
                else:
                    return days
            else:
                return days

    def get_remaining_days_to_reenrollment(self):
        if self._reenrollment_handle is not None:
            return int(round(self._reenrollment_handle.get_remaining_time().in_days()))
        return 0

    def get_pending_start_of_term_time(self):
        if self._start_of_term_handle is not None:
            return self._start_of_term_handle.finishing_time

    def get_degree_info_description(self):
        gpa = self.get_gpa()
        if gpa is None:
            gpa = self.NO_GPA_TEXT()
        else:
            gpa = self.get_gpa_string(gpa)
        days = self.get_remaining_days_in_term()
        if self._enrollment_status == EnrollmentStatus.GRADUATED:
            days = self.GRADUATED_TERM_TEXT()
        elif days is None:
            days = self.TERM_NOT_STARTED_TEXT()
        elif days == 0:
            days = self.LAST_DAY_TERM_TEXT()
        else:
            days = str(days)
        current_credits = self._current_credits
        if self._enrollment_status == EnrollmentStatus.GRADUATED:
            current_credits = self.CREDITS_REQUIRED
        return self.DEGREE_INFO_TEXT(self._current_university.display_name, self._current_major.display_name, gpa, current_credits, self.CREDITS_REQUIRED, days)

    def get_degree_info_tooltip_description(self):
        return self.DEGREE_INFO_TOOLTIP_TEXT(self._current_university.display_name, self._current_major.display_name)

    def _set_degree_info_slot(self):
        career_tracker = self._sim_info.career_tracker
        for course_slot in career_tracker.careers.values():
            if course_slot.career_panel_type == CareerPanelType.UNIVERSITY_COURSE:
                return
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        course_slots = list(career_manager.get_ordered_types(only_subclasses_of=UniversityCourseCareerSlot))
        for course_slot in course_slots:
            if course_slot.career_panel_type == CareerPanelType.UNIVERSITY_COURSE:
                career_tracker.add_career(course_slot(self._sim_info), show_join_msg=False, schedule_init_only=True)
                return

    def _remove_degree_info_slot(self):
        career_tracker = self._sim_info.career_tracker
        for (career_guid, course_slot) in list(career_tracker.careers.items()):
            if course_slot.career_panel_type == CareerPanelType.UNIVERSITY_COURSE:
                career_tracker.remove_career(career_guid, post_quit_msg=False)
                return

    def _get_schedule_count_by_type(self, final_type):
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        course_slots = career_manager.get_ordered_types(only_subclasses_of=UniversityCourseCareerSlot)
        count = 0
        for slot in course_slots:
            if slot.career_category == CareerCategory.UniversityCourse:
                schedules = slot.start_track.career_levels
                for schedule in schedules:
                    if schedule.final_requirement_type == final_type:
                        count += 1
                return count
        return count

    def _get_courses_to_take(self, major, university, course_count, credit_count, courses=()):
        if not (self.TERM_COURSE_COUNT.lower_bound <= course_count and course_count <= self.TERM_COURSE_COUNT.upper_bound):
            logger.error('Invalid number of courses requested: {} Total courses to take. Min {}, Max {}', course_count, self.TERM_COURSE_COUNT.lower_bound, self.TERM_COURSE_COUNT.upper_bound)
        courses_to_take = []
        start_index = credit_count
        core_class_count = course_count - len(courses)
        previous_courses = ()
        if self._current_university.guid64 == university.guid64:
            previous_courses = self._previous_courses
        major_course_count = len(major.courses)
        while self._current_university is not None and core_class_count > 0 and start_index < major_course_count:
            current_index = start_index
            while current_index >= 0:
                course = major.courses[current_index]
                if course.guid64 not in previous_courses:
                    courses_to_take.append(course)
                    break
                current_index -= 1
            logger.error('Negative current_index reached in degree_tracker enroll function.')
            start_index += 1
            core_class_count -= 1
        if core_class_count > 0:
            logger.warn('Degree Tracker: Taking the same course multiple times.  Insufficient courses.\ncredits:{}\ncourse count:{}\nelective count:{}\nmajor:{}', credit_count, course_count, len(courses), major)
            for _ in range(core_class_count):
                courses_to_take.append(major.courses[0])
        courses_to_take.extend(courses)
        return courses_to_take

    @property
    def allowed_to_enroll(self):
        if self._enrollment_status == EnrollmentStatus.PROBATION or self._enrollment_status == EnrollmentStatus.NONE:
            return True
        if self._enrollment_status == EnrollmentStatus.NOT_ENROLLED:
            if self.WITHDRAW_COOLDOWN_BUFF is None:
                return True
            else:
                return not self._sim_info.commodity_tracker.has_statistic(self.WITHDRAW_COOLDOWN_BUFF.commodity)
        return False

    def _find_replacement_course(self, courses_to_take):
        core_courses = self._current_major.courses
        for course in core_courses:
            if course.guid64 not in self._previous_courses and course not in courses_to_take and course.final_requirement_type == FinalCourseRequirement.EXAM:
                return course
        for course in core_courses:
            if course not in courses_to_take and course.final_requirement_type == FinalCourseRequirement.EXAM:
                return course
        course_data_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY_COURSE_DATA)
        elective_list = self.get_elective_course_ids(self._current_university.guid64)
        while elective_list:
            course_id = elective_list.pop()
            course_data = course_data_manager.get(course_id)
            if course_data.final_requirement_type == FinalCourseRequirement.EXAM and course_id not in self._previous_courses:
                return course_data

    def _validate_and_update_courses_to_take(self, courses_to_take):
        paper_schedule_count = self._get_schedule_count_by_type(FinalCourseRequirement.PAPER)
        presentation_schedule_count = self._get_schedule_count_by_type(FinalCourseRequirement.PRESENTATION)
        presentation_course_count = 0
        paper_course_count = 0
        for course in courses_to_take:
            if course.final_requirement_type == FinalCourseRequirement.PAPER:
                paper_course_count += 1
            elif course.final_requirement_type == FinalCourseRequirement.PRESENTATION:
                presentation_course_count += 1
        if paper_course_count > paper_schedule_count or presentation_course_count > presentation_schedule_count:
            replacement_course = self._find_replacement_course(courses_to_take)
            for course in courses_to_take:
                if course.final_requirement_type == FinalCourseRequirement.PAPER and paper_course_count > paper_schedule_count:
                    courses_to_take.remove(course)
                    if replacement_course is not None:
                        courses_to_take.append(replacement_course)
                    break
                elif course.final_requirement_type == FinalCourseRequirement.PRESENTATION and presentation_course_count > presentation_schedule_count:
                    courses_to_take.remove(course)
                    if replacement_course is not None:
                        courses_to_take.append(replacement_course)
                    break
        return courses_to_take

    def enroll(self, major, university, course_count, courses=()):
        if not self.allowed_to_enroll:
            logger.error('Sim {} current enrollment status does not allow for enrollment: {}', self._sim_info, self._enrollment_status.name)
            return
        if not self.is_accepted_degree(university, major):
            logger.error('Sim {} is trying to enroll in University: {}, Major: {}, which Sim has never been accepted into.', self._sim_info, university.__name__, major.__name__)
            return
        if self._current_major is not major and self._current_major is not None:
            self.switch_majors(major)
        self._current_major = major
        if self._current_university is not None and self._current_university is not university:
            self._unenrollment_pre_actions()
        self._current_university = university
        resolver = SingleSimResolver(self._sim_info)
        if self._current_credits == 0:
            for tested_benefits in DegreeTracker.ENROLLMENT_BENEFITS:
                if tested_benefits.test.run_tests(resolver):
                    benefits = tested_benefits.benefits
                    self._current_credits = benefits.starting_credits
                    break
        preliminary_courses_to_take = self._get_courses_to_take(major, university, course_count, self._current_credits, courses)
        courses_to_take = self._validate_and_update_courses_to_take(preliminary_courses_to_take)
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        available_course_slots = list(career_manager.get_ordered_types(only_subclasses_of=UniversityCourseCareerSlot))
        for slot in available_course_slots:
            if slot.career_panel_type == CareerPanelType.UNIVERSITY_COURSE:
                available_course_slots.remove(slot)
                break
        used_schedule_indexes = []
        for course in courses_to_take:
            if not available_course_slots:
                logger.error('Insufficient course slots for requested number of courses: {}', course_count)
                return
            slot = random.choice(available_course_slots)
            available_course_slots.remove(slot)
            skill = course.course_skill_data.related_skill
            if skill is not None:
                stat_tracker = self._sim_info.get_tracker(skill)
                skill_value = stat_tracker.get_value(skill)
            else:
                skill_value = 0
            self._course_infos[slot.guid64] = DegreeTracker.CourseInfo(course, initial_skill=skill_value)
            schedules = list(slot.start_track.career_levels)
            random.shuffle(schedules)
            course_schedule = None
            while schedules:
                course_schedule = schedules.pop()
                if course_schedule.final_requirement_type == course.final_requirement_type:
                    schedule_index = slot.start_track.career_levels.index(course_schedule)
                    if schedule_index not in used_schedule_indexes:
                        used_schedule_indexes.append(schedule_index)
                        course_schedule.career = slot
                        self._sim_info.career_tracker.add_career(slot(self._sim_info), user_level_override=schedule_index + 1, schedule_init_only=True)
                        break
        if self._enrollment_status != EnrollmentStatus.PROBATION:
            self._set_enrollment_status(EnrollmentStatus.ENROLLED)
        else:
            probation_notification_dialog = self.PROBATION_NOTIFICATION(self._sim_info, SingleSimResolver(self._sim_info))
            probation_notification_dialog.show_dialog()
            self._apply_enrollment_status_loot(EnrollmentStatus.ENROLLED)
        self._set_degree_info_slot()
        self._setup_start_of_term_alarm()
        self._setup_daily_update_alarm()
        self._activate_organization_membership()
        services.get_event_manager().process_event(test_events.TestEvent.SimEnrolledInUniversity, enrolled_sim_id=self._sim_info.id)
        self.clear_kickout_info()
        self.is_immune_to_kickout = False
        DegreeTracker.IS_REENROLLMENT_DIALOGS_IN_PROCESS = False
        UniversityTelemetry.send_university_enroll_telemetry(self._sim_info, self._current_major)
        self._sim_info.career_tracker.resend_career_data()
        self._sim_info.career_tracker.resend_at_work_infos()

    def get_grade_performance(self, career_guid):
        course_slot = self._sim_info.career_tracker.get_career_by_uid(career_guid)
        if course_slot is None:
            return 0
        course_info = self._course_infos[career_guid]
        if course_info is None:
            return 0
        skill = course_info.course_data.course_skill_data.related_skill
        if skill is None:
            return 0
        stat_tracker = self._sim_info.get_tracker(skill)
        current_skill = stat_tracker.get_value(skill)
        skill_delta = current_skill - course_info.initial_skill
        mod = self.GRADE_SKILL_MODIFICATION.get(skill_delta)
        if current_skill == skill.max_value:
            mod += self.GRADE_SKILL_MAX_MODIFICATION
        course_stat = course_slot.current_level_tuning.performance_stat
        return min(course_slot.work_performance + mod, course_stat.max_value)

    def get_grade_report(self, career_guid):
        sim_info = self._sim_info
        course_info = self._course_infos[career_guid]
        if course_info is None:
            logger.error('Unable to find course info for career guid {}', career_guid)
            return
        course_data = course_info.course_data
        course_name = self.get_course_name(course_data)
        performance = self.get_grade_performance(career_guid)
        current_day = self.get_current_day_of_term()
        if current_day is None:
            current_day = 1
        elif current_day > 5:
            current_day = 5
        performance_strings_list = self.GRADE_REPORT_MAPPING[current_day]
        for performance_tuple in performance_strings_list:
            performance_range = performance_tuple.performance_range
            if performance_range.lower_bound <= performance and performance < performance_range.upper_bound:
                text = performance_tuple.report_text(self._sim_info, course_name)
                additional_text = ''
                final_requirement_text_map = performance_tuple.final_requirement_text_map
                if not course_info.final_requirement_completed:
                    additional_text = final_requirement_text_map[course_data.final_requirement_type]()
                report_dialog = self.COURSE_GRADE_REPORT_NOTIFICATION(sim_info, SingleSimResolver(sim_info))
                icon_override = IconInfoData(icon_resource=course_data.icon) if final_requirement_text_map and course_data.final_requirement_type in final_requirement_text_map.keys() and course_data.icon is not None else DEFAULT
                report_dialog.show_dialog(icon_override=icon_override, additional_tokens=(course_name, text, additional_text))
                return

    def get_core_course_ids_for_enrollment(self, major, university, credit_count, credits_remaining):
        course_count = min(credits_remaining, self.TERM_COURSE_COUNT.upper_bound)
        core_courses = self._get_courses_to_take(major, university, course_count, credit_count)
        return [course.guid64 for course in core_courses]

    def get_elective_course_ids(self, university_id):
        current_day = math.floor(services.time_service().sim_now.absolute_days())
        change_frequency = University.COURSE_ELECTIVES.elective_change_frequency
        if self._elective_timestamp is None or current_day - self._elective_timestamp >= change_frequency:
            self._elective_timestamp = current_day
            if self._elective_courses_map is None:
                self._elective_courses_map = defaultdict(list)
            resolver = SingleSimResolver(self._sim_info)
            for university in University.ALL_UNIVERSITIES:
                self._elective_courses_map[university.guid64] = [e.guid64 for e in University.generate_elective_courses(resolver)]
        return self._elective_courses_map[university_id]

    def get_housing_zone_ids_for_enrollment(self):
        return UniversityHousingTuning.get_university_housing_zone_ids()

    def get_credits_remaining(self, university_id, major_id):
        return DegreeTracker.CREDITS_REQUIRED - self.calculate_credits(university_id, major_id)

    def add_credits(self, number_of_credits):
        self._current_credits += number_of_credits

    def get_major_status(self, university_id, major_id):
        if major_id in self._previous_majors:
            return UniversityMajorStatus.GRADUATED
        if self._accepted_degrees is not None and university_id in self._accepted_degrees and major_id in self._accepted_degrees[university_id]:
            return UniversityMajorStatus.ACCEPTED
        return UniversityMajorStatus.NOT_ACCEPTED

    def calculate_credits(self, university_id, major_id):
        current_credits = self._current_credits
        if self._current_major.guid64 != major_id:
            current_credits = self.get_credits_carryover()
        if self._current_major is not None and current_credits == 0:
            resolver = SingleSimResolver(self._sim_info)
            for tested_benefits in DegreeTracker.ENROLLMENT_BENEFITS:
                if tested_benefits.test.run_tests(resolver):
                    current_credits = tested_benefits.benefits.starting_credits
                    break
        return current_credits

    def _build_reenrollment_message(self):
        msg = UI_pb2.UniversityEnrollmentSimData()
        msg.university_id = self._current_university.guid64
        msg.major_id = self._current_major.guid64
        return msg

    def generate_enrollment_information(self, is_reenrollment=False):
        msg = UI_pb2.UniversityEnrollmentData()
        msg.household_id = self._sim_info.household.id
        msg.is_pregnant = self._sim_info.is_pregnant
        for university in University.ALL_UNIVERSITIES:
            with ProtocolBufferRollback(msg.universities) as university_message:
                university_id = university.guid64
                university_message.university_id = university_id
                university_message.elective_class_ids.extend(self.get_elective_course_ids(university_id))
                for degree in University.ALL_DEGREES:
                    with ProtocolBufferRollback(university_message.degrees) as degree_message:
                        degree_id = degree.guid64
                        credits_remaining = self.get_credits_remaining(university_id, degree_id)
                        major_status = self.get_major_status(university_id, degree_id)
                        degree_message.major_id = degree_id
                        degree_message.class_remaining = credits_remaining
                        degree_message.status = major_status
                        if major_status == UniversityMajorStatus.ACCEPTED:
                            core_class_ids = self.get_core_course_ids_for_enrollment(degree, university, self.calculate_credits(university_id, degree_id), credits_remaining)
                            degree_message.core_class_ids.extend(core_class_ids)
        msg.housing_zone_ids.extend(self.get_housing_zone_ids_for_enrollment())
        if is_reenrollment:
            if self._current_university is not None and self._current_major is not None:
                msg.current_enrollment = self._build_reenrollment_message()
            else:
                logger.error('Trying to re-enroll sim {} but the current university or major is None', self._sim_info)
        scholarship_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        merit_scholarship_info = ()
        merit_scholarship = ScholarshipTuning.MERIT_SCHOLARSHIP
        if merit_scholarship.guid64 not in self._active_scholarships:
            resolver = SingleSimResolver(self._sim_info)
            if merit_scholarship.evaluation_type.evaluation_type.get_score(self._sim_info, resolver):
                merit_scholarship_info = (merit_scholarship.guid64,)
        self._active_scholarships = list(set(self._active_scholarships))
        for scholarship_id in itertools.chain(self._active_scholarships, self._accepted_scholarships, merit_scholarship_info):
            value = scholarship_manager.get(scholarship_id).get_value(self._sim_info)
            if value is not None and value > 0:
                with ProtocolBufferRollback(msg.scholarships) as scholarship_message:
                    scholarship_message.scholarship_id = scholarship_id
                    scholarship_message.value = value
        op = GenericProtocolBufferOp(Operation.UNIVERSITY_ENROLLMENT_WIZARD, msg)
        Distributor.instance().add_op(self._sim_info, op)

    def assign_professor_to_course(self, course_info, professor_assignment_trait):
        archetypes = University.PROFESSOR_ARCHETYPES[self.get_university()]
        archetype = random.choice(archetypes)
        professor = services.sim_filter_service().submit_matching_filter(sim_filter=archetype, callback=None, number_of_sims_to_find=1, allow_yielding=False, gsi_source_fn=lambda : 'DegreeTracker: Assigning professor with {} to course'.format(str(professor_assignment_trait)))
        if professor:
            professor[0].sim_info.add_trait(professor_assignment_trait)
        return professor

    def clear_all_alarms(self):
        if self._start_of_term_handle is not None:
            alarms.cancel_alarm(self._start_of_term_handle)
            self._start_of_term_handle = None
        if self._end_of_term_handle is not None:
            alarms.cancel_alarm(self._end_of_term_handle)
            self._end_of_term_handle = None
        if self._diploma_handle is not None:
            alarms.cancel_alarm(self._diploma_handle)
            self._diploma_handle = None
        if self._reenrollment_handle is not None:
            alarms.cancel_alarm(self._reenrollment_handle)
            self._reenrollment_handle = None
        if self._pending_scholarship_alarm_handles:
            for alarm in self._pending_scholarship_alarm_handles.values():
                alarms.cancel_alarm(alarm)
            self._pending_scholarship_alarm_handles.clear()
        if self._daily_update_handle is not None:
            alarms.cancel_alarm(self._daily_update_handle)
            self._daily_update_handle = None

    def on_lod_update(self, old_lod, new_lod):
        if new_lod == SimInfoLODLevel.MINIMUM:
            self.clear_all_alarms()

    def on_death(self):
        self._set_enrollment_status(EnrollmentStatus.NONE)
        self._previous_courses.clear()
        self._current_university = None
        self._current_major = None
        self._current_credits = 0
        self._total_gp = 0.0
        self._total_courses = 0
        self.remove_sim_knowlege()
        self.clear_all_alarms()
        self.clear_scholarships()

    def get_rejected_scholarships(self):
        return self._rejected_scholarships

    def get_active_scholarships(self):
        return self._active_scholarships

    def get_accepted_scholarships(self):
        return self._accepted_scholarships

    def get_pending_scholarships(self):
        return self._pending_scholarship_alarm_handles.keys()

    def get_scholarship_list_helper(self, header_string, scholarships, subject, first_list_entry, with_values=False):
        if not scholarships:
            return
        if first_list_entry:
            list_entries = [header_string]
        else:
            list_entries = [EMPTY_LINE, header_string]
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)

        def populate_list_with_values(list_entries, scholarships, subject):
            scholarship_entries = []
            for scholarship_id in scholarships:
                scholarship = snippet_manager.get(scholarship_id)
                if scholarship.amount.amount_enum == ScholarshipAmountEnum.EVALUATION_TYPE:
                    value = scholarship.get_value(subject)
                else:
                    value = scholarship.amount.amount
                scholarship_attributes_string = LocalizationHelperTuning.get_new_line_separated_strings(scholarship.display_name(subject), LocalizationHelperTuning.get_money(value))
                scholarship_entries.append(scholarship_attributes_string)
            list_entries.append(LocalizationHelperTuning.get_bulleted_list((None,), scholarship_entries))
            list_entries.append(EMPTY_LINE)
            return list_entries

        def populate_list_without_values(list_entries, scholarships, subject):
            scholarship_entries = []
            for scholarship_id in scholarships:
                scholarship = snippet_manager.get(scholarship_id)
                scholarship_attributes_string = LocalizationHelperTuning.get_new_line_separated_strings(scholarship.display_name(subject))
                scholarship_entries.append(scholarship_attributes_string)
            scholarship_entries_string = LocalizationHelperTuning.get_bulleted_list((None,), scholarship_entries)
            list_entries.append(scholarship_entries_string)
            list_entries.append(EMPTY_LINE)
            return list_entries

        if with_values:
            return populate_list_with_values(list_entries, scholarships, subject)
        return populate_list_without_values(list_entries, scholarships, subject)

    def get_scholarships_list_by_status(self, status, subject, first_list_entry):
        list_entries = []
        if status == ScholarshipStatus.ACTIVE:
            list_entries = self.get_scholarship_list_helper(GetScholarshipStatusLoot.SCHOLARSHIP_STATUS_HEADER_ENTRY_ACTIVE, self.get_active_scholarships(), subject, first_list_entry, with_values=True)
        elif status == ScholarshipStatus.REJECTED:
            list_entries = self.get_scholarship_list_helper(GetScholarshipStatusLoot.SCHOLARSHIP_STATUS_HEADER_ENTRY_REJECTED, self.get_rejected_scholarships(), subject, first_list_entry)
        elif status == ScholarshipStatus.ACCEPTED:
            list_entries = self.get_scholarship_list_helper(GetScholarshipStatusLoot.SCHOLARSHIP_STATUS_HEADER_ENTRY_ACCEPTED, self.get_accepted_scholarships(), subject, first_list_entry, with_values=True)
        elif status == ScholarshipStatus.PENDING:
            list_entries = self.get_scholarship_list_helper(GetScholarshipStatusLoot.SCHOLARSHIP_STATUS_HEADER_ENTRY_PENDING, self.get_pending_scholarships(), subject, first_list_entry)
        if list_entries is not None:
            return LocalizationHelperTuning.get_new_line_separated_strings(*list_entries)

    def get_best_scored_scholarships(self, amount, resolver):

        def get_score(scored_scholarship):
            return scored_scholarship[1]

        scored_scholarships = []
        for scholarship in services.get_instance_manager(sims4.resources.Types.SNIPPET).get_ordered_types(only_subclasses_of=Scholarship):
            score = scholarship.evaluation_type.evaluation_type.get_score(self._sim_info, resolver, from_get_scholarship_chances=True)
            if not score is None:
                if score == 0:
                    pass
                else:
                    scored_scholarships.append((scholarship, score))
        if not scored_scholarships:
            logger.warning('No scholarships were found, so none were scored for Sim ({}).', self._sim_info)
            return scored_scholarships
        ordered_scholarships = sorted(scored_scholarships, key=get_score, reverse=True)
        if len(ordered_scholarships) < amount:
            return ordered_scholarships
        return ordered_scholarships[0:amount]

    def get_best_scored_scholarship_list(self, amount, resolver, sim_info):
        best_scored_scholarships = self.get_best_scored_scholarships(amount, resolver)
        scholarship_items = []
        for (scholarship, _) in best_scored_scholarships:
            scholarship_attributes = LocalizationHelperTuning.get_new_line_separated_strings(scholarship.display_name(sim_info), scholarship.display_description(sim_info), GetScholarshipStatusLoot.SCHOLARSHIP_VALUE_ENTRY_POINT, LocalizationHelperTuning.get_money(scholarship.get_value(sim_info)), EMPTY_LINE)
            scholarship_items.append(scholarship_attributes)
        best_scholarships_string = LocalizationHelperTuning.get_bulleted_list((None,), scholarship_items)
        return best_scholarships_string

    def _post_create_func(self, created_object, scholarship):
        if created_object.has_component(objects.components.types.SCHOLARSHIP_LETTER_COMPONENT):
            scholarship_letter_comp = created_object.get_component(objects.components.types.SCHOLARSHIP_LETTER_COMPONENT)
            scholarship_letter_comp.set_applicant_sim_id(self._sim_info.id)
            scholarship_letter_comp.set_scholarship_id(scholarship.guid64)

    def _run_scholarship_resolve_loot_actions(self, scholarship, loot):
        resolver = SingleSimResolver(self._sim_info)
        for action in loot.loot_actions:
            if isinstance(action, ObjectRewardsOperation):
                if scholarship is ScholarshipTuning.MERIT_SCHOLARSHIP:
                    pass
                else:
                    action.apply_with_post_create(self._sim_info, resolver, lambda *args: self._post_create_func(scholarship, *args))
                    action.apply_to_resolver(resolver)
            else:
                action.apply_to_resolver(resolver)

    def lose_scholarship(self, scholarship):
        if scholarship.guid64 in self._active_scholarships:
            self._active_scholarships.remove(scholarship.guid64)
        if scholarship.guid64 in self._accepted_scholarships:
            self._accepted_scholarships.remove(scholarship.guid64)
        if scholarship.guid64 not in self._rejected_scholarships:
            self._rejected_scholarships.append(scholarship.guid64)

    def grant_scholarship(self, scholarship):
        if scholarship.guid64 in self._accepted_scholarships:
            return
        self._accepted_scholarships.append(scholarship.guid64)
        if scholarship.get_value(self._sim_info) > ScholarshipTuning.APPLICATION_RESPONSE_TUNING.value_threshold:
            self._run_scholarship_resolve_loot_actions(scholarship, ScholarshipTuning.APPLICATION_RESPONSE_TUNING.accepted_beyond_value_threshold)
        else:
            self._run_scholarship_resolve_loot_actions(scholarship, ScholarshipTuning.APPLICATION_RESPONSE_TUNING.accepted_below_value_threshold)

    def reject_scholarship(self, scholarship):
        if scholarship.guid64 in self._rejected_scholarships:
            return
        self._rejected_scholarships.append(scholarship.guid64)
        self._run_scholarship_resolve_loot_actions(scholarship, ScholarshipTuning.APPLICATION_RESPONSE_TUNING.rejected)

    def evaluate_scholarship(self, scholarship, skip_pending=False):
        resolver = SingleSimResolver(self._sim_info)
        if not skip_pending:
            del self._pending_scholarship_alarm_handles[scholarship.guid64]
        score = scholarship.evaluation_type.evaluation_type.get_score(self._sim_info, resolver)
        if score is None:
            return
        if random.randrange(0, 100, 1) <= score:
            self.grant_scholarship(scholarship)
        else:
            self.reject_scholarship(scholarship)

    def process_scholarship_application(self, scholarship, delay_time):
        evaluation_alarm_handle = alarms.add_alarm(self, delay_time, lambda _: self.evaluate_scholarship(scholarship), cross_zone=True)
        self._pending_scholarship_alarm_handles[scholarship.guid64] = evaluation_alarm_handle

    def handle_scholarships_after_enrollment(self, total_scholarship_taken):
        scholarship_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        merit_scholarship = ScholarshipTuning.MERIT_SCHOLARSHIP
        if merit_scholarship.guid64 not in self._active_scholarships:
            self.evaluate_scholarship(ScholarshipTuning.MERIT_SCHOLARSHIP, skip_pending=True)
        active_scholarships = [scholarship_manager.get(scholarship_id) for scholarship_id in itertools.chain(self.get_active_scholarships(), self.get_accepted_scholarships())]
        if active_scholarships:
            sum_scholarship_value = sum(scholarship().get_value(self._sim_info) for scholarship in active_scholarships)
            if sum_scholarship_value > total_scholarship_taken:
                surplus_scholarship_value = sum_scholarship_value - total_scholarship_taken
                if surplus_scholarship_value > 0:
                    self._sim_info.household.funds.add(surplus_scholarship_value, Consts_pb2.FUNDS_SCHOLARSHIP_SURPLUS, sim=self._sim_info)
                ScholarshipTuning.FULL_RIDE_LOOT.apply_to_resolver(SingleSimResolver(self._sim_info))
            for scholarship_id in self.get_accepted_scholarships():
                scholarship = scholarship_manager.get(scholarship_id)
                if scholarship.maintenance_type.maintenance_type.maintenance_enum == ScholarshipMaintenanceEnum.ACTIVITY:
                    career_type = scholarship.maintenance_type.maintenance_type.activity
                    self._sim_info.career_tracker.add_career(career_type(self._sim_info))
        self._active_scholarships.extend(self._accepted_scholarships)
        self._accepted_scholarships.clear()
        self._rejected_scholarships.clear()

    def clear_scholarships(self):
        self._active_scholarships.clear()
        self._accepted_scholarships.clear()
        self._rejected_scholarships.clear()

    def create_university_objects(self):
        for (career_guid, course_info) in self._course_infos.items():
            career = self._sim_info.career_tracker.get_career_by_uid(career_guid)
            if career is None:
                pass
            else:
                career_level_tuning = career.current_level_tuning
                if career_level_tuning is None:
                    pass
                else:
                    resolver = SingleSimResolver(self._sim_info)
                    for loot in career_level_tuning.loot_on_join:
                        loot.apply_to_resolver(resolver)
