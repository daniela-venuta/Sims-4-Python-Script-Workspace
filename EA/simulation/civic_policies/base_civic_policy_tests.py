from date_and_time import TimeSpan, create_time_spanfrom event_testing.test_events import TestEventfrom sims4.tuning.tunable import AutoFactoryInit, TunableReference, Tunable, HasTunableSingletonFactory, TunableList, TunableVariant, TunableThreshold, TunableEnumEntryimport sims4from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom tunable_time import TunableTimeSpanfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport services
class BaseCivicPolicyTestBWList(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'white_black_list': TunableWhiteBlackList(description='\n            The civic policies must pass the whitelist and blacklist\n            to pass the test.\n            ', tunable=TunableReference(description='\n                Allowed and disallowed civic policies.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('BaseCivicPolicy',), pack_safe=True))}

    def get_custom_event_keys(self, provider_owner):
        return []

    def get_civic_policy_tuning_test_list(self, provider):
        raise NotImplementedError

    def run_test(self, provider, tooltip):
        civic_policies = () if provider is None else self.get_civic_policy_tuning_test_list(provider)
        if not self.white_black_list.test_collection(civic_policies):
            return TestResult(False, 'Civic Policy Provider failed enacted white or black list {}', civic_policies, tooltip=tooltip)
        return TestResult.TRUE

class BaseCivicPolicyTestEnacted(BaseCivicPolicyTestBWList):

    def get_custom_event_keys(self, provider_owner):
        keys = []
        for policy in self.white_black_list.get_items():
            keys.append((TestEvent.CivicPoliciesChanged, (provider_owner, policy)))
        return keys

    def get_civic_policy_tuning_test_list(self, provider):
        return provider.get_enacted_policies(tuning=True)

class BaseCivicPolicyTestBalloted(BaseCivicPolicyTestBWList):

    def get_civic_policy_tuning_test_list(self, provider):
        return provider.get_balloted_policies(tuning=True)

class BaseCivicPolicyTestRepealable(BaseCivicPolicyTestBWList):

    def get_custom_event_keys(self, provider_owner):
        keys = []
        for policy in self.white_black_list.get_items:
            keys.append((TestEvent.CivicPoliciesChanged, (provider_owner, policy)))
        return keys

    def get_civic_policy_tuning_test_list(self, provider):
        return provider.get_up_for_repeal_policies(tuning=True)

class BaseCivicPolicyTestDormant(BaseCivicPolicyTestBWList):

    def get_civic_policy_tuning_test_list(self, provider):
        return provider.get_dormant_policies(tuning=True)

class BaseCivicPolicyTestAvailable(BaseCivicPolicyTestBWList):

    def get_civic_policy_tuning_test_list(self, provider):
        return provider.get_civic_policies(tuning=True)

class BaseCivicPolicyTestVotingOpen(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'negate': Tunable(description='\n            If checked then this test will return True when not active.\n            ', tunable_type=bool, default=False)}

    def get_custom_event_keys(self, provider_owner):
        return []

    def run_test(self, provider, tooltip):
        street_service = services.street_service()
        voting_open = street_service is not None and street_service.voting_open
        if voting_open:
            if self.negate:
                return TestResult(False, 'Civic Policy Provider failed negated voting open', tooltip=tooltip)
        elif not self.negate:
            return TestResult(False, 'Civic Policy Provider failed voting open', tooltip=tooltip)
        return TestResult.TRUE

class BaseCivicPolicyTestVotingTimeUntilChange(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'threshold': TunableThreshold(description='\n            The amount of time relative to the next voting state change to test.\n            ', value=TunableTimeSpan(description='\n                Duration before the next change.\n                ', default_hours=1))}

    def get_custom_event_keys(self, provider_owner):
        return []

    def run_test(self, provider, tooltip):
        street_service = services.street_service()
        voting_open = street_service is not None and street_service.voting_open
        if voting_open:
            time_of_change = street_service.voting_close_time
        else:
            time_of_change = street_service.voting_open_time
        now = services.time_service().sim_now
        time_left = time_of_change - now
        if callable(self.threshold.value):
            self.threshold.value = self.threshold.value()
        result = self.threshold.compare(time_left)
        if not result:
            return TestResult(False, 'Civic Policy Provider failed voting time until change test', tooltip=tooltip)
        return TestResult.TRUE

class BaseCivicPolicyTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'civic_policy_tests': TunableList(description='\n            The tests we wish to run on the civic policies in question, run in\n            order.  AND operation, all must pass, first to fail stops tests.\n            ', tunable=TunableVariant(description='\n                Individual tests run on Civic Policy Provider.\n                ', default='voting_open', enacted=BaseCivicPolicyTestEnacted.TunableFactory(), balloted=BaseCivicPolicyTestBalloted.TunableFactory(), repealable=BaseCivicPolicyTestRepealable.TunableFactory(), dormant=BaseCivicPolicyTestDormant.TunableFactory(), available=BaseCivicPolicyTestAvailable.TunableFactory(), voting_open=BaseCivicPolicyTestVotingOpen.TunableFactory(), voting_time_until_change=BaseCivicPolicyTestVotingTimeUntilChange.TunableFactory()))}

    def _get_civic_policy_provider(self, *args, **kwargs):
        raise NotImplementedError

    def get_custom_event_registration_keys(self):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        provider = self._get_civic_policy_provider(*args, **kwargs)
        for test in self.civic_policy_tests:
            result = test.run_test(provider, self.tooltip)
            if not result:
                return result
        return TestResult.TRUE
