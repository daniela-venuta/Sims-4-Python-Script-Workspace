from sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReference, Tunableimport sims4import serviceslogger = sims4.log.Logger('OpenStreetDirector', default_owner='jjacobson')
class DirectManipulateConditionalLayer(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'conditional_layer': TunableReference(description='\n            The conditional layer to manipulate.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)), 'show_conditional_layer': Tunable(description='\n            If checked then the specified conditional layer will be shown.\n            If unchecked then the specified conditional layer will be hidden.\n            ', tunable_type=bool, default=True), 'immediate': Tunable(description='\n            Whether or not the manipulation of the conditional layer is \n            immediate or can take place over longer periods of time.\n            ', tunable_type=bool, default=True)}

    def change_conditional_layer(self, invert_show=False):
        zone_director = services.venue_service().get_zone_director()
        open_street_director = zone_director.open_street_director
        if open_street_director is None:
            return
        if not open_street_director.has_conditional_layer(self.conditional_layer):
            return
        show_conditional_layer = self.show_conditional_layer
        if invert_show:
            show_conditional_layer = not show_conditional_layer
        if show_conditional_layer:
            if self.immediate:
                open_street_director.load_layer_immediately(self.conditional_layer)
            else:
                open_street_director.load_layer_gradually(self.conditional_layer)
        else:
            open_street_director.remove_layer_objects(self.conditional_layer)
