from display_snippet_tuning import Organizationfrom organizations.organization_enums import OrganizationStatusEnumfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesorganization_schema = GsiGridSchema(label='Organizations', auto_refresh=False)organization_schema.add_field('organization', label='Organization')with organization_schema.add_has_many('active_members', GsiGridSchema, label='Active Members') as sub_schema:
    sub_schema.add_field('sim', label='Sim')
    sub_schema.add_field('progress', label='Progress')
    sub_schema.add_field('rank', label='Rank')with organization_schema.add_has_many('inactive_members', GsiGridSchema, label='Inactive Members') as sub_schema:
    sub_schema.add_field('sim', label='Sim')
    sub_schema.add_field('progress', label='Progress')
    sub_schema.add_field('rank', label='Rank')
def get_organization_members(org_id, status_enum):
    organization_member_data = []
    organization_service = services.organization_service()
    if organization_service is None:
        return organization_member_data
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return
    snippet_manager = services.snippet_manager()
    if snippet_manager is None:
        return
    progress_stat_type = snippet_manager.get(org_id).progress_statistic
    members_list = organization_service.get_organization_members(org_id)
    for member_id in members_list:
        sim_info = sim_info_manager.get(member_id)
        organization_tracker = sim_info.organization_tracker
        if organization_tracker is None:
            pass
        elif organization_tracker.get_organization_status(org_id) != status_enum:
            pass
        else:
            tracker = sim_info.get_tracker(progress_stat_type)
            progress_stat = tracker.get_statistic(progress_stat_type)
            organization_member_data.append({'sim': sim_info.full_name, 'progress': progress_stat.get_value(), 'rank': progress_stat.rank_level})
    return organization_member_data

@GsiHandler('organization_view', organization_schema)
def generate_organization_view():
    organizations = []
    for org in services.snippet_manager().get_ordered_types(only_subclasses_of=Organization):
        organizations.append({'organization': str(org), 'active_members': get_organization_members(org.guid64, OrganizationStatusEnum.ACTIVE), 'inactive_members': get_organization_members(org.guid64, OrganizationStatusEnum.INACTIVE)})
    return organizations
organization_task_schema = GsiGridSchema(label='Organization Tasks', sim_specific=True, auto_refresh=False)organization_task_schema.add_field('organization', label='Organization')with organization_task_schema.add_has_many('active_tasks', GsiGridSchema, label='Active Tasks') as sub_schema:
    sub_schema.add_field('task', label='Task')
    sub_schema.add_field('completed', label='Completed')
    sub_schema.add_field('end_time', label='End Time')
@GsiHandler('organization_task_view', organization_task_schema)
def generate_aspiration_view_data(sim_id:int=None):
    sim_info = services.sim_info_manager().get(sim_id)
    snippet_manager = services.snippet_manager()
    if snippet_manager is None:
        return
    all_orgs = []
    if sim_info.organization_tracker is None:
        return all_orgs
    enrolled_orgs = sim_info.organization_tracker.get_enrolled_organizations(OrganizationStatusEnum.ACTIVE)
    for org_id in enrolled_orgs:
        org_data = {}
        organization_instance = snippet_manager.get(org_id)
        org_data['organization'] = str(organization_instance)
        active_tasks = sim_info.organization_tracker.get_active_tasks(org_id)
        tasks = []
        for task_data_org_info in active_tasks.values():
            task_data = {}
            task_data['task'] = str(task_data_org_info.task)
            task_data['completed'] = str(task_data_org_info.completed)
            task_data['end_time'] = str(task_data_org_info.end_time)
            tasks.append(task_data)
        org_data['active_tasks'] = tasks
        all_orgs.append(org_data)
    return all_orgs
