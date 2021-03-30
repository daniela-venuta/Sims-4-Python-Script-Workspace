import routingimport sims4.logfrom protocolbuffers import Routing_pb2from routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_enums import PathSplitTypefrom routing.portals.portal_tuning import PortalType, PortalFlagsfrom sims4 import hash_utilfrom sims4.tuning.tunable import Tunablefrom sims4.tuning.tunable_base import GroupNameslogger = sims4.log.Logger('LaddersPortalData', default_owner='bnguyen')
class _PortalTypeDataLadders(_PortalTypeDataBase):
    FACTORY_TUNABLES = {'ladder_rung_distance': Tunable(description='\n            The distance between rungs on the ladder object.\n            ', tunable_type=float, default=0.25), 'ladder_up_start_cycle': Tunable(description='\n            The name of the animation clip for the up start cycle.\n            ', tunable_type=str, default='ladder_up_start', tuning_group=GroupNames.ANIMATION), 'ladder_up_climb_cycle': Tunable(description='\n            The name of the animation clip for the up climb cycle.\n            ', tunable_type=str, default='ladder_up_cycle_r', tuning_group=GroupNames.ANIMATION), 'ladder_up_stop_cycle': Tunable(description='\n            The name of the animation clip for the up stop cycle.\n            ', tunable_type=str, default='ladder_up_stop', tuning_group=GroupNames.ANIMATION), 'ladder_down_start_cycle': Tunable(description='\n            The name of the animation clip for the down start cycle.\n            ', tunable_type=str, default='ladder_down_start', tuning_group=GroupNames.ANIMATION), 'ladder_down_climb_cycle': Tunable(description='\n            The name of the animation clip for the down climb cycle.\n            ', tunable_type=str, default='ladder_down_cycle_r', tuning_group=GroupNames.ANIMATION), 'ladder_down_stop_cycle': Tunable(description='\n            The name of the animation clip for the down stop cycle.\n            ', tunable_type=str, default='ladder_down_stop', tuning_group=GroupNames.ANIMATION), 'walkstyle_duration': Tunable(description='\n            The name of the duration field in the animation data.\n            ', tunable_type=str, default='duration', tuning_group=GroupNames.ANIMATION)}
    WALKSTYLE_WALK = sims4.hash_util.hash32('Walk')
    WALKSTYLE_SWIM = sims4.hash_util.hash32('Swim')

    @property
    def portal_type(self):
        return PortalType.PortalType_Animate

    @property
    def requires_los_between_points(self):
        return False

    @property
    def lock_portal_on_use(self):
        return False

    def get_additional_required_portal_flags(self, entry_location, exit_location):
        return PortalFlags.STAIRS_PORTAL_LONG

    def split_path_on_portal(self):
        return PathSplitType.PathSplitType_LadderSplit

    def add_portal_data(self, actor, portal_instance, is_mirrored, walkstyle):
        node_data = Routing_pb2.RouteNodeData()
        node_data.type = Routing_pb2.RouteNodeData.DATA_LADDER
        node_data.data = self._get_route_ladder_data(is_mirrored).SerializeToString()
        node_data.do_stop_transition = True
        node_data.do_start_transition = True
        return node_data

    def _get_route_ladder_data(self, is_mirrored):
        op = Routing_pb2.RouteLadderData()
        op.traversing_up = not is_mirrored
        op.step_count = 0
        return op

    def _get_num_rungs(self, ladder):
        raise NotImplementedError

    def _calculate_walkstyle_duration(self, portal_instance, is_mirrored, age, gender, species, standard_walkstyle, mirrored_walkstyle):
        if is_mirrored:
            walkstyle = mirrored_walkstyle
            start_cycle = self.ladder_down_start_cycle
            stop_cycle = self.ladder_down_stop_cycle
            climb_cycle = self.ladder_down_climb_cycle
        else:
            walkstyle = standard_walkstyle
            start_cycle = self.ladder_up_start_cycle
            stop_cycle = self.ladder_up_stop_cycle
            climb_cycle = self.ladder_up_climb_cycle
        walkstyle_info_dict = routing.get_walkstyle_info_full(walkstyle, age, gender, species)
        walkstyle_duration = self._get_duration_for_cycle(start_cycle, walkstyle_info_dict) + self._get_duration_for_cycle(climb_cycle, walkstyle_info_dict)*self._get_num_rungs(portal_instance.obj) + self._get_duration_for_cycle(stop_cycle, walkstyle_info_dict)
        return walkstyle_duration

    def _get_duration_for_cycle(self, clip, walkstyle_info_dict):
        builder_name = hash_util.hash32(clip)
        if builder_name not in walkstyle_info_dict:
            logger.error("Can't find the ladder clip {} in the  walkstyle info.", clip)
            return 0
        return walkstyle_info_dict[builder_name][self.walkstyle_duration]
