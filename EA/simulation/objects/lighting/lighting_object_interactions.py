from objects.lighting.lighting_interactions import SwitchLightImmediateInteraction
class SwitchLightAndStateImmediateInteraction(SwitchLightImmediateInteraction):
    INSTANCE_TUNABLES = {'state_settings': ObjectStateHelper.TunableFactory(description='\n            Find objects in the same room or lot based on the tags and \n            set state to the desired state.\n            ')}

    def _run_interaction_gen(self, timeline):
        yield from super()._run_interaction_gen(timeline)
        self.state_settings.execute_helper(self.target)
