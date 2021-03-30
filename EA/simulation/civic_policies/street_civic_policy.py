import servicesimport sims4from civic_policies.base_civic_policy import BaseCivicPolicyfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.test_events import TestEventfrom protocolbuffers import GameplaySaveData_pb2from sims4.tuning.tunable import TunableList, TunableReferencelogger = sims4.log.Logger('StreetPolicy', default_owner='shouse')
class StreetCivicPolicy(BaseCivicPolicy):
    INSTANCE_TUNABLES = {'civic_policy_effects': TunableList(description='\n            Actions to apply when the civic policy is enacted.\n            ', tunable=TunableReference(description='\n                A Street Effect to include.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('StreetEffect',), pack_safe=True))}

    def __init__(self, provider, **kwargs):
        super().__init__(provider)
        self._civic_policy_effects = []
        for effect in self.civic_policy_effects:
            self._civic_policy_effects.append(effect())

    def finalize_startup(self):
        super().finalize_startup()
        for effect in self._civic_policy_effects:
            effect.finalize_startup(self)

    def enact(self):
        super().enact()
        for effect in self._civic_policy_effects:
            effect.enact()
        street_service = services.street_service()
        street = None if street_service is None else street_service.get_street(self.provider)
        services.get_event_manager().process_event(TestEvent.CivicPoliciesChanged, custom_keys=((street, type(self)),))

    def repeal(self):
        super().repeal()
        for effect in self._civic_policy_effects:
            effect.repeal()
        street_service = services.street_service()
        street = None if street_service is None else street_service.get_street(self.provider)
        services.get_event_manager().process_event(TestEvent.CivicPoliciesChanged, custom_keys=((street, type(self)),))

    def save(self, provider_data):
        effect_states = []
        for effect in self._civic_policy_effects:
            effect_custom_data = effect.get_save_state_msg()
            if effect_custom_data is not None:
                effect_states.append((type(effect).guid64, effect_custom_data))
        if not effect_states:
            super().save(provider_data)
            return
        policy_msg = GameplaySaveData_pb2.PersistableCivicPolicyStreetPolicyData()
        policy_msg.enacted = self.enacted
        for (effect_id, effect_custom_data) in effect_states:
            with ProtocolBufferRollback(policy_msg.effect_data) as effect_data:
                effect_data.policy_id = effect_id
                effect_data.custom_data = effect_custom_data
        with ProtocolBufferRollback(provider_data.policy_data) as policy_data:
            policy_data.policy_id = self.guid64
            policy_data.custom_data = policy_msg.SerializeToString()

    def load(self, policy_data):
        effects_to_load = dict()
        for effect in self._civic_policy_effects:
            effects_to_load[type(effect).guid64] = effect
        if policy_data.policy_id == self.guid64:
            if policy_data.custom_data:
                policy_msg = GameplaySaveData_pb2.PersistableCivicPolicyStreetPolicyData()
                policy_msg.ParseFromString(policy_data.custom_data)
                self._enacted = policy_msg.enacted
                for effect_data in policy_msg.effect_data:
                    effect = effects_to_load.get(effect_data.policy_id)
                    if effect is not None:
                        effect.set_load_state_from_msg(effect_data.custom_data)
            else:
                self._enacted = True
