from date_and_time import TimeSpanfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeParticipantOption, DramaNodeUiDisplayType, DramaNodeRunOutcomefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DoubleSimResolverfrom event_testing.results import TestResultfrom interactions import ParticipantTypeSingleSimfrom interactions.utils.loot import LootActionsfrom sims4.tuning.tunable import TunableReference, OptionalTunable, Tunable, TunableEnumEntry, TunablePackSafeLotDescription, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_job import SituationJobfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_notification import UiDialogNotificationfrom world.lot import get_lot_id_from_instance_idimport servicesimport sims4logger = sims4.log.Logger('SituationDramaNode', default_owner='bosee')
class SituationDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'situation_to_run': TunableReference(description='\n            The situation that this drama node will try and start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), tuning_group=GroupNames.SITUATION), 'sender_sim_info_job': OptionalTunable(description='\n            When enabled, this job will be assigned to sender sim.\n            A validation error will be thrown if sender_sim_info_job is set\n            but not sender_sim_info.\n            ', tunable=SituationJob.TunableReference(description='\n                The default job for the sender of this drama node.\n                '), tuning_group=GroupNames.SITUATION), 'host_sim_info_job': OptionalTunable(description='\n            If enabled, this job will be assigned to the host sim.\n            ', tunable=SituationJob.TunableReference(description='\n                Situation Job for the host sim of the situation to run.\n                '), tuning_group=GroupNames.SITUATION), 'notification': OptionalTunable(description='\n            If enabled this is the notification that will be displayed after\n            the situation is started.\n            ', tunable=UiDialogNotification.TunableFactory(description='\n                The notification that displays when the situation is started.\n                ')), 'loots_on_start': TunableList(description='\n            Loots that will be applied when situation runs.\n            ', tunable=LootActions.TunableReference(pack_safe=True)), 'household_milestone': OptionalTunable(description='\n            If enabled, the household milestone will reset when the situation runs.\n            Only resets if the situation is run successfully. Useful for situations\n            that are spun up when a household milestone is unlocked.\n            ', tunable=TunableReference(pack_safe=True, manager=services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE))), 'homelot_only': Tunable(description='\n            If checked, the situation will only be permitted to run if the active\n            sims are on their homelot.\n            ', tunable_type=bool, default=False), 'host_sim_participant': OptionalTunable(description='\n            If enabled, the participant type to use to find who the host Sim\n            of the situation will be.\n            ', tunable=TunableEnumEntry(description='\n                The participant type to use to find the host Sim.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), tuning_group=GroupNames.PARTICIPANT), 'lot': OptionalTunable(description='\n            If enabled, the Sim will travel to this zone for the situation.\n            ', tunable=TunablePackSafeLotDescription(description='\n                A reference to the lot description file for this situation. \n                This is used for easier zone ID lookups.\n                ')), 'confirm_dialog': OptionalTunable(description='\n            If enabled, a dialog will appear when this drama node runs, asking\n            the user if they wish to proceed.\n            ', tunable=UiDialogOkCancel.TunableFactory(description='\n                The dialog with ok/cancel buttons that will display, asking \n                the user if they want to proceed with the situation on this\n                drama node.\n                ')), 'advance_notice_time': TunableTimeSpan(description='\n            The amount of time between the alert and the start of the event.\n            ', default_minutes=0, default_hours=0, default_days=0), 'user_facing': Tunable(description='\n            If this situation should be user facing or not.\n            ', tunable_type=bool, default=False)}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.SITUATION

    @classproperty
    def spawn_sims_during_zone_spin_up(cls):
        return False

    def create_calendar_alert(self):
        calendar_alert = super().create_calendar_alert()
        if self.ui_display_data:
            build_icon_info_msg(IconInfoData(icon_resource=self.ui_display_data.icon), self.ui_display_data.name, calendar_alert.calendar_icon)
        return calendar_alert

    def load(self, drama_node_proto, schedule_alarm=True):
        success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if success and self.ui_display_type != DramaNodeUiDisplayType.NO_UI:
            services.calendar_service().mark_on_calendar(self, self.advance_notice_time())
        return success

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO, **kwargs):
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier, **kwargs)
        if success and self.ui_display_type != DramaNodeUiDisplayType.NO_UI:
            services.calendar_service().mark_on_calendar(self, self.advance_notice_time())
        return success

    def get_calendar_sims(self):
        return (self._receiver_sim_info,)

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.sender_sim_info_job is not None and cls.sender_sim_info.type == DramaNodeParticipantOption.DRAMA_PARTICIPANT_OPTION_NONE:
            logger.error('Setting sender sim info job but sender sim info is set to None for {}. Please make sure that sender sim info is set correctly.', cls)
        if cls.host_sim_info_job is not None and cls.host_sim_participant is None:
            logger.error('Setting host_sim_info_job but host_sim_participant is None in {}. Please set host_sim_participant to a valid participant.', cls, owner='nsavalani')

    def _test(self, resolver, skip_run_tests=False):
        homelot_id = services.active_household().home_zone_id
        if self.homelot_only and homelot_id != services.current_zone_id():
            return TestResult(False, 'Cannot run because the current zone is not the home lot.')
        if self.host_sim_participant is not None:
            host_sim_info = self._get_resolver().get_participant(self.host_sim_participant)
            if host_sim_info is None:
                return TestResult(False, 'Cannot run because there is no host sim info.')
        return super()._test(resolver, skip_run_tests=skip_run_tests)

    def _run(self):
        if self.confirm_dialog:
            sim_info = self._receiver_sim_info
            resolver = DoubleSimResolver(self._sender_sim_info, self._receiver_sim_info)
            confirm_dialog = self.confirm_dialog(sim_info, resolver=resolver)
            confirm_dialog.show_dialog(on_response=self._on_confirm_dialog_response)
            return DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE
        else:
            self._run_situation()
            return DramaNodeRunOutcome.SUCCESS_NODE_COMPLETE

    def _on_confirm_dialog_response(self, dialog):
        if dialog.accepted:
            self._run_situation()
        services.drama_scheduler_service().complete_node(self.uid)

    def _run_situation(self):
        host_sim_id = 0
        host_sim_info = None
        resolver = self._get_resolver()
        if self.host_sim_participant is not None:
            host_sim_info = resolver.get_participant(self.host_sim_participant)
            host_sim_id = host_sim_info.id
        guest_list = self.situation_to_run.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True, host_sim_id=host_sim_id)
        if self._sender_sim_info is not None and self.sender_sim_info_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(self._sender_sim_info.id, self.sender_sim_info_job, SituationInvitationPurpose.INVITED))
        if host_sim_info is not None and self.host_sim_info_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(host_sim_info.id, self.host_sim_info_job, SituationInvitationPurpose.HOSTING))
        zone_id = 0
        if self.lot is not None:
            lot_id = get_lot_id_from_instance_id(self.lot)
            zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        situation_id = services.get_zone_situation_manager().create_situation(self.situation_to_run, guest_list=guest_list, spawn_sims_during_zone_spin_up=self.spawn_sims_during_zone_spin_up, user_facing=self.user_facing, zone_id=zone_id)
        if self.household_milestone and situation_id:
            active_household_milestone_tracker = services.active_household().household_milestone_tracker
            active_household_milestone_tracker.reset_milestone(self.household_milestone)
        if self.notification is not None:
            target_sim_id = self._sender_sim_info.id if self._sender_sim_info is not None else None
            dialog = self.notification(self._receiver_sim_info, DoubleSimResolver(self._sender_sim_info, self._receiver_sim_info), target_sim_id=target_sim_id)
            dialog.show_dialog()
        for loot in self.loots_on_start:
            loot.apply_to_resolver(resolver)
        return True
