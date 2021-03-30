import enumimport placementimport servicesimport sims4.logimport sims4.mathfrom animation.animation_utils import StubActorfrom interactions.constraint_variants import TunableConstraintVariantfrom interactions.constraints import ANYWHEREfrom placement import FGLSearchFlagsDefaultForSim, FGLSearchFlagsDefault, FGLSearchFlag, FindGoodLocationContextfrom postures import DerailReasonfrom protocolbuffers import Routing_pb2from routing.formation.formation_type_base import FormationTypeBase, FormationRoutingTypefrom sims4 import mathfrom sims4.geometry import RelativeFacingRangefrom sims4.math import Vector2, Vector3, MAX_INT32, Quaternionfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import TunableList, Tunable, TunableTuple, TunableInterval, OptionalTunable, TunableRangefrom sims4.utils import classpropertyfrom world.ocean_tuning import OceanTuninglogger = sims4.log.Logger('RoutingFormations', default_owner='rmccord')
class RoutingFormationFollowType(enum.Int, export=False):
    NODE_TYPE_FOLLOW_LEADER = 0
    NODE_TYPE_CHAIN = 1
    NODE_TYPE_FISHTAIL = 2

class _RoutingFormationAttachmentNode:
    __slots__ = ('_parent_offset', '_offset', '_radius', '_angle_constraint', '_flags', '_type', '_noise_behavior', '_spring_behavior')

    def __init__(self, parent_offset:Vector2, offset:Vector2, radius, angle_constraint, flags, node_type, noise_behavior, spring_behavior):
        self._parent_offset = parent_offset
        self._offset = offset
        self._radius = radius
        self._angle_constraint = angle_constraint
        self._flags = flags
        self._type = node_type
        self._noise_behavior = noise_behavior
        self._spring_behavior = spring_behavior

    @property
    def parent_offset(self):
        return self._parent_offset

    @property
    def offset(self):
        return self._offset

    @property
    def radius(self):
        return self._radius

    @property
    def node_type(self):
        return self._type

    def populate_attachment_pb(self, attachment_pb):
        attachment_pb.parent_offset.x = self._parent_offset.x
        attachment_pb.parent_offset.y = self._parent_offset.y
        attachment_pb.offset.x = self._offset.x
        attachment_pb.offset.y = self._offset.y
        attachment_pb.radius = self._radius
        attachment_pb.angle_constraint = self._angle_constraint
        attachment_pb.flags = self._flags
        attachment_pb.type = self._type
        fishtail_pb = attachment_pb.fishtail_behavior
        if self._noise_behavior is not None:
            noise_pb = fishtail_pb.noise_behavior
            noise_pb.octave_count = self._noise_behavior.octave_count
            noise_pb.frequency = self._noise_behavior.frequency
            noise_pb.max_x_distance = self._noise_behavior.max_x_distance
            noise_pb.max_z_distance = self._noise_behavior.max_z_distance
        if self._spring_behavior is not None:
            spring_pb = fishtail_pb.spring_behavior
            spring_pb.tension = self._spring_behavior.tension
            spring_pb.damping = self._spring_behavior.damping
            spring_pb.velocity_scale = self._spring_behavior.velocity_scale

class FormationTypeFollow(FormationTypeBase):
    ATTACH_NODE_RADIUS = 0.25
    ATTACH_NODE_DIAMETER = ATTACH_NODE_RADIUS*2
    ATTACH_NODE_ANGLE = math.PI
    ATTACHMENT_NODE_FLAGS_ATTACHMENT_COLLISION = 1
    ATTACHMENT_NODE_FLAGS_AVOIDANCE_COLLISION = 2
    ATTACHMENT_NODE_FLAGS_STATIC_COLLISION = 4
    ATTACHMENT_NODE_FLAGS_DEFAULT = ATTACHMENT_NODE_FLAGS_STATIC_COLLISION
    RAYTRACE_HEIGHT = 1.5
    RAYTRACE_RADIUS = 0.1
    FACTORY_TUNABLES = {'formation_offsets': TunableList(description='\n            A list of offsets, relative to the master, that define where slaved\n            Sims are positioned.\n            ', tunable=TunableVector2(default=Vector2.ZERO()), minlength=1), 'formation_constraints': TunableList(description='\n            A list of constraints that slaved Sims must satisfy any time they\n            run interactions while in this formation. This can be a geometric\n            constraint, for example, that ensures Sims are always placed within\n            a radius or cone of their slaved position.\n            ', tunable=TunableConstraintVariant(constraint_locked_args={'multi_surface': True}, circle_locked_args={'require_los': False}, disabled_constraints={'spawn_points', 'relative_circle'})), '_route_length_interval': TunableInterval(description='\n            Sims are slaved in formation only if the route is within this range\n            amount, in meters.\n            \n            Furthermore, routes shorter than the minimum\n            will not interrupt behavior (e.g. a socializing Sim will not force\n            dogs to get up and move around).\n            \n            Also routes longer than the maximum will make the slaved sim  \n            instantly position next to their master\n            (e.g. if a leashed dog gets too far from the owner, we place it next to the owner).\n            ', tunable_type=float, default_lower=1, default_upper=20, minimum=0), 'fgl_on_routes': TunableTuple(description='\n            Data associated with the FGL Context on following slaves.\n            ', slave_should_face_master=Tunable(description='\n                If enabled, the Slave should attempt to face the master at the end\n                of routes.\n                ', tunable_type=bool, default=False), height_tolerance=OptionalTunable(description='\n                If enabled than we will set the height tolerance in FGL.\n                ', tunable=TunableRange(description='\n                    The height tolerance piped to FGL.\n                    ', tunable_type=float, default=0.035, minimum=0, maximum=1))), 'noise_behavior': OptionalTunable(description='\n            If enabled, adds smooth random movement to the sim.\n            ', tunable=TunableTuple(octave_count=TunableRange(description="\n                    Controls the detail of the sim's movement. The higher\n                    the octave count, the greater the detail.\n                    ", tunable_type=int, default=1, minimum=1, maximum=10), frequency=Tunable(description="\n                    Controls how frequently a sim's offset from the attachment\n                    node position changes over time due to noise.\n                    ", tunable_type=float, default=0.1), max_x_distance=Tunable(description='\n                    Controls how far in meters a sim will move in the \n                    x-direction away from the attachment node due to random\n                    noise.\n                    ', tunable_type=float, default=1.0), max_z_distance=Tunable(description='\n                    Controls how far in meters a sim will move in the \n                    y-direction away from the attachment node due to random\n                    noise.\n                    ', tunable_type=float, default=1.0))), 'spring_behavior': OptionalTunable(description='\n            If enabled, adds a spring-like behavior that smooths out sim \n            movement by gradually moving them toward a desired position.\n            ', tunable=TunableTuple(tension=Tunable(description='\n                    Controls the stiffness of the spring.\n                    ', tunable_type=float, default=10), damping=Tunable(description='\n                    Controls how the spring returns to rest.\n                    ', tunable_type=float, default=0.7), velocity_scale=Tunable(description='\n                    Controls the speed of the movement.\n                    ', tunable_type=float, default=1)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        formation_count = self.master.get_routing_slave_data_count(self._formation_cls)
        self.set_formation_offset_index(formation_count)
        self._slave_constraint = None
        self._slave_lock = None
        self._final_transform = None

    def set_formation_offset_index(self, index):
        self._attachment_chain = []
        self._formation_offset = self.formation_offsets[index]
        self._setup_right_angle_connections()
        self._offset = Vector3.ZERO()
        for attachment_info in self._attachment_chain:
            self._offset.x = self._offset.x + attachment_info.parent_offset.x - attachment_info.offset.x
            self._offset.z = self._offset.z + attachment_info.parent_offset.y - attachment_info.offset.y

    @classproperty
    def routing_type(cls):
        return FormationRoutingType.FOLLOW

    @property
    def offset(self):
        return self._formation_offset

    @property
    def slave_attachment_type(self):
        return Routing_pb2.SlaveData.SLAVE_FOLLOW_ATTACHMENT

    @staticmethod
    def get_max_slave_count(tuned_factory):
        return len(tuned_factory._tuned_values.formation_offsets)

    @property
    def route_length_minimum(self):
        return self._route_length_interval.lower_bound

    @property
    def route_length_maximum(self):
        return self._route_length_interval.upper_bound

    def attachment_info_gen(self):
        yield from self._attachment_chain

    def on_master_route_start(self):
        self._build_routing_slave_constraint()
        self._lock_slave()
        if self._slave.is_sim:
            master_transition_controller = self.master.transition_controller if self.master.is_sim else None
            for si in self._slave.get_all_running_and_queued_interactions():
                if si.transition is not None and si.transition is not master_transition_controller:
                    si.transition.derail(DerailReason.CONSTRAINTS_CHANGED, self._slave)

    def on_master_route_end(self):
        self._build_routing_slave_constraint()
        if self._slave.is_sim:
            master_transition_controller = self.master.transition_controller if self.master.is_sim else None
            for si in self._slave.get_all_running_and_queued_interactions():
                if si.transition is not None and si.transition is not master_transition_controller:
                    si.transition.derail(DerailReason.CONSTRAINTS_CHANGED, self._slave)
        self._unlock_slave()
        self._final_transform = None

    def _lock_slave(self):
        self._slave_lock = self._slave.add_work_lock(self)

    def _unlock_slave(self):
        self._slave.remove_work_lock(self)

    def _build_routing_slave_constraint(self):
        self._slave_constraint = ANYWHERE
        for constraint in self.formation_constraints:
            constraint = constraint.create_constraint(self._slave, target=self._master, target_position=self._master.intended_position)
            self._slave_constraint = self._slave_constraint.intersect(constraint)

    def get_routing_slave_constraint(self):
        if self._slave_constraint is None or not self._slave_constraint.valid:
            self._build_routing_slave_constraint()
        return self._slave_constraint

    def _add_attachment_node(self, parent_offset:Vector2, offset:Vector2, radius, angle_constraint, flags, node_type, noise_behavior=None, spring_behavior=None):
        attachment_node = _RoutingFormationAttachmentNode(parent_offset, offset, radius, angle_constraint, flags, node_type, noise_behavior, spring_behavior)
        self._attachment_chain.append(attachment_node)

    def find_good_location_for_slave(self, master_location):
        restrictions = []
        fgl_kwargs = {}
        fgl_flags = 0
        fgl_tuning = self.fgl_on_routes
        slave_position = master_location.transform.transform_point(self._offset)
        orientation = master_location.transform.orientation
        routing_surface = master_location.routing_surface
        if routing_surface is None:
            master_parent = master_location.parent
            if master_parent:
                routing_surface = master_parent.routing_surface
        if self.slave.is_sim or isinstance(self.slave, StubActor):
            (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(routing_surface, self.slave)
        else:
            min_water_depth = None
            max_water_depth = None
        (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(routing_surface, self.master, min_water_depth=min_water_depth, max_water_depth=max_water_depth)
        fgl_kwargs.update({'min_water_depth': min_water_depth, 'max_water_depth': max_water_depth})
        if fgl_tuning.height_tolerance is not None:
            fgl_kwargs['height_tolerance'] = fgl_tuning.height_tolerance
        if fgl_tuning.slave_should_face_master:
            restrictions.append(RelativeFacingRange(master_location.transform.translation, 0))
            fgl_kwargs.update({'raytest_radius': self.RAYTRACE_RADIUS, 'raytest_start_offset': self.RAYTRACE_HEIGHT, 'raytest_end_offset': self.RAYTRACE_HEIGHT, 'ignored_object_ids': {self.master.id, self.slave.id}, 'raytest_start_point_override': master_location.transform.translation})
            fgl_flags = FGLSearchFlag.SHOULD_RAYTEST
            orientation_offset = sims4.math.angle_to_yaw_quaternion(sims4.math.vector3_angle(sims4.math.vector_normalize(self._offset)))
            orientation = Quaternion.concatenate(orientation, orientation_offset)
        starting_location = placement.create_starting_location(position=slave_position, orientation=orientation, routing_surface=routing_surface)
        if self.slave.is_sim:
            fgl_flags |= FGLSearchFlagsDefaultForSim
            fgl_context = placement.create_fgl_context_for_sim(starting_location, self.slave, search_flags=fgl_flags, restrictions=restrictions, **fgl_kwargs)
        else:
            fgl_flags |= FGLSearchFlagsDefault
            footprint = self.slave.get_footprint()
            master_position = master_location.position if hasattr(master_location, 'position') else master_location.transform.translation
            fgl_context = FindGoodLocationContext(starting_location, object_id=self.slave.id, object_footprints=(footprint,) if footprint is not None else None, search_flags=fgl_flags, restrictions=restrictions, connectivity_group_override_point=master_position, **fgl_kwargs)
        (new_position, new_orientation) = placement.find_good_location(fgl_context)
        if new_position is None or new_orientation is None:
            logger.warn('No good location found for {} after slaved in a routing formation headed to {}.', self.slave, starting_location, owner='rmccord')
            return sims4.math.Transform(Vector3(*starting_location.position), Quaternion(*starting_location.orientation))
        new_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(new_position.x, new_position.z, master_location.routing_surface)
        final_transform = sims4.math.Transform(new_position, new_orientation)
        return final_transform

    def on_release(self):
        self._unlock_slave()

    def _setup_right_angle_connections(self):
        offset_x = abs(self._formation_offset.x)
        num_nodes_x = math.ceil(offset_x/self.ATTACH_NODE_DIAMETER)
        fishtail_nodes_enabled = self.noise_behavior is not None or self.spring_behavior is not None
        if fishtail_nodes_enabled:
            num_nodes_x = 1
        if num_nodes_x == 0 and num_nodes_x > 0:
            node_radius = offset_x/num_nodes_x/2
            if self._formation_offset.x >= 0.0:
                link_offset_x = Vector2(node_radius, 0.0)
            else:
                link_offset_x = Vector2(-node_radius, 0.0)
            for i in range(0, num_nodes_x):
                if i == num_nodes_x - 1 and fishtail_nodes_enabled:
                    self._add_attachment_node(link_offset_x, -link_offset_x, node_radius, 0, self.ATTACHMENT_NODE_FLAGS_DEFAULT, RoutingFormationFollowType.NODE_TYPE_FISHTAIL, self.noise_behavior, self.spring_behavior)
                else:
                    self._add_attachment_node(link_offset_x, -link_offset_x, node_radius, 0, self.ATTACHMENT_NODE_FLAGS_DEFAULT, RoutingFormationFollowType.NODE_TYPE_FOLLOW_LEADER)
        chain_length = -self._formation_offset.y
        self._setup_direct_connections(chain_length)

    def _setup_direct_connections(self, chain_length):
        num_nodes_y = math.ceil(chain_length/self.ATTACH_NODE_DIAMETER)
        if num_nodes_y > 0:
            node_radius = chain_length/num_nodes_y/2
            link_offset_y = Vector2(0.0, -node_radius)
            for i in range(num_nodes_y):
                flags = self.ATTACHMENT_NODE_FLAGS_DEFAULT
                if i == num_nodes_y - 2 or num_nodes_y == 1:
                    flags |= self.ATTACHMENT_NODE_FLAGS_ATTACHMENT_COLLISION
                self._add_attachment_node(link_offset_y, -link_offset_y, node_radius, self.ATTACH_NODE_ANGLE, flags, RoutingFormationFollowType.NODE_TYPE_CHAIN)

    def should_slave_for_path(self, path):
        path_length = path.length() if path is not None else MAX_INT32
        final_path_node = path.nodes[-1]
        final_position = sims4.math.Vector3(*final_path_node.position)
        final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
        routing_surface = final_path_node.routing_surface_id
        final_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(final_position.x, final_position.z, routing_surface)
        final_transform = sims4.math.Transform(final_position, final_orientation)
        slave_position = final_transform.transform_point(self._offset)
        slave_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(slave_position.x, slave_position.z, routing_surface)
        final_dist_sq = (slave_position - self.slave.position).magnitude_squared()
        if path_length >= self.route_length_minimum or final_dist_sq >= self.route_length_minimum*self.route_length_minimum:
            return True
        return False

    def build_routing_slave_pb(self, slave_pb, path=None):
        starting_location = path.final_location if path is not None else self.master.intended_location
        slave_transform = self.find_good_location_for_slave(starting_location)
        slave_loc = slave_pb.final_location_override
        (slave_loc.translation.x, slave_loc.translation.y, slave_loc.translation.z) = slave_transform.translation
        (slave_loc.orientation.x, slave_loc.orientation.y, slave_loc.orientation.z, slave_loc.orientation.w) = slave_transform.orientation
        self._final_transform = slave_transform

    def update_slave_position(self, master_transform, master_orientation, routing_surface, distribute=True, path=None, canceled=False):
        master_transform = sims4.math.Transform(master_transform.translation, master_orientation)
        if distribute and not canceled:
            slave_transform = self._final_transform if self._final_transform is not None else self.slave.transform
            slave_position = slave_transform.translation
        else:
            slave_position = master_transform.transform_point(self._offset)
            slave_transform = sims4.math.Transform(slave_position, master_orientation)
        slave_route_distance_sqrd = (self._slave.position - slave_position).magnitude_squared()
        if path is not None and path.length() < self.route_length_minimum and slave_route_distance_sqrd < self.route_length_minimum*self.route_length_minimum:
            return
        slave_too_far_from_master = False
        if slave_route_distance_sqrd > self.route_length_maximum*self.route_length_maximum:
            slave_too_far_from_master = True
        if distribute and not slave_too_far_from_master:
            self._slave.move_to(routing_surface=routing_surface, transform=slave_transform)
        else:
            location = self.slave.location.clone(routing_surface=routing_surface, transform=slave_transform)
            self.slave.set_location_without_distribution(location)
