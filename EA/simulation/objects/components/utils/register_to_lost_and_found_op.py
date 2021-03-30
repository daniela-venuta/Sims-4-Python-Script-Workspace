import servicesimport sims4.logfrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableEnumEntrylogger = sims4.log.Logger('RegisterToLostAndFoundOp')
class RegisterToLostAndFoundOp(BaseLootOperation):
    FACTORY_TUNABLES = {'object_to_register': TunableEnumEntry(description='\n            The participant who will be registered to lost and found service.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def __init__(self, object_to_register, **kwargs):
        super().__init__(target_participant_type=object_to_register, **kwargs)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to register lost and found for a None owner sim. participant {}. Loot: {}', self.subject, self, owner='yozhang')
            return
        if target is None:
            logger.error('Attempting to register lost and found for a None object. participant {}. Loot: {}', self.object_to_register, self, owner='yozhang')
            return
        lost_and_found_reg_info = target.get_lost_and_found_registration_info()
        if lost_and_found_reg_info is None:
            logger.error('Attempting to register lost and found for an object who has no lost and found registration info. object {}. Loot: {}', target, self, owner='yozhang')
            return
        services.get_object_lost_and_found_service().add_game_object(subject.zone_id, target.id, subject.id, subject.household_id, lost_and_found_reg_info.time_before_lost, lost_and_found_reg_info.return_to_individual_sim)
