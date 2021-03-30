from sims.fixup.sim_info_fixup_action import _SimInfoFixupActionfrom sims4.tuning.tunable import TunableListfrom statistics.statistic_ops import TunableStatisticChangefrom event_testing.resolver import SingleSimResolver
class _SimInfoStatisticOpsFixupAction(_SimInfoFixupAction):
    FACTORY_TUNABLES = {'statistics_list': TunableList(description='\n            A list of Statistics Ops to run on the Sim.\n            ', tunable=TunableStatisticChange())}

    def __call__(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for statistic_op in self.statistics_list:
            statistic_op.apply_to_resolver(resolver)
