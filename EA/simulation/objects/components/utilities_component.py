import servicesimport sims4from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.results import TestResultfrom interactions.interaction_finisher import FinishingTypefrom objects.components import Componentfrom objects.components.types import UTILITIES_COMPONENTfrom sims.household_utilities.utility_types import Utilitiesfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableList, TunableReference, TunableMapping, TunableEnumEntrylogger = sims4.log.Logger('UtilitiesComponent', default_owner='mkartika')
class UtilitiesComponent(Component, component_name=UTILITIES_COMPONENT, allow_dynamic=True, persistence_key=protocols.PersistenceMaster.PersistableData.UtilitiesComponent):
    UTILITIES_COMPONENT_AFFORDANCES = TunableList(description='\n        List of affordance for object that has Utilities Component.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    DISALLOW_UTILITY_USAGE_TOOLTIPS = TunableMapping(description='\n        Tooltips to show when an interaction cannot be run on the\n        object that has Utilities Component due to the utility usage\n        being disallowed.\n        ', key_type=TunableEnumEntry(description='\n            The utility type.\n            ', tunable_type=Utilities, default=Utilities.POWER), value_type=TunableLocalizedStringFactory(description='\n            A tooltip to show.\n            '))

    def __init__(self, *args, used_utilities=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_utility_usage_dict = {utility: True for utility in used_utilities}

    def component_super_affordances_gen(self, **kwargs):
        yield from self.UTILITIES_COMPONENT_AFFORDANCES

    def is_allowed_utility_usage(self, utility):
        if utility not in self.allow_utility_usage_dict:
            logger.error('Trying to check utility {} usage on object {}, but the object never use the utility.', utility, self.owner)
            return False
        return self.allow_utility_usage_dict[utility]

    def set_allow_utility_usage(self, utility, is_allowed):
        if utility not in self.allow_utility_usage_dict:
            logger.error('Trying to allow/disallow utility {} usage on object {}, but the object never use the utility.', utility, self.owner)
            return
        if self.allow_utility_usage_dict[utility] == is_allowed:
            return
        self.allow_utility_usage_dict[utility] = is_allowed
        is_utility_active = services.utilities_manager().is_utility_active(utility)
        if not is_utility_active:
            return
        if is_allowed:
            self._clear_shutoff_states(utility)
        else:
            self._cancel_utility_using_interactions(utility, 'Utilities Component. Interaction violates current utility usage of the object.')
            self._apply_shutoff_states(utility)

    def test_utility_info(self, utilities):
        if utilities is None:
            return TestResult.TRUE
        for utility in utilities:
            allow_usage = self.allow_utility_usage_dict.get(utility)
            if allow_usage is not None and not allow_usage:
                tooltip = self.DISALLOW_UTILITY_USAGE_TOOLTIPS.get(utility)
                return TestResult(False, 'Object {} is not allowed to use utility {}.', self.owner, utility, tooltip=tooltip)
        return TestResult.TRUE

    def _cancel_utility_using_interactions(self, utility, cancel_reason):
        obj = self.owner
        sims = obj.get_users(sims_only=True)
        for sim in sims:
            for interaction in sim.si_state:
                if not (interaction.target is not obj and obj.parts is None):
                    if interaction.target not in obj.parts:
                        pass
                    else:
                        utility_info = interaction.utility_info
                        if not utility_info is None:
                            if utility not in utility_info:
                                pass
                            else:
                                interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason)

    def _apply_shutoff_states(self, utility):
        state_component = self.owner.state_component
        if state_component is not None:
            state_component.apply_delinquent_states(utility=utility)

    def _clear_shutoff_states(self, utility):
        state_component = self.owner.state_component
        if state_component is not None:
            state_component.clear_delinquent_states(utility=utility)

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.UtilitiesComponent
        utilities_component_data = persistable_data.Extensions[protocols.PersistableUtilitiesComponent.persistable_data]
        for (utility, allow_usage) in self.allow_utility_usage_dict.items():
            with ProtocolBufferRollback(utilities_component_data.allow_utility_usage_list) as msg:
                msg.utility_enum = utility.value
                msg.allow_usage = allow_usage
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        utilities_component_data = persistable_data.Extensions[protocols.PersistableUtilitiesComponent.persistable_data]
        for data in utilities_component_data.allow_utility_usage_list:
            utility = Utilities(data.utility_enum)
            if utility not in self.allow_utility_usage_dict:
                pass
            else:
                self.allow_utility_usage_dict[utility] = data.allow_usage
