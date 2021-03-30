import routingimport sims4.logfrom routing import Locationfrom routing.portals.portal_enums import PortalAlignmentfrom routing.portals.portal_location import _PortalBoneLocationfrom routing.portals.portal_tuning import PortalFlagsfrom sims4.tuning.tunable import TunableTuple, TunableEnumEntry, OptionalTunable
class _BuildLaddersMixin:
    FACTORY_TUNABLES = {'portal_alignment': TunableEnumEntry(description='\n            Which direction this portal is aligned.  This direction is used to determine which animation to play\n            when getting on/off the top of ladder since there are three entrance/exit portals at the top of the ladder. \n            ', tunable_type=PortalAlignment, default=PortalAlignment.PA_FRONT), 'climb_up_locations': OptionalTunable(tunable=TunableTuple(description="\n                Location tunables for climbing up the ladder.  Optional because climbing up isn't supported on ladder\n                slide portals.\n                ", location_start=_PortalBoneLocation.TunableFactory(description='\n                    The location at the bottom of the ladder where climbing up starts.\n                    '), location_end=_PortalBoneLocation.TunableFactory(description='\n                    The location at the top of the ladder where climbing up ends.\n                    '))), 'climb_down_locations': TunableTuple(description='\n            Location tunables for climbing down the ladder.\n            ', location_start=_PortalBoneLocation.TunableFactory(description='\n                The location at the top of the ladder where climbing down starts.\n                '), location_end=_PortalBoneLocation.TunableFactory(description='\n                The location at the bottom of the ladder where climbing down ends.\n                '))}

    def _get_additional_portal_location_flags(self):
        return PortalFlags.DEFAULT

    def _get_ladder_portal_locations(self, obj):
        additional_portal_flags = self._get_additional_portal_location_flags()
        blocked_alignment_flags = routing.get_blocked_ladder_portals(obj.id, obj.zone_id)
        if blocked_alignment_flags & PortalAlignment.get_bit_flag(self.portal_alignment):
            return [(None, None, None, None, PortalFlags.DEFAULT)]
        (top_level, bottom_level, _) = routing.get_ladder_levels_and_height(obj.id, obj.zone_id)
        down_start = self.climb_down_locations.location_start(obj, override_level=top_level)
        down_end = self.climb_down_locations.location_end(obj, override_level=bottom_level)
        down_start_position = down_start.position
        down_start_routing_surface = routing.SurfaceIdentifier(obj.zone_id, top_level, down_start.routing_surface.type)
        down_end_routing_surface = routing.SurfaceIdentifier(obj.zone_id, bottom_level, down_end.routing_surface.type)
        if self.climb_up_locations is not None:
            up_start = self.climb_up_locations.location_start(obj, override_level=bottom_level)
            up_end = self.climb_up_locations.location_end(obj, override_level=top_level)
            up_end_position = up_end.position
            up_start_routing_surface = routing.SurfaceIdentifier(obj.zone_id, bottom_level, up_start.routing_surface.type)
            up_end_routing_surface = routing.SurfaceIdentifier(obj.zone_id, top_level, up_end.routing_surface.type)
            locations = [(Location(up_start.position, orientation=up_start.orientation, routing_surface=up_start_routing_surface), Location(up_end_position, orientation=up_end.orientation, routing_surface=up_end_routing_surface), Location(down_start_position, orientation=down_start.orientation, routing_surface=down_start_routing_surface), Location(down_end.position, orientation=down_end.orientation, routing_surface=down_end_routing_surface), additional_portal_flags)]
        else:
            locations = [(Location(down_start_position, orientation=down_start.orientation, routing_surface=down_start_routing_surface), Location(down_end.position, orientation=down_end.orientation, routing_surface=down_end_routing_surface), None, None, additional_portal_flags)]
        return locations
