import randomfrom protocolbuffers import SimObjectAttributes_pb2, DistributorOps_pb2from aspirations.timed_aspiration import AspirationOrganizationTaskData, TaskDataOrgInfofrom date_and_time import DateAndTimefrom display_snippet_tuning import Organizationfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom organizations.organization_enums import OrganizationStatusEnumfrom organizations.organization_ops import SendOrganizationUpdateOpfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.tuning.tunable import TunableRangefrom sims4.utils import staticpropertyimport servicesimport sims4ACTIVE = OrganizationStatusEnum.ACTIVENONMEMBER = OrganizationStatusEnum.NONMEMBERINACTIVE = OrganizationStatusEnum.INACTIVElogger = sims4.log.Logger('OrganizationTracker', default_owner='shipark')
class OrganizationTracker(SimInfoTracker):
    ACTIVE_TASK_AMOUNT = TunableRange(description='\n        Number of active tasks an organization member has assigned at a time.\n        ', tunable_type=int, default=3, minimum=0)
    _ALL_ORGANIZATION_IDS = None

    @staticproperty
    def ALL_ORGANIZATION_IDS():
        if OrganizationTracker._ALL_ORGANIZATION_IDS is None:
            OrganizationTracker._ALL_ORGANIZATION_IDS = [org.guid64 for org in services.snippet_manager().get_ordered_types(only_subclasses_of=Organization)]
        return OrganizationTracker._ALL_ORGANIZATION_IDS

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._organization_status = {}
        self._organization_active_tasks = {}
        self._completed_tasks = []
        self._unenrolled_org_ids = []

    def send_organization_update_message(self, update_type, org_id):
        degree_tracker = self._sim_info.degree_tracker
        if degree_tracker is None:
            return
        send_organization_update_op = SendOrganizationUpdateOp(update_type, org_id, self.get_task_objective_ids(org_id), degree_tracker.is_current_student())
        distributor = Distributor.instance()
        distributor.add_op(self._sim_info, send_organization_update_op)

    def get_task_objective_ids(self, org_id):
        objective_ids = []
        active_tasks = self.get_active_tasks(org_id)
        for active_task in active_tasks.values():
            objective_ids.extend([objective.guid64 for objective in active_task.task.objectives])
        return objective_ids

    def add_active_task(self, task_data_org_info):
        active_tasks = self._organization_active_tasks.get(task_data_org_info.org_id)
        if active_tasks:
            self._organization_active_tasks[task_data_org_info.org_id][task_data_org_info.task] = task_data_org_info
        else:
            self._organization_active_tasks[task_data_org_info.org_id] = {task_data_org_info.task: task_data_org_info}

    def save(self):
        data = SimObjectAttributes_pb2.PersistableOrganizationTracker()
        for (org_id, status) in self._organization_status.items():
            with ProtocolBufferRollback(data.org_status_map) as org_status_info:
                org_status_info.org_id = org_id
                org_status_info.membership_status = status
        for (org_id, active_task_map) in self._organization_active_tasks.items():
            with ProtocolBufferRollback(data.tasks_map) as org_active_tasks:
                org_active_tasks.org_id = org_id
                for timed_aspiration_data in active_task_map.values():
                    with ProtocolBufferRollback(org_active_tasks.active_tasks) as active_task_info:
                        active_task_info.aspiration = timed_aspiration_data.task.guid64
                        active_task_info.completed = timed_aspiration_data.completed
                        active_task_info.end_time = timed_aspiration_data.end_time.absolute_ticks()
        data.unenrolled_org_ids.extend(self._unenrolled_org_ids)
        return data

    def load(self, data=None):
        aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
        for org_status_info in data.org_status_map:
            self._organization_status[org_status_info.org_id] = org_status_info.membership_status
        for org_active_tasks in data.tasks_map:
            org_id = org_active_tasks.org_id
            self._organization_active_tasks[org_id] = {}
            for timed_aspiration_data in org_active_tasks.active_tasks:
                task = aspiration_manager.get(timed_aspiration_data.aspiration)
                if task is None:
                    pass
                else:
                    task_data_org_info = TaskDataOrgInfo(org_id=org_id, task=task, completed=timed_aspiration_data.completed, end_time=DateAndTime(timed_aspiration_data.end_time))
                    self.add_active_task(task_data_org_info)
                    if task_data_org_info.completed:
                        organization_task = AspirationOrganizationTaskData(None, task, org_id=org_id)
                        self._completed_tasks.append((organization_task, timed_aspiration_data))
        self._unenrolled_org_ids.extend(data.unenrolled_org_ids)

    def activate_organization_tasks(self):
        if not self._completed_tasks:
            return
        owner_aspiration_tracker = self._sim_info.aspiration_tracker
        if owner_aspiration_tracker is None:
            return
        for (task, task_data) in self._completed_tasks:
            task.set_tracker(owner_aspiration_tracker)
            loaded = task.load_alarm_data(task_data)
            if not loaded:
                logger.error("Organization Task ({}) was loaded to ({})'s Organization Tracker,                            but the end time alarm was not set up.", task, self._sim_info)
        self._completed_tasks.clear()

    def get_key_org(self, task):
        for (org, active_task_map) in self._organization_active_tasks.items():
            if task in active_task_map.keys():
                return org

    def get_active_tasks(self, org_id):
        active_task_set = self._organization_active_tasks.get(org_id, {})
        return active_task_set

    def get_organization_status(self, org_id):
        return self._organization_status.get(org_id)

    def _set_organization_status(self, organization_id, new_status):
        self._organization_status[organization_id] = new_status

    def _get_organization_tasks(self, org, amount):
        valid_tasks = []
        selected_tasks = []
        resolver = SingleSimResolver(self._sim_info)
        for task in org.organization_task_data:
            test_result = task.tests.run_tests(resolver)
            if test_result and task.organization_task not in self.get_active_tasks(org.guid64):
                valid_tasks.append(task)
        while valid_tasks and len(selected_tasks) < amount:
            random_choice = valid_tasks.pop(random.randint(0, len(valid_tasks) - 1)).organization_task
            selected_tasks.append(random_choice)
        if amount > len(selected_tasks):
            logger.warn('The amount of tasks found ({}) is less than the desired amount ({}). Check the task tuning for organization: {}.', len(selected_tasks), amount, str(org))
        return selected_tasks

    def _add_assignments_to_aspiration_tracker(self, org):
        owner_aspiration_tracker = self._sim_info.aspiration_tracker
        if owner_aspiration_tracker is None:
            return
        organization_tasks = self._get_organization_tasks(org, self.ACTIVE_TASK_AMOUNT)
        for task in organization_tasks:
            owner_aspiration_tracker.activate_timed_aspiration(task, org_id=org.guid64)
            aspiration_data = owner_aspiration_tracker.get_timed_aspiration_data(task)
            if aspiration_data is None:
                pass
            else:
                task_data_org_info = TaskDataOrgInfo(org_id=org.guid64, task=task, completed=False, end_time=aspiration_data.end_time)
                self.add_active_task(task_data_org_info)

    def _assign_organization_tasks(self, org, from_update=False):
        self._add_assignments_to_aspiration_tracker(org)
        if not from_update:
            self.send_organization_update_message(DistributorOps_pb2.OrganizationUpdate.ADD, org.guid64)
        else:
            self.send_organization_update_message(DistributorOps_pb2.OrganizationUpdate.UPDATE, org.guid64)

    def _assign_organizations_tasks_for_all_enrolled_orgs(self):
        snippet_manager = services.snippet_manager()
        for org_id in self.get_enrolled_organizations(enrolled_status=ACTIVE):
            org = snippet_manager.get(org_id)
            if org is None:
                pass
            else:
                self._add_assignments_to_aspiration_tracker(org)
                self.send_organization_update_message(DistributorOps_pb2.OrganizationUpdate.ADD, org.guid64)

    def update_stored_task(self, task_data_org_info):
        self._organization_active_tasks[task_data_org_info.org_id][task_data_org_info.task] = task_data_org_info

    def update_organization_task(self, task_data_org_info, timed_out=False):
        if timed_out:
            if self._organization_active_tasks.get(task_data_org_info.org_id) is None:
                return
            if self._organization_active_tasks.get(task_data_org_info.org_id).get(task_data_org_info.task) is None:
                return
            del self._organization_active_tasks[task_data_org_info.org_id][task_data_org_info.task]
        else:
            self.update_stored_task(task_data_org_info)
        if self._organization_active_tasks.get(task_data_org_info.org_id) or timed_out:
            snippet_manager = services.snippet_manager()
            if snippet_manager is None:
                return
            org = snippet_manager.get(task_data_org_info.org_id)
            self._assign_organization_tasks(org, from_update=True)

    def join_organization(self, organization_id):
        if self._organization_status.get(organization_id) == ACTIVE:
            return
        snippet_manager = services.snippet_manager()
        if snippet_manager is None:
            return
        organization_instance = snippet_manager.get(organization_id)
        progress_stat_type = organization_instance.progress_statistic
        tracker = self._sim_info.get_tracker(progress_stat_type)
        tracker.add_statistic(progress_stat_type)
        self._set_organization_status(organization_id, OrganizationStatusEnum.ACTIVE)
        if not self._sim_info.is_npc:
            self._assign_organization_tasks(organization_instance)

    def deactivate_organizations(self, university):
        valid_organization_ids = [organization.guid64 for organization in university.organizations]
        for (org_id, org_status) in self._organization_status.items():
            if org_status == ACTIVE and org_id in valid_organization_ids:
                self._unenrolled_org_ids.append(org_id)
                self.leave_organization(org_id)

    def reactivate_organizations(self, university):
        valid_organization_ids = [organization.guid64 for organization in university.organizations]
        if not self._unenrolled_org_ids:
            return
        for org_id in self._unenrolled_org_ids:
            if org_id in valid_organization_ids:
                self.join_organization(org_id)
        self._unenrolled_org_ids = []

    def leave_organization(self, organization_id):
        if self.get_organization_status(organization_id) != ACTIVE:
            return
        snippet_manager = services.snippet_manager()
        if snippet_manager is None:
            return
        progress_stat_type = snippet_manager.get(organization_id).progress_statistic
        tracker = self._sim_info.get_tracker(progress_stat_type)
        progress_stat = tracker.get_statistic(progress_stat_type)
        if progress_stat:
            tracker.set_value(progress_stat_type, progress_stat.points_to_current_rank())
        self._set_organization_status(organization_id, OrganizationStatusEnum.INACTIVE)
        aspiration_tracker = self._sim_info.aspiration_tracker
        if aspiration_tracker:
            for (task, task_data_org_info) in self.get_active_tasks(organization_id).items():
                if not task_data_org_info.completed:
                    aspiration_tracker.deactivate_timed_aspiration(task)
        if self._organization_active_tasks.get(organization_id):
            del self._organization_active_tasks[organization_id]
        self.send_organization_update_message(DistributorOps_pb2.OrganizationUpdate.REMOVE, organization_id)

    def get_organizations_by_membership_status(self, membership_status):
        enrolled_status = None if membership_status == NONMEMBER else membership_status
        filtered_enrolled_organizations = self.get_enrolled_organizations(enrolled_status=enrolled_status)
        if membership_status != NONMEMBER:
            return filtered_enrolled_organizations
        return [org for org in OrganizationTracker.ALL_ORGANIZATION_IDS if org not in filtered_enrolled_organizations]

    def get_enrolled_organizations(self, enrolled_status=None):
        if enrolled_status is None:
            return [org_id for (org_id, _) in self._organization_status.items()]
        return [org_id for (org_id, status) in self._organization_status.items() if status == enrolled_status]

    def on_zone_load(self):
        aspiration_tracker = self._sim_info.aspiration_tracker
        if aspiration_tracker is None:
            return
        org_ids = self.get_enrolled_organizations(enrolled_status=ACTIVE)
        for org in org_ids:
            active_tasks = self._organization_active_tasks.get(org, None)
            if active_tasks is None:
                pass
            else:
                for aspiration in active_tasks.keys():
                    aspiration.register_callbacks()
                    aspiration_tracker.process_test_events_for_aspiration(aspiration)

    def clean_up(self):
        organization_service = services.organization_service()
        for org_id in list(self._organization_status.keys()):
            organization_service.remove_organization_member(self._sim_info, org_id)
            del self._organization_status[org_id]
        self._completed_tasks.clear()

    def on_lod_update(self, old_lod, new_lod):
        if not self._organization_status:
            return
        if old_lod > new_lod and new_lod < SimInfoLODLevel.FULL:
            self._organization_active_tasks.clear()
            if new_lod == SimInfoLODLevel.MINIMUM:
                self.clean_up()
        if old_lod < SimInfoLODLevel.FULL and new_lod >= SimInfoLODLevel.FULL:
            self._assign_organizations_tasks_for_all_enrolled_orgs()
