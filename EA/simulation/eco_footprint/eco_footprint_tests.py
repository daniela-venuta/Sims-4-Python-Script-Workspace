from civic_policies.street_civic_policy_tests import StreetCivicPolicySelectorTestMixinfrom eco_footprint.eco_footprint_enums import EcoFootprintStateType, EcoFootprintDirectionfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableList, TunableVariant, Tunable
class _EcoFootprintTestState(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'required_eco_footprint_state': TunableEnumEntry(description='\n            If the tested street has this EcoFootprintStateType, the test will\n            pass.\n            ', tunable_type=EcoFootprintStateType, default=EcoFootprintStateType.NEUTRAL), 'invert': Tunable(description='\n            If True then the result of this test will be inverted. Otherwise\n            the results remain the same.\n            ', tunable_type=bool, default=False)}

    def run_test(self, provider):
        if not provider.is_eco_footprint_compatible:
            return TestResult(False, 'Eco Footprint is not compatible with this street')
        if provider.current_eco_footprint_state == self.required_eco_footprint_state:
            if self.invert:
                return TestResult(False, 'Eco Footprint state is not allowed: {}', self.required_eco_footprint_state)
            return TestResult.TRUE
        if self.invert:
            return TestResult.TRUE
        else:
            return TestResult(False, 'Eco Footprint state {} is not the required state {}', provider.current_eco_footprint_state, self.required_eco_footprint_state)

class _EcoFootprintTestDirection(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'required_direction': TunableEnumEntry(description='\n            If the tested street is moving toward this EcoFootprintDirection,\n            the test will pass.\n            ', tunable_type=EcoFootprintDirection, default=EcoFootprintDirection.AT_CONVERGENCE)}

    def run_test(self, provider):
        if not provider.is_eco_footprint_compatible:
            return TestResult(False, 'Eco Footprint is not compatible with this street')
        street_footprint = provider.get_street_footprint(add=False)
        if street_footprint is None:
            return TestResult(False, "Eco footprint commodity doesn't exist on street")
        footprint_current_value = street_footprint.get_value()
        if self.required_direction == EcoFootprintDirection.TOWARD_GREEN:
            if footprint_current_value > street_footprint.convergence_value:
                return TestResult.TRUE
            return TestResult(False, 'The street eco footprint is not moving toward green')
        elif self.required_direction == EcoFootprintDirection.TOWARD_INDUSTRIAL:
            if footprint_current_value < street_footprint.convergence_value:
                return TestResult.TRUE
            return TestResult(False, 'The street eco footprint is not moving toward industrial')
        elif footprint_current_value == street_footprint.convergence_value:
            return TestResult.TRUE
        else:
            return TestResult(False, 'The street eco footprint is not at convergence')

class StreetEcoFootprintTest(StreetCivicPolicySelectorTestMixin, BaseTest):
    FACTORY_TUNABLES = {'eco_footprint_tests': TunableList(description='\n            ', tunable=TunableVariant(description="\n                A test to run on the street's policy provider.\n                ", default='state', state=_EcoFootprintTestState.TunableFactory(), direction=_EcoFootprintTestDirection.TunableFactory()))}

    def __call__(self, *args, **kwargs):
        provider = self._get_civic_policy_provider(*args, **kwargs)
        if provider is None:
            return TestResult(False, 'Cannot find Civic Policy Provider', tooltip=self.tooltip)
        for test in self.eco_footprint_tests:
            test_result = test.run_test(provider)
            if not test_result:
                return test_result
        return TestResult.TRUE
