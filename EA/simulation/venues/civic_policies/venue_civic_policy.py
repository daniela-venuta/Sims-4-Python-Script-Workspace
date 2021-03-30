from event_testing.test_events import TestEventfrom sims4.tuning.tunable import TunableReferencefrom sims4.tuning.tunable_base import ExportModesimport sims4from civic_policies.base_civic_policy import BaseCivicPolicyimport services
class VenueCivicPolicy(BaseCivicPolicy):
    INSTANCE_TUNABLES = {'sub_venue': TunableReference(description='\n            Sub-Venue to make active when this policy is enacted.\n            ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True, export_modes=ExportModes.All)}

    def enact(self):
        if self.enacted:
            return
        for policy in tuple(self.provider.get_enacted_policies()):
            if policy is not self:
                self.provider.repeal(policy)
        super().enact()
        if not self.enacted:
            return
        self.provider.request_active_venue(self.sub_venue)
        venue_game_service = services.venue_game_service()
        zone = None if venue_game_service is None else venue_game_service.get_zone_for_provider(self.provider)
        zone_id = None if zone is None else zone.id
        services.get_event_manager().process_event(TestEvent.CivicPoliciesChanged, custom_keys=((zone_id, type(self)),))

    def repeal(self):
        super().repeal()
        if self.enacted:
            return
        self.provider.request_restore_default()
        venue_game_service = services.venue_game_service()
        zone = None if venue_game_service is None else venue_game_service.get_zone_for_provider(self.provider)
        zone_id = None if zone is None else zone.id
        services.get_event_manager().process_event(TestEvent.CivicPoliciesChanged, custom_keys=((zone_id, type(self)),))
