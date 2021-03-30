import servicesimport sims4from sims4.tuning.tunable import TunableReference
class LocatorTuning:
    TARGET_LOCATOR_ID_STAT = TunableReference(description='\n        The stat name used to check for a target locator id on the routing object.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
