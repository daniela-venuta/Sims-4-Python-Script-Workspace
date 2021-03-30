from civic_policies.base_civic_policy_provider import BaseCivicPolicyProviderimport servicesfrom event_testing.resolver import SingleSimResolver, VenuePolicyProviderResolverfrom gsi_handlers import zone_director_handlersfrom sims4.utils import classpropertyfrom world.street import get_world_description_id_from_zone_id
class VenueCivicPolicyProvider(BaseCivicPolicyProvider):

    def __init__(self, source_venue_type, active_venue_type=None, **kwargs):
        super().__init__(**kwargs)
        self.source_venue_type = source_venue_type
        self.active_venue_type = source_venue_type if active_venue_type is None else active_venue_type
        self._new_venue_type = None
        self._recursion_count = 0

    def new_enact_max_count(self):
        return 1

    @property
    def max_enacted_policy_count(self):
        return 1

    @property
    def max_balloted_policy_count(self):
        return len(self.get_civic_policies())

    @property
    def initial_balloted_policy_count(self):
        return len(self.get_civic_policies())

    @property
    def max_repealable_policy_count(self):
        return 1

    @property
    def open_close_voting_loot_resolver_list(self):
        venue_game_service = services.venue_game_service()
        if venue_game_service is None:
            return ()
        zone = venue_game_service.get_zone_for_provider(self)
        if zone is None:
            return ()
        if zone.is_instantiated:
            household_id = zone.lot.owner_household_id
        else:
            zone_data = services.get_persistence_service().get_zone_proto_buff(zone.id)
            if zone_data is not None:
                household_id = zone_data.household_id
        if household_id == 0:
            return ()
        household = services.household_manager().get(household_id)
        if household is None:
            return ()
        return [SingleSimResolver(sim_info) for sim_info in household.sim_infos()]

    @classproperty
    def provider_type_id(cls):
        return 1

    def get_world_description_id(self):
        venue_game_service = services.venue_game_service()
        if venue_game_service is None:
            return 0
        zone = venue_game_service.get_zone_for_provider(self)
        if zone is None:
            return 0
        else:
            world_description_id = get_world_description_id_from_zone_id(zone.id)
            if world_description_id is None:
                return 0
        return world_description_id

    def run_auto_voting_tests(self, test_set):
        if not services.street_service().enable_automatic_voting:
            return False
        if not test_set:
            return True
        resolvers = list(self.open_close_voting_loot_resolver_list)
        resolvers.append(VenuePolicyProviderResolver(self))
        for resolver in resolvers:
            if test_set.run_tests(resolver):
                return True
        return False

    def finalize_startup(self):
        super().finalize_startup()
        if not self.get_enacted_policies():
            policy = self.get_policy_instance_for_venue(self.active_venue_type)
            if policy is not None:
                self.enact(policy)

    def get_policy_instance_for_venue(self, venue_type):
        for policy in self.get_civic_policies():
            if policy.sub_venue is venue_type:
                return policy

    def request_active_venue(self, venue_type):
        self._new_venue_type = venue_type

    def request_restore_default(self):
        self._new_venue_type = None

    def _pre_change(self):
        self._recursion_count += 1
        if self._recursion_count == 1:
            self._new_venue_type = self.active_venue_type

    def _post_change(self):
        self._recursion_count -= 1
        if self._recursion_count <= 0:
            self._recursion_count = 0
            if self._new_venue_type is None:
                self._new_venue_type = self.source_venue_type
            if self.active_venue_type != self._new_venue_type:
                self.active_venue_type = self._new_venue_type
                services.venue_game_service().change_venue_type(self, self.active_venue_type, self.source_venue_type)

    def _post_forced_change(self):
        self._select_balloted_policies()

    def _log_event(self, op, *format_args):
        if self._recursion_count == 0 and zone_director_handlers.archiver.enabled:
            op_str = op.format(*format_args) if format_args else op
            zone_director_handlers.log_civic_policy_update(services.venue_service().get_zone_director(), services.current_zone(), op_str)

    def open_voting(self):
        super().open_voting()
        self._log_event('open voting')

    def close_voting(self):
        if services.venue_game_service() is None:
            return
        self._pre_change()
        super().close_voting()
        self._post_change()
        self._log_event('close voting')

    def enact(self, policy):
        self._pre_change()
        result = super().enact(policy)
        self._post_change()
        self._post_forced_change()
        self._log_event('enact {}', policy)
        return result

    def repeal(self, policy):
        self._pre_change()
        result = super().repeal(policy)
        self._post_change()
        self._post_forced_change()
        self._log_event('repeal {}', policy)
        return result

    def vote(self, policy, count=1):
        result = super().vote(policy, count)
        if result:
            self._log_event('vote {} +{}', policy, count)
        return result

    def is_eligible_voter(self, sim_info):
        venue_game_service = services.venue_game_service()
        if venue_game_service is None:
            return False
        zone = venue_game_service.get_zone_for_provider(self)
        world_id = services.get_persistence_service().get_world_id_from_zone(zone.id)
        return world_id == sim_info.household.get_home_world_id()
