import sims4.logfrom postures.base_postures import MobilePosturefrom postures.posture_specs import get_origin_spec_carry, get_origin_specfrom routing import Locationfrom routing.portals.portal_data_ladders import _PortalTypeDataLaddersfrom routing.portals.portal_enums import LadderTypefrom routing.portals.portal_location import _PortalLocationfrom routing.portals.portal_tuning import PortalFlagsfrom routing.route_enums import RouteEventTypefrom routing.route_events.route_event import RouteEventfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom sims4.tuning.tunable import TunableRange, TunableTuplelogger = sims4.log.Logger('OceanLaddersPortalData', default_owner='trevor')
class _PortalTypeDataOceanLadders(RouteEventProviderMixin, _PortalTypeDataLadders):
    FACTORY_TUNABLES = {'climb_up_locations': TunableTuple(description='\n            Location tunables for climbing up the ladder.\n            ', location_start=_PortalLocation.TunableFactory(description='\n                The location at the bottom of the ladder where climbing up starts.\n                '), location_end=_PortalLocation.TunableFactory(description='\n                The location at the top of the ladder where climbing up ends.\n                ')), 'climb_down_locations': TunableTuple(description='\n            Location tunables for climbing down the ladder.\n            ', location_start=_PortalLocation.TunableFactory(description='\n                The location at the top of the ladder where climbing down starts.\n                '), location_end=_PortalLocation.TunableFactory(description='\n                The location at the bottom of the ladder where climbing down ends.\n                ')), 'climb_up_route_event': RouteEvent.TunableReference(description="\n            The route event to set a posture while climing up the ladder portal.\n            Currently, only Set Posture is supported. If any other route events\n            are tuned here there's a good chance they won't work as expected.\n            "), 'climb_down_route_event': RouteEvent.TunableReference(description="\n            The route even tto set a posture while climbing down the ladder portal.\n            Currently, only Set Posture is supported. If any other route events\n            are tuned here there's a good chance they won't work as expected.\n            "), 'posture_start': MobilePosture.TunableReference(description='\n            Define the entry posture as you cross through this portal. e.g. For\n            the pool, the start posture is stand.\n            '), 'posture_end': MobilePosture.TunableReference(description='\n            Define the exit posture as you cross through this portal.\n            '), 'route_event_time_offset': TunableRange(description='\n            The amount of time after the start of the ladder portal to schedule \n            the route event. \n            ', tunable_type=float, default=0.5, minimum=0, maximum=1)}

    def get_portal_duration(self, portal_instance, is_mirrored, _, age, gender, species):
        return self._calculate_walkstyle_duration(portal_instance, is_mirrored, age, gender, species, self.WALKSTYLE_SWIM, self.WALKSTYLE_WALK)

    def get_portal_locations(self, obj):
        up_start = self.climb_up_locations.location_start(obj)
        up_end = self.climb_up_locations.location_end(obj)
        down_start = self.climb_down_locations.location_start(obj)
        down_end = self.climb_down_locations.location_end(obj)
        locations = [(Location(up_start.position, orientation=up_start.orientation, routing_surface=up_start.routing_surface), Location(up_end.position, orientation=up_end.orientation, routing_surface=up_end.routing_surface), Location(down_start.position, orientation=down_start.orientation, routing_surface=down_start.routing_surface), Location(down_end.position, orientation=down_end.orientation, routing_surface=down_end.routing_surface), PortalFlags.STAIRS_PORTAL_LONG)]
        return locations

    def provide_route_events(self, route_event_context, sim, path, is_mirrored=True, node=None, **kwargs):
        route_event = self.climb_down_route_event if is_mirrored else self.climb_up_route_event
        if route_event_context.route_event_already_scheduled(route_event, provider=self) or not route_event_context.route_event_already_fully_considered(route_event, self):
            route_event_context.add_route_event(RouteEventType.LOW_SINGLE, route_event(provider=self, time=node.time + self.route_event_time_offset))

    def is_route_event_valid(self, route_event, time, sim, path):
        return True

    def get_posture_change(self, portal_instance, is_mirrored, initial_posture):
        if initial_posture is not None and initial_posture.carry_target is not None:
            start_posture = get_origin_spec_carry(self.posture_start)
            end_posture = get_origin_spec_carry(self.posture_end)
        else:
            start_posture = get_origin_spec(self.posture_start)
            end_posture = get_origin_spec(self.posture_end)
        if is_mirrored:
            return (end_posture, start_posture)
        return (start_posture, end_posture)

    def _get_route_ladder_data(self, is_mirrored):
        op = super()._get_route_ladder_data(is_mirrored)
        op.ladder_type = LadderType.LADDER_OCEAN
        return op

    def _get_num_rungs(self, ladder):
        rung_start = self.climb_up_locations.location_start(ladder).position.y
        rung_end = self.climb_up_locations.location_end(ladder).position.y - self.ladder_rung_distance
        return (rung_end - rung_start)//self.ladder_rung_distance + 1
