from sims.university.university_scholarship_enums import ScholarshipStatusfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesimport sims4.resourcessim_university_schema = GsiGridSchema(label='University')sim_university_schema.add_field('sim', label='Sim', unique_field=True)sim_university_schema.add_field('sim_id', label='Sim ID')sim_university_schema.add_field('university', label='Current University')sim_university_schema.add_field('major', label='Current Major')sim_university_schema.add_field('status', label='Enrollment Status')sim_university_schema.add_field('gpa', label='GPA')sim_university_schema.add_field('credits', label='Credits')sim_university_schema.add_field('term_start', label='Term Start')sim_university_schema.add_field('current_day', label='Current Day of Term')with sim_university_schema.add_has_many('accepted_degrees', GsiGridSchema, label='Accepted Degrees') as sub_schema:
    sub_schema.add_field('degree', label='Degree')
    sub_schema.add_field('university', label='University')
    sub_schema.add_field('prestige', label='Prestige')with sim_university_schema.add_has_many('not_yet_accepted_degrees', GsiGridSchema, label='Not Yet Accepted Degrees') as sub_schema:
    sub_schema.add_field('degree', label='Degree')
    sub_schema.add_field('university', label='University')
    sub_schema.add_field('prestige', label='Prestige')
    sub_schema.add_field('degree_score', label='Degree Score Requirement')
    sub_schema.add_field('sim_score', label='Sim Score')
    sub_schema.add_field('is_qualify', label='Sim Qualify')with sim_university_schema.add_has_many('completed_degrees', GsiGridSchema, label='Completed Degrees') as sub_schema:
    sub_schema.add_field('degree', label='Degree')with sim_university_schema.add_has_many('previous_courses', GsiGridSchema, label='Previous Courses') as sub_schema:
    sub_schema.add_field('course', label='Course')
    sub_schema.add_field('core', label='Is Core Course?')with sim_university_schema.add_has_many('current_courses', GsiGridSchema, label='Current Courses') as sub_schema:
    sub_schema.add_field('course', label='Course')
    sub_schema.add_field('slot', label='Slot')
    sub_schema.add_field('grade', label='Grade')
    sub_schema.add_field('core', label='Is Core Course?')
    sub_schema.add_field('work performance', label='Work Performance')
def get_accepted_degrees(sim_info, university_manager, degree_manager):
    degrees_data = []
    accepted_degrees = sim_info.degree_tracker.accepted_degrees
    if accepted_degrees is not None:
        for (university_id, degree_ids) in accepted_degrees.items():
            university = university_manager.get(university_id)
            for degree_id in degree_ids:
                degree = degree_manager.get(degree_id)
                degrees_data.append({'degree': degree.__name__, 'university': university.__name__, 'prestige': degree in university.prestige_degrees})
    return degrees_data

def get_not_yet_accepted_degrees(sim_info, university_manager, degree_manager):
    degrees_data = []
    not_yet_accepted_degrees = sim_info.degree_tracker.get_not_yet_accepted_degrees()
    for (university_id, degree_ids) in not_yet_accepted_degrees.items():
        university = university_manager.get(university_id)
        for degree_id in degree_ids:
            degree = degree_manager.get(degree_id)
            is_prestige = degree in university.prestige_degrees
            degrees_data.append({'degree': degree.__name__, 'university': university.__name__, 'prestige': is_prestige, 'degree_score': str(degree.acceptance_score.score_threshold.value) if is_prestige else 'Not Required', 'sim_score': str(degree.get_sim_acceptance_score(sim_info)) if is_prestige else '', 'is_qualify': degree.can_sim_be_accepted(sim_info) if is_prestige else True})
    return degrees_data

def get_completed_degrees(sim_info, university_manager, degree_manager):
    degrees_data = []
    for degree_id in sim_info.degree_tracker.previous_majors:
        degrees_data.append({'degree': degree_manager.get(degree_id).__name__})
    return degrees_data

def get_current_courses(sim_info):
    data = []
    degree_tracker = sim_info.degree_tracker
    course_slots = degree_tracker.get_career_course_slots()
    for (slot_id, course_info) in degree_tracker.course_infos.items():
        course_data = course_info.course_data
        course_slot_career_ref = services.get_instance_manager(sims4.resources.Types.CAREER).get(slot_id)
        course_slot = next(filter(lambda c: c.guid64 == slot_id, course_slots), None)
        data.append({'slot': course_slot_career_ref.__name__, 'course': course_data.__name__, 'core': degree_tracker.is_core_course(course_data), 'grade': None if course_slot is None else degree_tracker.get_grade(course_slot.work_performance).name, 'work performance': None if course_slot is None else course_slot.work_performance})
    return data

def get_previous_courses(sim_info):
    data = []
    degree_tracker = sim_info.degree_tracker
    for course_data in degree_tracker.get_previous_courses():
        data.append({'course': course_data.__name__, 'core': degree_tracker.is_core_course(course_data)})
    return data

@GsiHandler('sim_university_view', sim_university_schema)
def generate_sim_university_view_data(sim_id:int=None):
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return
    degree_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY_MAJOR)
    university_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY)
    university_view_data = []
    for sim_info in list(sim_info_manager.objects):
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            pass
        else:
            university_data = {'sim': sim_info.full_name, 'sim_id': str(sim_info.sim_id), 'university': degree_tracker.get_university().__name__ if degree_tracker.get_university() is not None else 'None', 'major': degree_tracker.get_major().__name__ if degree_tracker.get_major() is not None else 'None', 'status': degree_tracker.get_enrollment_status().name, 'gpa': degree_tracker.get_gpa() if degree_tracker.get_gpa() is not None else 'None', 'credits': degree_tracker.current_credits, 'term_start': str(degree_tracker.term_started_time), 'current_day': str(degree_tracker.get_current_day_of_term())}
            university_data['accepted_degrees'] = get_accepted_degrees(sim_info, university_manager, degree_manager)
            university_data['not_yet_accepted_degrees'] = get_not_yet_accepted_degrees(sim_info, university_manager, degree_manager)
            university_data['completed_degrees'] = get_completed_degrees(sim_info, university_manager, degree_manager)
            university_data['previous_courses'] = get_previous_courses(sim_info)
            university_data['current_courses'] = get_current_courses(sim_info)
            university_view_data.append(university_data)
    return university_view_data
scholarship_schema = GsiGridSchema(label='Scholarships', sim_specific=True, auto_refresh=True)scholarship_schema.add_field('scholarship', label='Scholarship')scholarship_schema.add_field('status', label='Status')scholarship_schema.add_field('value', label='Value')
@GsiHandler('scholarship_schema', scholarship_schema)
def generate_scholarship_view_data(sim_id:int=None):
    sim_info = services.sim_info_manager().get(sim_id)
    snippet_manager = services.snippet_manager()
    if snippet_manager is None:
        return
    degree_tracker = sim_info.degree_tracker
    if degree_tracker is None:
        return
    scholarships_view_data = []

    def _process_scholarship_view_data(scholarships, status):
        scholarship_entries = []
        for scholarship_id in scholarships:
            scholarship_entry_data = {}
            scholarship = snippet_manager.get(scholarship_id)
            scholarship_entry_data['scholarship'] = str(scholarship)
            scholarship_entry_data['status'] = status
            scholarship_entry_data['value'] = str(scholarship.get_value(sim_info))
            scholarship_entries.append(scholarship_entry_data)
        return scholarship_entries

    accepted_scholarships_data = _process_scholarship_view_data(degree_tracker.get_accepted_scholarships(), str(ScholarshipStatus.ACCEPTED))
    if accepted_scholarships_data:
        scholarships_view_data.extend(accepted_scholarships_data)
    rejected_scholarships_data = _process_scholarship_view_data(degree_tracker.get_rejected_scholarships(), str(ScholarshipStatus.REJECTED))
    if rejected_scholarships_data:
        scholarships_view_data.extend(rejected_scholarships_data)
    pending_scholarships_data = _process_scholarship_view_data(degree_tracker.get_pending_scholarships(), str(ScholarshipStatus.PENDING))
    if pending_scholarships_data:
        scholarships_view_data.extend(pending_scholarships_data)
    active_scholarships_data = _process_scholarship_view_data(degree_tracker.get_active_scholarships(), str(ScholarshipStatus.ACTIVE))
    if active_scholarships_data:
        scholarships_view_data.extend(active_scholarships_data)
    return scholarships_view_data
