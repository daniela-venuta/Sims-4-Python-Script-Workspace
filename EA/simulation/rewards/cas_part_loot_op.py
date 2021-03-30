from interactions import ParticipantTypeCASPartfrom interactions.utils.loot_basic_op import BaseLootOperationimport sims4.logfrom objects.components.stored_info_component import StoredInfoComponentfrom rewards.tunable_reward_base import TunableRewardBasefrom sims4.tuning.tunable import TunableVariant, AutoFactoryInit, TunableCasPart, TunableEnumEntry, HasTunableSingletonFactory, TunableList, Tunablelogger = sims4.log.Logger('CASUnlockLootOp', default_owner='rrodgers')
class CASPartFromReference(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'cas_parts': TunableList(description='\n            A list of cas parts to unlock\n            ', tunable=TunableCasPart())}

    def __call__(self, resolver, *args, **kwargs):
        return self.cas_parts

class CASPartFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant to use to find the cas part.\n            ', tunable_type=ParticipantTypeCASPart, default=ParticipantTypeCASPart.StoredCASPartsOnObject)}

    def __call__(self, resolver, *args, **kwargs):
        return resolver.get_participants(self.participant)

class CASUnlockLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'cas_part_source': TunableVariant(description='\n            The source from which we should get the cas parts.\n            ', reference=CASPartFromReference.TunableFactory(), participant=CASPartFromParticipant.TunableFactory())}

    def __init__(self, cas_part_source, **kwargs):
        super().__init__(**kwargs)
        self.cas_part_source = cas_part_source

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('Attempting to apply CAS Unlock Loot Op to {} which is not a Sim.', subject)
            return False
        for cas_part in self.cas_part_source(resolver):
            if cas_part is None:
                return
            household = subject.household
            household.add_cas_part_to_reward_inventory(cas_part)
            TunableRewardBase.send_unlock_telemetry(subject, cas_part, 0)
        return True

class StoreCASPartsLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'cas_part_source': TunableVariant(description='\n            The source from which we should get the cas parts.\n            ', reference=CASPartFromReference.TunableFactory(), participant=CASPartFromParticipant.TunableFactory()), 'overwrite': Tunable(description='\n            If checked, the stored cas parts will replace any existing stored\n            cas parts. If not checked, existing cas parts will be preserved.\n            ', tunable_type=bool, default=True)}

    def __init__(self, cas_part_source, overwrite, **kwargs):
        super().__init__(**kwargs)
        self.cas_part_source = cas_part_source
        self.overwrite = overwrite

    def _apply_to_subject_and_target(self, subject, target, resolver):
        cas_parts = self.cas_part_source(resolver)
        if not self.overwrite:
            existing_stored_parts = subject.get_stored_casparts()
            if existing_stored_parts is not None:
                cas_parts.extend(existing_stored_parts)
        StoredInfoComponent.store_info_on_object(subject, _cas_parts=cas_parts)
