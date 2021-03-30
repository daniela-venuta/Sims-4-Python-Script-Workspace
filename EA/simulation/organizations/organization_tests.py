from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeSimfrom organizations.organization_enums import OrganizationStatusEnumfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableList, TunableEnumEntry, Tunable, TunableReferenceimport servicesimport sims4
class OrganizationMembershipTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'organizations': TunableList(description="\n            The organization(s) against which to test the Sim's membership. If\n            any in the list do not pass, the test will return False.\n            ", tunable=TunableReference(description='\n                An organization against which to test membership status.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='Organization', pack_safe=True)), 'membership_status': TunableEnumEntry(description='\n            The status of the Sim in the organization(s).\n            ', tunable_type=OrganizationStatusEnum, default=OrganizationStatusEnum.ACTIVE), 'invert': Tunable(description='\n            If checked, test will pass if all subjects do NOT qualify.\n            ', tunable_type=bool, default=False), 'subject': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor)}

    def is_valid(self, sim_info, status, organizations):
        organization_tracker = sim_info.organization_tracker
        if organization_tracker is None:
            return False
        filtered_organizations = organization_tracker.get_organizations_by_membership_status(status)
        for organization in organizations:
            if organization not in filtered_organizations:
                return False
        return True

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets, targets=None, tooltip=None):
        if len(self.organizations) < 1:
            if not self.invert:
                return TestResult(False, 'No tuned organizations exist, {0} fail(s) membership test', test_targets, tooltip=tooltip)
            return TestResult.TRUE
        org_ids = [organization.guid64 for organization in self.organizations]
        for target in test_targets:
            if self.is_valid(target, self.membership_status, org_ids):
                if self.invert:
                    return TestResult(False, "{0} passes membership but shouldn't.", target, tooltip=tooltip)
                    if not self.invert:
                        return TestResult(False, "{0} doesn't pass membership but should.", target, tooltip=tooltip)
            elif not self.invert:
                return TestResult(False, "{0} doesn't pass membership but should.", target, tooltip=tooltip)
        return TestResult.TRUE
