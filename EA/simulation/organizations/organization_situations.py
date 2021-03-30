from _collections import defaultdictimport randomfrom filters.tunable import FilterTermVariantfrom open_street_director.festival_situations import BaseGenericFestivalSituation, CooldownFestivalSituationStatefrom services import sim_info_managerfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableInterval, TunableList, TunableReference, AutoFactoryInit, TunableMapping, TunableTuple, TunableEnumEntry, TunableRange, HasTunableSingletonFactoryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriority, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, SituationState, CommonSituationState, TunableSituationJobAndRolesfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationSerializationOption, SituationCallbackOption, SituationCreationUIOptionimport enumimport servicesimport sims4logger = sims4.log.Logger('OrganizationSituations', default_owner='shipark')
class OrganizationEventBase(SituationComplexCommon):
    INSTANCE_TUNABLES = {'organization': TunableReference(description="\n            The membership list of this organization fills in the situation's\n            jobs.\n            ", manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='Organization', tuning_group=GroupNames.SITUATION), 'number_of_members': TunableInterval(description='\n            The interval defines the range of number of members that need to \n            fill in the situation job.\n            ', tunable_type=int, default_lower=2, default_upper=3, minimum=1, tuning_group=GroupNames.SITUATION), 'additional_filters': TunableList(tunable=FilterTermVariant(description='\n            Additional filters to be applied to the members request.\n            \n            If the existing members pool does not include sims that pass these\n            filters, the org service will attempt to populate the list with\n            more members that satisfy these filters.\n            '), tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classproperty
    def always_elevated_importance(cls):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    def submit_replace_request(self, sim, request, job_type):
        self._on_remove_sim_from_situation(sim)
        blacklist_sims = [sim.id]
        blacklist_sims.extend(sim_info.id for sim_info in services.sim_info_manager().get_all() if sim_info.is_player_sim)
        blacklist_sims.extend(sim.id for sim in self._situation_sims)
        organization_member = services.organization_service().generate_organization_members(self.organization.guid64, amount=1, blacklist_sims=blacklist_sims, additional_filter_terms=self.additional_filters)
        guest_info = SituationGuestInfo(organization_member[0], job_type, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH)
        new_request = self._create_request_from_guest_info(guest_info)
        if new_request is not None:
            self.manager.bouncer.submit_request(new_request)

    @classmethod
    def get_members_sim_infos(cls, blacklist_sims=None):
        hh_sims = tuple(sim_info.id for sim_info in services.sim_info_manager().get_all() if sim_info.is_player_sim)
        members_sim_ids = services.organization_service().generate_organization_members(cls.organization.guid64, amount=cls.number_of_members.upper_bound, blacklist_sims=hh_sims, additional_filter_terms=cls.additional_filters, minimum=cls.number_of_members.lower_bound)
        if not members_sim_ids:
            logger.error('Situation ({}) failed to populate the situation job with members from organization ({}).', str(cls), str(cls.organization))
        return members_sim_ids
lock_instance_tunables(OrganizationEventBase, exclusivity=BouncerExclusivityCategory.FESTIVAL_GOER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class OrganizationMemberSingleJobSituation(OrganizationEventBase):
    INSTANCE_TUNABLES = {'job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role that a member will be used to fill in.\n            ', tuning_group=GroupNames.SITUATION)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, SituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role_state.job, cls.job_and_role_state.role_state)]

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        members_sim_ids = cls.get_members_sim_infos()
        for member_sim_id in members_sim_ids:
            guest_list.add_guest_info(SituationGuestInfo(member_sim_id, cls.job_and_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH))
        return guest_list

    @classmethod
    def default_job(cls):
        return cls.job_and_role_state.job

    def start_situation(self):
        super().start_situation()
        self._change_state(SituationState())

class SubSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'sub_situation': Situation.TunableReference(description='\n            Sub-situation to run within this situation state. When the sub-situation\n            ends, the owning situation state will end.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, class_restrictions='SituationSimple')}

    def __init__(self, sub_situation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sub_situation = sub_situation
        self._sub_situation_id = None

    def start_situation(self):
        if self._sub_situation_id is None:
            sub_situation_id = self.owner.manager.create_situation(self.sub_situation)
            self._sub_situation_id = sub_situation_id
        if self._sub_situation_id is not None:
            self.owner.manager.register_for_callback(self._sub_situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_sub_situation_end_callback)
            self.owner.manager.disable_save_to_situation_manager(self._sub_situation_id)

    def on_activate(self, *args, **kwargs):
        super().on_activate(*args, **kwargs)
        self.start_situation()

    def _on_sub_situation_end_callback(self, sub_situation_id, situation_callback_option, data):
        if sub_situation_id == self._sub_situation_id:
            self._sub_situation_id = None
            self._on_sub_situation_end(sub_situation_id)

    def on_deactivate(self, *args, **kwargs):
        super().on_deactivate(*args, **kwargs)
        if self._sub_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(self._sub_situation_id)

    def _on_sub_situation_end(self, sub_situation_id):
        raise NotImplementedError

class ReUseType(enum.Int):
    SAME_SIM = 0
    DIFFERENT_SIM = 1

class JobAssignedSubSituationState(SubSituationState):
    FACTORY_TUNABLES = {'job_mapping': TunableMapping(description="\n            A mapping between sub-situation job and the owner situation job.\n            When creating the guest list for the sub-situation, job pairings will\n            inform which Sim is pulled in to fill the sub-situation's job. \n            ", key_type=TunableReference(description='\n                A job created for the sub-situation.\n                ', manager=services.situation_job_manager()), key_name='Sub Situation Job', value_type=TunableTuple(reuse_type=TunableEnumEntry(description='\n                    Rule to determine how the sub-situation job should be filled\n                    on next creation.\n                    \n                    If Same, then on repeated iterations of the sub-situation, its job will\n                    be filled by the sim that had filled it in the past iterations.\n                    \n                    If Different, then on repeated iterations of the sub-situation, its job\n                    will be filled by a sim other than those that filled it in past iterations.\n                    ', tunable_type=ReUseType, default=ReUseType.SAME_SIM), job=TunableReference(description="\n                    A job from the owner situation. Sims with this job will be\n                    used as a source for the sub-situation's job.\n                    ", manager=services.situation_job_manager())), value_name='Sub Situation Job Constraint', minlength=1)}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.sub_situation.default_job not in cls.job_mapping.values():
            logger.error("Sub-situation ({})'s default job ({}) is not in the situation's job constraint mapping. The sub-situation will not be created.", str(cls.sub_situation), str(cls.sub_situation.default_job))

    def __init__(self, job_mapping, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_mapping = job_mapping
        self._used_sims = defaultdict(list)

    def _filter_guest_with_constraint(self, sub_sit_job, job_constraint, filtered_guests):
        guests_had_job = self._used_sims.get(sub_sit_job, [])
        if not guests_had_job:
            return random.choice(filtered_guests)
        if job_constraint == ReUseType.DIFFERENT_SIM:
            valid_guests = [filtered_guest for filtered_guest in filtered_guests if filtered_guest not in guests_had_job]
            if len(valid_guests) < 1:
                owner_guest = random.choice(guests_had_job)
                self._used_sims[sub_sit_job].clear()
                return owner_guest
            return random.choice(valid_guests)
        if job_constraint == ReUseType.SAME_SIM:
            return random.choice(guests_had_job)
        logger.error('Tuned ReUse Type ({}) is not handled. No Sim for sub-situation job ({}) was found.', str(job_constraint), str(sub_sit_job))

    def get_guest_by_job_constraint(self, sub_sit_job, job_constraint_info, owner_guests):
        owner_guests_with_job = [guest_info.sim_id for guest_info in owner_guests._job_type_to_guest_infos.get(job_constraint_info.job)]
        if not owner_guests_with_job:
            logger.error('No guests of owning situation ({}) were found to have the job ({}) of the sub-situation ({}) job constraint.', str(self.owner), str(job_constraint_info.job), str(self.sub_situation))
            return
        return self._filter_guest_with_constraint(sub_sit_job, job_constraint_info.reuse_type, owner_guests_with_job)

    def get_guest_list(self):
        owner_guests = self.owner.guest_list
        jobs = self.sub_situation.get_tuned_jobs()
        guest_list = SituationGuestList(invite_only=True)
        for job in jobs:
            job_constraint_info = self.job_mapping.get(job)
            if job_constraint_info is None:
                logger.error("Failed to find job mapping constraint for sub-situation's default job ({}). Tune ({}) constraint in Activity State.", str(job), str(job))
                return
            owner_guest_id = self.get_guest_by_job_constraint(job, job_constraint_info, owner_guests)
            if owner_guest_id is None:
                logger.error('Failed to find guest for situation ({}). Situation will not run.', str(self.sub_situation))
                return
            guest_list.add_guest_info(SituationGuestInfo(owner_guest_id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
            self._used_sims[job].append(owner_guest_id)
        return guest_list

    def start_situation(self):
        guest_list = self.get_guest_list()
        if guest_list is None:
            logger.error('Failed to start sub-situation. Transitioning to next phase ({}).', str(self.owner.end_state))
            self._on_sub_situation_end()
        self._sub_situation_id = services.get_zone_situation_manager().create_situation(self.sub_situation, guest_list=guest_list, user_facing=False)
        super().start_situation()

class LoopingJobAssignedSubSituationState(JobAssignedSubSituationState):
    FACTORY_TUNABLES = {'situation_iterations': TunableRange(description='\n            Number of iterations for which the sub-situation is created within\n            the owning situation state.\n            ', tunable_type=int, default=3, minimum=1)}

    def __init__(self, situation_iterations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.situation_iterations = situation_iterations
        self._count = 0

    def _on_sub_situation_end(self, sub_situation_id):
        if self.owner is None:
            return
        if self._count >= self.situation_iterations - 1:
            self._change_state(self.owner.end_state())
        else:
            self._count += 1
            self.start_situation()

class GatherEventSituationState(CommonSituationState):

    def timer_expired(self):
        if isinstance(self.owner, MajorOrganizationEvent) or isinstance(self.owner, MembershipSmartMajorOrganizationEvent):
            self._change_state(self.owner.activity_state())
        else:
            self.put_on_cooldown()

class ArtPhaseSituationState(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.party_phase())

class PartyPhaseSituationState(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.end_state())

class ActivityEventSituationState(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.end_state())

class ActivityLoopingSmartSituationState(LoopingJobAssignedSubSituationState):

    def timer_expired(self):
        self._change_state(self.owner.end_state())

class EndEventSituationState(CommonSituationState):
    pass

class OrgMemberJobAndRoles(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'org_member_jobs_and_roles': TunableMapping(description="\n            A mapping between a situation's jobs and default role states.\n            ", key_type=TunableReference(description='\n                A job created for this situation.\n                ', manager=services.situation_job_manager()), key_name='Member Situation Job', value_type=TunableTuple(role=TunableReference(description='\n                    The role state that the sim of this job starts the situation with.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), organization=TunableReference(description="\n                    The membership list of this organization fills in the situation's\n                    jobs.\n                    ", manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='Organization', tuning_group=GroupNames.SITUATION), number_of_members=TunableInterval(description='\n                    The interval defines the range of number of members that need to \n                    fill in the situation job.\n                    ', tunable_type=int, default_lower=2, default_upper=3, minimum=1, tuning_group=GroupNames.SITUATION), additional_filters=TunableList(tunable=FilterTermVariant(description='\n                    Additional filters to be applied to the members request.\n                    \n                    If the existing members pool does not include sims that pass these\n                    filters, the org service will attempt to populate the list with\n                    more members that satisfy these filters.\n                    '), tuning_group=GroupNames.SITUATION)), value_name='Member Role State and Organization Info')}

class FestivalOrganizationEventType(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'gather_state': GatherEventSituationState.TunableFactory(description='\n            The first state that the Sims will be put into when this Situation\n            Starts.\n            ', locked_args={'allow_join_situation': True}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='1. Gather State'), 'member_job_and_role_states': OrgMemberJobAndRoles.TunableFactory(description='\n            The jobs and roles that an org member will be used to fill in.\n            ', tuning_group=GroupNames.SITUATION), 'non_member_job_and_role_states': TunableSituationJobAndRoles.TunableFactory(description='\n            The jobs and roles filled by sims outside of the organization.\n            \n            Ensure the filters of these jobs include a filter term to exclude \n            organization members.\n            ', tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def default_job(cls):
        return cls.non_member_job_and_role_states.jobs_and_roles.keys()[0]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        tuned_jobs_and_roles = []
        for (job, member_info) in cls.member_job_and_role_states.org_member_jobs_and_roles.items():
            tuned_jobs_and_roles.append((job, member_info.role))
        for (job, role_info) in cls.non_member_job_and_role_states.jobs_and_roles.items():
            tuned_jobs_and_roles.append((job, role_info.role))
        return tuned_jobs_and_roles

    @classmethod
    def get_members_sim_infos(cls, job, member_info, blacklist_sims=None):
        hh_sims = tuple(sim_info.id for sim_info in services.sim_info_manager().get_all() if sim_info.is_player_sim)
        if blacklist_sims is not None:
            blacklist_sims.extend(hh_sims)
        else:
            blacklist_sims = hh_sims
        members_sim_ids = services.organization_service().generate_organization_members(member_info.organization.guid64, amount=member_info.number_of_members.upper_bound, blacklist_sims=blacklist_sims, additional_filter_terms=member_info.additional_filters, minimum=member_info.number_of_members.lower_bound)
        if not members_sim_ids:
            logger.error('Situation ({}) failed to populate the situation job ({}) with members from organization ({}).', str(cls), str(job), str(cls.organization))
        return members_sim_ids

    @classmethod
    def is_job_type_org_member(cls, job_type):
        return job_type in cls.member_job_and_role_states.org_member_jobs_and_roles

    def submit_replace_request(self, sim, request, job_type):
        self._on_remove_sim_from_situation(sim)
        if not self.is_job_type_org_member(job_type):
            new_request = request.clone_for_replace()
            if new_request is not None:
                self.manager.bouncer.submit_request(new_request)
            return
        organization = self.member_job_and_role_states.org_member_jobs_and_roles.get(job_type).organization
        blacklist_sims = [sim.id]
        blacklist_sims.extend(sim_info.id for sim_info in services.sim_info_manager().get_all() if sim_info.is_player_sim)
        blacklist_sims.extend(sim.id for sim in self._situation_sims)
        additional_filter_terms = self.member_job_and_role_states.org_member_jobs_and_roles.get(job_type).additional_filters
        organization_member = services.organization_service().generate_organization_members(organization.guid64, amount=1, blacklist_sims=blacklist_sims, additional_filter_terms=additional_filter_terms)
        guest_info = SituationGuestInfo(organization_member[0], job_type, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH)
        new_request = self._create_request_from_guest_info(guest_info)
        if new_request is not None:
            self.manager.bouncer.submit_request(new_request)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.gather_state())

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GatherEventSituationState, factory=cls.gather_state), SituationStateData(2, CooldownFestivalSituationState, factory=cls.cooldown_state))

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        grabbed_members = []
        for (job, member_info) in cls.member_job_and_role_states.org_member_jobs_and_roles.items():
            members_sim_ids = cls.get_members_sim_infos(job, member_info, blacklist_sims=grabbed_members)
            grabbed_members.extend(members_sim_ids)
            for member_sim_id in members_sim_ids:
                guest_list.add_guest_info(SituationGuestInfo(member_sim_id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH))
        filter_service = services.sim_filter_service()
        grabbed_non_members = []
        for (job, role_info) in cls.non_member_job_and_role_states.jobs_and_roles.items():
            non_member_ids = filter_service.submit_matching_filter(sim_filter=job.filter, number_of_sims_to_find=role_info.number_of_sims_to_find, allow_yielding=False, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, gsi_source_fn=lambda : 'OrganizationSituations: Add non member sims to situation guest list based on {}'.format(str(job)))
            grabbed_non_members.extend(non_member_ids)
            for non_member_result in non_member_ids:
                guest_list.add_guest_info(SituationGuestInfo(non_member_result.sim_info.id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH))
        return guest_list

class MajorOrganizationEvent(FestivalOrganizationEventType):
    INSTANCE_TUNABLES = {'activity_state': ActivityEventSituationState.TunableFactory(description='\n            The second state that this situation will be put into once the\n            gather state ends.\n            ', locked_args={'allow_join_situation': False}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='2. Activity State'), 'end_state': EndEventSituationState.TunableFactory(description='\n            The third state that this situation will be put into once the activity\n            state ends.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='3. End State')}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GatherEventSituationState, factory=cls.gather_state), SituationStateData(2, ActivityEventSituationState, factory=cls.activity_state), SituationStateData(3, EndEventSituationState, factory=cls.end_state), SituationStateData(4, CooldownFestivalSituationState, factory=cls.cooldown_state))

class CreativityCelebrationEvent(FestivalOrganizationEventType):
    INSTANCE_TUNABLES = {'art_phase': ArtPhaseSituationState.TunableFactory(description='\n            The second state that this situation will be put into once the\n            gather state ends.\n            ', locked_args={'allow_join_situation': True}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='2. Art Phase'), 'party_phase': PartyPhaseSituationState.TunableFactory(description='\n            The third state that this situation will be put into once the first\n            activity state ends.\n            ', locked_args={'allow_join_situation': False}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='3. Party Phase'), 'end_state': EndEventSituationState.TunableFactory(description='\n            The fourth state this situation will be put into once the activity\n            states end.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='4. End State')}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GatherEventSituationState, factory=cls.gather_state), SituationStateData(2, ArtPhaseSituationState, factory=cls.art_phase), SituationStateData(3, PartyPhaseSituationState, factory=cls.party_phase), SituationStateData(4, EndEventSituationState, factory=cls.end_state), SituationStateData(5, CooldownFestivalSituationState, factory=cls.cooldown_state))

class MembershipSmartMajorOrganizationEvent(FestivalOrganizationEventType):
    INSTANCE_TUNABLES = {'activity_state': ActivityLoopingSmartSituationState.TunableFactory(description='\n            The second state that this situation will be put into once the\n            gather state ends.\n            ', locked_args={'allow_join_situation': False}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='2. Activity State'), 'end_state': EndEventSituationState.TunableFactory(description='\n            The third state that this situation will be put into once the activity\n            state ends.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='3. End State')}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GatherEventSituationState, factory=cls.gather_state), SituationStateData(2, ActivityLoopingSmartSituationState, factory=cls.activity_state), SituationStateData(3, EndEventSituationState, factory=cls.end_state), SituationStateData(4, CooldownFestivalSituationState, factory=cls.cooldown_state))
