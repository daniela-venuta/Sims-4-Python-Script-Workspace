from game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom interactions.utils.affordance_filter import AffordanceFilterVariantfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import OptionalTunable, HasTunableSingletonFactory, AutoFactoryInit
class PieMenuModifier(HasTunableSingletonFactory, AutoFactoryInit, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'affordance_filter': AffordanceFilterVariant(description='\n            Affordances this modifier affects.\n            '), 'suppression_tooltip': OptionalTunable(description='\n            If supplied, interactions are disabled with this tooltip.\n            Otherwise, interactions are hidden.\n            ', tunable=TunableLocalizedStringFactory(description='Reason of failure.'))}

    def __init__(self, **kwargs):
        super().__init__(GameEffectType.PIE_MENU_MODIFIER, **kwargs)

    def affordance_is_allowed(self, affordance):
        return self.affordance_filter(affordance)
