import servicesimport sims4from event_testing.resolver import GlobalResolverfrom interactions.constraints import Circlefrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import TunableList, TunableLocator, AutoFactoryInit, TunableTuple, TunableMapping, TunableRange, HasTunableSingletonFactoryfrom snippets import define_snippet, WAYPOINT_GRAPHfrom tunable_multiplier import TunableMultiplierlogger = sims4.log.Logger('WaypointGraph', default_owner='miking')
class TunableWaypointWeightedSet(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'connections': TunableList(description='\n            List of connected waypoints.\n            ', tunable=TunableTuple(description='\n                Pair of waypoint and a tested weight.\n                ', connected_waypoint=TunableLocator(description='\n                    Waypoint reference.\n                    '), weight=TunableMultiplier.TunableFactory(description='\n                    A weight with testable multipliers that is used to \n                    determine how likely this entry is to be picked when \n                    selecting randomly.\n                    ')))}

    def choose(self, waypoint_graph, routing_surface, resolver=None, previous_waypoint=None):
        if not self.connections:
            return (None, None)
        if resolver is None:
            resolver = GlobalResolver()
        weighted_waypoints = tuple((connection.weight.get_multiplier(resolver), connection.connected_waypoint) for connection in self.connections if connection.weight.get_multiplier(resolver) > 0)
        valid_waypoints = tuple(pair for pair in weighted_waypoints if pair[1] != previous_waypoint)
        if not valid_waypoints:
            valid_waypoints = tuple(pair for pair in weighted_waypoints if pair[1] == previous_waypoint)
        if not valid_waypoints:
            return (None, None)
        locator_id = weighted_random_item(valid_waypoints)
        waypoint_constraint = waypoint_graph.locator_to_waypoint_constraint(locator_id, waypoint_graph.constraint_radius, routing_surface)
        return (locator_id, waypoint_constraint)

class TunableWaypointGraph(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'connections': TunableMapping(description='\n            Defines the connections between waypoints in this graph.\n            ', key_name='waypoint', key_type=TunableLocator(description='\n                Waypoint reference.\n                '), value_name='connections', value_type=TunableWaypointWeightedSet.TunableFactory()), 'constraint_radius': TunableRange(description='\n            The radius, in meters, for each of the generated waypoint\n            constraints.\n            ', tunable_type=float, default=1.5, minimum=0)}

    @staticmethod
    def locator_to_waypoint_constraint(locator_id, constraint_radius, routing_surface):
        locators = services.locator_manager().get(locator_id)
        if not locators:
            logger.error('Waypoint id {} has no associated locator in the current zone.', locator_id)
            return
        if len(locators) > 1:
            logger.warn('Waypoint id {} has more than one associated locator in the current zone. Choosing the first one that was found.', locator_id)
        locator = locators[0]
        waypoint_position = locator.transform.translation
        return Circle(waypoint_position, constraint_radius, routing_surface=routing_surface, los_reference_point=None)
(TunableWaypointGraphReference, TunableWaypointGraphSnippet) = define_snippet(WAYPOINT_GRAPH, TunableWaypointGraph.TunableFactory())