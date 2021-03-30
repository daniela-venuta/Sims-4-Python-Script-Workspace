import enumimport servicesimport sims4from autonomy.autonomy_modifier import AutonomyModifierfrom event_testing.resolver import GlobalResolverfrom interactions import ParticipantTypeLotfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunablePackSafeReference, TunableEnumEntry, Tunablelogger = sims4.log.Logger('ZoneModifierAction', default_owner='mkartika')
class ZoneModifierFromObjectsActionType(enum.Int, export=False):
    INVALID = 0
    STATISTIC_CHANGE = 1
    CONVERGENCE_CHANGE = 2
    STATISTIC_MODIFIER = 3

class ZoneModifierFromObjectsActionVariants(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, convergence_change=ZoneModifierFromObjectsActionConvergenceChange.TunableFactory(), statistic_change=ZoneModifierFromObjectsActionStatisticChange.TunableFactory(), statistic_modifier=ZoneModifierFromObjectsActionStatisticModifier.TunableFactory(), default='statistic_change', **kwargs)

class ZoneModifierFromObjectsAction(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'multiplier': Tunable(description='\n            The multiplier to apply to the object count.\n            ', tunable_type=float, default=0)}

    @property
    def action_type(self):
        return ZoneModifierFromObjectsActionType.INVALID

    def _get_participant_stat_tracker(self, stat):
        target = self._get_target()
        if target is None:
            logger.error('Failed to get participant {}, when trying to get tracker for Zone Modifier Convergence Change', self.participant)
            return
        else:
            tracker = target.get_tracker(stat)
            if tracker is None:
                logger.error('Failed to get tracker of statistic {} from {}, when trying to get tracker for Zone Modifier Convergence Change', stat, target)
                return
        return tracker

    def _get_target(self):
        resolver = GlobalResolver()
        return resolver.get_participant(ParticipantTypeLot.Lot)

    def get_value(self, object_count):
        return self.multiplier*object_count

    def apply(self, object_count):
        pass

    def revert(self, object_count):
        pass

class ZoneModifierFromObjectsActionStatisticChange(ZoneModifierFromObjectsAction):
    FACTORY_TUNABLES = {'stat': TunablePackSafeReference(description='\n            The statistic we are operating on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))}

    @property
    def action_type(self):
        return ZoneModifierFromObjectsActionType.STATISTIC_CHANGE

class ZoneModifierFromObjectsActionConvergenceChange(ZoneModifierFromObjectsAction):
    FACTORY_TUNABLES = {'stat': TunablePackSafeReference(description='\n            The statistic we are operating on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity',))}

    @property
    def action_type(self):
        return ZoneModifierFromObjectsActionType.CONVERGENCE_CHANGE

    def _get_stat_instance(self):
        if self.stat is None:
            return
        tracker = self._get_participant_stat_tracker(self.stat)
        if tracker is None:
            return
        return tracker.get_statistic(self.stat)

    def apply(self, object_count):
        stat_inst = self._get_stat_instance()
        if stat_inst is None:
            return False
        value = self.get_value(object_count)
        stat_inst.convergence_value += value
        return True

    def revert(self, object_count):
        stat_inst = self._get_stat_instance()
        if stat_inst is None:
            return False
        value = self.get_value(object_count)
        stat_inst.convergence_value -= value
        return True

class ZoneModifierFromObjectsActionStatisticModifier(ZoneModifierFromObjectsAction):
    FACTORY_TUNABLES = {'stat': TunablePackSafeReference(description='\n            The statistic we are operating on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._modifier_handles = None

    @property
    def action_type(self):
        return ZoneModifierFromObjectsActionType.STATISTIC_MODIFIER

    def apply(self, object_count):
        if self.stat is None:
            return False
        target = self._get_target()
        if target is None:
            return False
        autonomy_modifier = AutonomyModifier(statistic_modifiers={self.stat: self.get_value(object_count)})
        modifier_handle = target.add_statistic_modifier(autonomy_modifier)
        if self._modifier_handles is None:
            self._modifier_handles = []
        self._modifier_handles.append(modifier_handle)
        return True

    def revert(self, object_count):
        if self.stat is None:
            return False
        if self._modifier_handles is None:
            return False
        target = self._get_target()
        if target is None:
            return False
        for modifier_handle in self._modifier_handles:
            target.remove_statistic_modifier(modifier_handle)
        self._modifier_handles = None
        return True
