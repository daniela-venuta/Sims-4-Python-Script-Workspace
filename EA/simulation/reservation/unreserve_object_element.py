from element_utils import CleanupType
class UnreserveObjectElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'timing': TunableTuple(description="\n            The behavior should occur at the very beginning of the\n            interaction.  It will not be tightly synchronized visually with\n            animation.  This isn't a very common use case and would most\n            likely be used in an immediate interaction or to change hidden\n            state that is used for bookkeeping rather than visual\n            appearance.\n            ", offset_time=OptionalTunable(description='\n                If enabled, the interaction will wait this amount of time\n                after the beginning before running the element.\n\n                Only use this if absolutely necessary. Better alternatives\n                include using xevts, time based conditional action with\n                loot ops, and using outcomes.\n                ', tunable=TunableSimMinute(description='The interaction will wait this amount of time after the beginning before running the element', default=2), enabled_by_default=True), locked_args={'timing': XevtTriggeredElement.AT_BEGINNING, 'criticality': CleanupType.NotCritical, 'xevt_id': None, 'supports_failsafe': None})}

    def _do_behavior(self):
        self.interaction.remove_liability(RESERVATION_LIABILITY)
        self.interaction.remove_liability(WaitingLineInteractionChainLiability.LIABILITY_TOKEN)
        return True
