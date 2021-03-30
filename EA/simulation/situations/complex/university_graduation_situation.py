from sims.university.university_enums import EnrollmentStatusfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import BouncerRequestfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, CommonSituationState, CommonInteractionStartedSituationStateimport servicesimport sims4logger = sims4.log.Logger('University Graduation Situation', default_owner='madang')
class _GatherState(CommonInteractionStartedSituationState):

    def on_activate(self, reader=None):
        logger.debug('The graduating Sims are gathering for the graduation ceremony.')
        super().on_activate(reader)

    def timer_expired(self):
        self._change_state(self.owner.ceremony_state())

    def _on_interaction_of_interest_started(self):
        self._change_state(self.owner.ceremony_state())

class _CeremonyState(CommonSituationState):

    def on_activate(self, reader=None):
        logger.debug('The graduation ceremony has started.')
        super().on_activate(reader)

    def timer_expired(self):
        self._change_state(self.owner.celebration_state())

class _CelebrationState(CommonSituationState):

    def on_activate(self, reader=None):
        logger.debug('The Sims have completed the graduation ceremony and are now celebrating.')
        super().on_activate(reader)

class UniversityGraduationSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'gather_state': _GatherState.TunableFactory(description='\n            The gather state for the graduation situation, where the graduating \n            Sims gather at the sports arena shell. \n            ', display_name='1. Gather State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'ceremony_state': _CeremonyState.TunableFactory(description='\n            The ceremony state for the graduation situation, where the Sims\n            rabbithole into the sports arena shell.\n            ', display_name='2. Ceremony State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'celebration_state': _CelebrationState.TunableFactory(description='\n            The post-ceremony state for the graduation situation.  The Sims \n            should exit the sports arena rabbithole, and then perform the \n            cap throw interaction.\n            ', display_name='3. Celebration State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'household_member_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for a household member who is also \n            graduating from the same university.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.SITUATION_SCORING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GatherState, factory=cls.gather_state), SituationStateData(2, _CeremonyState, factory=cls.ceremony_state), SituationStateData(3, _CelebrationState, factory=cls.celebration_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.gather_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def _issue_requests(self):
        super()._issue_requests()
        host_sim_info = self._guest_list.host_sim_info
        host_university = host_sim_info.degree_tracker.get_university()
        for sim_info in services.active_household().sim_info_gen():
            degree_tracker = sim_info.degree_tracker
            if sim_info.id != host_sim_info.id and degree_tracker.get_university() == host_university and degree_tracker.get_enrollment_status() == EnrollmentStatus.GRADUATED:
                request = BouncerRequest(self, callback_data=_RequestUserData(), job_type=self.household_member_job_and_role_state.job, request_priority=BouncerRequestPriority.EVENT_VIP, user_facing=self.is_user_facing, exclusivity=self.exclusivity, requested_sim_id=sim_info.id, spawning_option=RequestSpawningOption.DONT_CARE)
                self.manager.bouncer.submit_request(request)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.gather_state())
