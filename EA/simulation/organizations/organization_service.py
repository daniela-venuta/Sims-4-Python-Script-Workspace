from _collections import defaultdictimport itertoolsimport randomfrom protocolbuffers import GameplaySaveData_pb2, DistributorOps_pb2from date_and_time import create_date_and_time, date_and_time_from_week_time, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom drama_scheduler.drama_node import TimeSelectionOptionfrom drama_scheduler.festival_drama_node import MajorOrganizationEventDramaNodefrom event_testing.resolver import DataResolverfrom filters.tunable import FilterTermVariantfrom gsi_handlers.drama_handlers import GSIDramaScoringData, is_scoring_archive_enabledfrom organizations.organization_enums import OrganizationStatusEnumfrom organizations.organization_ops import SendOrganizationEventUpdateOpfrom organizations.organization_tracker import OrganizationTrackerfrom services import snippet_managerfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableList, TunableMapping, TunableTuple, TunableRange, TunableRegionDescription, TunableReferencefrom sims4.utils import classpropertyfrom time_service import FrozenTimelinefrom venues.venue_event_drama_node import OrganizationEventDramaNode, VenueEventDramaNodefrom world.region import Regionimport alarmsimport persistence_error_typesimport servicesimport sims4logger = sims4.log.Logger('OrganizationService', default_owner='shipark')
class OrganizationService(Service):
    ORGANIZATION_EVENTS = TunableList(description='\n        The list of organization event drama nodes that will be scheduled\n        at the start of the game.\n        \n        NOTE: These should not include venue drama nodes, which are handled\n        separately in the Venue Org Event Mapping.\n        ', tunable=TunableReference(description="\n            Drama Node that is part of an organization's events.\n            ", manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), pack_safe=True))
    VENUE_ORG_EVENT_MAPPING = TunableMapping(description='\n        Each entry in the venue org event mapping maps a venue-type to the org\n        events that should be scheduled at the venue.\n        ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True), value_type=TunableTuple(org_drama_node_events=TunableList(description="\n                A list of drama nodes that provide organization events to venues\n                that they're a part of.\n                ", tunable=TunableReference(description='\n                    A drama node that will contain an organization event on a venue.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions=('OrganizationEventDramaNode',), pack_safe=True)), org_zones_to_schedule=TunableRange(description='\n                The number of zones with this venue type on which to schedule\n                org drama nodes.\n                ', tunable_type=int, minimum=0, default=1), org_preferred_regions=TunableList(description='\n                A list of regions that will be used to initially attempt to schedule\n                a venue event on. If no venues of the venue type exist within that region,\n                any available venue will be used, as long as it is not blacklisted.\n                ', tunable=TunableRegionDescription(description="\n                    The venue's street owner that is preferred to schedule a venue event.\n                    ", pack_safe=True)), org_blacklisted_regions=TunableList(description='\n                A list of regions that are invalid for scheduling venue event on.\n                ', tunable=TunableRegionDescription(description="\n                    The venue's street owner that is invalid for scheduling a venue event.\n                    ", pack_safe=True))))
    ADDITIONAL_FILTER_TERMS_ON_GENERATING_NEW_MEMBERS = TunableList(description='\n        A list of additional filter terms to apply on sims that are considered\n        for membership in any organization. \n        ', tunable=FilterTermVariant())

    @classmethod
    def verify_tunable_callback(cls):
        for (i, drama_node) in enumerate(cls.ORGANIZATION_EVENTS):
            if type(drama_node) is VenueEventDramaNode:
                logger.error('Drama Node ({}) at index ({}) is tuned on Organization Events but is                            a Venue Event Drama Node and cannot be. Try moving it to VENUE_ORG_EVENT_MAPPING', drama_node, i)

    def __init__(self, *_, **__):
        self._organization_members = defaultdict(list)
        self._event_updates = defaultdict(list)
        self._organization_festival_events = {}
        self._organization_venue_events = {}
        self._schedule_cancelled_venue_event_alarm = {}

    def save(self, save_slot_data=None, **__):
        organization_proto = GameplaySaveData_pb2.PersistableOrganizationService()
        for (org_id, members_list) in self._organization_members.items():
            with ProtocolBufferRollback(organization_proto.organizations) as organization_msg:
                organization_msg.organization_id = org_id
                for member_id in members_list:
                    with ProtocolBufferRollback(organization_msg.organization_members) as organization_members_msg:
                        organization_members_msg.organization_member_id = member_id
        for (drama_node_id, alarm_handle) in self._schedule_cancelled_venue_event_alarm.items():
            with ProtocolBufferRollback(organization_proto.schedule_cancelled_event_data) as schedule_cancelled_event_msg:
                schedule_cancelled_event_msg.schedule_venue_event_time = alarm_handle.get_remaining_time().in_ticks()
                schedule_cancelled_event_msg.org_event_id = drama_node_id
        save_slot_data.gameplay_data.organization_service = organization_proto

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_ORGANIZATION_SERVICE

    def load(self, **__):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.gameplay_data.HasField('organization_service'):
            data = save_slot_data_msg.gameplay_data.organization_service
            for org_data in data.organizations:
                members_list = []
                for org_member_data in org_data.organization_members:
                    members_list.append(org_member_data.organization_member_id)
                self._organization_members[org_data.organization_id] = members_list
            for schedule_cancelled_event_data in data.schedule_cancelled_event_data:
                if schedule_cancelled_event_data.HasField('schedule_venue_event_time') and schedule_cancelled_event_data.HasField('org_event_id'):
                    alarm_handle = alarms.add_alarm(self, TimeSpan(schedule_cancelled_event_data.schedule_venue_event_time), lambda *_: self._schedule_cancelled_organization_event(schedule_cancelled_event_data.org_event_id), cross_zone=True)
                    self._schedule_cancelled_venue_event_alarm[schedule_cancelled_event_data.org_event_id] = alarm_handle

    def _is_organization_event_type(self, drama_node):
        return issubclass(type(drama_node), OrganizationEventDramaNode) or issubclass(type(drama_node), MajorOrganizationEventDramaNode)

    def _schedule_cancelled_organization_event(self, org_event_id, *args):
        drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
        node_type = drama_node_manager.get(org_event_id)
        if node_type is None:
            return
        if org_event_id in self._schedule_cancelled_venue_event_alarm:
            del self._schedule_cancelled_venue_event_alarm[org_event_id]
        event_venue_tuning = self.get_organization_venue_tuning(node_type)
        if event_venue_tuning is None:
            return
        org_venue_event_info = self.VENUE_ORG_EVENT_MAPPING.get(event_venue_tuning)
        max_allowed = org_venue_event_info.org_zones_to_schedule
        if max_allowed == 0:
            return

        def schedule_cancelled_org_event(zone_ids_gen, org_event_type, max_allowed):
            for zone_id in zone_ids_gen:
                self._schedule_venue_organization_event(node_type, zone_id)
                max_allowed -= 1
                if max_allowed <= 0:
                    return max_allowed
            return max_allowed

        venue_service = services.venue_service()
        try_zones_in_preferred_regions = True
        preferred_zone_ids_gen = self.get_preferred_zones_gen(org_venue_event_info.org_preferred_regions, event_venue_tuning)
        if preferred_zone_ids_gen is None:
            try_zones_in_preferred_regions = False
        if try_zones_in_preferred_regions:
            max_allowed = schedule_cancelled_org_event(preferred_zone_ids_gen, node_type, max_allowed)
            if max_allowed <= 0:
                self.update_organization_events_panel()
                return
        all_zones_with_venue_tuning_gen = venue_service.get_zones_for_venue_type_gen(event_venue_tuning, region_blacklist=org_venue_event_info.org_blacklisted_regions)
        max_allowed = schedule_cancelled_org_event(all_zones_with_venue_tuning_gen, node_type, max_allowed)
        if max_allowed <= 0:
            self.update_organization_events_panel()

    def _schedule_venue_organization_event(self, org_drama_node, zone_id):
        drama_scheduler = services.drama_scheduler_service()
        resolver = DataResolver(None)
        org_start_time = self.verify_valid_time(org_drama_node)
        if org_start_time is None:
            return
        gsi_data = None
        if is_scoring_archive_enabled():
            gsi_data = GSIDramaScoringData()
            gsi_data.bucket = 'Venue Organization Event'
        uid = drama_scheduler.schedule_node(org_drama_node, resolver, specific_time=org_start_time, setup_kwargs={'gsi_data': gsi_data, 'zone_id': zone_id})
        if uid is not None:
            self._organization_venue_events[uid] = str(org_drama_node)
            drama_scheduler.add_complete_callback(uid, self._reschedule_venue_org_event)

    def get_preferred_zones_gen(self, preferred_regions, event_venue_tuning):
        venue_service = services.venue_service()
        preferred_zone_ids_gen = None
        for region_id in preferred_regions:
            region = Region.REGION_DESCRIPTION_TUNING_MAP.get(region_id)
            if preferred_zone_ids_gen is None:
                preferred_zone_ids_gen = venue_service.get_zones_for_venue_type_gen(event_venue_tuning, compatible_region=region, ignore_region_compatability_tags=True)
            else:
                preferred_zone_ids_gen = itertools.chain(preferred_zone_ids_gen, venue_service.get_zones_for_venue_type_gen(event_venue_tuning, compatible_region=region, ignore_region_compatability_tags=True))
        return preferred_zone_ids_gen

    def verify_valid_time(self, drama_node):
        time_option = drama_node.time_option
        if time_option.option != TimeSelectionOption.SINGLE_TIME:
            logger.error('Drama Node ({}) does not have a valid time tuned and will not schedule.', drama_node)
            return
        else:
            now = services.time_service().sim_now
            org_day_and_hour = create_date_and_time(days=time_option.valid_time.day, hours=time_option.valid_time.hour)
            org_start_time = date_and_time_from_week_time(now.week(), org_day_and_hour)
            if org_start_time < now:
                org_start_time = date_and_time_from_week_time(now.week() + 1, org_day_and_hour)
            if org_start_time < now:
                return
        return org_start_time

    def schedule_org_events(self):
        resolver = DataResolver(None)
        drama_scheduler = services.drama_scheduler_service()
        scheduled_org_events = [type(drama_node) for drama_node in drama_scheduler.scheduled_nodes_gen() if self._is_organization_event_type(drama_node)]
        active_org_events = [type(drama_node) for drama_node in drama_scheduler.active_nodes_gen() if self._is_organization_event_type(drama_node)]
        for org_drama_node in self.ORGANIZATION_EVENTS:
            if not org_drama_node in scheduled_org_events:
                if org_drama_node in active_org_events:
                    pass
                else:
                    org_start_time = self.verify_valid_time(org_drama_node)
                    if org_start_time is None:
                        pass
                    else:
                        gsi_data = None
                        if is_scoring_archive_enabled():
                            gsi_data = GSIDramaScoringData()
                            gsi_data.bucket = 'Organization Event'
                        uid = drama_scheduler.schedule_node(org_drama_node, resolver, gsi_data=gsi_data, specific_time=org_start_time, setup_kwargs={'gsi_data': gsi_data})
                        if uid is not None:
                            self._organization_festival_events[uid] = str(org_drama_node)
                            drama_scheduler.add_complete_callback(uid, self._reschedule_festival_org_event)
        venue_service = services.venue_service()
        for (event_venue_tuning, org_venue_event_info) in self.VENUE_ORG_EVENT_MAPPING.items():
            if not org_venue_event_info.org_drama_node_events:
                pass
            else:
                org_drama_nodes = [drama_node for drama_node in org_venue_event_info.org_drama_node_events if drama_node not in scheduled_org_events and drama_node not in active_org_events and drama_node.guid64 not in self._schedule_cancelled_venue_event_alarm.keys()]
                if not org_drama_nodes:
                    pass
                else:
                    max_allowed = org_venue_event_info.org_zones_to_schedule
                    if max_allowed == 0:
                        pass
                    else:
                        try_zones_in_preferred_regions = True
                        preferred_zone_ids_gen = self.get_preferred_zones_gen(org_venue_event_info.org_preferred_regions, event_venue_tuning)
                        if preferred_zone_ids_gen is None:
                            try_zones_in_preferred_regions = False

                        def schedule_events(zone_ids, max_allowed, org_drama_nodes):
                            for zone_id in zone_ids:
                                for org_drama_node in org_drama_nodes:
                                    self._schedule_venue_organization_event(org_drama_node, zone_id)
                                max_allowed -= 1
                                if max_allowed <= 0:
                                    break
                            return max_allowed

                        if try_zones_in_preferred_regions:
                            max_allowed = schedule_events(preferred_zone_ids_gen, max_allowed, org_drama_nodes)
                            if max_allowed <= 0:
                                pass
                            else:
                                all_zones_with_venue_tuning_gen = venue_service.get_zones_for_venue_type_gen(event_venue_tuning, region_blacklist=org_venue_event_info.org_blacklisted_regions)
                                schedule_events(all_zones_with_venue_tuning_gen, max_allowed, org_drama_nodes)
                        else:
                            all_zones_with_venue_tuning_gen = venue_service.get_zones_for_venue_type_gen(event_venue_tuning, region_blacklist=org_venue_event_info.org_blacklisted_regions)
                            schedule_events(all_zones_with_venue_tuning_gen, max_allowed, org_drama_nodes)

    def on_zone_load(self):
        for (org_id, sims) in self._organization_members.items():
            for sim_id in sims:
                sim = services.sim_info_manager().get(sim_id)
                if sim is None:
                    pass
                else:
                    organization_tracker = sim.organization_tracker
                    if organization_tracker.get_organization_status(org_id) == OrganizationStatusEnum.ACTIVE:
                        organization_tracker.send_organization_update_message(DistributorOps_pb2.OrganizationUpdate.ADD, org_id)
        self.update_organization_events_panel()

    def post_game_services_zone_load(self):
        self.cleanup_scheduled_or_active_events()
        self.schedule_org_events()
        self.update_organization_events_panel()

    def cleanup_scheduled_or_active_events(self):
        drama_scheduler = services.drama_scheduler_service()
        persistence_service = services.get_persistence_service()
        for uid in self._organization_festival_events.keys():
            drama_scheduler.add_complete_callback(uid, self._reschedule_festival_org_event)
        cancelled_venue_event_nodes_uids = []
        for uid in self._organization_venue_events.keys():
            drama_node_inst = drama_scheduler.get_scheduled_node_by_uid(uid)
            if drama_node_inst is not None:
                zone_data = persistence_service.get_zone_proto_buff(drama_node_inst.zone_id)
                if zone_data is None:
                    drama_scheduler.cancel_scheduled_node(uid)
                    cancelled_venue_event_nodes_uids.append(uid)
                else:
                    venue_tuning = services.venue_service().get_venue_tuning(drama_node_inst.zone_id)
                    if venue_tuning is not self.get_organization_venue_tuning(type(drama_node_inst)):
                        drama_scheduler.cancel_scheduled_node(uid)
                        cancelled_venue_event_nodes_uids.append(uid)
                    else:
                        drama_scheduler.add_complete_callback(uid, self._reschedule_venue_org_event)
            else:
                drama_scheduler.add_complete_callback(uid, self._reschedule_venue_org_event)
        for cancelled_node_uid in cancelled_venue_event_nodes_uids:
            if cancelled_node_uid in self._organization_venue_events:
                del self._organization_venue_events[cancelled_node_uid]
            self.remove_event_update(cancelled_node_uid)

    def get_organization_venue_tuning(self, drama_node):
        for (venue_tuning, org_venue_data) in self.VENUE_ORG_EVENT_MAPPING.items():
            if drama_node in org_venue_data.org_drama_node_events:
                return venue_tuning

    def event_is_scheduled(self, org_id, drama_node):
        return type(drama_node) in [type(org_event_info.drama_node) for org_event_info in self._event_updates.get(org_id, [])]

    def add_festival_event_update(self, org_id, org_event_info, drama_node_uid, drama_node_name):
        self._organization_festival_events[drama_node_uid] = drama_node_name
        self.add_event_update(org_id, org_event_info)

    def validate_venue_event(self, drama_node):
        venue_tuning = services.venue_service().get_venue_tuning(drama_node.zone_id)
        if venue_tuning is not self.get_organization_venue_tuning(type(drama_node)):
            drama_scheduler = services.drama_scheduler_service()
            if drama_scheduler is None:
                return False
            else:
                self.remove_event_update(drama_node.uid)
                drama_scheduler.complete_node(drama_node.uid)
                alarm_handle = drama_node.schedule_duration_alarm(lambda *_: self._schedule_cancelled_organization_event(drama_node.guid64), cross_zone=True)
                self._schedule_cancelled_venue_event_alarm[drama_node.guid64] = alarm_handle
                return False
        return True

    def add_venue_event_update(self, org_id, org_event_info, drama_node_uid, drama_node_name):
        self._organization_venue_events[drama_node_uid] = drama_node_name
        self.add_event_update(org_id, org_event_info)

    def add_event_update(self, org_id, org_event_info):
        if not self.event_is_scheduled(org_id, org_event_info.drama_node):
            self._event_updates[org_id].append(org_event_info)

    def get_scheduled_org_event_info_from_drama_node_uid(self, drama_node_uid):
        for (org_id, org_event_infos) in self._event_updates.items():
            for org_event_info in org_event_infos:
                if org_event_info.drama_node.uid == drama_node_uid:
                    return (org_id, org_event_info)
        return (None, None)

    def remove_event_update(self, drama_node_uid):
        (org_id, event_info_to_remove) = self.get_scheduled_org_event_info_from_drama_node_uid(drama_node_uid)
        if event_info_to_remove is None:
            return
        if org_id not in self._event_updates:
            return
        org_event_infos = self._event_updates[org_id]
        org_event_infos.remove(event_info_to_remove)
        if not org_event_infos:
            del self._event_updates[org_id]
        else:
            self._event_updates[org_id] = org_event_infos

    def send_event_update_message(self, org_id, event_infos, no_events_string=None):
        send_event_update_op = SendOrganizationEventUpdateOp(org_id, event_infos, no_events_string)
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(send_event_update_op)

    def update_organization_events_panel(self):
        no_events_orgs = {}
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for org_id in OrganizationTracker.ALL_ORGANIZATION_IDS:
            organization = snippet_manager.get(org_id)
            no_events_orgs[org_id] = organization.no_events_are_scheduled_string
        for (org_id, event_infos) in self._event_updates.items():
            self.send_event_update_message(org_id, event_infos)
            if no_events_orgs.get(org_id) is not None:
                del no_events_orgs[org_id]
        for (org_id, no_events_string) in no_events_orgs.items():
            self.send_event_update_message(org_id, [], no_events_string)

    def clear_stored_organization_events(self):
        self._event_updates.clear()

    def get_organization_members(self, org_id):
        org_members = self._organization_members.get(org_id)
        if org_members is not None:
            return org_members
        return []

    def remove_organization_member(self, sim_info, org_id):
        members_list = self._organization_members.get(org_id)
        if members_list is None:
            return
        if sim_info.id in members_list:
            members_list.remove(sim_info.id)

    def add_organization_member(self, sim_info, org_id):
        organization_tracker = sim_info.organization_tracker
        if organization_tracker is None:
            return False
        organization_tracker.join_organization(org_id)
        members_list = self._organization_members.get(org_id)
        if members_list is None:
            self._organization_members[org_id] = [sim_info.id]
        elif sim_info.id not in members_list:
            self._organization_members[org_id].append(sim_info.id)
        return True

    def generate_organization_members(self, org_id, amount=0, blacklist_sims=(), additional_filter_terms=None, minimum=None):
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        filter_service = services.sim_filter_service()
        sim_info_manager = services.sim_info_manager()
        if snippet_manager is None or filter_service is None or sim_info_manager is None:
            return []
        organization_snippet = snippet_manager.get(org_id)
        member_result_ids = self._organization_members.get(org_id)
        if member_result_ids is None:
            member_result_ids = []
        else:
            valid_org_member_ids = []
            invalid_org_member_ids = []
            for org_member_id in member_result_ids:
                if filter_service.does_sim_match_filter(org_member_id, sim_filter=organization_snippet.organization_filter, gsi_source_fn=lambda : str(self) + ': ' + str(organization_snippet)):
                    valid_org_member_ids.append(org_member_id)
                else:
                    invalid_org_member_ids.append(org_member_id)
            if invalid_org_member_ids:
                for invalid_org_member_id in invalid_org_member_ids:
                    invalid_org_member_info = sim_info_manager.get(invalid_org_member_id)
                    if invalid_org_member_info is not None and invalid_org_member_info.is_played_sim:
                        pass
                    else:
                        member_result_ids.remove(invalid_org_member_id)
                        if invalid_org_member_info is None:
                            pass
                        else:
                            organization_tracker = invalid_org_member_info.organization_tracker
                            if organization_tracker is not None:
                                organization_tracker.leave_organization(org_id)
            valid_org_member_ids = []
            for org_member_id in valid_org_member_ids:
                if org_member_id not in blacklist_sims and filter_service.does_sim_match_filter(org_member_id, sim_filter=organization_snippet.organization_filter, additional_filter_terms=additional_filter_terms, gsi_source_fn=lambda : str(self) + ': ' + str(organization_snippet)):
                    valid_org_member_ids.append(org_member_id)
            picked_sims = []
            if amount < len(valid_org_member_ids):
                while valid_org_member_ids and len(picked_sims) < amount:
                    random_choice = valid_org_member_ids.pop(random.randint(0, len(valid_org_member_ids) - 1))
                    picked_sims.append(random_choice)
                return picked_sims
            member_result_ids = valid_org_member_ids
        additional_membership_filter_terms = additional_filter_terms + OrganizationService.ADDITIONAL_FILTER_TERMS_ON_GENERATING_NEW_MEMBERS
        members_needed = minimum - len(member_result_ids) if minimum is not None and len(member_result_ids) <= minimum else amount - len(member_result_ids)
        if members_needed > 0:
            new_members = filter_service.submit_matching_filter(number_of_sims_to_find=members_needed, sim_filter=organization_snippet.organization_filter, callback=None, allow_yielding=False, allow_instanced_sims=True, additional_filter_terms=additional_membership_filter_terms, blacklist_sim_ids=blacklist_sims, gsi_source_fn=lambda : str(self) + ': ' + str(organization_snippet))
            for new_member in new_members:
                sim_info = new_member.sim_info
                if sim_info and self.add_organization_member(sim_info, org_id):
                    member_result_ids.append(sim_info.id)
        return member_result_ids

    def _reschedule_org_event(self, drama_node, **setup_kwargs):
        drama_scheduler = services.drama_scheduler_service()
        if drama_scheduler is None:
            return
        resolver = drama_node._get_resolver()
        next_time = self.verify_valid_time(drama_node)
        uid = drama_scheduler.schedule_node(type(drama_node), resolver, specific_time=next_time, update_org_panel_immediately=True, setup_kwargs=setup_kwargs)
        return uid

    def _reschedule_venue_org_event(self, drama_node, **kwargs):
        if drama_node.uid in self._organization_venue_events:
            del self._organization_venue_events[drama_node.uid]
        setup_kwargs = {}
        if is_scoring_archive_enabled():
            gsi_data = GSIDramaScoringData()
            gsi_data.bucket = 'Venue Organization Event'
            setup_kwargs['gsi_data'] = gsi_data
        setup_kwargs['zone_id'] = drama_node.zone_id
        new_uid = self._reschedule_org_event(drama_node, **setup_kwargs)
        if new_uid is None:
            logger.error('Organization event ({}) was not rescheduled', drama_node)
        self._organization_venue_events[new_uid] = str(type(drama_node))

    def _reschedule_festival_org_event(self, drama_node, from_shutdown=False):
        if drama_node.uid in self._organization_festival_events:
            del self._organization_festival_events[drama_node.uid]
        if from_shutdown and isinstance(services.time_service().sim_timeline, FrozenTimeline):
            return
        setup_kwargs = {}
        if is_scoring_archive_enabled():
            gsi_data = GSIDramaScoringData()
            gsi_data.bucket = 'Festival Organization Event'
            setup_kwargs['gsi_data'] = gsi_data
        new_uid = self._reschedule_org_event(drama_node, **setup_kwargs)
        if new_uid is None:
            logger.error('Organization event ({}) was not rescheduled', drama_node)
        self._organization_festival_events[new_uid] = str(type(drama_node))
