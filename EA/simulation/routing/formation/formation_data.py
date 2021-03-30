from distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import DoubleObjectResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom objects.components.types import IDLE_COMPONENTfrom routing.formation.formation_behavior import RoutingFormationBehaviorfrom routing.formation.formation_liability import RoutingFormationLiabilityfrom routing.formation.formation_type_follow import FormationTypeFollowfrom routing.formation.formation_type_paired import FormationTypePairedfrom routing.route_enums import RoutingStageEventfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom routing.walkstyle.walkstyle_tuning import TunableWalkstylefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableReference, TunableMapping, Tunable, TunableVariant, TunableList, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableTuple, TunableSetfrom sims4.utils import classpropertyfrom snippets import define_snippet, ROUTING_FORMATION_LISTfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport servicesimport sims4.logimport snippetslogger = sims4.log.Logger('RoutingFormations', default_owner='rmccord')
class RoutingFormation(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.snippet_manager()):
    INSTANCE_TUNABLES = {'formation_behavior': RoutingFormationBehavior.TunableFactory(), 'formation_routing_type': TunableVariant(description='\n            The purpose of the routing formation which governs how the slave\n            behaves on routes.\n            ', follow=FormationTypeFollow.TunableFactory(), paired=FormationTypePaired.TunableFactory(), default='follow'), 'formation_compatibility': TunableWhiteBlackList(description='\n            This routing formation is able to coexist with any other formation\n            listed here. For example, "Walk Dog" on the right side of a Sim is\n            compatible with "Walk Dog" on their left side (and vice-versa).\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RoutingFormation',), pack_safe=True)), 'formation_tests': TunableTestSet(description='\n            A test set to determine whether or not the master and slave can be\n            in a formation together.\n            \n            Master: Participant Actor\n            Slave: Participant Slave\n            '), 'walkstyle_mapping': TunableMapping(description='\n            Mapping of Master walkstyles to Slave walkstyles. This is how we\n            ensure that slaves use a walkstyle to keep pace with their masters.\n            \n            Note you do not need to worry about combo replacement walkstyles\n            like GhostRun or GhostWalk. We get the first non-combo from the\n            master and apply the walkstyle to get any combos from the slave.\n            ', key_type=TunableWalkstyle(description='\n                The walkstyle that the master must be in to apply the value\n                walkstyle to the slave.\n                '), value_type=WalkStyleRequest.TunableFactory(), key_name='Master Walkstyle', value_name='Slave Walkstyle Request'), 'should_increase_master_agent_radius': Tunable(description="\n            If enabled, we combine the slave's agent radius with the master's.\n            ", tunable_type=bool, default=True), 'allow_slave_to_teleport_with_master': Tunable(description='\n            If enabled, when the master teleports using a teleport style, the \n            slave will also be teleported nearby.  If this is false, the master\n            cannot use teleport styles at all while they have a routing slave\n            using this data.\n            ', tunable_type=bool, default=False), 'require_interaction_compatibility': Tunable(description='\n            If enabled, an interaction will always require compatibility with \n            the owning interaction to run while the master is routing, even if\n            the owning interaction is no longer in the sims SI_State.\n            ', tunable_type=bool, default=True), 'affordances_pause_slave_routing': OptionalTunable(description="\n            Master sim queued/running these affordances on the slave will temporarily pause slave routing.\n            \n            One use case is we can tune Droids social interactions here so when Sims have a Droid following them,\n            they can run these social interactions without triggering Droid's routing, otherwise the Droid will\n            constantly route to the back of the master and the master Sim can never social with them. \n            ", tunable=TunableTuple(affordances=TunableSet(tunable=TunableReference(services.affordance_manager(), pack_safe=True)), affordance_lists=TunableSet(tunable=snippets.TunableAffordanceListReference())))}

    def __init__(self, master, slave, *args, interaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._master = master
        self._slave = slave
        self._interaction = interaction
        self._routing_type = self.formation_routing_type(self._master, self._slave, self.formation_type)
        self._formation_behavior = self.formation_behavior(master, slave)
        self._all_affordances_pause_slave_routing = None
        if interaction is not None:
            formation_liability = RoutingFormationLiability(self)
            interaction.add_liability(formation_liability.LIABILITY_TOKEN, formation_liability)
            master.routing_component.add_routing_slave(self)
        else:
            logger.callstack('Routing Formation created without an interaction, this should not happen. Slave: {} Master: {} Formation: {}', slave, master, self)
            self.release_formation_data()

    @classmethod
    def test_formation(cls, master, slave):
        resolver = DoubleObjectResolver(master, slave)
        return cls.formation_tests.run_tests(resolver)

    @classproperty
    def formation_type(cls):
        return cls

    @property
    def interaction(self):
        return self._interaction

    @property
    def required_interaction(self):
        if self.require_interaction_compatibility and self.master is not None and self.master.routing_component.is_moving:
            return self._interaction

    @property
    def master(self):
        return self._master

    @property
    def slave(self):
        return self._slave

    @classproperty
    def max_slave_count(cls):
        return cls.formation_routing_type.factory.get_max_slave_count(cls.formation_routing_type)

    @property
    def offset(self):
        return self._routing_type.offset

    @property
    def route_length_minimum(self):
        return self._routing_type.route_length_minimum

    @property
    def all_affordances_pause_slave_routing(self):
        if self._all_affordances_pause_slave_routing is None:
            if self.affordances_pause_slave_routing:
                self._all_affordances_pause_slave_routing = set([affordance for affordance in self.affordances_pause_slave_routing.affordances])
                for affordance_list in self.affordances_pause_slave_routing.affordance_lists:
                    self._all_affordances_pause_slave_routing.update([affordance for affordance in affordance_list])
            else:
                self._all_affordances_pause_slave_routing = set()
        return self._all_affordances_pause_slave_routing

    def on_add(self):
        self.master.register_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_master_route_start)
        self.master.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_master_route_end)
        self._formation_behavior.on_add()
        services.get_event_manager().process_event(TestEvent.RoutingFormationStarted, slave=self.slave, master=self.master)

    def on_release(self):
        self._routing_type.on_release()
        self._formation_behavior.on_release()
        self.master.unregister_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_master_route_start)
        self.master.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_master_route_end)

    def attachment_info_gen(self):
        yield from self._routing_type.attachment_info_gen()

    def _on_master_route_start(self, *_, **__):
        self._routing_type.on_master_route_start()

    def _on_master_route_end(self, *_, **__):
        self._routing_type.on_master_route_end()
        slave_idle_component = self.slave.get_component(IDLE_COMPONENT)
        if slave_idle_component is not None:
            slave_idle_component.reapply_idle_state()

    def get_routing_slave_constraint(self):
        return self._routing_type.get_routing_slave_constraint()

    def get_walkstyle_override(self):
        walkstyle_request = self.walkstyle_mapping.get(self.master.get_walkstyle())
        slaved_walkstyle = self._slave.get_walkstyle()
        if walkstyle_request is not None:
            with self._slave.routing_component.temporary_walkstyle_request(walkstyle_request):
                slaved_walkstyle = self._slave.get_walkstyle()
        return slaved_walkstyle

    def find_good_location_for_slave(self, master_location):
        return self._routing_type.find_good_location_for_slave(master_location)

    def add_routing_slave_to_pb(self, route_pb, path=None):
        slave_pb = route_pb.slaves.add()
        slave_pb.id = self._slave.id
        slave_pb.type = self._routing_type.slave_attachment_type
        walkstyle_override_msg = slave_pb.walkstyle_overrides.add()
        walkstyle_override_msg.from_walkstyle = 0
        walkstyle_override_msg.to_walkstyle = self.get_walkstyle_override()
        for (from_walkstyle, to_walkstyle_request) in self.walkstyle_mapping.items():
            walkstyle_override_msg = slave_pb.walkstyle_overrides.add()
            walkstyle_override_msg.from_walkstyle = from_walkstyle
            with self._slave.routing_component.temporary_walkstyle_request(to_walkstyle_request):
                walkstyle_override_msg.to_walkstyle = self._slave.get_walkstyle()
        for attachment_node in self.attachment_info_gen():
            with ProtocolBufferRollback(slave_pb.offset) as attachment_pb:
                attachment_node.populate_attachment_pb(attachment_pb)
        self._routing_type.build_routing_slave_pb(slave_pb, path=path)
        return (self._slave, slave_pb)

    def release_formation_data(self):
        self._routing_type.on_release()
        if self._master.routing_component is not None:
            self._master.routing_component.clear_slave(self._slave)

    def should_slave_for_path(self, path):
        return self._routing_type.should_slave_for_path(path)

    def has_affordance_pause_slave_routing(self):
        if self.all_affordances_pause_slave_routing:
            for interaction in self.master.running_interactions_with_target_gen(self.slave):
                if interaction.affordance in self.all_affordances_pause_slave_routing:
                    return True
        return False

    def update_slave_position(self, master_transform, master_orientation, routing_surface, distribute=True, path=None, canceled=False):
        self._routing_type.update_slave_position(master_transform, master_orientation, routing_surface, distribute=distribute, path=path, canceled=canceled)

    def set_formation_offset_index(self, index):
        self._routing_type.set_formation_offset_index(index)

class RoutingFormationList(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'formations': TunableList(description="\n            A list of routing formations. One will be chosen based on the number of members of the group.\n            It will use the closest match based on the number of offsets in the formation.\n            Note that you will generally always want to use the 'follow' formation type here.\n            ", tunable=RoutingFormation.TunableReference(), minlength=1)}

    def choose_formation_based_on_group_size(self, desired_size):
        closest_formation = None
        closest_size_delta = None
        for formation in self.formations:
            formation_size = formation.max_slave_count
            if formation_size == desired_size:
                return formation
            size_delta = formation_size - desired_size
            if not closest_size_delta is None:
                if size_delta < closest_size_delta:
                    closest_formation = formation
                    closest_size_delta = size_delta
            closest_formation = formation
            closest_size_delta = size_delta
        return closest_formation
(TunableRoutingFormationListReference, TunableRoutingFormationListSnippet) = define_snippet(ROUTING_FORMATION_LIST, RoutingFormationList.TunableFactory())