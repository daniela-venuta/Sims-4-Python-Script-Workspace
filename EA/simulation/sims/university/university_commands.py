from protocolbuffers import Consts_pb2from event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom server_commands.argument_helpers import TunableInstanceParam, get_optional_target, OptionalSimInfoParamfrom server_commands.household_commands import household_splitfrom sims.loan_tuning import LoanTunables, LoanTypefrom sims.university.university_enums import EnrollmentStatus, Grade, UniversityHousingKickOutReasonfrom sims.university.university_housing_tuning import UniversityHousingTuningfrom sims.university.university_telemetry import UniversityTelemetryfrom sims.university.university_tuning import Universityfrom sims4.common import Packfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, Tunablefrom situations.situation_guest_list import SituationGuestListimport build_buyimport servicesimport sims4.commands
class UniversityCommandTuning:
    DEGREE_TRAITS = TunableList(description='\n        A list of all possible combinations of degrees, where each list\n        is assigned a specific prestige and honors permutation.\n        ', tunable=TunableTuple(description='\n            A tuple of prestige and honors booleans, and the associated list\n            of degree traits.\n            ', prestige=Tunable(description='\n                The prestige type (Prestige or No Prestige) of this degree\n                list.\n                ', tunable_type=bool, default=False), honors=Tunable(description='\n                The honors type (Honors or No Honors) of this degree list.\n                ', tunable_type=bool, default=False), traits=TunableList(description='\n                The list of degree traits for this prestige and honors \n                permutation.\n                ', tunable=TunableReference(description='\n                    The degree trait.\n                    ', manager=services.get_instance_manager(Types.TRAIT), pack_safe=True))))

def get_target_household_id_for_zone(zone_id, account):
    target_household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
    if target_household_id is None or target_household_id == 0:
        household = services.household_manager().create_household(account, starting_funds=0)
        target_household_id = household.id
    return target_household_id

@sims4.commands.Command('university.enroll', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def enroll(major:TunableInstanceParam(sims4.resources.Types.UNIVERSITY_MAJOR), university:TunableInstanceParam(sims4.resources.Types.UNIVERSITY), opt_sim:OptionalSimInfoParam=None, classes:int=3, elective:TunableInstanceParam(sims4.resources.Types.UNIVERSITY_COURSE_DATA)=None, tuition_cost:int=0, total_scholarship_taken:int=0, is_using_loan:bool=False, destination_zone_id:int=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.enroll', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.enroll'.format(sim_info), _connection)
        return False
    electives = () if elective is None else (elective,)
    degree_tracker.enroll(major, university, classes, courses=electives)
    if is_using_loan:
        LoanTunables.add_debt(sim_info, LoanTunables.get_loan_amount(tuition_cost, LoanType.UNIVERSITY))
    else:
        sim_info.household.funds.try_remove(tuition_cost, Consts_pb2.FUNDS_TUITION_COST, sim_info)
    UniversityTelemetry.send_university_tuition_telemetry(sim_info, tuition_cost, is_using_loan)
    degree_tracker.handle_scholarships_after_enrollment(total_scholarship_taken)
    UniversityTelemetry.send_university_housing_telemetry(destination_zone_id)
    if destination_zone_id is None:
        return True
    home_zone_id = sim_info.household.home_zone_id
    if home_zone_id == destination_zone_id:
        degree_tracker.on_enroll_in_same_housing()
        return True
    venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
    venue = venue_manager.get(build_buy.get_current_venue(home_zone_id))
    if venue.is_university_housing:
        sim_info.degree_tracker.set_kickout_info(destination_zone_id, UniversityHousingKickOutReason.MOVED)
        return True
    target_household_id = 0
    if destination_zone_id != 0:
        account = services.client_manager().get(_connection).account
        target_household_id = get_target_household_id_for_zone(destination_zone_id, account)
    household_split(sourceHouseholdId=sim_info.household.id, targetHouseholdId=target_household_id, cancelable=False, allow_sim_transfer=False, selected_sim_ids=[sim_info.sim_id], destination_zone_id=destination_zone_id)
    return True

@sims4.commands.Command('university.accept_all_degrees', pack=Pack.EP08)
def accept_all_degrees(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to find SimInfo.', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.accept_all_degrees'.format(sim_info), _connection)
        return False
    for university in University.ALL_UNIVERSITIES:
        for degree in University.ALL_DEGREES:
            if degree_tracker.is_accepted_degree(university, degree):
                pass
            else:
                degree_tracker.set_accepted_degree(university, degree)
    return True

@sims4.commands.Command('university.show_brochure', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def show_brochure(university:TunableInstanceParam(sims4.resources.Types.UNIVERSITY), opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to find SimInfo.', _connection)
        return False
    university.brochure_loot.apply_to_resolver(SingleSimResolver(sim_info))
    return True

@sims4.commands.Command('university.show_enrollment_dialog', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def show_enrollment_dialog(opt_sim:OptionalSimInfoParam=None, is_reenrollment:bool=False, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to find SimInfo.', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker.'.format(sim_info), _connection)
        return False
    degree_tracker.generate_enrollment_information(is_reenrollment=is_reenrollment)
    return True

@sims4.commands.Command('university.cancel_enrollment_dialog', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def cancel_enrollment_dialog(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to find SimInfo.', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker.'.format(sim_info), _connection)
        return False
    degree_tracker.on_cancel_enrollment_dialog()
    return True

@sims4.commands.Command('university.create_kick_out_situation', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def create_kick_out_situation(kick_out_reason:UniversityHousingKickOutReason, sim_id:int=None, additional_sim_ids:[]=None, university_housing_destination_zone_id:int=0, _connection=None):
    if sim_id is None:
        active_sim = services.get_active_sim()
        sim_id = active_sim.sim_id
    guest_list = SituationGuestList(invite_only=True, host_sim_id=sim_id)
    services.get_zone_situation_manager().create_situation(UniversityHousingTuning.UNIVERSITY_HOUSING_KICK_OUT_SITUATION, guest_list=guest_list, scoring_enabled=False, kick_out_reason=kick_out_reason, additional_sim_ids=additional_sim_ids, university_housing_destination_zone_id=university_housing_destination_zone_id)

@sims4.commands.Command('university.dropout', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def dropout(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.dropout', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.dropout'.format(sim_info), _connection)
        return False
    degree_tracker.show_dropout_dialog()
    return True

@sims4.commands.Command('university.withdraw', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def withdraw(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.withdraw', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.withdraw'.format(sim_info), _connection)
        return False
    degree_tracker.withdraw()
    services.venue_service().validate_university_housing_household_sims()
    return True

@sims4.commands.Command('university.complete_course', pack=Pack.EP08)
def complete_course(course:TunableInstanceParam(sims4.resources.Types.UNIVERSITY_COURSE_DATA), course_score:int=100, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.complete_course', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.complete_course'.format(sim_info), _connection)
        return False
    for (course_guid, course_info) in list(degree_tracker._course_infos.items()):
        if course_info.course_data is course:
            course_info.lectures = degree_tracker.COURSE_LECTURE_COUNT
            course_info.final_requirement_completed = True
            degree_tracker.course_infos[course_guid] = course_info
            degree_tracker.complete_course(course_guid, course_score)
            return True
    sims4.commands.output('Sim is not currently enrolled in course {}'.format(course), _connection)
    return False

@sims4.commands.Command('university.finish_term', pack=Pack.EP08)
def finish_term(course_score:int=100, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.finish_term', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.finish_term'.format(sim_info), _connection)
        return False
    enrollment_status = degree_tracker.get_enrollment_status()
    if enrollment_status == EnrollmentStatus.ENROLLED or not enrollment_status == EnrollmentStatus.PROBATION:
        sims4.commands.output('The Sim is not currently enrolled in a university term.', _connection)
        return False
    for (course_guid, course_info) in list(degree_tracker._course_infos.items()):
        if course_info.final_grade == Grade.UNKNOWN:
            course_info.lectures = degree_tracker.COURSE_LECTURE_COUNT
            course_info.final_requirement_completed = True
            degree_tracker.course_infos[course_guid] = course_info
            degree_tracker.complete_course(course_guid, course_score)
    degree_tracker.complete_term()
    return True

@sims4.commands.Command('university.graduate', pack=Pack.EP08)
def graduate(gpa:float=4.0, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.graduate', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.graduate'.format(sim_info), _connection)
        return False
    if degree_tracker.get_enrollment_status() == EnrollmentStatus.NONE:
        sims4.commands.output('The Sim is not currently in a degree program.', _connection)
        return False
    degree_tracker.drop_enrolled_courses()
    degree_tracker.graduate(gpa=gpa)

@sims4.commands.Command('university.grade_report', pack=Pack.EP08)
def grade_report(course:TunableInstanceParam(sims4.resources.Types.UNIVERSITY_COURSE_DATA), opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.grade_report', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.grade_report'.format(sim_info), _connection)
        return False
    for (course_guid, course_info) in degree_tracker._course_infos.items():
        if course_info.course_data is course:
            degree_tracker.get_grade_report(course_guid)
    return True

@sims4.commands.Command('university.degree_info', pack=Pack.EP08)
def degree_info(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.degree_info', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker in university.degree_info'.format(sim_info), _connection)
        return False
    major = degree_tracker.get_major()
    university = degree_tracker.get_university()
    current_day = degree_tracker.get_current_day_of_term()
    previous_courses = degree_tracker.get_previous_courses()
    sims4.commands.output('Major: {}'.format(major.__name__ if major else 'None'), _connection)
    sims4.commands.output('University: {}'.format(university.__name__ if university else 'None'), _connection)
    sims4.commands.output('GPA: {}'.format(degree_tracker.get_gpa()), _connection)
    sims4.commands.output('Enrollment Status: {}'.format(degree_tracker.get_enrollment_status().name), _connection)
    sims4.commands.output('Current day of term: {}'.format(current_day if current_day else 'None'), _connection)
    sims4.commands.output('Previous Courses: {}'.format('' if previous_courses else 'None'), _connection)
    for course_data in previous_courses:
        sims4.commands.output(' {}'.format(course_data.__name__), _connection)
    return True

@sims4.commands.Command('university.end_kickout_situation', pack=Pack.EP08)
def end_kickout_situation(_connection=None):
    services.get_event_manager().process_event(test_events.TestEvent.HouseholdSplitPanelClosed)

@sims4.commands.Command('university.clear_scholarships', pack=Pack.EP08, command_type=sims4.commands.CommandType.Live)
def clear_scholarships(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for clear scholarship command.', _connection)
        return False
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        sims4.commands.output('Sim: {} has no degree tracker.'.format(sim_info), _connection)
        return False
    degree_tracker.clear_scholarships()

@sims4.commands.Command('university.award_all_degrees', pack=Pack.EP08)
def award_all_degrees(prestige:bool=False, honors:bool=False, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No valid target for university.award_all_degrees.', _connection)
        return False
    for degree_trait_tuple in UniversityCommandTuning.DEGREE_TRAITS:
        if degree_trait_tuple.prestige == prestige and degree_trait_tuple.honors == honors:
            for trait in degree_trait_tuple.traits:
                sim_info.add_trait(trait)
            return True
    return False
