from objects.components import Component, typesfrom sims4.tuning.tunable import HasTunableFactoryimport services
class AutonomyMarkerComponent(Component, HasTunableFactory, component_name=types.AUTONOMY_MARKER_COMPONENT):

    def on_remove(self):
        services.current_zone().clear_autonomy_area()
