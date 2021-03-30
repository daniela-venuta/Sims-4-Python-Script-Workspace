from _collections import defaultdictimport randomimport timefrom protocolbuffers import Roommates_pb2, Consts_pb2from autonomy.autonomy_preference import ObjectPreferenceTagfrom build_buy import HouseholdInventoryFlagsfrom clock import ClockSpeedModefrom date_and_time import create_time_span, TimeSpan, create_date_and_timefrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import GlobalResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom filters.tunable import TunableSimFilterfrom interactions.base.super_interaction import SuperInteractionfrom interactions.utils.loot import LootActionsfrom objects.object_manager import BED_PREFIX_FILTERfrom objects.system import create_objectfrom relationships.relationship_bit import RelationshipBitfrom scheduler import WeeklySchedulefrom services.roommate_service_utils.roommate_enums import RoommateLeaveReason, LeaveReasonTestingTimefrom sims.university.university_utils import UniversityUtilsfrom sims4.common import Pack, is_available_packfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.service_manager import Servicefrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import TunableRange, TunableSet, TunableEnumWithFilter, TunableEnumEntry, TunablePackSafeReference, TunableEnumSet, TunablePercent, TunableList, TunableTuple, TunableInterval, Tunable, TunableReference, TunableMapping, OptionalTunable, HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, TunableRealSecondfrom sims4 import mathfrom sims4.utils import classpropertyfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCallbackOptionfrom snippets import define_snippetfrom statistics.statistic import Statisticfrom tunable_multiplier import TunableMultiplierfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog_notification import UiDialogNotificationimport alarmsimport build_buyimport persistence_error_typesimport routingimport servicesimport sims4.logimport tagimport traits.traitslogger = sims4.log.Logger('RoommateService', default_owner='nabaker')(TunableRoommateArchetypeReference, TunableRoommateArchetypeSnippet) = define_snippet('roommate_archetype', TunableTuple(sim_filter=TunableSimFilter.TunableReference(description='\n            Sim Filter to conform the roommate to if this archetype is selected.\n            '), weight=TunableMultiplier.TunableFactory(description='\n            The weight of this archetype relative to other entries in this list\n            ')))with sims4.reload.protected(globals()):
    LEAVE_REASONS = {}
class RoommateService(Service):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        required_packs = RoommateService.required_packs
        if not any(is_available_pack(pack) for pack in required_packs):
            return
        if value is None:
            logger.error('Packsafe error in RoommateService: {} is not available in required packs: {}', tunable_name, required_packs)

    HOUSEHOLD_AND_ROOMMATE_CAP = TunableRange(description='\n        Maximum number of sims allowed in household & roommates combined.\n        ', tunable_type=int, default=12, minimum=8, maximum=20)
    UNPLAYED_HOUSEHOLD_AND_ROOMMATE_CAP = TunableRange(description="\n        Maximum number of sims allowed in household & roommates combined if\n        household either doesn't exist or is unplayed.\n        ", tunable_type=int, default=4, minimum=0, maximum=10)
    BED_TAGS = TunableSet(description='\n        Tags that specify which objects count as bed for determining how many\n        roommates a lot supports, as well as claiming them\n        ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=BED_PREFIX_FILTER))
    BED_PREFERENCE_TAG = TunableEnumEntry(description='\n        The preference tag used to claim beds for autonomous use.\n        ', tunable_type=ObjectPreferenceTag, default=ObjectPreferenceTag.INVALID, invalid_enums=(ObjectPreferenceTag.INVALID,))
    AUTO_INVITE_TRAIT = TunablePackSafeReference(description='\n        The trait used to identify sims that should invite themselves when\n        active household travels.\n        ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), verify_tunable_callback=_verify_tunable_callback)
    AUTO_INVITE_BLACKLIST_TAGS = TunableEnumSet(description="\n        Set of tags that blacklist situations that shouldn't allow sims with\n        the auto-invite trait to automatically join.\n        ", enum_type=tag.Tag, enum_default=tag.Tag.INVALID)
    AUTO_INVITE_CHANCE = TunablePercent(description="\n        Chance a sim with the auto invite trait will tag along to any travel\n        situation that doesn't have the blacklist tag.\n        ", default=50)
    AUTO_INVITE_DIALOG = UiDialogNotification.TunableFactory(description='\n        Notification on arrival from sim who tagged along.\n        ')
    ROOMMATE_RELATIONSHIP_BIT = RelationshipBit.TunablePackSafeReference(description='\n        The relationship bit to add between sims in the household that owns the\n        lot, and any roommates\n        ', verify_tunable_callback=_verify_tunable_callback)
    ROOMMATE_SIM_FILTERS = TunableList(description='\n        List of paired tests and simfilters.\n        The first simfilter whose test passes will be used to acquire (potential)\n        roommates.\n        ', tunable=TunableTuple(test=TunableTestSet(), sim_filter=TunableSimFilter.TunableReference(description='\n                Sim Filter to find roommates if the associated test is the first\n                one to pass.\n                ', pack_safe=True)))
    ROOMMATE_SITUATION = TunablePackSafeReference(description='\n        The situation that the roommate is in.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions='RoommateSituation', verify_tunable_callback=_verify_tunable_callback)
    ROOMMATE_JOB = SituationJob.TunablePackSafeReference(description='\n        The job for the roommate\n        ', verify_tunable_callback=_verify_tunable_callback)
    OFFLOT_ALARM_INTERVAL = TunableTimeSpan(description='\n        Interval between attempts to bring roommates back onto the lot if they\n        have been pulled off/pushed out by travel/higher priority sims.\n        ')
    UNIVERSITY_ROOMMATE_TIMESLICE = TunableTimeSpan(description='\n        Interval between creating roommates for University\n        ', default_hours=1)
    SS3_PARK_INTERACTIONS = TunableList(description='\n        Interactions in which to park roommates during SS3\n        ', tunable=SuperInteraction.TunableReference(pack_safe=True))
    ADDITIONAL_CULLING_IMMUNITY = TunableTuple(description='\n        This number will boost Roommates when the culling\n        system scores this Sim. Higher the number, lower the probability \n        of this Sim being culled.\n        ', active_household=TunableRange(tunable_type=int, default=20, minimum=0), previously_played_household=TunableRange(tunable_type=int, default=10, minimum=0), unplayed_household=TunableRange(tunable_type=int, default=2, minimum=0), no_household=TunableRange(tunable_type=int, default=0, minimum=0))
    INTERVIEW = TunableTuple(description='\n        Tuning related to the roommate interview process.\n        ', situation=Situation.TunablePackSafeReference(description='\n            The interview situation.\n            '), job=SituationJob.TunablePackSafeReference(description='\n            The job for the interviewee\n            ', verify_tunable_callback=_verify_tunable_callback), start_stop_times=TunableInterval(description='\n            The hours between when potential roommates can show up to be\n            interviewed.\n            ', tunable_type=float, default_lower=10, default_upper=18, minimum=0, maximum=24), interviews_per_day=TunableInterval(description='\n            How many interviews can be randomly scheduled each day\n            ', tunable_type=int, default_lower=0, default_upper=3, minimum=0), ad_auto_close_notification=UiDialogNotification.TunableFactory(description='\n            The notification to display when the ad is auto closed due to no\n            more room for roommates.  (Either household got to big or enough\n            roommates added.)\n            '), interviewee_blackout_duration=TunableTimeSpan(description='\n            How long after being rejected before an interviewee can show up again.\n            '))
    RENT = TunableTuple(description='\n        Tuning related to roommate rent.\n        ', schedule=WeeklySchedule.TunableFactory(description='\n            Schedule for receiving rent.\n            '), rent_modifer=Tunable(description='\n            Rent per tenant = lot value * rent modifier / total household sims and roommates \n            ', tunable_type=float, default=0.5), non_payment_trait=TunablePackSafeReference(description='\n            The trait used to identify sims that should occasionally not pay rent.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), verify_tunable_callback=_verify_tunable_callback), non_payment_chance=TunablePercent(description="\n            Percent chance a sim with the non payment trait won't pay.\n            ", default=50), all_pay_notification=UiDialogNotification.TunableFactory(description='\n            The notification to display when all sims pay.  1st extra token is\n            individual rent, 2nd extra token is total rent.\n            '), pay_failure_notification=UiDialogNotification.TunableFactory(description="\n            The notification to display when at least one sim doesn't pay.  1st\n            extra token is individual rent, 2nd extra token is total rent, 3rd\n            extra token is number of sims that didn't pay.  4th extra token is\n            bulleted list of non paying sims.\n            "), non_payment_format=TunableLocalizedStringFactory(description='\n            String to use to format sims into the list.  Token is sim.\n            '), rent_owed_statistic=Statistic.TunablePackSafeReference(description='\n            Statistic that keeps track of how much rent is owned.\n            '))

    class DefinitionDecoration(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'definition': TunableReference(description='\n                A reference to the specific item.\n                ', manager=services.definition_manager(), pack_safe=True)}

        def get_definitions(self):
            return [self.definition]

    class TagDecoration(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'tag_set': TunableSet(description='\n                A list of category tags to specify decorations. Will match if\n                any tag matches.\n                ', tunable=TunableEnumEntry(description='\n                    What tag to test for\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID), minlength=1)}

        def get_definitions(self):
            all_definitions = list(services.definition_manager().get_definitions_for_tags_gen(self.tag_set))
            if not all_definitions:
                logger.warn('Unable to find any possible roommate decorations with tag set: {}', self.tag_set)
                return []
            random.shuffle(all_definitions)
            return all_definitions

    DECORATING = TunableTuple(description='\n        Tuning related to roommate decorations\n        ', number_to_place=TunableInterval(description='\n            How many items to try to place\n            ', tunable_type=int, default_lower=0, default_upper=3, minimum=0), distance=TunableDistanceSquared(description='\n            Maxium distance from bed objects can be placed\n            ', default=5), decorations=TunableList(description='\n            Weighted list of decorations to be placed\n            ', tunable=TunableTuple(item=TunableVariant(description='\n                    A reference to the item.\n                    ', by_tag=TagDecoration.TunableFactory(), by_definition=DefinitionDecoration.TunableFactory(), default='by_definition'), weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this item relative to other items\n                    '))))
    LOCKED_OUT_SITUATION = TunableTuple(description='\n        Tuning related to a roommate being locked out.\n        ', situation=Situation.TunablePackSafeReference(description='\n            The situation in which a locked out roommate is placed.\n            ', verify_tunable_callback=_verify_tunable_callback), job=SituationJob.TunablePackSafeReference(description='\n            The job for the locked out sim\n            ', verify_tunable_callback=_verify_tunable_callback))

    @staticmethod
    def _get_leave_reason_testing_time(data):
        if data.tests is None:
            return LeaveReasonTestingTime.UNTESTED
        return data.tests.testing_time

    @staticmethod
    def _populate_leave_reasons(*args):
        LEAVE_REASONS[LeaveReasonTestingTime.UNTESTED] = []
        LEAVE_REASONS[LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_ALL_LOTS] = []
        LEAVE_REASONS[LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_HOME_LOT] = []
        LEAVE_REASONS[LeaveReasonTestingTime.ALL_ROOMMATES] = []
        for (leave_enum, data) in RoommateService.LEAVING.leave_reasons.items():
            LEAVE_REASONS[RoommateService._get_leave_reason_testing_time(data)].append(leave_enum)

    LEAVING = TunableTuple(description='\n        Tuning related to roommate deciding to leave\n        ', check_interval=TunableTimeSpan(description='\n            Interval between leave condition checks.\n            '), loot=LootActions.TunableReference(description='\n            The loot action applied every check interval to roommates of\n            active household if on active lot.\n            ', pack_safe=True), time_slice_seconds=TunableRealSecond(description='\n            The maximum alloted time for checking roommates between time slices.\n            ', default=0.1), leave_reasons=TunableMapping(description='\n            Mapping between leave reason and tuning related to that reason.\n            ', key_type=TunableEnumEntry(tunable_type=RoommateLeaveReason, default=RoommateLeaveReason.INVALID, invalid_enums=(RoommateLeaveReason.INVALID,)), value_type=TunableTuple(tests=OptionalTunable(description='\n                    If enabled, will add/update this exit reason during the check if\n                    the specified requirements are met.\n                    If disabled, exit reason must be added either through a loot\n                    or code.\n                    ', tunable=TunableTuple(tests=TunableTestSet(description='\n                            Test set that, if passed, means the sim wants to leave for\n                            the associated reason.\n                            '), testing_time=TunableEnumEntry(description='\n                            When sims should be tested for this leave reason.\n\n                            HOUSEHOLD_ROOMMATES_ALL_LOTS: Tests instantiated \n                                    roommates of active household on any lot.\n                            HOUSEHOLD_ROOMMATES_HOME_LOT: Tests instantiated \n                                    roommates of active household on home lot.\n                            ALL_ROOMMATE: Tests all roommates period.\n                            ', tunable_type=LeaveReasonTestingTime, default=LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_HOME_LOT, invalid_enums=LeaveReasonTestingTime.UNTESTED)), enabled_by_default=True), time_till_warning=OptionalTunable(description='\n                    Required time for LeaveReason to continue to apply before\n                    displaying warning.\n                    ', tunable=TunableTimeSpan()), warning_notification=OptionalTunable(description='\n                    The notification to display when sim has been wanting to\n                    leave for specified reason for longer than the time till\n                    warning. \n                    ', tunable=UiDialogNotification.TunableFactory()), time_till_leave=TunableTimeSpan(description='\n                    Required time for LeaveReason to continue to apply before\n                    roommate leaves.\n                    '), leaving_notification=UiDialogNotification.TunableFactory(description='\n                    The notification to display when sim leaves\n                    '), fixed_notification=OptionalTunable(description='\n                    The notification to display when problem is detected fixed.\n                    ', tunable=UiDialogNotification.TunableFactory())), callback=_populate_leave_reasons))
    ARCHETYPE_CATEGORIES = TunableList(description='\n        Categories from which archetypes are selected.  The specified\n        number of archetypes will be randomly selected from each category.\n        ', tunable=TunableTuple(count=TunableInterval(description='\n                Adds a random count of archetypes between min and max.\n                ', tunable_type=int, default_lower=1, default_upper=1, minimum=0), archetypes=TunableList(tunable=TunableRoommateArchetypeReference(pack_safe=True))))

    class LeaveReasonData:

        def __init__(self):
            self.total_time = TimeSpan.ZERO
            self.been_warned = False

    class SimData:

        def __init__(self):
            self.bed_id = 0
            self.decoration_ids = None
            self.leave_reasons = {}
            self.leave_reason_times = {}

    class HouseholdsRoommatesData:

        def __init__(self, household_id, sim_ids):
            self.household_id = household_id
            self.sim_datas = {}
            for sim_id in sim_ids:
                self.sim_datas[sim_id] = RoommateService.SimData()
            self.blacklist = {}
            self.pending_destroy_decoration_ids = None
            self.locked_out_sim_id = None
            self.available_beds = 0

        @property
        def sim_ids(self):
            return self.sim_datas.keys()

    def __init__(self):
        super().__init__()
        self._zone_to_roommates = {}
        self._roommates_to_zone = {}
        self._reacquire_alarm_handle = None
        self._rent_schedule_alarm = None
        self._auto_invite_sim_infos = None
        self._interview_schedule_alarm = None
        self._interview_alarms = []
        self._interview_conformed_sims = []
        self._last_blacklist_update_time = None
        self._saved_ad_household_id = None
        self._last_check_time = None
        self._roommate_ids_to_update = None

    @classproperty
    def required_packs(cls):
        return (Pack.EP08,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_ROOMMATE_SERVICE

    def save(self, save_slot_data=None, **kwargs):
        roommate_service_data = Roommates_pb2.PersistableRoommateService()
        current_zone_id = services.current_zone_id()
        household_zone_id = None
        active_household = services.active_household()
        if active_household is not None:
            household_zone_id = active_household.home_zone_id
            self._roommate_ids_to_update = None
            for sim_id in tuple(self._roommates_to_zone):
                self._update_leave_reasons(sim_id)
        household_id = services.get_persistence_service().get_household_id_from_zone_id(current_zone_id)
        if household_id != 0:
            if current_zone_id not in self._zone_to_roommates:
                self._zone_to_roommates[current_zone_id] = RoommateService.HouseholdsRoommatesData(household_id, tuple())
            self._zone_to_roommates[current_zone_id].available_beds = self.get_available_roommate_count()
        for (zone_id, household_data) in self._zone_to_roommates.items():
            with ProtocolBufferRollback(roommate_service_data.roommate_datas) as roommate_data:
                roommate_data.zone_id = zone_id
                roommate_data.household_id = household_data.household_id
                for (sim_id, sim_data) in household_data.sim_datas.items():
                    with ProtocolBufferRollback(roommate_data.roommate_infos) as roommate_info:
                        roommate_info.sim_id = sim_id
                        roommate_info.bed_id = sim_data.bed_id
                        if sim_data.decoration_ids:
                            roommate_info.decoration_ids.extend(sim_data.decoration_ids)
                        for (reason, reason_data) in sim_data.leave_reasons.items():
                            with ProtocolBufferRollback(roommate_info.leave_reason_infos) as leave_reason_info:
                                leave_reason_info.reason = reason
                                leave_reason_info.total_time = reason_data.total_time.in_ticks()
                                leave_reason_info.been_warned = reason_data.been_warned
                if zone_id == household_zone_id:
                    self._update_blacklist(zone_id)
                for (sim_id, time_left) in household_data.blacklist.items():
                    with ProtocolBufferRollback(roommate_data.blacklist_infos) as blacklist_info:
                        blacklist_info.sim_id = sim_id
                        blacklist_info.time_left = time_left.in_ticks()
                roommate_data.available_beds = household_data.available_beds
                if household_data.pending_destroy_decoration_ids:
                    roommate_data.pending_destroy_decoration_ids.extend(household_data.pending_destroy_decoration_ids)
                if household_data.locked_out_sim_id is not None:
                    roommate_data.locked_out_id = household_data.locked_out_sim_id
        if household_id is not None and self._interview_schedule_alarm is not None:
            roommate_service_data.ad_info.interviewee_ids.extend(self._interview_conformed_sims)
            roommate_service_data.ad_info.household_id = services.active_household_id()
            for handle in self._interview_alarms:
                roommate_service_data.ad_info.pending_interview_alarms.append(handle.get_remaining_time().in_ticks())
        save_slot_data.gameplay_data.roommate_service = roommate_service_data

    def load(self, **_):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        roommate_service_data = save_slot_data_msg.gameplay_data.roommate_service
        for roommate_data in roommate_service_data.roommate_datas:
            household_data = RoommateService.HouseholdsRoommatesData(roommate_data.household_id, tuple())
            household_data.available_beds = roommate_data.available_beds
            for roommate_info in roommate_data.roommate_infos:
                sim_data = RoommateService.SimData()
                if roommate_info.decoration_ids:
                    sim_data.decoration_ids = []
                    sim_data.decoration_ids.extend(roommate_info.decoration_ids)
                sim_data.bed_id = roommate_info.bed_id
                for leave_reason_info in roommate_info.leave_reason_infos:
                    reason_data = RoommateService.LeaveReasonData()
                    reason_data.total_time = TimeSpan(leave_reason_info.total_time)
                    reason_data.been_warned = leave_reason_info.been_warned
                    sim_data.leave_reasons[leave_reason_info.reason] = reason_data
                household_data.sim_datas[roommate_info.sim_id] = sim_data
                self._roommates_to_zone[roommate_info.sim_id] = roommate_data.zone_id
            for blacklist_info in roommate_data.blacklist_infos:
                household_data.blacklist[blacklist_info.sim_id] = TimeSpan(blacklist_info.time_left)
            household_data.available_beds = roommate_data.available_beds
            for sim_id in household_data.sim_ids:
                self._roommates_to_zone[sim_id] = roommate_data.zone_id
            self._zone_to_roommates[roommate_data.zone_id] = household_data
            if roommate_data.pending_destroy_decoration_ids:
                household_data.pending_destroy_decoration_ids = []
                household_data.pending_destroy_decoration_ids.extend(roommate_data.pending_destroy_decoration_ids)
            if roommate_data.HasField('locked_out_id'):
                household_data.locked_out_sim_id = roommate_data.locked_out_id
        if roommate_service_data.HasField('ad_info'):
            self.trigger_interviews(True)
            self._interview_conformed_sims.extend(roommate_service_data.ad_info.interviewee_ids)
            self._saved_ad_household_id = roommate_service_data.ad_info.household_id
            for alarm_tick in roommate_service_data.ad_info.pending_interview_alarms:
                handle = alarms.add_alarm(self, TimeSpan(alarm_tick), lambda _: self._trigger_interview(), cross_zone=True)
                self._interview_alarms.append(handle)

    def _deconform_if_not_roommate(self, sim_id):
        if sim_id in self._roommates_to_zone:
            return
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is not None:
            self._deconform_roommate(sim_info)

    def _get_zone_and_data_from_sim_id(self, sim_id):
        if sim_id not in self._roommates_to_zone:
            return (None, None)
        zone_id = self._roommates_to_zone[sim_id]
        sim_data = self._zone_to_roommates[zone_id].sim_datas[sim_id]
        return (zone_id, sim_data)

    def _get_household_from_zone_id(self, zone_id):
        household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
        if household_id:
            return services.household_manager().get(household_id)

    def _clear_interview_sims(self):
        for sim_id in self._interview_conformed_sims:
            self._deconform_if_not_roommate(sim_id)

    def trigger_interviews(self, enabled, show_tns=False):
        if enabled:
            now = services.time_service().sim_now
            start_time = create_date_and_time(hours=self.INTERVIEW.start_stop_times.lower_bound)
            time_span = now.time_till_next_day_time(start_time)
            repeating_time_span = create_time_span(days=1)
            self._interview_schedule_alarm = alarms.add_alarm(self, time_span, lambda _: self._schedule_interviews(), repeating=True, repeating_time_span=repeating_time_span, cross_zone=True)
        else:
            if show_tns:
                active_sim_info = services.active_sim_info()
                resolver = SingleSimResolver(services.active_sim_info())
                notification = self.INTERVIEW.ad_auto_close_notification(active_sim_info, resolver=resolver)
                notification.show_dialog()
            if self._interview_schedule_alarm is not None:
                self._interview_schedule_alarm.cancel()
                self._interview_schedule_alarm = None
            for alarm in self._interview_alarms:
                alarm.cancel()
            self._interview_alarms = []
            situation_manager = services.get_zone_situation_manager()
            for situation in situation_manager.get_situations_by_type(self.INTERVIEW.situation):
                situation_manager.destroy_situation_by_id(situation.id)
            self._clear_interview_sims()

    def are_interviews_scheduled(self):
        return self._interview_schedule_alarm is not None

    def _process_removed_leave_reason(self, sim_info, sim_data_reason, leave_reason):
        if not sim_data_reason.been_warned:
            return
        household = services.active_household()
        sim_id = sim_info.sim_id
        sim_zone = self._roommates_to_zone[sim_id]
        if household.home_zone_id != sim_zone:
            return
        reason_data = self.LEAVING.leave_reasons[leave_reason]
        if reason_data.fixed_notification is not None:
            resolver = SingleSimResolver(sim_info)
            notification = reason_data.fixed_notification(services.active_sim_info(), resolver=resolver)
            notification.show_dialog()

    def _process_continuing_leave_reason(self, sim_info, sim_data_reason, leave_reason, time_span):
        reason_data = self.LEAVING.leave_reasons[leave_reason]
        total_time = sim_data_reason.total_time + time_span
        sim_data_reason.total_time = total_time
        if sim_data_reason.been_warned or reason_data.time_till_warning is None or total_time >= reason_data.time_till_warning():
            sim_data_reason.been_warned = True
            if reason_data.warning_notification is not None:
                resolver = SingleSimResolver(sim_info)
                notification = reason_data.warning_notification(services.active_sim_info(), resolver=resolver)
                notification.show_dialog()
                return False
            elif total_time >= reason_data.time_till_leave():
                resolver = SingleSimResolver(sim_info)
                notification = reason_data.leaving_notification(services.active_sim_info(), resolver=resolver)
                notification.show_dialog()
                self._remove_roommate(sim_info.sim_id)
                return True
        elif total_time >= reason_data.time_till_leave():
            resolver = SingleSimResolver(sim_info)
            notification = reason_data.leaving_notification(services.active_sim_info(), resolver=resolver)
            notification.show_dialog()
            self._remove_roommate(sim_info.sim_id)
            return True
        return False

    def _update_leave_reason_testing_time(self, sim_data, sim_id, testing_time, evict):
        now = services.time_service().sim_now
        span = TimeSpan.ZERO
        if testing_time in sim_data.leave_reason_times:
            span = now - sim_data.leave_reason_times[testing_time]
        sim_data.leave_reason_times[testing_time] = now
        sim_info = services.sim_info_manager().get(sim_id)
        resolver = SingleSimResolver(sim_info)
        for leave_reason in LEAVE_REASONS[testing_time]:
            leave_data = self.LEAVING.leave_reasons[leave_reason]
            if leave_data.tests is None:
                if leave_reason in sim_data.leave_reasons and self._process_continuing_leave_reason(sim_info, sim_data.leave_reasons[leave_reason], leave_reason, span):
                    return True
            elif leave_data.tests.tests.run_tests(resolver):
                if evict:
                    self._remove_roommate(sim_id)
                    return True
                if leave_reason not in sim_data.leave_reasons:
                    sim_data_reason = RoommateService.LeaveReasonData()
                    sim_data.leave_reasons[leave_reason] = sim_data_reason
                    temp_time_span = TimeSpan.ZERO
                else:
                    sim_data_reason = sim_data.leave_reasons[leave_reason]
                    temp_time_span = span
                if self._process_continuing_leave_reason(sim_info, sim_data_reason, leave_reason, temp_time_span):
                    return True
            elif leave_reason in sim_data.leave_reasons:
                sim_data_reason = sim_data.leave_reasons[leave_reason]
                del sim_data.leave_reasons[leave_reason]
                self._process_removed_leave_reason(sim_info, sim_data_reason, leave_reason)
        return False

    def _get_should_evict(self, zone_id):
        household = services.active_household()
        if household.home_zone_id != zone_id:
            return True
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue = venue_manager.get(build_buy.get_current_venue(zone_id))
        return venue.is_university_housing

    def _update_leave_reasons(self, sim_id, do_loot=False):
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            self._remove_roommate(sim_id)
            return
        (sim_zone_id, sim_data) = self._get_zone_and_data_from_sim_id(sim_id)
        if sim_zone_id is None:
            return
        evict = self._get_should_evict(sim_zone_id)
        if self._update_leave_reason_testing_time(sim_data, sim_id, LeaveReasonTestingTime.ALL_ROOMMATES, evict):
            return
        household = services.active_household()
        home_zone_id = household.home_zone_id
        if home_zone_id != sim_zone_id:
            sim_data.leave_reason_times.pop(LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_ALL_LOTS, None)
            sim_data.leave_reason_times.pop(LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_HOME_LOT, None)
            sim_data.leave_reason_times.pop(LeaveReasonTestingTime.UNTESTED, None)
            return
        if self._update_leave_reason_testing_time(sim_data, sim_id, LeaveReasonTestingTime.UNTESTED, evict):
            return
        if sim_info.get_sim_instance() is None:
            sim_data.leave_reason_times.pop(LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_ALL_LOTS, None)
            sim_data.leave_reason_times.pop(LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_HOME_LOT, None)
            return
        if do_loot:
            self.LEAVING.loot.apply_to_resolver(SingleSimResolver(sim_info))
        if household.home_zone_id == services.current_zone_id():
            if self._update_leave_reason_testing_time(sim_data, sim_id, LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_HOME_LOT, evict):
                return
        else:
            sim_data.leave_reason_times.pop(LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_HOME_LOT, None)
        self._update_leave_reason_testing_time(sim_data, sim_id, LeaveReasonTestingTime.HOUSEHOLD_ROOMMATES_ALL_LOTS, evict)

    def add_leave_reason(self, sim_info, leave_reason):
        sim_id = sim_info.sim_id
        (sim_zone_id, sim_data) = self._get_zone_and_data_from_sim_id(sim_id)
        if sim_zone_id is None:
            return
        if self._get_should_evict(sim_zone_id):
            self._remove_roommate(sim_id)
            return
        self._update_leave_reasons(sim_info.sim_id)
        if leave_reason not in sim_data.leave_reasons:
            sim_data_reason = RoommateService.LeaveReasonData()
            sim_data.leave_reasons[leave_reason] = sim_data_reason
            self._process_continuing_leave_reason(sim_info, sim_data_reason, leave_reason, TimeSpan.ZERO)

    def remove_leave_reason(self, sim_info, leave_reason):
        sim_id = sim_info.sim_id
        (_, sim_data) = self._get_zone_and_data_from_sim_id(sim_id)
        if leave_reason in sim_data.leave_reasons:
            sim_data_reason = sim_data.leave_reasons[leave_reason]
            del sim_data.leave_reasons[leave_reason]
            self._process_removed_leave_reason(sim_info, sim_data_reason, leave_reason)

    def has_leave_reasons(self, sim_info, leave_reasons):
        sim_id = sim_info.sim_id
        (_, sim_data) = self._get_zone_and_data_from_sim_id(sim_id)
        for leave_reason in leave_reasons:
            if leave_reason not in sim_data.leave_reasons:
                return False
        return True

    def update(self, zone_id):
        if not self._zone_to_roommates:
            return
        if services.active_household() is None:
            return
        if zone_id in self._zone_to_roommates:
            household_roommate_data = self._zone_to_roommates[zone_id]
            total_sims = len(household_roommate_data.sim_ids)
            household = self._get_household_from_zone_id(zone_id)
            available_roommate_space = self.UNPLAYED_HOUSEHOLD_AND_ROOMMATE_CAP
            if household is not None:
                total_sims += len(household)
                if household.is_played_household:
                    available_roommate_space = self.HOUSEHOLD_AND_ROOMMATE_CAP
            available_roommate_space -= total_sims
            leaving_roommates = []
            leaving_roommate_count = 0
            available_roommates = []
            for (sim_id, sim_data) in household_roommate_data.sim_datas.items():
                if RoommateLeaveReason.OVERCAPACITY in sim_data.leave_reasons:
                    leaving_roommates.append(sim_id)
                    leaving_roommate_count += 1
                else:
                    available_roommates.append(sim_id)
            if available_roommate_space + leaving_roommate_count < 0:
                if available_roommates:
                    sim_info_manager = services.sim_info_manager()
                    random.shuffle(available_roommates)
                    for _ in range(-(available_roommate_space + leaving_roommate_count)):
                        sim_info = sim_info_manager.get(available_roommates.pop())
                        self.add_leave_reason(sim_info, RoommateLeaveReason.OVERCAPACITY)
                        if not available_roommates:
                            break
            elif available_roommate_space + leaving_roommate_count > 0:
                sim_info_manager = services.sim_info_manager()
                random.shuffle(leaving_roommates)
                number_over = min(available_roommate_space + leaving_roommate_count, leaving_roommate_count)
                for _ in range(number_over):
                    sim_info = sim_info_manager.get(leaving_roommates.pop())
                    self.remove_leave_reason(sim_info, RoommateLeaveReason.OVERCAPACITY)
        if self._roommate_ids_to_update:
            start_time = time.clock()
            while time.clock() - start_time < self.LEAVING.time_slice_seconds and self._roommate_ids_to_update:
                self._update_leave_reasons(self._roommate_ids_to_update.pop(), do_loot=True)
        else:
            now = services.time_service().sim_now
            if self._last_check_time is None or now - self._last_check_time > self.LEAVING.check_interval():
                self._last_check_time = now
                self._roommate_ids_to_update = list(self._roommates_to_zone)

    def _schedule_interviews(self):
        self._interview_alarms = []
        for _ in range(self.INTERVIEW.interviews_per_day.random_int()):
            start_time = self.INTERVIEW.start_stop_times.random_float() - self.INTERVIEW.start_stop_times.lower_bound
            time_span = create_time_span(hours=start_time)
            handle = alarms.add_alarm(self, time_span, lambda _: self._trigger_interview(), cross_zone=True)
            self._interview_alarms.append(handle)
        self._interview_alarms = sorted(self._interview_alarms, key=lambda x: x.finishing_time, reverse=True)

    def _trigger_interview(self):
        self._interview_alarms.pop()
        zone_id = services.current_zone_id()
        if zone_id != services.active_household().home_zone_id:
            return
        self._update_blacklist(zone_id)
        if self.get_available_roommate_count() <= 0:
            self.trigger_interviews(False, show_tns=True)
        sim_info = self.find_potential_roommate()
        if sim_info is None:
            return
        if not self.conform_potential_roommate(sim_info):
            self._deconform_roommate(sim_info)
            return
        guest_list = self.INTERVIEW.situation.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        if self.INTERVIEW.job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(sim_info.sim_id, self.INTERVIEW.job, SituationInvitationPurpose.INVITED))
        situation_id = services.get_zone_situation_manager().create_situation(self.INTERVIEW.situation, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False)
        if situation_id is None:
            self._deconform_roommate(sim_info)
            return
        if zone_id not in self._zone_to_roommates:
            self._zone_to_roommates[zone_id] = RoommateService.HouseholdsRoommatesData(services.active_household_id(), tuple())
        self._zone_to_roommates[zone_id].blacklist[sim_info.sim_id] = self.INTERVIEW.interviewee_blackout_duration()
        self._last_blacklist_update_time = services.time_service().sim_now
        self._interview_conformed_sims.append(sim_info.sim_id)
        situation_manager = services.get_zone_situation_manager()
        situation_manager.register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._end_interview)

    def _end_interview(self, situation_id, callback_option, _):
        situation = services.get_zone_situation_manager().get(situation_id)
        if situation is None:
            return
        for sim_id in situation.invited_sim_ids:
            self._deconform_if_not_roommate(sim_id)

    def _reacquire_interview_situation(self):
        household = services.active_household()
        if household.home_zone_id != services.current_zone_id():
            self._clear_interview_sims()
        if self._saved_ad_household_id is None:
            return
        if self._saved_ad_household_id != household.id:
            self.trigger_interviews(False)
            self._saved_ad_household_id = None
            return
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_by_type(self.INTERVIEW.situation):
            situation_manager.register_for_callback(situation.id, SituationCallbackOption.END_OF_SITUATION, self._end_interview)

    def _update_blacklist(self, zone_id):
        if zone_id not in self._zone_to_roommates or self._last_blacklist_update_time is None:
            return
        new_blacklist = {}
        now = services.time_service().sim_now
        time_span = now - self._last_blacklist_update_time
        for (sim_id, time_left) in self._zone_to_roommates[zone_id].blacklist.items():
            time_left -= time_span
            if time_left > TimeSpan.ZERO:
                new_blacklist[sim_id] = time_left
        self._zone_to_roommates[zone_id].blacklist = new_blacklist
        self._last_blacklist_update_time = now

    def get_roommate_ids(self):
        return set(self._roommates_to_zone)

    def is_sim_info_roommate(self, sim_info, household_id=None):
        if sim_info.id not in self._roommates_to_zone:
            return False
        elif household_id is not None:
            return self._zone_to_roommates[self._roommates_to_zone[sim_info.id]].household_id == household_id
        return True

    def get_culling_npc_score(self, sim_id):
        if sim_id not in self._roommates_to_zone:
            return 0
        zone_id = self._roommates_to_zone[sim_id]
        household_id = self._zone_to_roommates[zone_id].household_id
        household = None
        if household_id != 0:
            household = services.household_manager().get(household_id)
        if household_id is not None and household is None:
            return self.ADDITIONAL_CULLING_IMMUNITY.no_household
        if household.is_active_household:
            return self.ADDITIONAL_CULLING_IMMUNITY.active_household
        if household.is_played_household:
            return self.ADDITIONAL_CULLING_IMMUNITY.previously_played_household
        return self.ADDITIONAL_CULLING_IMMUNITY.unplayed_household

    def get_auto_invite_sim_infos(self, host_sim, situation):
        invite_sims = []
        if situation.tags & self.AUTO_INVITE_BLACKLIST_TAGS:
            return invite_sims
        home_zone_id = host_sim.household.home_zone_id
        if home_zone_id not in self._zone_to_roommates:
            return invite_sims
        sim_info_manager = services.sim_info_manager()
        for sim_id in self._zone_to_roommates[home_zone_id].sim_ids:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info.has_trait(self.AUTO_INVITE_TRAIT) and random.random() <= self.AUTO_INVITE_CHANCE and sim_info.get_sim_instance() is not None:
                invite_sims.append(sim_info)
        if invite_sims:
            self._auto_invite_sim_infos = invite_sims
        return invite_sims

    def get_home_zone_id(self, sim_id):
        if sim_id not in self._roommates_to_zone:
            return 0
        else:
            return self._roommates_to_zone[sim_id]

    def get_ss3_affordance(self):
        return random.choice(self.SS3_PARK_INTERACTIONS)

    def generate_organization_roommate(self, org_id, sim_filter, additional_filter_terms, blacklist_sims):
        organization_service = services.organization_service()
        if organization_service:
            roommate_filter_terms = sim_filter.get_filter_terms() + additional_filter_terms
            results = organization_service.generate_organization_members(org_id, amount=1, blacklist_sims=blacklist_sims, additional_filter_terms=roommate_filter_terms)
            if results:
                return services.sim_info_manager().get(results[0])

    def find_potential_roommate(self, additional_filter_terms=(), org_sim_constraints=[], org_id=None):
        if org_id is None or len(org_sim_constraints) == 0:
            org_sim_constraints = None
        resolver = GlobalResolver(None)
        services.current_zone().service_npc_service
        blacklist = services.current_zone().service_npc_service.get_sim_info_ids()
        blacklist.update(self._roommates_to_zone)
        zone_id = services.current_zone_id()
        if zone_id in self._zone_to_roommates:
            blacklist.update(self._zone_to_roommates[zone_id].blacklist.keys())
        for test_filter_pair in self.ROOMMATE_SIM_FILTERS:
            if test_filter_pair.test.run_tests(resolver):

                def get_sim_filter_gsi_name():
                    return 'RoommateService find filter: {}'.format(test_filter_pair.sim_filter)

                if org_id is not None and org_sim_constraints is None:
                    return self.generate_organization_roommate(org_id, test_filter_pair.sim_filter, additional_filter_terms, blacklist)
                results = services.sim_filter_service().submit_matching_filter(sim_filter=test_filter_pair.sim_filter, callback=None, blacklist_sim_ids=blacklist, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name, additional_filter_terms=additional_filter_terms, sim_constraints=org_sim_constraints)
                if results:
                    return results[0].sim_info
                elif org_id is not None:
                    return self.generate_organization_roommate(org_id, test_filter_pair.sim_filter, additional_filter_terms, blacklist)
                return

    def conform_potential_roommate(self, roommate_sim_info):
        if roommate_sim_info.sim_id in self._interview_conformed_sims:
            return True
        resolver = SingleSimResolver(roommate_sim_info)
        sim_constraints = (roommate_sim_info.sim_id,)
        for category in self.ARCHETYPE_CATEGORIES:
            count = category.count.random_int()
            weighted_options = [(entry.weight.get_multiplier(resolver), entry.sim_filter) for entry in category.archetypes]
            while count > 0 and weighted_options:
                count -= 1
                sim_filter = sims4.random.pop_weighted(weighted_options)

                def get_sim_filter_gsi_name():
                    return 'RoommateService conform filter: {}'.format(sim_filter)

                results = services.sim_filter_service().submit_matching_filter(sim_filter=sim_filter, callback=None, sim_constraints=sim_constraints, allow_yielding=False, conform_if_constraints_fail=True, gsi_source_fn=get_sim_filter_gsi_name)
                if not results:
                    logger.error('Failed to conform potential roommate {} to filter {}', roommate_sim_info, sim_filter)
                    return False
        return True

    def add_roommate(self, sim_info, zone_id, assign_bed=True):
        sim_info_id = sim_info.id
        sim_info.roommate_zone_id = zone_id
        household_manager = services.household_manager()
        if len(sim_info.household) > 1:
            sim_info.household.remove_sim_info(sim_info)
            household = household_manager.create_household(sim_info.account)
            household.add_sim_info(sim_info)
            sim_info.assign_to_household(household)
        persistence_service = services.get_persistence_service()
        household_id = persistence_service.get_household_id_from_zone_id(zone_id)
        if household_id is None:
            household_id = 0
        if household_id != 0:
            household = household_manager.get(household_id)
            relationship_tracker = sim_info.relationship_tracker
            for household_sim_info in household:
                relationship_tracker.add_relationship_bit(household_sim_info.id, self.ROOMMATE_RELATIONSHIP_BIT, force_add=True)
        self._roommates_to_zone[sim_info_id] = zone_id
        if zone_id in self._zone_to_roommates:
            self._zone_to_roommates[zone_id].sim_datas[sim_info_id] = RoommateService.SimData()
        else:
            self._zone_to_roommates[zone_id] = RoommateService.HouseholdsRoommatesData(household_id, {sim_info_id})
        if zone_id == services.current_zone_id():
            if assign_bed:
                self.assign_bed(sim_info_id)
            self._add_roommate_to_situation(sim_info_id)
            self._zone_to_roommates[zone_id].available_beds = self.get_available_roommate_count()
        else:
            self._zone_to_roommates[zone_id].available_beds -= 1
        self._update_alarms()
        if self._interview_schedule_alarm and self._zone_to_roommates[zone_id].available_beds <= 0:
            self.trigger_interviews(False, show_tns=True)

    def remove_all_roommates_in_zone(self, zone_id, filter_func=None):
        if zone_id not in self._zone_to_roommates:
            return
        sim_ids = list(self._zone_to_roommates[zone_id].sim_ids)
        for sim_id in sim_ids:
            if not filter_func is None:
                if not filter_func(sim_id):
                    self._remove_roommate(sim_id)
            self._remove_roommate(sim_id)

    def remove_roommate(self, sim_info):
        self._remove_roommate(sim_info.id)

    def _remove_roommate(self, sim_id):
        if sim_id not in self._roommates_to_zone:
            return
        self._destroy_decorations(sim_id)
        zone_id = self._roommates_to_zone[sim_id]
        del self._roommates_to_zone[sim_id]
        del self._zone_to_roommates[zone_id].sim_datas[sim_id]
        if not self._zone_to_roommates[zone_id].sim_ids:
            del self._zone_to_roommates[zone_id]
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is not None:
            self._deconform_roommate(sim_info)
        if zone_id == services.current_zone_id():
            situation_manager = services.get_zone_situation_manager()
            for situation in situation_manager.get_situations_by_type(self.ROOMMATE_SITUATION):
                if sim_id in situation.invited_sim_ids:
                    situation_manager.destroy_situation_by_id(situation.id)
                    break
        household = self._get_household_from_zone_id(zone_id)
        if household is not None:
            household.object_preference_tracker.clear_sim_restriction(sim_id)
        self._update_alarms()

    def _deconform_roommate(self, sim_info):
        sim_info.roommate_zone_id = 0
        for relationship in sim_info.relationship_tracker:
            relationship.remove_bit(relationship.sim_id_a, relationship.sim_id_b, self.ROOMMATE_RELATIONSHIP_BIT)
        sim_info.trait_tracker.remove_traits_of_type(traits.traits.TraitType.ROOMMATE)

    def _add_roommate_to_situation(self, sim_id):
        guest_list = self.ROOMMATE_SITUATION.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        if self.ROOMMATE_JOB is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(sim_id, self.ROOMMATE_JOB, SituationInvitationPurpose.INVITED))
        services.get_zone_situation_manager().create_situation(self.ROOMMATE_SITUATION, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False)

    def on_all_households_and_sim_infos_loaded(self, client):
        for roommate_id in self.get_roommate_ids():
            sim_info = services.sim_info_manager().get(roommate_id)
            if sim_info is None or sim_info.household.home_zone_id != 0 or not sim_info.can_instantiate_sim:
                self._remove_roommate(roommate_id)
            else:
                sim_info.roommate_zone_id = self._roommates_to_zone[roommate_id]
        persistence_service = services.get_persistence_service()
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        for (zone_id, household_data) in self._zone_to_roommates.copy().items():
            try:
                venue = venue_manager.get(build_buy.get_current_venue(zone_id))
            except RuntimeError:
                venue = None
            if not venue is None:
                pass
            if not household_data.household_id != persistence_service.get_household_id_from_zone_id(zone_id):
                if household_data.household_id == 0:
                    for sim_id in tuple(household_data.sim_ids):
                        self._remove_roommate(sim_id)
            for sim_id in tuple(household_data.sim_ids):
                self._remove_roommate(sim_id)
        services.get_event_manager().register_single_event(self, TestEvent.SimDeathTypeSet)
        household = services.active_household()
        if household is None:
            return
        self._update_relationships(household.home_zone_id)

    def _do_rent(self, *_):
        household = services.get_active_sim().household
        zone_id = household.home_zone_id
        sim_ids = self._zone_to_roommates[zone_id].sim_ids
        total_rent = 0
        unpaid_sim_strings = []
        roommate_count = len(sim_ids)
        rent_per_sim = int(household.get_home_lot_value()*self.RENT.rent_modifer/(len(household) + roommate_count))
        for sim_id in sim_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info.has_trait(self.RENT.non_payment_trait) and sims4.random.random_chance(self.RENT.non_payment_chance*100):
                rent_owed_stat = sim_info.get_statistic(self.RENT.rent_owed_statistic)
                rent_owed_stat.add_value(rent_per_sim)
                unpaid_sim_strings.append(self.RENT.non_payment_format(sim_info))
            else:
                total_rent += rent_per_sim
        if unpaid_sim_strings or total_rent == 0:
            logger.error('Roommate rent payment: Somehow no rent')
        if total_rent != 0:
            household.funds.add(total_rent, Consts_pb2.FUNDS_ROOMMATE_RENT)
        client = services.client_manager().get_first_client()
        active_sim = client.active_sim
        if not unpaid_sim_strings:
            dialog = self.RENT.all_pay_notification(active_sim, SingleSimResolver(active_sim))
            dialog.show_dialog(additional_tokens=(rent_per_sim, total_rent))
        else:
            dialog = self.RENT.pay_failure_notification(active_sim, SingleSimResolver(active_sim))
            dialog.show_dialog(additional_tokens=(rent_per_sim, total_rent, roommate_count - len(unpaid_sim_strings), LocalizationHelperTuning.get_bulleted_list((None,), unpaid_sim_strings)))

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SimDeathTypeSet:
            self._remove_roommate(sim_info.sim_id)

    def on_household_member_added(self, household, sim_info):
        zone_id = household.home_zone_id
        if zone_id not in self._zone_to_roommates:
            return
        relationship_tracker = sim_info.relationship_tracker
        for sim_id in self._zone_to_roommates[zone_id].sim_ids:
            relationship_tracker.add_relationship_bit(sim_id, self.ROOMMATE_RELATIONSHIP_BIT, force_add=True)

    def on_household_member_removed(self, household, sim_info):
        zone_id = household.home_zone_id
        if zone_id not in self._zone_to_roommates:
            return
        relationship_tracker = sim_info.relationship_tracker
        for sim_id in self._zone_to_roommates[zone_id].sim_ids:
            relationship_tracker.remove_relationship_bit(sim_id, self.ROOMMATE_RELATIONSHIP_BIT)

    def _reacquire_roommates(self, *_, on_lot_only=False):
        if services.game_clock_service().clock_speed == ClockSpeedMode.SUPER_SPEED3:
            return
        zone_id = services.current_zone_id()
        if zone_id in self._zone_to_roommates:
            sim_ids = set(self._zone_to_roommates[zone_id].sim_ids)
            situation_manager = services.get_zone_situation_manager()
            for situation in situation_manager.get_situations_by_type(self.ROOMMATE_SITUATION):
                sim_ids.difference_update(situation.invited_sim_ids)
            for sim_id in sim_ids:
                sim_info = services.sim_info_manager().get(sim_id)
                if sim_info is None:
                    pass
                else:
                    (is_busy, _) = sim_info.is_busy()
                    if is_busy:
                        pass
                    elif on_lot_only and sim_info.zone_id != zone_id:
                        pass
                    else:
                        self._add_roommate_to_situation(sim_id)

    def _get_unassigned_household_count(self, household, beds, zone_id):
        unassigned_household_count = 0
        object_preference_tracker = household.object_preference_tracker
        object_manager = services.object_manager()
        for sim_info in household:
            (object_id, _) = object_preference_tracker.get_restricted_object(sim_info.sim_id, self.BED_PREFERENCE_TAG)
            if object_id is not None:
                obj = object_manager.get(object_id)
                if obj is not None:
                    beds.discard(obj)
                else:
                    unassigned_household_count += 1
            else:
                unassigned_household_count += 1
        beds_to_remove = set()
        for bed in beds:
            sim_ids = object_preference_tracker.get_restricted_sims(bed.id, self.BED_PREFERENCE_TAG)
            if sim_ids is not None and zone_id in self._zone_to_roommates:
                for sim_id in sim_ids:
                    if sim_id not in self._zone_to_roommates[zone_id].sim_ids:
                        beds_to_remove.add(bed)
        beds.difference_update(beds_to_remove)
        return unassigned_household_count

    def _populate_roommate_bed_assignments(self, household, beds, zone_id):
        unassigned_roommates = []
        single_occupied_beds = {}
        double_occupied_beds = {}
        object_preference_tracker = household.object_preference_tracker
        object_manager = services.object_manager()
        if zone_id in self._zone_to_roommates:
            for sim_id in self._zone_to_roommates[zone_id].sim_ids:
                (object_id, _) = object_preference_tracker.get_restricted_object(sim_id, self.BED_PREFERENCE_TAG)
                if object_id is not None:
                    obj = object_manager.get(object_id)
                    if obj is not None:
                        if obj in beds:
                            sim_ids = tuple(object_preference_tracker.get_restricted_sims(object_id, self.BED_PREFERENCE_TAG))
                            if len(sim_ids) > 1:
                                double_occupied_beds[obj] = sim_ids
                            else:
                                single_occupied_beds[obj] = sim_ids
                            beds.remove(obj)
                            unassigned_roommates.append(sim_id)
                    else:
                        unassigned_roommates.append(sim_id)
                else:
                    unassigned_roommates.append(sim_id)
        return (unassigned_roommates, single_occupied_beds, double_occupied_beds)

    def _remove_excess_roommates(self, beds, bed_delta, max_possible_new, zone_id, unassigned_roommates, double_occupied_beds, single_occupied_beds):
        while unassigned_roommates:
            while bed_delta < 0 or max_possible_new < 0:
                roommate_id_to_remove = unassigned_roommates.pop()
                self._remove_roommate(roommate_id_to_remove)
                bed_delta += 1
                max_possible_new += 1
        while bed_delta < 0:
            dict_to_pop = None
            if max_possible_new <= min(bed_delta, -1)*2 and double_occupied_beds:
                dict_to_pop = double_occupied_beds
            elif single_occupied_beds:
                dict_to_pop = single_occupied_beds
            elif double_occupied_beds:
                dict_to_pop = double_occupied_beds
            if dict_to_pop is None:
                break
            (obj, sim_ids) = dict_to_pop.popitem()
            for sim_id in sim_ids:
                self._remove_roommate(sim_id)
                max_possible_new += 1
            bed_delta += 1
            beds.add(obj)
        if max_possible_new < 0:
            sim_ids = self._zone_to_roommates[zone_id].sim_ids
            if sim_ids:
                for _ in range(-max_possible_new):
                    sim_id = random.choice(list(sim_ids))
                    self._remove_roommate(sim_id)
                    if not sim_ids:
                        break

    def get_available_roommate_count(self, beds=None, remove_extra=False):
        zone_id = services.current_zone_id()
        household = self._get_household_from_zone_id(zone_id)
        if household is None:
            if beds is None:
                beds = set(services.object_manager().get_objects_with_tags_gen(*self.BED_TAGS))
            roommate_count = min(self.UNPLAYED_HOUSEHOLD_AND_ROOMMATE_CAP, len(beds))
            if zone_id in self._zone_to_roommates:
                roommate_count -= len(self._zone_to_roommates[zone_id].sim_ids)
            if roommate_count < 0 and remove_extra:
                sim_ids = self._zone_to_roommates[zone_id].sim_ids
                for _ in range(-roommate_count):
                    sim_id = random.choice(list(sim_ids))
                    self._remove_roommate(sim_id)
                return 0
            return roommate_count
        if household.is_played_household:
            max_possible_new = self.HOUSEHOLD_AND_ROOMMATE_CAP - len(household)
        else:
            max_possible_new = self.UNPLAYED_HOUSEHOLD_AND_ROOMMATE_CAP - len(household)
        if zone_id in self._zone_to_roommates:
            max_possible_new -= len(self._zone_to_roommates[zone_id].sim_ids)
            if remove_extra or max_possible_new < 0:
                return -1
        if beds is None:
            beds = set(services.object_manager().get_objects_with_tags_gen(*self.BED_TAGS))
        unassigned_household_count = self._get_unassigned_household_count(household, beds, zone_id)
        unassigned_roommates = []
        double_occupied_beds = {}
        single_occupied_beds = {}
        (unassigned_roommates, single_occupied_beds, double_occupied_beds) = self._populate_roommate_bed_assignments(household, beds, zone_id)
        bed_delta = len(beds) - len(unassigned_roommates) - unassigned_household_count
        if bed_delta >= 0 and max_possible_new >= 0:
            return min(max_possible_new, bed_delta)
        if not remove_extra:
            if bed_delta < 0:
                return -1
            if bed_delta == 0:
                return 0
            else:
                self._remove_excess_roommates(beds, bed_delta, max_possible_new, zone_id, unassigned_roommates, double_occupied_beds, single_occupied_beds)
                return 0
        self._remove_excess_roommates(beds, bed_delta, max_possible_new, zone_id, unassigned_roommates, double_occupied_beds, single_occupied_beds)
        return 0

    def assign_bed(self, sim_id, avoid_id=None):
        zone_id = services.current_zone_id()
        if zone_id not in self._zone_to_roommates:
            return
        if sim_id not in self._zone_to_roommates[zone_id].sim_ids:
            return
        household = self._get_household_from_zone_id(zone_id)
        if household is None:
            return
        object_preference_tracker = household.object_preference_tracker
        old_bed = None
        for bed in services.object_manager().get_objects_with_tags_gen(*self.BED_TAGS):
            bed_id = bed.id
            if object_preference_tracker.get_restricted_sims(bed_id, self.BED_PREFERENCE_TAG) is None:
                if bed_id == avoid_id:
                    old_bed = bed
                else:
                    object_preference_tracker.set_object_restriction(sim_id, bed, self.BED_PREFERENCE_TAG)
                    return
        if old_bed is not None:
            object_preference_tracker.set_object_restriction(sim_id, old_bed, self.BED_PREFERENCE_TAG)

    def get_available_roommate_count_for_zone(self, zone_id):
        if zone_id == services.current_zone_id():
            return self.get_available_roommate_count()
        elif zone_id in self._zone_to_roommates:
            return self._zone_to_roommates[zone_id].available_beds
        else:
            return 0
        return 0

    def on_zone_unload(self):
        self._reacquire_alarm_handle = None
        self._roommate_ids_to_update = None
        if services.active_household() is not None:
            for sim_id in tuple(self._roommates_to_zone):
                self._update_leave_reasons(sim_id)
        zone_id = services.current_zone_id()
        persistence_service = services.get_persistence_service()
        household_id = persistence_service.get_household_id_from_zone_id(zone_id)
        if household_id is None:
            household_id = 0
        if household_id != 0:
            if zone_id not in self._zone_to_roommates:
                self._zone_to_roommates[zone_id] = RoommateService.HouseholdsRoommatesData(household_id, tuple())
            self._zone_to_roommates[zone_id].available_beds = self.get_available_roommate_count()

    def _destroy_decorations(self, sim_id):
        if sim_id not in self._roommates_to_zone:
            return
        zone_id = self._roommates_to_zone[sim_id]
        household_data = self._zone_to_roommates[zone_id]
        sim_data = household_data.sim_datas[sim_id]
        decoration_ids = sim_data.decoration_ids
        if not decoration_ids:
            return
        if zone_id != services.current_zone_id():
            if household_data.pending_destroy_decoration_ids is None:
                household_data.pending_destroy_decoration_ids = []
            household_data.pending_destroy_decoration_ids.extend(decoration_ids)
        else:
            object_manager = services.object_manager()
            for object_id in decoration_ids:
                obj = object_manager.get(object_id)
                if obj is not None:
                    obj.destroy(source=self, cause='Destroying roommate decorations')
        sim_data.decoration_ids = None

    def _try_to_place(self, obj_to_place, nearby_slots, household):
        for runtime_slot in nearby_slots:
            if runtime_slot.is_valid_for_placement(definition=obj_to_place, objects_to_ignore=runtime_slot.children):
                break
        return
        obj = create_object(obj_to_place)
        if obj is None:
            return
        obj.update_ownership(household.sim_infos[0])
        for child in list(runtime_slot.children):
            build_buy.move_object_to_household_inventory(child, failure_flags=HouseholdInventoryFlags.DESTROY_OBJECT)
        runtime_slot.add_child(obj)
        nearby_slots.remove(runtime_slot)
        return obj

    def _handle_pending_destroy_decorations(self):
        zone_id = services.current_zone_id()
        if zone_id not in self._zone_to_roommates:
            return
        household_data = self._zone_to_roommates[zone_id]
        object_manager = services.object_manager()
        if household_data.pending_destroy_decoration_ids:
            for object_id in household_data.pending_destroy_decoration_ids:
                obj = object_manager.get(object_id)
                if obj is not None:
                    obj.destroy(source=self, cause='Destroying roommate decorations')
            household_data.pending_destroy_decoration_ids = None

    def do_decorations(self):
        zone_id = services.current_zone_id()
        if zone_id not in self._zone_to_roommates:
            return
        household_data = self._zone_to_roommates[zone_id]
        household = self._get_household_from_zone_id(zone_id)
        if household is None:
            return
        object_preference_tracker = household.object_preference_tracker
        object_manager = services.object_manager()
        bed_to_sim_id = {}
        blacklist_object_ids = set()
        for (sim_id, sim_data) in household_data.sim_datas.items():
            (bed_id, _) = object_preference_tracker.get_restricted_object(sim_id, self.BED_PREFERENCE_TAG)
            if bed_id is not None and bed_id != sim_data.bed_id:
                sim_data.bed_id = bed_id
                self._destroy_decorations(sim_id)
                bed = object_manager.get(bed_id)
                if bed is None:
                    logger.error("Roommate with sim_id: {} assigned to bed id {} that doesn't exist", sim_id, bed_id)
                bed_to_sim_id[bed] = sim_id
            elif sim_data.decoration_ids:
                blacklist_object_ids.update(sim_data.decoration_ids)
        if not bed_to_sim_id:
            return
        sim_info_manager = services.sim_info_manager()
        slottable_objects = defaultdict(list)
        for obj in object_manager.valid_objects():
            for _ in obj.get_runtime_slots_gen():
                slottable_objects[obj.routing_surface].append(obj)
                break
        if not slottable_objects:
            return
        for (bed, sim_id) in bed_to_sim_id.items():
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            else:
                weighted_objects = []
                resolver = SingleSimResolver(sim_info)
                sim_data = household_data.sim_datas[sim_id]
                for decoration in self.DECORATING.decorations:
                    weight = decoration.weight.get_multiplier(resolver)
                    if weight > 0:
                        definitions = decoration.item.get_definitions()
                        if definitions:
                            weighted_objects.append((weight, definitions))
                if not weighted_objects:
                    pass
                else:
                    nearby_slots = set()
                    for obj in slottable_objects[bed.routing_surface]:
                        delta = obj.position - bed.position
                        if delta.magnitude_squared() > self.DECORATING.distance:
                            pass
                        else:
                            (result, obj_id) = obj.check_line_of_sight(bed.transform, verbose=True)
                            if (result == routing.RAYCAST_HIT_TYPE_IMPASSABLE or result == routing.RAYCAST_HIT_TYPE_LOS_IMPASSABLE) and not obj_id:
                                pass
                            else:
                                for run_time_slot in obj.get_runtime_slots_gen():
                                    for child in run_time_slot.children:
                                        if child.id in blacklist_object_ids:
                                            break
                                    nearby_slots.add(run_time_slot)
                    placed_definitions = set()
                    for _ in range(self.DECORATING.number_to_place.random_int()):
                        while weighted_objects:
                            index_to_place = sims4.random.weighted_random_index(weighted_objects)
                            obj_list = weighted_objects[index_to_place][1]
                            obj_to_place = obj_list.pop()
                            if not obj_list:
                                weighted_objects.pop(index_to_place)
                            if obj_to_place not in placed_definitions:
                                break
                        placed_definitions.add(obj_to_place)
                        obj = self._try_to_place(obj_to_place, nearby_slots, household)
                        if obj is not None:
                            if sim_data.decoration_ids is None:
                                sim_data.decoration_ids = [obj.id]
                            else:
                                sim_data.decoration_ids.append(obj.id)
                            blacklist_object_ids.add(obj.id)
                        if weighted_objects:
                            if not nearby_slots:
                                return
                        return

    def assign_beds_for_current_zone(self, beds=None):
        zone_id = services.current_zone_id()
        household = self._get_household_from_zone_id(zone_id)
        if household is None:
            return
        object_preference_tracker = household.object_preference_tracker
        if beds is None:
            beds = set()
            for bed in services.object_manager().get_objects_with_tags_gen(*self.BED_TAGS):
                if object_preference_tracker.get_restricted_sims(bed.id, self.BED_PREFERENCE_TAG) is None:
                    beds.add(bed)
        for sim_id in self._zone_to_roommates[zone_id].sim_ids:
            if not beds:
                break
            (object_id, _) = object_preference_tracker.get_restricted_object(sim_id, self.BED_PREFERENCE_TAG)
            if object_id is None:
                bed = beds.pop()
                object_preference_tracker.set_object_restriction(sim_id, bed, self.BED_PREFERENCE_TAG)

    def _fixup_university_household(self):
        zone_id = services.current_zone_id()
        if zone_id in self._zone_to_roommates:
            persistence_service = services.get_persistence_service()
            household_id = persistence_service.get_household_id_from_zone_id(zone_id)
            if household_id is None:
                household_id = 0
            household_data = self._zone_to_roommates[zone_id]
            old_household_id = household_data.household_id
            sim_ids = household_data.sim_ids
            if old_household_id != household_id:
                self._zone_to_roommates[zone_id] = RoommateService.HouseholdsRoommatesData(household_id, sim_ids)

    def _update_relationships(self, zone_id):
        if zone_id in self._zone_to_roommates:
            persistence_service = services.get_persistence_service()
            household_id = persistence_service.get_household_id_from_zone_id(zone_id)
            if household_id is None:
                household_id = 0
            if household_id == 0:
                return
            household = services.household_manager().get(household_id)
            if household is None:
                return
            for sim_id in self._zone_to_roommates[zone_id].sim_ids:
                sim_info = services.sim_info_manager().get(sim_id)
                if sim_info is not None:
                    relationship_tracker = sim_info.relationship_tracker
                    for household_sim_info in household:
                        relationship_tracker.add_relationship_bit(household_sim_info.id, self.ROOMMATE_RELATIONSHIP_BIT, force_add=True)

    def initialize_editmode_roommates(self):
        self._handle_pending_destroy_decorations()

    def initialize_roommates(self):
        self._handle_auto_invite()
        self._initialize_roommates()
        self._reacquire_interview_situation()
        self._handle_pending_destroy_decorations()
        self._handle_queued_lock_out()
        self._update_alarms()

    def _handle_queued_lock_out(self):
        zone_id = services.current_zone_id()
        if zone_id not in self._zone_to_roommates:
            return
        household_data = self._zone_to_roommates[zone_id]
        sim_id = household_data.locked_out_sim_id
        if sim_id is None:
            return
        household_data.locked_out_sim_id = None
        if sim_id not in household_data.sim_ids:
            return
        guest_list = self.LOCKED_OUT_SITUATION.situation.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        if self.LOCKED_OUT_SITUATION.job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(sim_id, self.LOCKED_OUT_SITUATION.job, SituationInvitationPurpose.INVITED))
        services.get_zone_situation_manager().create_situation(self.LOCKED_OUT_SITUATION.situation, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False)

    def queue_locked_out_sim_id(self, sim_id):
        if sim_id not in self._roommates_to_zone:
            return
        zone_id = self._roommates_to_zone[sim_id]
        household_data = self._zone_to_roommates[zone_id]
        household_data.locked_out_sim_id = sim_id

    def _handle_auto_invite(self):
        zone_id = services.current_zone_id()
        if self._auto_invite_sim_infos:
            travelled_auto_invite_sim_infos = []
            for sim_info in self._auto_invite_sim_infos:
                if sim_info.zone_id == zone_id:
                    travelled_auto_invite_sim_infos.append(sim_info)
            if travelled_auto_invite_sim_infos:
                notified_sim = random.choice(travelled_auto_invite_sim_infos)
                if notified_sim:
                    resolver = SingleSimResolver(notified_sim)
                    dialog = self.AUTO_INVITE_DIALOG(None, target_sim_id=notified_sim.sim_id, resolver=resolver)
                    dialog.show_dialog()
        self._auto_invite_sim_infos = None

    def _cleanup_university_housing_roommates(self, zone_id):

        def filter_function(sim_id):
            return UniversityUtils.validate_household_roommate(sim_id, zone_id)

        self.remove_all_roommates_in_zone(zone_id, filter_function)

    def _create_university_roommate(self, _, beds=None, assign_bed=True, remove_extra=False, create_half=False):
        self._university_roommate_timeslice_alarm = None
        zone_id = services.current_zone_id()
        additional_filter_terms = UniversityUtils.get_university_housing_roommate_filter_terms(zone_id)
        roommate_count = self.get_available_roommate_count(beds=beds, remove_extra=remove_extra)
        if roommate_count == 0:
            return
        if create_half and roommate_count > 1:
            roommate_to_create = math.floor(roommate_count/2)
        else:
            roommate_to_create = 1
        org_members_list = []
        organization = UniversityUtils.get_university_organization_requirement(zone_id)
        if organization is not None:
            organization_service = services.organization_service()
            if organization_service:
                org_members_list = organization_service.get_organization_members(organization.guid64)
        if roommate_to_create > 0:
            org_id = organization.guid64 if organization is not None else None
            for _ in range(roommate_to_create):
                sim_info = self.find_potential_roommate(additional_filter_terms, org_members_list, org_id)
                if sim_info is not None:
                    if self.conform_potential_roommate(sim_info):
                        self.add_roommate(sim_info, zone_id, assign_bed=assign_bed)
                    else:
                        self._deconform_roommate(sim_info)
        if roommate_count - roommate_to_create > 0:
            self._university_roommate_timeslice_alarm = alarms.add_alarm(self, self.UNIVERSITY_ROOMMATE_TIMESLICE(), self._create_university_roommate)

    def _initialize_roommates(self):
        zone_id = services.current_zone_id()
        venue = services.get_current_venue()
        beds = None
        household = services.active_household()
        if household is None or household.home_zone_id != zone_id:
            self._update_relationships(zone_id)
        if venue.is_university_housing:
            self._cleanup_university_housing_roommates(zone_id)
            self._fixup_university_household()
            beds = set(services.object_manager().get_objects_with_tags_gen(*self.BED_TAGS))
            self._create_university_roommate(None, beds=beds, assign_bed=False, remove_extra=True, create_half=True)
        if zone_id in self._zone_to_roommates:
            self.assign_beds_for_current_zone(beds=beds)
            self._reacquire_roommates(on_lot_only=True)

    def _update_alarms(self):
        household = services.active_household()
        zone_id = household.home_zone_id
        if zone_id in self._zone_to_roommates and self._zone_to_roommates[zone_id].sim_ids:
            if self._rent_schedule_alarm is None:
                venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
                venue = venue_manager.get(build_buy.get_current_venue(zone_id))
                if not venue.is_university_housing:
                    self._rent_schedule_alarm = self.RENT.schedule(start_callback=self._do_rent, schedule_immediate=False, cross_zone=True)
        elif self._rent_schedule_alarm is not None:
            self._rent_schedule_alarm.destroy()
            self._rent_schedule_alarm = None
        zone_id = services.current_zone_id()
        if zone_id in self._zone_to_roommates:
            if self._reacquire_alarm_handle is None:
                self._reacquire_alarm_handle = alarms.add_alarm(self, self.OFFLOT_ALARM_INTERVAL(), self._reacquire_roommates, repeating=True)
        else:
            self._reacquire_alarm_handle = None
