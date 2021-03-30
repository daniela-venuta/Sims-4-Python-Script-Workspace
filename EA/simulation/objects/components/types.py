from objects.components import component_definition
class NativeComponent(objects.components.Component, use_owner=False):

    @classmethod
    def create_component(cls, owner):
        return cls(owner)

    @classmethod
    def has_server_component(cls):
        return True

class ClientOnlyComponent(NativeComponent):

    @classmethod
    def has_server_component(cls):
        return False

class PositionComponent(ClientOnlyComponent, component_name=POSITION_COMPONENT, key=1578750580):
    pass

class RenderComponent(ClientOnlyComponent, component_name=RENDER_COMPONENT, key=573464449):
    pass

class AnimationComponent(ClientOnlyComponent, component_name=ANIMATION_COMPONENT, key=3994535597):
    pass

class RoutingComponent(ClientOnlyComponent, component_name=ROUTING_COMPONENT, key=2561111181):
    pass

class SimComponent(ClientOnlyComponent, component_name=SIM_COMPONENT, key=577793786):
    pass

class AudioComponent(ClientOnlyComponent, component_name=AUDIO_COMPONENT, key=1069811801):
    pass

class EffectsComponent(ClientOnlyComponent, component_name=EFFECTS_COMPONENT, key=1942696649):
    pass

class GameplayComponent(ClientOnlyComponent, component_name=GAMEPLAY_COMPONENT, key=89505537):
    pass
