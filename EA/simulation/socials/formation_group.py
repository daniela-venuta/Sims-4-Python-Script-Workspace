from itertools import isliceimport enumimport randomimport servicesfrom _collections import defaultdictfrom event_testing.resolver import DoubleSimResolverfrom interactions.utils.success_chance import SuccessChancefrom objects.system import create_objectfrom postures import DerailReasonfrom routing.formation.formation_data import TunableRoutingFormationListSnippetfrom routing.route_enums import RouteEventTypefrom routing.route_events.route_event_paired import RouteEventPairedfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom sims4.math import EPSILONfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, TunableList, TunableTuple, TunableRange, TunableIntervalfrom sims4.tuning.tunable_base import GroupNamesfrom socials.group import SocialGroupimport sims4.loglogger = sims4.log.Logger('Formation Social Group', default_owner='miking')
class FormationSocialGroupState(enum.Int, export=False):
    WAITING_FOR_SIMS = 0
    ROUTING = 1
    PAUSED = 2

class FormationSocialGroup(SocialGroup, RouteEventProviderMixin):
    INSTANCE_TUNABLES = {'routing_object': TunableReference(description='\n            An object with a routing component that will be used as the anchor object for this group.\n            ', manager=services.definition_manager(), tuning_group=GroupNames.ROUTING), 'routing_object_on_state': TunableReference(description='\n            object state to activate the routing object.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', tuning_group=GroupNames.ROUTING), 'routing_object_off_state': TunableReference(description='\n            object state to deactivate the routing object.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', tuning_group=GroupNames.ROUTING), 'formation_tuning': TunableRoutingFormationListSnippet(description="\n            A list of routing formations. One will be chosen based on the number of members of the group.\n            It will use the closest match based on the number of offsets in the formation.\n            Note that you will generally always want to use the 'follow' formation type here.\n            ", tuning_group=GroupNames.ROUTING), 'routing_events': TunableList(description='\n            Events and weight for paired events.\n            Only one pair can occur within the specified routing event delay.\n            To avoid overlap, minimum delay must be longer than duration of\n            route event.\n            ', tunable=TunableTuple(actor_event=RouteEventPaired.TunableReference(description='\n                    A paired route event for the sim tested as the actor sim.\n                    ', pack_safe=True), target_event=RouteEventPaired.TunableReference(description='\n                    A paired route event for the sim tested as the target sim.\n                    ', pack_safe=True), weight=TunableRange(description='\n                    The weight to assign to this event.\n                    ', tunable_type=float, default=1, minimum=1), chance=SuccessChance.TunableFactory(description='\n                    Percent Chance that the Route Event pair will play.\n                    '))), 'routing_event_delay': TunableInterval(description='\n            Delay between the START of a routing event to when the next one can\n            first be scheduled in real world seconds\n            ', tunable_type=int, default_lower=3, default_upper=5), 'minimum_paired_angle': TunableRange(description='\n            Minimum angle between sims in formation (from straight ahead/behind)\n            for paired conversation to be attempted.  (ignored if for actor sim\n            No sim is far enough off)\n            ', tunable_type=float, default=10, minimum=0, maximum=90)}

    def __init__(self, si, *args, **kwargs):
        super().__init__(*args, si=si, **kwargs)
        self._interaction = si
        self._state = FormationSocialGroupState.WAITING_FOR_SIMS
        self._situation = None
        self._formation_si_map = {}
        self._routing_formation_needs_update = False
        self._route_duration = None
        self._planned_route_events = None
        self._formation_offset_map = {}

    def shutdown(self, finishing_type):
        if self.anchor:
            if self._state == FormationSocialGroupState.ROUTING:
                self.anchor.routing_component.on_set_routing_path.unregister(self._update_formation_offsets)
            self.anchor.make_transient()
        self._formation_offset_map.clear()
        super().shutdown(finishing_type)

    def _add(self, sim, attaching_si):
        super()._add(sim, attaching_si)
        self._formation_si_map[sim] = attaching_si
        self._try_update_routing_formations()
        if self._state == FormationSocialGroupState.WAITING_FOR_SIMS and self._situation is not None:
            self._situation.on_sim_added_to_social_group()
        sim.routing_component.add_route_event_provider(self)

    def _remove(self, sim, finishing_type=None, **kwargs):
        super()._remove(sim, **kwargs)
        self._try_update_routing_formations()
        if self._situation is not None:
            self._situation.on_sim_removed_from_social_group(sim, finishing_type)
        if sim in self._formation_offset_map:
            del self._formation_offset_map[sim]
        sim.routing_component.remove_route_event_provider(self)

    @classmethod
    def _get_social_anchor_object(cls, si, target_sim):
        routing_object = create_object(cls.routing_object)
        if routing_object is None:
            logger.error('{} is being created but failed to create routing_object.', cls)
            return
        initiating_sim = si.context.sim
        if initiating_sim is None:
            logger.error('{} is being created but cannot get initiating_sim.', cls)
            return
        logger.debug('Social anchor object created, id = {}', routing_object.id)
        root_object = initiating_sim.get_parenting_root()
        object_location = root_object.location.clone()
        routing_object.set_location(object_location)
        return routing_object

    @classmethod
    def can_get_close_and_wait(cls, sim, target):
        return False

    def set_situation(self, situation):
        self._situation = situation

    def _try_update_routing_formations(self):
        if self._state == FormationSocialGroupState.PAUSED:
            self._update_routing_formations()
        else:
            self._routing_formation_needs_update = True

    def _process_pending_routing_formation_updates(self):
        sims_to_remove = [sim for sim in self._formation_si_map.keys() if sim not in self]
        for sim in sims_to_remove:
            del self._formation_si_map[sim]
        if self._routing_formation_needs_update:
            self._update_routing_formations()

    def _update_routing_formations(self):
        current_sims = len(self)
        formation = self.formation_tuning.choose_formation_based_on_group_size(current_sims)
        if formation is None:
            logger.error('{} was unable to get a routing formation for {} sims.', self, current_sims)
            return
        logger.debug('_update_routing_formations: using formation {}.', str(formation))
        self.anchor.routing_component.clear_routing_slaves()
        leader_sim = self.group_leader_sim
        if leader_sim in self:
            formation(self.anchor, leader_sim, interaction=self._formation_si_map[leader_sim])
        for group_sim in self:
            if group_sim is not leader_sim:
                formation(self.anchor, group_sim, interaction=self._formation_si_map[group_sim])
        self._routing_formation_needs_update = False

    def _update_formation_offsets(self, path):
        if path is None:
            return
        self._formation_offset_map.clear()
        leader_sim = self.group_leader_sim
        slave_datas = list(self.anchor.routing_component.get_routing_slave_data())
        if not slave_datas:
            logger.error('No slave data in formation_group _update_formation_offsets')
            return
        formation = slave_datas.pop(0)
        if leader_sim is not None:
            self._formation_offset_map[leader_sim] = formation.formation_routing_type.formation_offsets[0]
            logger.assert_log(formation.slave is leader_sim, "leader sim isn't in 0th position in formation_group _update_formation_offsets")
        if not slave_datas:
            return
        available_slave_slots = [(formation.formation_routing_type.formation_offsets[index], index) for index in range(1, len(formation.formation_routing_type.formation_offsets))]
        available_slave_slots.sort(key=lambda x: x[0].magnitude_squared(), reverse=True)
        max_dist_squared = available_slave_slots[0][0].magnitude_squared()
        for (transform, _, _) in path.get_location_data_along_path_gen(time_step=0.5, start_time=0.5):
            translation = transform.translation
            for slave_data in slave_datas:
                if (slave_data.slave.location.transform.translation - translation).magnitude_2d_squared() < max_dist_squared:
                    break
            break
        return
        while available_slave_slots and slave_datas:
            (offset, index) = available_slave_slots.pop()
            offset3 = sims4.math.Vector3(offset.x, 0, offset.y)
            offset_position = transform.transform_point(offset3)
            nearest_slave_data = None
            nearest_distance_squared = sims4.math.MAX_FLOAT
            for slave_data in slave_datas:
                distance_squared = (slave_data.slave.location.transform.translation - offset_position).magnitude_2d_squared()
                if distance_squared < nearest_distance_squared:
                    nearest_slave_data = slave_data
                    nearest_distance_squared = distance_squared
            nearest_slave_data.set_formation_offset_index(index)
            slave_datas.remove(nearest_slave_data)
            self._formation_offset_map[nearest_slave_data.slave] = offset
            if type(nearest_slave_data) is not type(formation):
                logger.error('Slaves in formation group not using the same formation, formation A: {}, formation B: {}', type(nearest_slave_data), type(formation))
        if slave_datas:
            logger.error("Didn't update all slaves offset index")
        self._adjust_group_constraints(routing_location=path.final_location)

    def route_to_waypoint(self, waypoint_ids):
        object_routing_component = self.anchor.routing_component.get_object_routing_component()
        object_routing_component.locators = waypoint_ids
        self._start_routing()

    def _start_routing(self):
        logger.debug('FormationSocialGroup start routing.')
        self._route_duration = None
        self._planned_route_events = defaultdict(list)
        self._process_pending_routing_formation_updates()
        self._state = FormationSocialGroupState.ROUTING
        self.anchor.routing_component.on_set_routing_path.register(self._update_formation_offsets)
        on_state = self.routing_object_on_state
        self.anchor.routing_component.pathplan_context.add_path_boundary_obstacle = True
        self.anchor.state_component.set_state(on_state.state, on_state, force_update=True)

    def stop_routing(self):
        logger.debug('FormationSocialGroup stop routing.')
        self._planned_route_events = None
        self._state = FormationSocialGroupState.PAUSED
        off_state = self.routing_object_off_state
        self.anchor.state_component.set_state(off_state.state, off_state)
        self._process_pending_routing_formation_updates()
        self.anchor.routing_component.on_set_routing_path.unregister(self._update_formation_offsets)
        self._adjust_group_constraints()

    def _adjust_group_constraints(self, routing_location=None):
        if routing_location is None:
            routing_location = self.anchor.routing_location
        self._try_adjusting_constraint_to_location(routing_location.position, routing_location.routing_surface, force_adjust=True)
        for group_sim in self:
            for si in group_sim.get_all_running_and_queued_interactions():
                if si.transition is not None and si.social_group is not self:
                    logger.debug('Derailing si {} transition due to constraint change from social group stop_routing().', si)
                    si.transition.derail(DerailReason.CONSTRAINTS_CHANGED, group_sim)

    def _populate_planned_route_events(self, start_time, end_time):
        formation_sims = list(self._formation_offset_map)
        weighted_events_dict = {}
        while start_time < end_time:
            random.shuffle(formation_sims)
            actor = formation_sims[0]
            actor_offset = self._formation_offset_map[actor]
            for target in islice(formation_sims, 1, None):
                target_offset = self._formation_offset_map[target]
                delta_offset = target_offset - actor_offset
                delta_offset.y = abs(delta_offset.y)
                angle = abs(sims4.math.rad_to_deg(sims4.math.atan2(delta_offset.x, delta_offset.y)))
                if angle > self.minimum_paired_angle:
                    break
            resolver = DoubleSimResolver(actor.sim_info, target.sim_info)
            target_resolver = DoubleSimResolver(actor.sim_info, target.sim_info)
            weighted_events = weighted_events_dict.get((actor, target))
            if weighted_events is None:
                weighted_events = []
                for routing_event_tuple in self.routing_events:
                    if routing_event_tuple.actor_event.test(resolver) and routing_event_tuple.target_event.test(target_resolver):
                        weighted_events.append((routing_event_tuple.weight, routing_event_tuple))
                weighted_events_dict[(actor, target)] = weighted_events
            if weighted_events:
                routing_event_tuple = sims4.random.weighted_random_item(weighted_events)
                if random.random() <= routing_event_tuple.chance.get_chance(resolver):
                    actor_event = routing_event_tuple.actor_event(provider=self, provider_required=True, time=start_time, actor=actor)
                    target_event = routing_event_tuple.target_event(provider=self, provider_required=True, time=start_time, actor=target)
                    actor_event.paired_event = target_event
                    target_event.paired_event = actor_event
                    self._planned_route_events[actor].append(actor_event)
                    self._planned_route_events[target].append(target_event)
            start_time += self.routing_event_delay.random_float()

    def provide_route_events(self, route_event_context, sim, path, start_time=0, **kwargs):
        if self._planned_route_events is None:
            return
        if path.sim is not self.anchor:
            return
        if len(self) < 2:
            return
        duration = path.duration()
        if self._route_duration != duration:
            self._planned_route_events = defaultdict(list)
            self._route_duration = duration
        if not self._planned_route_events:
            self._populate_planned_route_events(start_time, duration)
        for route_event in self._planned_route_events[sim]:
            if route_event.processed:
                pass
            elif route_event.time < start_time:
                pass
            elif route_event_context.route_event_already_scheduled(type(route_event), provider=self, time=route_event.time, epsilon_override=EPSILON):
                pass
            else:
                route_event_context.add_route_event(RouteEventType.HIGH_SINGLE, route_event)

    def is_route_event_valid(self, route_event, time, sim, path):
        return sim in self and route_event.paired_event.actor in self
lock_instance_tunables(FormationSocialGroup, adjust_sim_positions_dynamically=False, social_anchor_object=None)