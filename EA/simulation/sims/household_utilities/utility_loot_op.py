from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects.components.types import UTILITIES_COMPONENTfrom sims.household_utilities.utility_types import Utilities, UtilityShutoffReasonPriorityfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableEnumEntry, AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableMapping, Tunableimport game_servicesimport servicesimport sims4logger = sims4.log.Logger('UtilityLootOp', default_owner='mkartika')
class UtilityModifierOp(BaseLootOperation):

    class ShutOffUtility(AutoFactoryInit, HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'shutoff_tooltip': TunableLocalizedStringFactory(description='\n                A tooltip to show when an interaction cannot be run due to this\n                utility being shutoff.\n                ')}

        def __call__(self, utility_manager, utility, shutoff_reason):
            utility_manager.shut_off_utility(utility, shutoff_reason, self.shutoff_tooltip)

    class RestoreUtility(HasTunableSingletonFactory):

        def __call__(self, utility_manager, utility, shutoff_reason):
            utility_manager.restore_utility(utility, shutoff_reason)

    FACTORY_TUNABLES = {'utility': TunableEnumEntry(description='\n            The utility we want to shut off.\n            ', tunable_type=Utilities, default=Utilities.POWER), 'shutoff_reason': TunableEnumEntry(description='\n            The priority of our shutoff reason. This determines how important\n            the shutoff tooltip is relative to other reasons the utility is\n            being shutoff.\n            ', tunable_type=UtilityShutoffReasonPriority, default=UtilityShutoffReasonPriority.NO_REASON), 'action': TunableVariant(description='\n            Action to change utility.\n            ', restore=RestoreUtility.TunableFactory(), shut_off=ShutOffUtility.TunableFactory(), default='shut_off'), 'locked_args': {'subject': ParticipantType.Lot}}

    def __init__(self, *args, utility, shutoff_reason, action, **kwargs):
        super().__init__(*args, **kwargs)
        self.utility = utility
        self.shutoff_reason = shutoff_reason
        self.action = action

    def _apply_to_subject_and_target(self, subject, target, resolver):
        household = subject.get_household()
        household_id = household.id if household is not None else None
        _manager = game_services.service_manager.utilities_manager
        if household_id:
            utilities_manager = _manager.get_manager_for_household(household_id)
        else:
            utilities_manager = _manager.get_manager_for_zone(subject.zone_id)
        self.action(utilities_manager, self.utility, self.shutoff_reason)

class UtilityUsageOp(BaseLootOperation):
    FACTORY_TUNABLES = {'allow_utility_usage': TunableMapping(description='\n            A mapping of utility to utility usage.\n            ', key_name='utility', key_type=TunableEnumEntry(description='\n                The utility that we want to change.\n                ', tunable_type=Utilities, default=None), value_name='allow_usage', value_type=Tunable(description='\n                Whether the tuned utility is allowed to be\n                used by the subject.\n                ', tunable_type=bool, default=True))}

    def __init__(self, *args, allow_utility_usage, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_utility_usage = allow_utility_usage

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to change Utility Usage but the subject is None. Resolver: {}.', resolver)
            return
        utilities_component = subject.get_component(UTILITIES_COMPONENT)
        if utilities_component is None:
            logger.error('Attempting to change Utility Usage but the subject {} has no Utility Component. Resolver: {}.', subject, resolver)
            return
        for (utility, allow_usage) in self.allow_utility_usage.items():
            utilities_component.set_allow_utility_usage(utility, allow_usage)
