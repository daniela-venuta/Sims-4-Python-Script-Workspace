import sims4.log
class SetObjectVoiceActorState(ElementDistributionOpMixin, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'voice_actor_override': OptionalTunable(description='\n            We can override an object\'s voice actor. This will be sent to Client,\n            then when audio request the actor suffix, we check for this override\n            on the object.\n            If "No Override" is chosen, existing override will be removed.\n            ', tunable=TunableStringHash32(), disabled_name='no_override', enabled_name='override_voice_actor', enabled_by_default=True)}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target

    def start(self, *args, **kwargs):
        if not self.is_attached:
            self.attach(self._target)

    def stop(self, *args, **kwargs):
        if self.is_attached:
            self.detach()

    def write(self, msg):
        suffix_hash = self.voice_actor_override if self.voice_actor_override else 0
        voice_op = SetVoiceActor(suffix_hash)
        voice_op.write(msg)
