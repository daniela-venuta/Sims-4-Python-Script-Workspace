import event_testingimport sims4from bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEvent, cached_testfrom interactions import ParticipantTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableThreshold, TunableEnumEntrylogger = sims4.log.Logger('CurrencyTests', default_owner='skorman')
class BucksTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.BucksEarned,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'bucks_type': TunableEnumEntry(description='\n            Bucks type that will be tested against the value threshold.\n            ', tunable_type=BucksType, default=BucksType.INVALID), 'value_threshold': TunableThreshold(description='\n            Bucks amount required to pass\n            '), 'subject': TunableEnumEntry(description='\n            Who or what to test against.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def get_expected_args(self):
        return {'test_targets': self.subject, 'bucks_data': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, test_targets=(), bucks_data=None, objective_guid64=None, tooltip=None):
        for target in test_targets:
            current_bucks = 0
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(self.bucks_type, owner_id=target.id)
            if objective_guid64 is not None and bucks_data is not None:
                current_bucks = bucks_data.get_bucks_earned(self.bucks_type)
                relative_start_values = bucks_data.get_starting_values(objective_guid64)
                if relative_start_values is not None:
                    current_bucks -= relative_start_values[0]
            elif bucks_tracker is not None:
                current_bucks = bucks_tracker.get_bucks_amount_for_type(self.bucks_type)
            if not self.value_threshold.compare(current_bucks):
                return TestResult(False, 'Bucks type {} value does not pass the value threshold.', self.bucks_type, tooltip=self.tooltip)
        return TestResult.TRUE

    def save_relative_start_values(self, objective_guid64, bucks_data):
        bucks_data.set_starting_values(objective_guid64, (bucks_data.get_bucks_earned(self.bucks_type),))
