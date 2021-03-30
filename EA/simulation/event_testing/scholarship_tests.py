from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom interactions import ParticipantTypeActorTargetSimfrom sims.university.university_scholarship_enums import ScholarshipStatusfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableEnumEntry, Tunable, TunableVariant, TunablePackSafeReferencefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport servicesimport sims4
class ScholarshipStatusTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    class _SpecificScholarships(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'_scholarships': TunableWhiteBlackList(description='\n                Scholarships against which to test against application status.\n                ', tunable=TunablePackSafeReference(description='\n                    The scholarship instance to check.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET))), '_status': TunableEnumEntry(description='\n                Status of the scholarship(s).\n                ', tunable_type=ScholarshipStatus, default=ScholarshipStatus.ACCEPTED)}

        def is_valid_scholarship(self, sim_info, tooltip=None):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, '{} has no degree tracker.', sim_info, tooltip=tooltip)

            def _scholarship_container_helper(scholarships_of_status, sim_info, tooltip):
                snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
                scholarship_insts_of_status = [snippet_manager.get(scholarship) for scholarship in scholarships_of_status]
                if not self._scholarships.test_collection(scholarship_insts_of_status):
                    return TestResult(False, "{0}'s scholarships do not match the tuned whitelist/blacklist.", sim_info, tooltip=tooltip)
                return TestResult.TRUE

            if self._status == ScholarshipStatus.ACTIVE:
                return _scholarship_container_helper(degree_tracker.get_active_scholarships(), sim_info, tooltip)
            if self._status == ScholarshipStatus.REJECTED:
                return _scholarship_container_helper(degree_tracker.get_rejected_scholarships(), sim_info, tooltip)
            if self._status == ScholarshipStatus.ACCEPTED:
                return _scholarship_container_helper(degree_tracker.get_accepted_scholarships(), sim_info, tooltip)
            if self._status == ScholarshipStatus.PENDING:
                return _scholarship_container_helper(degree_tracker.get_pending_scholarships(), sim_info, tooltip)
            return TestResult.TRUE

    class _AnyScholarship(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'_status': TunableEnumEntry(description='\n                Status of the scholarship(s).\n                ', tunable_type=ScholarshipStatus, default=ScholarshipStatus.ACCEPTED), 'negate': Tunable(description='\n                If checked then we will negate the results of this test.\n                ', tunable_type=bool, default=False)}

        def is_valid_scholarship(self, sim_info, tooltip=None):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                return TestResult(False, '{} has no degree tracker.', sim_info, tooltip=tooltip)
            if self._status == ScholarshipStatus.ACTIVE:
                if not degree_tracker.get_active_scholarships():
                    if self.negate:
                        return TestResult.TRUE
                    return TestResult(False, '{} has no active scholarships', sim_info, tooltip=tooltip)
            elif self._status == ScholarshipStatus.REJECTED:
                if not degree_tracker.get_rejected_scholarships():
                    if self.negate:
                        return TestResult.TRUE
                    return TestResult(False, '{} has no rejected scholarships', sim_info, tooltip=tooltip)
            elif self._status == ScholarshipStatus.ACCEPTED:
                if not degree_tracker.get_accepted_scholarships():
                    if self.negate:
                        return TestResult.TRUE
                    return TestResult(False, '{} has no accepted scholarships', sim_info, tooltip=tooltip)
            elif self._status == ScholarshipStatus.PENDING and not degree_tracker.get_pending_scholarships():
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, '{} has no pending scholarships', sim_info, tooltip=tooltip)
            if self.negate:
                return TestResult(False, "{}'s scholarships are of                                        status ({}), and cannot  be.", sim_info, self._status, tooltip=tooltip)
            return TestResult.TRUE

    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The Sim against which to test scholarship status.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.TargetSim), 'test': TunableVariant(description='\n            The test used to check scholarship status.\n            ', specific_scholarship=_SpecificScholarships.TunableFactory(), any_scholarship=_AnyScholarship.TunableFactory(), default='specific_scholarship')}

    def get_expected_args(self):
        return {'targets': self.target}

    def __call__(self, targets):
        for target in targets:
            result = self.test.is_valid_scholarship(target, tooltip=self.tooltip)
            if not result:
                return result
        return TestResult.TRUE
