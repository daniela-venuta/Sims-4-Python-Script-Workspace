import servicesimport sims4from display_snippet_tuning import DisplaySnippetfrom sims4.tuning.tunable import TunableList, TunableReference
class EcoFootprintState(DisplaySnippet):
    INSTANCE_TUNABLES = {'effects': TunableList(description='\n            A list of StreetEffects that will be enabled when this\n            state is entered and disabled when this state is exited.\n            ', tunable=TunableReference(description='\n                A Street Effect to include.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('StreetEffect',), pack_safe=True))}

    def __init__(self, provider, **kwargs):
        self._provider = provider
        self._effect_instances = []
        self._enacted = False
        for effect in self.effects:
            self._effect_instances.append(effect())

    def finalize_startup(self, is_active):
        self._enacted = is_active
        for effect in self._effect_instances:
            effect.finalize_startup(self)

    @property
    def provider(self):
        return self._provider

    @property
    def enacted(self):
        return self._enacted

    def enter(self):
        self._enacted = True
        for effect in self._effect_instances:
            effect.enact()

    def exit(self):
        self._enacted = False
        for effect in self._effect_instances:
            effect.repeal()
