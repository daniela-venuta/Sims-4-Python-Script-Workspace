from interactions import ParticipantTypeSingleSimfrom interactions.utils import LootTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom services.roommate_service_utils.roommate_enums import RoommateLeaveReasonfrom sims4.tuning.tunable import Tunable, TunableVariant, TunableEnumEntry, HasTunableSingletonFactory, AutoFactoryInit, TunableFactoryimport servicesimport sims4.logimport singletonsimport traits.traitslogger = sims4.log.Logger('Roommate Loot', default_owner='nabaker')
class RoommateLootOp(BaseLootOperation):

    class AddRemoveRoommate(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n                The subject to add/remove as roommate.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'remove': Tunable(description='\n                If checked, remove the subject as a roommate.\n                Otherwise add the subject as roommate of active household.\n                ', tunable_type=bool, default=False)}

        def perform(self, resolver):
            roommate_service = services.get_roommate_service()
            if roommate_service is not None:
                participant = resolver.get_participant(self.subject)
                if participant is not None:
                    sim_info = participant.sim_info
                    if self.remove:
                        roommate_service.remove_roommate(sim_info)
                    else:
                        zone_id = services.get_active_sim().household.home_zone_id
                        if roommate_service.conform_potential_roommate(sim_info):
                            roommate_service.add_roommate(sim_info, zone_id)
                        else:
                            logger.error('Failed to conform {} to be a roommate', sim_info)
                            sim_info.trait_tracker.remove_traits_of_type(traits.traits.TraitType.ROOMMATE)

    class AdOnOff(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'turn_on': Tunable(description='\n                If checked, turn the ad on.\n                Otherwise turn the ad off.\n                ', tunable_type=bool, default=False)}

        def perform(self, resolver):
            roommate_service = services.get_roommate_service()
            if roommate_service is not None:
                roommate_service.trigger_interviews(self.turn_on)

    class QueueLockedOutSituation(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n                The subject roommate to enter the locked out situation on\n                return to home lot.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

        def perform(self, resolver):
            roommate_service = services.get_roommate_service()
            if roommate_service is not None:
                participant = resolver.get_participant(self.subject)
                if participant is not None:
                    roommate_service.queue_locked_out_sim_id(participant.sim_id)

    class SetClearRoommateLeaveReason(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n                The subject roommate to set/clear the roommate leave reason on.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'clear': Tunable(description='\n                If checked, clear the reason.\n                Otherwise set it.\n                ', tunable_type=bool, default=True), 'reason': TunableEnumEntry(description='\n                Reason to be set/cleared\n                ', tunable_type=RoommateLeaveReason, default=RoommateLeaveReason.INVALID, invalid_enums=(RoommateLeaveReason.INVALID,))}

        def perform(self, resolver):
            roommate_service = services.get_roommate_service()
            if roommate_service is not None:
                participant = resolver.get_participant(self.subject)
                if participant is not None:
                    sim_info = participant.sim_info
                    if self.clear:
                        roommate_service.remove_leave_reason(sim_info, self.reason)
                        return
                    roommate_service.add_leave_reason(sim_info, self.reason)

    FACTORY_TUNABLES = {'operation_type': TunableVariant(description='\n            The type of roommate operation to perform.\n            ', add_remove_roommate=AddRemoveRoommate.TunableFactory(), ad_on_off=AdOnOff.TunableFactory(), queue_locked_out_situation=QueueLockedOutSituation.TunableFactory(), set_clear_roommate_leave_reason=SetClearRoommateLeaveReason.TunableFactory(), default='add_remove_roommate')}

    def __init__(self, operation_type, **kwargs):
        super().__init__(**kwargs)
        self.operation_type = operation_type

    @property
    def loot_type(self):
        return LootType.GENERIC

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return {}

    def _apply_to_subject_and_target(self, subject, target, resolver):
        self.operation_type.perform(resolver)
