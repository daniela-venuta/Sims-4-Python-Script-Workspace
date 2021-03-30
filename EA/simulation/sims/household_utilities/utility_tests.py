from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_test, TestEventfrom interactions import ParticipantType, ParticipantTypeObject, ParticipantTypeSinglefrom objects.components.types import UTILITIES_COMPONENTfrom sims.household_utilities.utility_types import Utilitiesfrom sims4.tuning.tunable import TunableEnumEntry, TunableTuple, Tunable, AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableSet, OptionalTunable, TunableMappingfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport servicesimport sims4logger = sims4.log.Logger('UtilityTests', default_owner='mkartika')
class UtilityTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    PARTICIPANT_HOUSEHOLD = 'participant_household'
    ACTIVE_HOUSEHOLD = 'active_household'
    ACTIVE_LOT_HOUSEHOLD = 'active_lot_household'
    test_events = (TestEvent.UtilityStatusChanged,)
    FACTORY_TUNABLES = {'household_to_test': TunableVariant(description='\n            A variant that decides where the household to test comes from.\n            ', participant_household=TunableTuple(description="\n                Either the participant's household if they are a Sim or the\n                owning household if they are not.\n                ", participant=TunableEnumEntry(description='\n                    The subject whose household is the object of this delinquency test.\n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), locked_args={'household_source': PARTICIPANT_HOUSEHOLD}), active_household=TunableTuple(description='\n                The household being controlled by the player.\n                ', locked_args={'household_source': ACTIVE_HOUSEHOLD}), active_lot_household=TunableTuple(description='\n                The household that owns the active lot.\n                ', consider_non_household_lot=Tunable(description="\n                    If checked, when active lot has no household, we'll take \n                    utilities manager from active zone lot.\n                    Otherwise, non household lot will always fail the test.\n                    ", tunable_type=bool, default=True), locked_args={'household_source': ACTIVE_LOT_HOUSEHOLD}), default='active_lot_household'), 'utility_states': TunableSet(description='\n            List of utilities and whether they are required to be active or not.\n            ', tunable=TunableTuple(description='\n                Tuple containing a utility and its required active state.\n                ', utility=TunableEnumEntry(description='\n                    The utility type.\n                    ', tunable_type=Utilities, default=Utilities.POWER), require_active=Tunable(description='\n                    Whether this utility is required to be active or not.\n                    ', tunable_type=bool, default=True)), minlength=1)}

    def get_expected_args(self):
        if self.household_to_test.household_source == UtilityTest.PARTICIPANT_HOUSEHOLD:
            return {'test_targets': self.household_to_test.participant}
        return {}

    @cached_test
    def __call__(self, test_targets=None):
        target_household = None
        if self.household_to_test.household_source == UtilityTest.ACTIVE_LOT_HOUSEHOLD:
            target_household = services.owning_household_of_active_lot()
        elif self.household_to_test.household_source == UtilityTest.ACTIVE_HOUSEHOLD:
            target_household = services.active_household()
        elif self.household_to_test.household_source == UtilityTest.PARTICIPANT_HOUSEHOLD:
            target = next(iter(test_targets), None)
            if target is not None:
                if target.is_sim:
                    target_household = target.household
                else:
                    target_household = services.household_manager().get(target.get_household_owner_id())
        if target_household is not None:
            utilities_manager = services.get_utilities_manager_by_household_id(target_household.id)
        elif self.household_to_test.household_source == UtilityTest.ACTIVE_LOT_HOUSEHOLD and self.household_to_test.consider_non_household_lot:
            utilities_manager = services.get_utilities_manager_by_zone_id(services.current_zone_id())
        else:
            return TestResult(False, 'UtilitiesTest: Required to check utility, but there is no household. Check participant tuning.', tooltip=self.tooltip)
        if utilities_manager is None:
            return TestResult(False, 'UtilitiesTest: Required to check utility, but utilities manager is None. Check participant tuning.', tooltip=self.tooltip)
        for utility_state in self.utility_states:
            if utilities_manager.is_utility_active(utility_state.utility) != utility_state.require_active:
                return TestResult(False, 'UtilitiesTest: Utility status for the {} is not correct.', utility_state.utility, tooltip=self.tooltip)
        return TestResult.TRUE

class UtilitiesComponentTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of the test.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), 'can_run_on_utilities': OptionalTunable(description='\n            If enabled, will verify if subject can be run\n            on tuned utilities.\n            ', tunable=TunableWhiteBlackList(description='\n                A White/black list to check whether or not the \n                subject can be run on tuned utilities.\n                ', tunable=TunableEnumEntry(description='\n                    The utility that we want to test.\n                    ', tunable_type=Utilities, default=None)), disabled_name='ignore'), 'is_allowed_utility_usage': OptionalTunable(description='\n            If enabled, will verify if utility is allowed to be used\n            by the subject.\n            ', tunable=TunableMapping(description='\n                A mapping of utility to utility usage.\n                ', key_name='utility', key_type=TunableEnumEntry(description='\n                    The utility that we want to test.\n                    ', tunable_type=Utilities, default=None), value_name='allow_usage', value_type=Tunable(description='\n                    Whether the tuned utility is allowed to be\n                    used by the subject.\n                    ', tunable_type=bool, default=True)), disabled_name='ignore')}

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            utilities_component = target.get_component(UTILITIES_COMPONENT)
            if utilities_component is None:
                return TestResult(False, "{} doesn't have Utilities Component.", target, tooltip=self.tooltip)
            if self.can_run_on_utilities and not self.can_run_on_utilities.test_collection(list(utilities_component.allow_utility_usage_dict.keys())):
                return TestResult(False, '{} failed the Can-Run-On-Utilities test.', target, tooltip=self.tooltip)
            if self.is_allowed_utility_usage:
                for (utility, allow_usage) in self.is_allowed_utility_usage.items():
                    if allow_usage != utilities_component.is_allowed_utility_usage(utility):
                        return TestResult(False, '{} failed the Is-Allowed-Utility-Usage test.', target, tooltip=self.tooltip)
        return TestResult.TRUE
