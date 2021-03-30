from animation.animation_constants import ActorTypefrom animation.animation_overrides_tuning import TunableParameterMappingfrom distributor.fields import ComponentField, Fieldfrom distributor.ops import SetActorType, SetActorStateMachine, SetActorStateMachineParamsfrom objects.components import Componentfrom objects.components.types import PORTAL_ANIMATION_COMPONENTfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableInteractionAsmResourceKey
class PortalAnimationComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=PORTAL_ANIMATION_COMPONENT):
    FACTORY_TUNABLES = {'_portal_asm': TunableInteractionAsmResourceKey(description='\n            The animation to use for this portal.\n            '), '_portal_asm_parameters': TunableParameterMapping(description='\n            The parameters to utilize in the portal asm for this object.\n            ')}

    @ComponentField(op=SetActorType, priority=Field.Priority.HIGH)
    def actor_type(self):
        return ActorType.Door

    @ComponentField(op=SetActorStateMachine)
    def portal_asm(self):
        return self._portal_asm

    @ComponentField(op=SetActorStateMachineParams, default=None)
    def portal_asm_params(self):
        if self._portal_asm_parameters:
            return self._portal_asm_parameters
