from civic_policies.base_civic_policy_tests import BaseCivicPolicyTestimport servicesfrom civic_policies.street_civic_policy_tuning import StreetCivicPolicySelectorMixin
class StreetCivicPolicySelectorTestMixin(StreetCivicPolicySelectorMixin):

    def get_expected_args(self):
        if self.street is None or hasattr(self.street, 'civic_policy'):
            return {}
        return self.street.get_expected_args()

    def get_custom_event_registration_keys(self):
        if self.street is None or not hasattr(self.street, 'civic_policy'):
            return ()
        keys = []
        for test in self.civic_policy_tests:
            custom_keys = test.get_custom_event_keys(self.street)
            if not custom_keys:
                pass
            else:
                keys.extend(custom_keys)
        return keys

class StreetCivicPolicyTest(StreetCivicPolicySelectorTestMixin, BaseCivicPolicyTest):
    pass
