from collections import defaultdictfrom event_testing.resolver import SingleSimResolverfrom protocolbuffers import Consts_pb2from build_buy import HouseholdInventoryFlagsfrom objects.object_manager import DistributableObjectManagerfrom sims4.utils import classpropertyfrom travel_group.travel_group_telemetry import write_travel_group_telemetry, TELEMETRY_HOOK_TRAVEL_GROUP_START, TELEMETRY_HOOK_TRAVEL_GROUP_ENDfrom world import regionfrom world.region import Regionfrom world.street import get_vacation_zone_idfrom travel_group.travel_group import TravelGroupimport build_buyimport objects.systemimport persistence_error_typesimport servicesimport sims4.logimport sims4.resourcesimport sims4.telemetrylogger = sims4.log.Logger('TravelGroupManager')
class TravelGroupManager(DistributableObjectManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rented_zones = defaultdict(set)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_TRAVEL_GROUP_MANAGER

    def is_current_zone_rented(self):
        return services.current_zone_id() in self._rented_zones.keys()

    def is_zone_rented(self, zone_id):
        return zone_id in self._rented_zones.keys()

    def is_zone_rentable(self, zone_id, venue_tuning):
        if venue_tuning.travel_group_limit is None:
            return True
        if zone_id not in self._rented_zones.keys():
            return True
        player_travel_group_count = sum(1 for group in self._rented_zones[zone_id] if group.played)
        return player_travel_group_count < venue_tuning.travel_group_limit

    def get_travel_group_by_sim_info(self, sim_info):
        return self.get(sim_info.travel_group_id)

    def get_travel_group_by_household(self, household):
        for sim_info in household.sim_info_gen():
            travel_group = self.get(sim_info.travel_group_id)
            if travel_group is not None:
                return travel_group

    def get_travel_group_by_sim_id(self, sim_id):
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is not None or not sim_info.travel_group_id:
            return
        return self.get_travel_group_by_sim_info(sim_info)

    def get_travel_group_ids_in_region(self, region_id=None):
        region_id = region_id or services.current_region().guid64
        return (group.id for group in self.values() if region.get_region_instance_from_zone_id(group.zone_id).guid64 == region_id)

    def get_travel_group_by_zone_id(self, zone_id):
        for travel_group in self.values():
            if travel_group.zone_id == zone_id:
                return travel_group

    def create_travel_group_and_rent_zone(self, sim_infos, zone_id, played, create_timestamp, end_timestamp=None, cost=0):
        travel_group_sim_infos = []
        for sim_info in sim_infos:
            if sim_info.household.any_member_in_travel_group():
                logger.error('Attempted to add a second travel group to household of {} . This is not allowed.', sim_info)
            else:
                travel_group_sim_infos.append(sim_info)
        vacation_zone_id = get_vacation_zone_id(zone_id)
        setup_alarms = not played
        travel_group = TravelGroup(played=played, create_timestamp=create_timestamp, end_timestamp=end_timestamp, setup_alarms=setup_alarms)
        result = self.rent_zone(vacation_zone_id, travel_group)
        if not (result and travel_group_sim_infos):
            return False
        self.add(travel_group)
        for sim_info in travel_group_sim_infos:
            travel_group.add_sim_info(sim_info)
        if played:
            leader_sim_info = services.active_sim_info()
            if leader_sim_info not in travel_group:
                leader_sim_info = next(iter(sim_info for sim_info in travel_group_sim_infos if sim_info.is_selectable))
            if cost:
                services.active_household().funds.try_remove(cost, reason=Consts_pb2.FUNDS_MONEY_VACATION, sim=services.get_active_sim())
            write_travel_group_telemetry(travel_group, TELEMETRY_HOOK_TRAVEL_GROUP_START, sim_info=leader_sim_info)
        return True

    def destroy_travel_group_and_release_zone(self, travel_group, last_sim_info=None, return_objects=False):
        if travel_group.played:
            if last_sim_info is None:
                leader_sim_info = services.active_sim_info()
                if leader_sim_info not in travel_group:
                    leader_sim_info = next(iter(travel_group), None)
            else:
                leader_sim_info = last_sim_info
            write_travel_group_telemetry(travel_group, TELEMETRY_HOOK_TRAVEL_GROUP_END, sim_info=leader_sim_info)
        for sim_info in tuple(travel_group):
            travel_group.remove_sim_info(sim_info, destroy_on_empty=False)
        self.release_zone(travel_group)
        services.get_persistence_service().del_travel_group_proto_buff(travel_group.id)
        services.travel_group_manager().remove(travel_group)
        if return_objects:
            self.return_objects_left_in_destination_world()
        return True

    def rent_zone(self, zone_id, travel_group):
        venue_tuning_id = build_buy.get_current_venue(zone_id)
        if venue_tuning_id is None:
            return False
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_tuning = venue_manager.get(venue_tuning_id)
        if venue_tuning is None:
            return False
        if not self.is_zone_rentable(zone_id, venue_tuning):
            return False
        for existing_travel_group in tuple(self._rented_zones[zone_id]):
            if existing_travel_group.played:
                pass
            else:
                self.destroy_travel_group_and_release_zone(existing_travel_group, return_objects=False)
        travel_group.rent_zone(zone_id)
        self._rented_zones[zone_id].add(travel_group)
        return True

    def release_zone(self, travel_group):
        groups_in_zone = self._rented_zones[travel_group.zone_id]
        groups_in_zone.discard(travel_group)

    def return_objects_left_in_destination_world(self):
        zone = services.current_zone()
        neighborhood_protocol_buffer = services.get_persistence_service().get_neighborhood_proto_buff(zone.neighborhood_id)
        region_tuning = Region.REGION_DESCRIPTION_TUNING_MAP.get(neighborhood_protocol_buffer.region_id)
        if region_tuning is not None and region_tuning.store_travel_group_placed_objects:
            return
        venue_instance = services.get_current_venue()
        if venue_instance is not None and venue_instance.store_travel_group_placed_objects:
            return
        household_manager = services.household_manager()
        save_game_protocol_buffer = services.get_persistence_service().get_save_game_data_proto()
        for clean_up_save_data in save_game_protocol_buffer.destination_clean_up_data:
            if clean_up_save_data.travel_group_id in self:
                pass
            elif clean_up_save_data.household_id not in household_manager:
                clean_up_save_data.household_id = 0
            else:
                object_manager = services.object_manager()
                for obj_clean_up_data in clean_up_save_data.object_clean_up_data_list:
                    obj_data = obj_clean_up_data.object_data

                    def post_create_old_object(created_obj):
                        created_obj.load_object(obj_data)
                        build_buy.move_object_to_household_inventory(created_obj, failure_flags=HouseholdInventoryFlags.DESTROY_OBJECT)

                    definition_id = build_buy.get_vetted_object_defn_guid(obj_data.object_id, obj_data.guid or obj_data.type)
                    if definition_id is None:
                        pass
                    else:
                        existing_object = object_manager.get(obj_data.object_id)
                        if existing_object and existing_object.definition.id == definition_id:
                            object_manager.remove(existing_object)
                            logger.error('Trying to return an object that is already present. Removing the existing object and not loading the object again.{}: {}', existing_object.definition, existing_object.id)
                        else:
                            objects.system.create_object(definition_id, obj_id=obj_data.object_id, loc_type=obj_data.loc_type, post_add=post_create_old_object)
                clean_up_save_data.household_id = 0

    def on_all_households_and_sim_infos_loaded(self, client):
        self.load_travel_groups()

    def clean_objects_left_in_destination_world(self):
        zone = services.current_zone()
        current_zone_id = zone.id
        open_street_id = zone.open_street_id
        travel_group_manager = services.travel_group_manager()
        clean_up_data_indexes_to_remove = []
        object_manager = services.object_manager()
        save_game_protocol_buffer = services.get_persistence_service().get_save_game_data_proto()
        for (clean_up_index, clean_up_save_data) in enumerate(save_game_protocol_buffer.destination_clean_up_data):
            if clean_up_save_data.travel_group_id in travel_group_manager:
                pass
            elif clean_up_save_data.household_id != 0:
                pass
            else:
                object_indexes_to_delete = []
                for (index, object_clean_up_data) in enumerate(clean_up_save_data.object_clean_up_data_list):
                    if not object_clean_up_data.zone_id == current_zone_id:
                        if object_clean_up_data.world_id == open_street_id:
                            obj = object_manager.get(object_clean_up_data.object_data.object_id)
                            if obj is not None:
                                obj.destroy(source=self, cause='Destination world clean up.')
                            object_indexes_to_delete.append(index)
                    obj = object_manager.get(object_clean_up_data.object_data.object_id)
                    if obj is not None:
                        obj.destroy(source=self, cause='Destination world clean up.')
                    object_indexes_to_delete.append(index)
                if len(object_indexes_to_delete) == len(clean_up_save_data.object_clean_up_data_list):
                    clean_up_save_data.ClearField('object_clean_up_data_list')
                else:
                    for index in reversed(object_indexes_to_delete):
                        del clean_up_save_data.object_clean_up_data_list[index]
                if len(clean_up_save_data.object_clean_up_data_list) == 0:
                    clean_up_data_indexes_to_remove.append(clean_up_index)
        for index in reversed(clean_up_data_indexes_to_remove):
            del save_game_protocol_buffer.destination_clean_up_data[index]

    def load_travel_groups(self):
        delete_group_ids = []
        persistence_service = services.get_persistence_service()
        for travel_group_proto in persistence_service.all_travel_group_proto_gen():
            travel_group_id = travel_group_proto.travel_group_id
            travel_group = self.get(travel_group_id)
            if travel_group is None:
                travel_group = self.load_travel_group(travel_group_proto)
            if travel_group is None:
                delete_group_ids.append(travel_group_id)
        for travel_group_id in delete_group_ids:
            persistence_service.del_travel_group_proto_buff(travel_group_id)
        save_game_proto = persistence_service.get_save_game_data_proto()
        if save_game_proto is not None:
            sim_info_manager = services.sim_info_manager()
            for sim_id in save_game_proto.sims_removed_from_travel_groups:
                sim_info = sim_info_manager.get(sim_id)
                if sim_info is None:
                    pass
                else:
                    resolver = SingleSimResolver(sim_info)
                    for loot in TravelGroup.ON_LEAVE_TRAVEL_GROUP_LOOT:
                        loot.apply_to_resolver(resolver)
            del save_game_proto.sims_removed_from_travel_groups[:]

    def load_travel_group(self, travel_group_proto):
        travel_group = TravelGroup(setup_alarms=True)
        travel_group.load_data(travel_group_proto)
        logger.info('Travel Group loaded. id:{:10} #sim_infos:{:2}', travel_group.id, len(travel_group))
        if not travel_group.travel_group_size:
            return
        self.add(travel_group)
        self._rented_zones[travel_group.zone_id].add(travel_group)
        for sim_info in travel_group.sim_info_gen():
            sim_info.career_tracker.resend_at_work_infos()
        return travel_group

    def save(self, **kwargs):
        for travel_group in self.values():
            self.save_travel_group(travel_group)

    def save_travel_group(self, travel_group):
        persistence_service = services.get_persistence_service()
        travel_group_proto = persistence_service.get_travel_group_proto_buff(travel_group.id)
        if travel_group_proto is None:
            travel_group_proto = persistence_service.add_travel_group_proto_buff()
        travel_group.save_data(travel_group_proto)
