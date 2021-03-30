from event_testing.resolver import SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom objects.components import Component, types, ComponentPriorityfrom objects.components.state import TunableStateTypeReference, TunableStateValueReferencefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableList, TunableReference, Tunable, TunableTuple, TunableSetimport servicesimport sims4.resourcesfrom snippets import define_snippet
class StereoComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.STEREO_COMPONENT):
    FACTORY_TUNABLES = {'channel_state': TunableStateTypeReference(description='\n            The state used to populate the radio stations'), 'off_state': TunableStateValueReference(description='\n            The channel that represents the off state.'), 'listen_affordances': TunableList(description='\n            An ordered list of affordances that define "listening" to this\n            stereo. The first succeeding affordance is used.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), 'play_on_active_sim_only': Tunable(description='\n            If enabled, and audio target is Sim, the audio will only be \n            played on selected Sim. Otherwise it will be played regardless \n            Sim is selected or not.\n            \n            If audio target is Object, always set this to False. Otherwise\n            the audio will never be played.\n            \n            ex. This will be useful for Earbuds where we want to hear the\n            music only when the Sim is selected.\n            \n            This is passed down to the audio state when it is triggered, and thus\n            will overwrite any tuning on the state value.\n            ', tunable_type=bool, default=False), 'immediate': Tunable(description='\n            If checked, this audio will be triggered immediately, nothing\n            will block.\n            \n            ex. Earbuds audio will be played immediately while \n            the Sim is routing or animating.\n            \n            This is passed down to the audio state when it is triggered, and thus\n            will overwrite any tuning on the state value.\n            ', tunable_type=bool, default=False), 'whitelist_channels': TunableList(description='\n            This acts like a filter. Items in this list who pass their test will be combined together\n            and become a whitelist. We will check against this whitelist to generate available picker\n            channel states.\n            If this list is empty, the filter will be disabled.\n            ', tunable=TunableTuple(channel_states=TunableSet(description='\n                    If the test passes, channel states in this list will be in the whitelist and become available.\n                    ', tunable=TunableStateValueReference(pack_safe=True)), test=TunableTestSet(description='\n                    Tests for whitelist channel states. Note that we also have tests on listen affordances, please\n                    make sure they are not duplicated so to save performance.\n                    ')))}

    def is_stereo_turned_on(self):
        current_channel = self.owner.get_state(self.channel_state)
        return current_channel != self.off_state

    def get_available_picker_channel_states(self, context):
        whitelist_channels = self._get_whitelist_channels()
        for client_state in self.owner.get_client_states(self.channel_state):
            if not whitelist_channels is not None or client_state not in whitelist_channels:
                pass
            elif client_state.show_in_picker and client_state.test_channel(self.owner, context):
                yield client_state

    def component_potential_interactions_gen(self, context, **kwargs):
        current_channel = self.owner.get_state(self.channel_state)
        if current_channel != self.off_state:
            for listen_affordance in self.listen_affordances:
                yield from listen_affordance.potential_interactions(self.owner, context, required_station=current_channel, off_state=self.off_state, **kwargs)

    def _get_whitelist_channels(self):
        if not self.whitelist_channels:
            return
        resolver = SingleObjectResolver(self.owner)
        tested_channels_sets = []
        for channels_to_test in self.whitelist_channels:
            if channels_to_test.test.run_tests(resolver):
                tested_channels_sets.append(channels_to_test.channel_states)
        if tested_channels_sets:
            return frozenset.union(*tested_channels_sets)
        return frozenset()
(_, TunableStereoComponentSnippet) = define_snippet('stereo_component', StereoComponent.TunableFactory())