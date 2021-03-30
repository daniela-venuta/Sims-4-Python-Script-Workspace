from routing.waypoints.tunable_waypoint_graph import TunableWaypointGraphfrom routing.waypoints.waypoint_generator import _WaypointGeneratorBase
class LocatorIdToWaypointGenerator(_WaypointGeneratorBase):

    def __init__(self, locator_ids, constraint_radius, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locator_ids = locator_ids
        self._constraint_radius = constraint_radius
        if locator_ids:
            self._start_constraint = TunableWaypointGraph.locator_to_waypoint_constraint(locator_ids[0], constraint_radius, self._routing_surface)
        else:
            self._start_constraint = None

    def get_start_constraint(self):
        return self._start_constraint

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        for locator_id in self._locator_ids:
            if waypoint_count == 0:
                return
            constraint = TunableWaypointGraph.locator_to_waypoint_constraint(locator_id, self._constraint_radius, self._routing_surface)
            if constraint is not None:
                yield constraint
                waypoint_count -= 1
