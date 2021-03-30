from objects.components.types import ROUTING_COMPONENTfrom routing.path_planner.path_plan_context import DEFAULT_REQUIRED_HEIGHT_CLEARANCEfrom sims4.tuning.tunable import AutoFactoryInit, TunableVariant, HasTunableSingletonFactory, Tunableimport placementimport sims4logger = sims4.log.Logger('HeightClearanceHelper', default_owner='skorman')
class HeightClearance(AutoFactoryInit, HasTunableSingletonFactory):

    class _FromPathPlanContext(AutoFactoryInit, HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'additional_head_clearance': Tunable(description="\n                The minimum additional head clearance required when running this \n                interaction. This will be added to the required height clearance\n                tuned in the actor's path plan context (in the routing\n                component).\n                ", tunable_type=float, default=0.0)}

        def get_height_clearance(self, path_plan_context):
            return path_plan_context.get_required_height_clearance(additional_head_room=self.additional_head_clearance)

    class _SpecifyOverride(AutoFactoryInit, HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'required_height_clearance': Tunable(description='\n                The minimum req.\n                ', tunable_type=float, default=0.0)}

        def get_height_clearance(self, _):
            return self.required_height_clearance

    FACTORY_TUNABLES = {'height_clearance': TunableVariant(description='\n            The minimum height clearance from the floor to the ceiling that is\n            required.\n            ', from_path_plan_context=_FromPathPlanContext.TunableFactory(description="\n                Use the sim's path plan context to determine how much height\n                clearance they need.\n                "), specify_override=_SpecifyOverride.TunableFactory(description='\n                Specify a value that encompasses the total distance from the\n                floor to the ceiling that is required.\n                '), default='from_path_plan_context')}

    def __call__(self, path_plan_context):
        return self.height_clearance.get_height_clearance(path_plan_context)

def get_required_height_clearance(height_clearance_target, override_tuning=None):
    if hasattr(height_clearance_target, 'routing_component') and height_clearance_target.has_component(ROUTING_COMPONENT):
        routing_context = height_clearance_target.routing_component.routing_context
        if override_tuning is not None:
            return override_tuning(routing_context)
        return routing_context.get_required_height_clearance()
    if hasattr(height_clearance_target, 'footprint'):
        footprint = height_clearance_target.footprint
        if footprint is not None:
            try:
                return placement.get_object_height(footprint)
            except ValueError:
                logger.error('Unable to get object height from footprint key {} for object {}.', footprint, height_clearance_target)
    return DEFAULT_REQUIRED_HEIGHT_CLEARANCE
