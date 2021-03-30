from event_testing.resolver import SingleSimResolver, GlobalResolverfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom routing.route_enums import RoutingStageEventfrom routing.waypoints.tunable_waypoint_graph import TunableWaypointGraphSnippet, TunableWaypointWeightedSetfrom routing.waypoints.waypoint_generator_locators import LocatorIdToWaypointGeneratorfrom sims4.random import weighted_random_itemfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableRange, TunableList, TunableReference, TunableMapping, TunableLocator, TunableTuple, TunableSimMinute, OptionalTunable, TunableSetfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import CommonSituationState, CommonInteractionStartingSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, SituationStatefrom situations.situation_types import SituationCreationUIOptionimport sims4import servicesfrom socials.formation_group import FormationSocialGroupfrom tunable_multiplier import TunableMultiplierfrom zone_types import ZoneStatelogger = sims4.log.Logger('Group Waypoint Situation', default_owner='jmorrow')
class _StartSoloSituationState(SituationState):

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        super()._on_set_sim_role_state(sim, job_type, role_state_type, role_affordance_target)
        if job_type is self.owner.leader_job_and_role.job:
            self.owner.begin_routing()

class _GroupWaypointStartState(CommonInteractionStartingSituationState):
    min_required_member_sims = 1
    min_required_group_sims = 2

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

    def timer_expired(self):
        num_group_sims = len(self.owner.social_group)
        if self.owner.get_num_sims_in_job(self.owner.leader_job_and_role.job) > 0 and self.owner.get_num_sims_in_job(self.owner.member_job_and_role.job) >= _GroupWaypointStartState.min_required_member_sims and num_group_sims >= _GroupWaypointStartState.min_required_group_sims:
            self.owner.begin_routing()
        else:
            self.owner.on_failure_shutdown()

    def on_leader_sim_removed_from_social_group(self):
        logger.debug('Leader sim removed from situation. Shutting down.')
        self.owner._self_destruct()

class _GroupWaypointRouteState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown_situation_on_route_end = False

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if reader is None:
            self.owner.route_to_waypoint()
        else:
            services.current_zone().register_callback(ZoneState.HITTING_THEIR_MARKS, self._on_zone_state_hitting_their_marks)

    def _on_zone_state_hitting_their_marks(self):
        if self.owner is not None:
            self.owner.route_to_waypoint()

    def _route_to_next_waypoint(self):
        if self.owner.choose_next_waypoint():
            self.owner.route_to_waypoint()

    def on_route_end(self, *args, **kwargs):
        at_waypoint = self.owner.current_waypoint
        logger.debug('_on_route_end(): arrived at waypoint {}', at_waypoint)
        if self._shutdown_situation_on_route_end:
            self.owner._self_destruct()
        elif self.owner._next_interaction is not None:
            self.owner.start_interacting()
        else:
            self._route_to_next_waypoint()

    def on_leader_sim_removed_from_social_group(self):
        logger.debug('Leader sim removed from situation. Will shut down when route ends.')
        self._shutdown_situation_on_route_end = True

class _GroupWaypointInteractState(CommonSituationState):
    POST_INTERACTION_DELAY_TIMEOUT = 'post_interaction_delay_timeout'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._num_queued_interactions = 0
        self._post_interaction_delay = 0
        self._timeout_handle = None
        self._zone_callback = False

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        (leader_interaction, member_interaction, post_interaction_delay, target_object_definition) = self.owner._next_interaction
        if leader_interaction is not None:
            self._test_event_register(TestEvent.InteractionExitedPipeline, leader_interaction)
        if member_interaction is not None:
            self._test_event_register(TestEvent.InteractionExitedPipeline, member_interaction)
        if reader is None:
            if leader_interaction is None and member_interaction is None:
                self._route_to_next_waypoint()
                return
            logger.debug('doing interactions at waypoint {}', self.owner.current_waypoint)
            self._perform_interactions(leader_interaction, member_interaction, target_object_definition, post_interaction_delay)
            if self._num_queued_interactions == 0:
                self._route_to_next_waypoint()
        else:
            services.current_zone().register_callback(ZoneState.RUNNING, self._on_zone_running)
            self._zone_callback = True

    def _on_zone_running(self):
        self._zone_callback = False
        self._num_queued_interactions = 0
        (leader_interaction, member_interaction, *_) = self.owner._next_interaction
        if leader_interaction is not None:
            leader_sim = self.owner.leader_sim
            if leader_sim is not None:
                for si in leader_sim.si_state:
                    if type(si) is leader_interaction:
                        self._num_queued_interactions += 1
                        break
            else:
                logger.error('Leader sim is None in group_waypoint_situation _on_zone_running.  Should be: {}', self.owner.guest_list.host_sim_info)
                self.owner.on_completed()
                return
        if member_interaction is not None:
            for sim in self.owner.all_sims_in_job_gen(self.owner.member_job_and_role.job):
                for si in sim.si_state:
                    if type(si) is member_interaction:
                        self._num_queued_interactions += 1
                        break
        if self._num_queued_interactions == 0:
            self._route_to_next_waypoint()

    def on_deactivate(self):
        if self._zone_callback:
            services.current_zone().unregister_callback(ZoneState.RUNNING, self._on_zone_running)
        if self._timeout_handle is not None:
            self._cancel_alarm(self._timeout_handle)
            self._timeout_handle = None
        super().on_deactivate()

    def _perform_interactions(self, leader_interaction, member_interaction, target_object_definition, post_interaction_delay):
        self._num_queued_interactions = 0
        self._post_interaction_delay = post_interaction_delay
        if target_object_definition is None:
            target_object = None
        else:
            target_object = next(services.object_manager().get_objects_of_type_gen(target_object_definition), None)
            if target_object is None:
                logger.warn('Failed to find target object {} for interaction in {}', target_object_definition, self)
                return
        if leader_interaction is not None:
            self._perform_interaction_on_sim(self.owner.leader_sim, target_object, leader_interaction)
        if self.owner is None:
            return
        if member_interaction is not None:
            for member_sim in self.owner.all_sims_in_job_gen(self.owner.member_job_and_role.job):
                self._perform_interaction_on_sim(member_sim, target_object, member_interaction)

    def _perform_interaction_on_sim(self, sim, target, interaction_type):
        interaction_context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True)
        enqueue_result = sim.push_super_affordance(interaction_type, target, interaction_context)
        if enqueue_result and enqueue_result.interaction.is_finishing:
            logger.warn('Failed to push interaction {} on sim {}. Enqueue result = {}', interaction_type, sim, enqueue_result)
            return
        logger.debug('Pushed {} successfully on {}', interaction_type, sim)
        self._num_queued_interactions += 1

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionExitedPipeline:
            for sim in tuple(self.owner.all_sims_in_situation_gen()):
                if sim.id != sim_info.sim_id:
                    pass
                else:
                    interaction = resolver.interaction
                    continuation_id = interaction.id if not interaction.continuation_id else interaction.continuation_id
                    continuation_interaction = sim.find_continuation_by_id(continuation_id)
                    if continuation_interaction is not None:
                        self._test_event_register(TestEvent.InteractionExitedPipeline, continuation_interaction.affordance)
                        return
                    logger.debug('Interaction complete for {}', sim_info)
                    self._on_interaction_complete()

    def _on_interaction_complete(self):
        self._num_queued_interactions -= 1
        if self._num_queued_interactions <= 0:
            if self._post_interaction_delay > 0:
                self._timeout_handle = self._create_or_load_alarm(self.POST_INTERACTION_DELAY_TIMEOUT, self._post_interaction_delay, self._route_to_next_waypoint, should_persist=True)
            else:
                self._route_to_next_waypoint()

    def _route_to_next_waypoint(self, *args):
        if self.owner.choose_next_waypoint():
            self.owner._change_state(self.owner.route_state())

    def on_leader_sim_removed_from_social_group(self):
        logger.debug('Leader sim removed from situation. Shutting down.')
        self.owner._self_destruct()

    def timer_expired(self):
        self._route_to_next_waypoint()
PREVIOUS_WAYPOINT_TOKEN = 'previous_waypoint'CURRENT_WAYPOINT_TOKEN = 'current_waypoint'NUM_VISITED_WAYPOINTS_TOKEN = 'num_visited_waypoints'NEXT_LEADER_INTERACTION_ID = 'next_leader_interaction_id'NEXT_MEMBER_INTERACTION_ID = 'next_member_interaction_id'NEXT_POST_INTERACTION_DELAY_TIME = 'next_post_interaction_delay_time'NEXT_INTERACTION_TARGET_OBJECT_DEF_ID = 'next_interaction_target_object_def_id'
class GroupWaypointSituation(SituationComplexCommon):
    INFINITE_WAYPOINTS = 0
    INSTANCE_TUNABLES = {'waypoint_graph': TunableWaypointGraphSnippet(description='\n            Defines the waypoints and connections between them.\n            ', tuning_group=GroupNames.ROUTING), 'starting_waypoint': TunableWaypointWeightedSet.TunableFactory(description='\n            Waypoint for the generator to start at (will choose one based on the tests/weights).\n            ', tuning_group=GroupNames.ROUTING), 'ending_waypoints': TunableSet(description='\n            Waypoints to end at.  Will end at the first one encountered after \n            meeting the tuned minimum number of waypoints.\n            ', tunable=TunableLocator(description='\n                Waypoint reference.\n                '), tuning_group=GroupNames.ROUTING), 'max_waypoints': TunableRange(description='\n            The maximum number of waypoints to visit. Set to 0 to keep going until and ending_waypoint is reached.\n            ', tunable_type=int, default=0, minimum=0, maximum=100, tuning_group=GroupNames.ROUTING), 'min_waypoints': TunableRange(description="\n            The minimum number of waypoints to visit.  Won't stop at reaching\n            an ending waypoint until visited minimum number of waypoints.\n            (Unless fails to connect from there to another waypoint)\n            ", tunable_type=int, default=2, minimum=2, tuning_group=GroupNames.ROUTING), 'max_waypoints_per_route': TunableRange(description='\n            If there is no interaction available at the next waypoint, the\n            situation will try to build a route through that waypoint rather \n            than ending the route at that waypoint. This tunable puts a limit\n            on how many waypoints the situation will try to stitch together\n            into a single route. Without this limit, the situation could enter\n            an endless loop. \n            ', tunable_type=int, default=4, minimum=1, tuning_group=GroupNames.ROUTING), 'interaction_tuning': TunableMapping(description='\n            Mapping of waypoint ids to groups interactions to run at them. Interactions can be tuned for the leader,\n            members, or both, along with an optional delay to pause before resuming routing. Also able to specify a\n            weight for each choice so tested and weighted choices can be made. \n            ', key_name='waypoint_id', key_type=TunableLocator(), value_name='interactions', value_type=TunableList(description='\n                List of one or more interactions to perform at this waypoint.\n                ', tunable=TunableTuple(description='\n                    Defines interaction behavior at this waypoint, along with a weight for choosing.\n                    ', leader_interaction=OptionalTunable(description='\n                        Optional interaction to push on the leader of the group.\n                        ', tunable=TunableReference(description='\n                            Interaction to push on the leader of the group.\n                            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',))), member_interaction=OptionalTunable(description='\n                        Optional interaction to push on the members of the group (excluding the leader).\n                        ', tunable=TunableReference(description='\n                            Interaction to push on the members of the group (excluding the leader).\n                            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',))), target_object_definition=OptionalTunable(description='\n                        If enabled, gives a target object for the leader\n                        and member interactions.\n                        ', tunable=TunableReference(description='\n                            A target object for the leader and member \n                            interactions.\n                            ', manager=services.definition_manager())), post_interaction_delay=TunableSimMinute(description='\n                        How long to wait after the interaction(s) complete before moving on to the next waypoint.\n                        0 means no delay.\n                        ', default=0, minimum=0), weight=TunableMultiplier.TunableFactory(description='\n                        A weight with testable multipliers that is used to \n                        determine how likely this entry is to be picked when \n                        selecting randomly.\n                        ')))), 'starting_state': _GroupWaypointStartState.TunableFactory(description='\n            State that runs while the Sims are routing to the next waypoint.\n            ', display_name='1. Start State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'route_state': _GroupWaypointRouteState.TunableFactory(description='\n            State that runs while the Sims are routing to the next waypoint.\n            ', display_name='2. Route State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'interact_state': _GroupWaypointInteractState.TunableFactory(description='\n            State that runs while the Sims are interacting with a point-of-interest at a waypoint.\n            ', display_name='3. Interact State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leader_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the leader.\n            '), 'member_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the (non-leader) group members.\n            '), 'npc_go_home_interaction': OptionalTunable(description='\n            Optional interaction to push on NPCs to send them "home" when the situation ends.\n            ', tunable=TunableReference(description='\n                Interaction to push on NPCs to send them "home" when the situation ends.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',))), 'solo_waypoint_interaction': TunableReference(description='\n            Interaction that routes a solo sim from point to point when they\n            are not in a group.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('WaypointInteraction',)), 'solo_waypoint_generator': LocatorIdToWaypointGenerator.TunableFactory(description='\n            Waypoint generator for interaction that routes a solo sim from \n            point to point.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._social_group = None
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self.current_waypoint = None
            self.current_waypoint_sequence = []
            self.previous_waypoint = None
            self._num_visited_waypoints = 0
            self._next_interaction = None
        else:
            self.current_waypoint = reader.read_uint32(CURRENT_WAYPOINT_TOKEN, None)
            self.current_waypoint_sequence = [self.current_waypoint]
            self.previous_waypoint = reader.read_uint32(PREVIOUS_WAYPOINT_TOKEN, None)
            self._num_visited_waypoints = reader.read_uint32(NUM_VISITED_WAYPOINTS_TOKEN, 0)
            self._next_interaction = None
            instance_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
            leader_interaction = instance_manager.get(reader.read_uint64(NEXT_LEADER_INTERACTION_ID, None))
            member_interaction = instance_manager.get(reader.read_uint64(NEXT_MEMBER_INTERACTION_ID, None))
            if leader_interaction is not None or member_interaction is not None:
                interaction_delay = reader.read_float(NEXT_POST_INTERACTION_DELAY_TIME, 0)
                target_def_id = reader.read_uint64(NEXT_INTERACTION_TARGET_OBJECT_DEF_ID, 0)
                target_def = services.definition_manager().get(target_def_id)
                self._next_interaction = (leader_interaction, member_interaction, interaction_delay, target_def)
            services.current_zone().register_callback(ZoneState.HITTING_THEIR_MARKS, self._on_zone_state_hitting_their_marks)

    def _on_zone_state_hitting_their_marks(self):
        if self.num_invited_sims > 1 and not self._initialize_social_group():
            self.on_failure_shutdown()
            return

    def choose_interactions_for_waypoint(self, waypoint):
        choices = self.interaction_tuning.get(waypoint, None)
        if not choices:
            return
        resolver = self.get_resolver()
        weighted_choices = tuple((choice.weight.get_multiplier(resolver), (choice.leader_interaction, choice.member_interaction, choice.post_interaction_delay, choice.target_object_definition)) for choice in choices if choice.weight.get_multiplier(resolver) > 0)
        if not weighted_choices:
            return
        return weighted_random_item(weighted_choices)

    @classmethod
    def default_job(cls):
        return cls.member_job_and_role.job

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GroupWaypointStartState, factory=cls.starting_state), SituationStateData(2, _GroupWaypointRouteState, factory=cls.route_state), SituationStateData(3, _GroupWaypointInteractState, factory=cls.interact_state), SituationStateData(4, _StartSoloSituationState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.leader_job_and_role.job, cls.leader_job_and_role.role_state), (cls.member_job_and_role.job, cls.member_job_and_role.role_state)]

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self.current_waypoint is not None:
            writer.write_uint32(CURRENT_WAYPOINT_TOKEN, self.current_waypoint)
        if self.previous_waypoint is not None:
            writer.write_uint32(PREVIOUS_WAYPOINT_TOKEN, self.previous_waypoint)
        writer.write_uint32(NUM_VISITED_WAYPOINTS_TOKEN, self._num_visited_waypoints)
        if self._next_interaction is not None:
            (leader_interaction, member_interaction, delay, object_def) = self._next_interaction
            if leader_interaction is not None:
                writer.write_uint64(NEXT_LEADER_INTERACTION_ID, leader_interaction.guid64)
            if member_interaction is not None:
                writer.write_uint64(NEXT_MEMBER_INTERACTION_ID, member_interaction.guid64)
            writer.write_float(NEXT_POST_INTERACTION_DELAY_TIME, delay)
            if object_def is not None:
                writer.write_uint64(NEXT_INTERACTION_TARGET_OBJECT_DEF_ID, object_def.id)

    def route_to_waypoint(self):
        if self._social_group is not None:
            self._social_group.anchor.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_social_group_route_end)
            self._social_group.route_to_waypoint(self.current_waypoint_sequence)
        else:
            leader_sim = self.leader_sim
            interaction_context = InteractionContext(leader_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
            waypoint_generator = self.solo_waypoint_generator(self.current_waypoint_sequence, self.waypoint_graph.constraint_radius, context=interaction_context, target=None)
            enqueue_result = leader_sim.push_super_affordance(self.solo_waypoint_interaction, None, interaction_context, waypoint_generator=waypoint_generator)
            if enqueue_result and enqueue_result.interaction.is_finishing:
                logger.error('Failed to push interaction {} on sim {}. Enqueue result = {}', self.solo_waypoint_interaction, self.leader_sim, enqueue_result)
                return
            enqueue_result.interaction.register_on_finishing_callback(self._on_solo_waypoint_interaction_finishing)

    def _on_social_group_route_end(self, *args, **kwargs):
        self._social_group.stop_routing()
        anchor = self._social_group.anchor
        if anchor is not None:
            anchor.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_social_group_route_end)
        if type(self._cur_state) == _GroupWaypointRouteState:
            self._cur_state.on_route_end()

    def _on_solo_waypoint_interaction_finishing(self, interaction):
        interaction.unregister_on_finishing_callback(self._on_solo_waypoint_interaction_finishing)
        if type(self._cur_state) == _GroupWaypointRouteState:
            self._cur_state.on_route_end()

    def on_remove(self):
        super().on_remove()
        if self._social_group:
            logger.debug('Shutting down GroupWaypointSituation.')
            self._social_group.shutdown(finishing_type=FinishingType.NATURAL)

    @property
    def leader_sim(self):
        return next(self.all_sims_in_job_gen(self.leader_job_and_role.job), None)

    @property
    def social_group(self):
        return self._social_group

    def _initialize_social_group(self):
        host = self.guest_list.host_sim
        if host is None:
            logger.error('No host sim for GroupWaypointSituation._initialize_social_group()')
            return False
        social_group = host.get_main_group()
        if social_group is None:
            logger.error('No social group found for GroupWaypointSituation._initialize_social_group()')
            return False
        if not isinstance(social_group, FormationSocialGroup):
            logger.error('Host social group is not a FormationSocialGroup in GroupWaypointSituation._initialize_social_group()')
            return False
        social_group.set_situation(self)
        self._social_group = social_group
        return True

    def start_situation(self):
        super().start_situation()
        if self.num_invited_sims > 1:
            if not self._initialize_social_group():
                self.on_failure_shutdown()
                return
            self._change_state(self.starting_state())
        else:
            self._change_state(_StartSoloSituationState())

    def get_resolver(self):
        if self.leader_sim is not None:
            return SingleSimResolver(self.leader_sim)
        else:
            logger.error("Requested a resolver but we don't have a leader_sim (yet?). Using global resolver instead.")
            return GlobalResolver()

    def on_sim_added_to_social_group(self):
        if type(self._cur_state) == _GroupWaypointStartState and self.num_of_sims >= self.num_invited_sims:
            self.on_all_sims_spawned()

    def on_sim_removed_from_social_group(self, sim, finishing_type):
        if sim is self.leader_sim:
            if self._cur_state is None:
                logger.debug('Leader sim removed from situation. Shutting down.')
                self._self_destruct()
            else:
                self._cur_state.on_leader_sim_removed_from_social_group()
        elif finishing_type is not FinishingType.SOCIALS:
            self.remove_sim_from_situation(sim)

    def on_all_sims_spawned(self):
        if self._social_group is not None:
            num_group_sims = len(self._social_group)
            if num_group_sims >= self.num_invited_sims:
                self.begin_routing()

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        super()._on_set_sim_role_state(sim, job_type, role_state_type, role_affordance_target)
        if self.num_invited_sims == 1 and job_type is not self.leader_job_and_role.job:
            logger.error('{} has no leader sim. Ending GroupWaypointSituation.', str(self))
            self.on_failure_shutdown()

    def begin_routing(self):
        if self.choose_next_waypoint():
            self._change_state(self.route_state())

    def choose_next_waypoint(self):
        if self.current_waypoint is not None:
            self._num_visited_waypoints += len(self.current_waypoint_sequence)
            if self._num_visited_waypoints >= self.max_waypoints and self.max_waypoints is not self.INFINITE_WAYPOINTS:
                logger.debug('Fulfilled exit condition of GroupWaypointSituation. Visited {} waypoints. Ending situation.', self._num_visited_waypoints)
                self.on_completed()
                return False
            if self.current_waypoint in self.ending_waypoints and self._num_visited_waypoints >= self.min_waypoints:
                logger.debug('Fulfilled exit condition of GroupWaypointSituation. Reached and end waypoint. Ending situation.')
                self.on_completed()
                return False
        resolver = self.get_resolver()
        self.current_waypoint_sequence = []
        self._next_interaction = None
        waypoint_budget = self.max_waypoints_per_route
        if self.max_waypoints is not self.INFINITE_WAYPOINTS:
            max_waypoints_still_to_visit = self.max_waypoints - self._num_visited_waypoints
            if max_waypoints_still_to_visit < waypoint_budget:
                waypoint_budget = max_waypoints_still_to_visit
        current_count = self._num_visited_waypoints
        if waypoint_budget > 0:
            if self.current_waypoint is None:
                (next_waypoint, _) = self.starting_waypoint.choose(self.waypoint_graph, self.leader_sim.routing_surface, resolver=resolver)
            else:
                connections = self.waypoint_graph.connections.get(self.current_waypoint, None)
                if connections is None:
                    if self.current_waypoint not in self.ending_waypoints:
                        logger.error('Tuning Error: Encountered waypoint {} with no connections. Shutting down the situation {}.', self.current_waypoint, self)
                    elif current_count < self.min_waypoints:
                        logger.error('Tuning Error: Encountered end waypoint {} with no connections before reaching minimum waypoints of {}. Shutting down the situation {}.', self.current_waypoint, self.min_waypoints, self)
                    else:
                        logger.debug('Fulfilled exit condition of GroupWaypointSituation. Reached end waypoint. Ending situation {}.', self)
                    self.on_completed()
                    return False
                (next_waypoint, _) = connections.choose(self.waypoint_graph, self.leader_sim.routing_surface, resolver=resolver, previous_waypoint=self.previous_waypoint)
            if next_waypoint is None:
                if self.current_waypoint_sequence:
                    return True
                if self.current_waypoint not in self.ending_waypoints:
                    logger.error("Tuning Error: Encountered waypoint {} with no valid next waypoint and it isn't the ending waypoint in {}.", self.current_waypoint, self)
                elif current_count < self.min_waypoints:
                    logger.error('Tuning Error: Encountered end waypoint {} with no valid next waypoint before reaching minimum waypoints of {} in {}.', self.current_waypoint, self.min_waypoints, self)
                else:
                    logger.debug('Fulfilled exit condition of GroupWaypointSituation. Reached end waypoint. Ending situation {}.', self)
                self.on_completed()
                return False
            self.previous_waypoint = self.current_waypoint
            self.current_waypoint = next_waypoint
            self.current_waypoint_sequence.append(self.current_waypoint)
            waypoint_budget -= 1
            current_count += 1
            self._next_interaction = self.choose_interactions_for_waypoint(self.current_waypoint)
            logger.debug('choose_next_waypoint(): at_waypoint = {} next_waypoint = {}', self.previous_waypoint, next_waypoint)
            if self.current_waypoint in self.ending_waypoints and current_count >= self.min_waypoints:
                break
        return True

    def start_interacting(self):
        self._change_state(self.interact_state())

    def on_completed(self):
        logger.debug('Group waypoint situation completed.')
        npcs = [sim for sim in self.all_sims_in_job_gen(self.member_job_and_role.job) if sim.is_npc]
        self._self_destruct()
        self._send_npcs_home(npcs)

    def on_failure_shutdown(self):
        logger.debug('Group waypoint situation failed.')
        self._self_destruct()

    def _send_npcs_home(self, npcs):
        if self.npc_go_home_interaction is not None:
            for npc_sim in npcs:
                interaction_context = InteractionContext(npc_sim, InteractionContext.SOURCE_SCRIPT, Priority.Low)
                enqueue_result = npc_sim.push_super_affordance(self.npc_go_home_interaction, None, interaction_context)
                if enqueue_result:
                    if enqueue_result.interaction.is_finishing:
                        logger.warn('Failed to push go home interaction {} on npc sim {}. Enqueue result = {}', self.npc_go_home_interaction, npc_sim, enqueue_result)
                logger.warn('Failed to push go home interaction {} on npc sim {}. Enqueue result = {}', self.npc_go_home_interaction, npc_sim, enqueue_result)
lock_instance_tunables(GroupWaypointSituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)