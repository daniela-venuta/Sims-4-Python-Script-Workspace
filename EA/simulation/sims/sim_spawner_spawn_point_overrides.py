from event_testing.resolver import SingleSimResolver
class TestedSpawnPointOverride(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tested_list': TunableTestedList(tunable_type=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=SPAWN_PREFIX), stop_processing_behavior=STOP_PROCESSING_ALWAYS)}

    def get_spawner_tag(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        return next(iter(tag for tag in self.tested_list(resolver=resolver)), None)
