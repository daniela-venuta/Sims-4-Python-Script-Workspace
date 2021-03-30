from sims4.tuning.tunable import TunablePackSafeReference, TunableColor
class FactionRepModuleTuning:
    FIRST_ORDER_REPUTATION = TunablePackSafeReference(description='\n        Ranked statistic for first order reputation.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',), export_modes=ExportModes.All)
    RESISTANCE_REPUTATION = TunablePackSafeReference(description='\n        Ranked statistic for resistance reputation.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',), export_modes=ExportModes.All)
    SCOUNDREL_REPUTATION = TunablePackSafeReference(description='\n        Ranked statistic for scoundrel reputation.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',), export_modes=ExportModes.All)
