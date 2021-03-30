from interactions.liability import Liabilityfrom placement import FindGoodLocationContext, ScoringFunctionPolygon, FGLSearchFlag, FGLSearchFlagsDefault, find_good_location, create_starting_locationfrom sims4.geometry import CompoundPolygonfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableReference, Tunableimport services
class TeleportLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'TeleportLiability'
    FACTORY_TUNABLES = {'on_success_affordance': TunableReference(description='\n            If specified, the affordance to push if the teleportation was\n            successful.\n            ', manager=services.affordance_manager()), 'on_failure_affordance': TunableReference(description='\n            If specified, the affordance to push if the teleportation failed or\n            if on_success_affordance is specified and failed to execute.\n            ', manager=services.affordance_manager()), 'stay_in_connected_connectivity_group': Tunable(description='\n            If checked, the Sim will only be able to teleport to the \n            "connected" areas.\n\n            If unchecked, ignores the "connected" areas the Sim is able to\n            teleport to. For example, if a Sim tries to age up while standing\n            on a platform, then the Sim will be able to teleport to areas\n            that would have been "unconnected" to complete the interaction.\n            ', tunable_type=bool, default=True), 'require_target_for_teleport': Tunable(description='\n            If checked, the interaction will require a target sim for the actor\n            sim to teleport to. For example, for death, the reaper may need to\n            teleport to the dying target sim.\n            ', tunable_type=bool, default=True)}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction
        self._interaction.route_fail_on_transition_fail = False
        self._constraint = self._interaction.constraint_intersection()

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, liability_tuning):
        affordance.disable_distance_estimation_and_posture_checks = True

    def release(self):
        if self._interaction.transition_failed:
            if self._teleport() and self.on_success_affordance is not None and self._interaction.sim.push_super_affordance(self.on_success_affordance, self._interaction.target, self._interaction.context):
                return
            if self.on_failure_affordance is not None:
                self._interaction.sim.push_super_affordance(self.on_failure_affordance, self._interaction.target, self._interaction.context)

    def _teleport(self):
        polygon = None if self._constraint.geometry is None else self._constraint.geometry.polygon
        if polygon:
            if isinstance(polygon, CompoundPolygon):
                scoring_functions = [ScoringFunctionPolygon(cp) for cp in polygon]
            else:
                scoring_functions = (ScoringFunctionPolygon(polygon),)
            search_flags = FGLSearchFlagsDefault | FGLSearchFlag.USE_SIM_FOOTPRINT | FGLSearchFlag.SHOULD_TEST_BUILDBUY
            if not self.stay_in_connected_connectivity_group:
                search_flags &= ~FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
            routing_surface = self._constraint.routing_surface
            target_object = self._interaction.get_constraint_target(self._interaction.target)
            if target_object is None and self.require_target_for_teleport:
                return True
            else:
                obj_id = self._interaction.sim.id
                obj_def_state_index = self._interaction.sim.state_index
                starting_location = create_starting_location(position=self._constraint.average_position, routing_surface=routing_surface)
                fgl_context = FindGoodLocationContext(starting_location, scoring_functions=scoring_functions, object_id=obj_id, object_def_state_index=obj_def_state_index, search_flags=search_flags, routing_context=self._interaction.sim.routing_context)
                (translation, orientation) = find_good_location(fgl_context)
                if translation is not None and orientation is not None:
                    self._interaction.sim.move_to(translation=translation, orientation=orientation, routing_surface=routing_surface)
                    return True
        return False
