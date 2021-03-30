from _collections import defaultdictfrom _weakrefset import WeakSetfrom collections import Counterfrom contextlib import contextmanagerimport collectionsfrom event_testing.resolver import GlobalResolverfrom event_testing.tests import TunableTestSetfrom objects.components.inventory_availability_tuning import get_available_rulesfrom objects.gallery_tuning import ContentSourcefrom protocolbuffers import FileSerialization_pb2 as file_serialization, GameplaySaveData_pb2 as gameplay_serialization, SimObjectAttributes_pb2 as protocolsfrom crafting.crafting_cache import CraftingObjectCachefrom distributor.rollback import ProtocolBufferRollbackfrom indexed_manager import IndexedManager, CallbackTypesfrom objects import componentsfrom objects.attractors.attractor_manager_mixin import AttractorManagerMixinfrom objects.components.inventory_enums import StackSchemefrom objects.components.types import PORTAL_COMPONENT, INVENTORY_ITEM_COMPONENTfrom objects.object_enums import ItemLocationfrom objects.water_terrain_objects import WaterTerrainObjectCachefrom sims4.callback_utils import CallableListfrom sims4.math import MAX_INT32from sims4.tuning.tunable import Tunable, TunableTuple, TunableSet, TunableEnumWithFilter, TunableMapping, TunableRangefrom sims4.utils import classpropertyfrom singletons import DEFAULT, EMPTY_SETfrom tag import TunableTags, Tagfrom world.region import Regionimport build_buyimport distributor.systemimport objects.persistence_groupsimport persistence_error_typesimport servicesimport sims4.logimport taglogger = sims4.log.Logger('Object Manager')
class DistributableObjectManager(IndexedManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zone_id = services.current_zone_id()

    def setup(self, **kwargs):
        super().setup()
        services.client_object_managers().add(self)

    def stop(self):
        super().stop()
        services.client_object_managers().remove(self)

    def call_on_add(self, obj):
        if self.auto_manage_distributor:
            distributor.system.Distributor.instance().add_object(obj)
        super().call_on_add(obj)

    @property
    def auto_manage_distributor(self):
        return True

    def remove_from_client(self, obj, **kwargs):
        if obj.id not in self:
            logger.error('Object was not found in object manager: {}', obj)
            return
        if not obj.visible_to_client:
            return
        if self.supports_parenting:
            for child_object in tuple(obj.get_all_children_gen()):
                child_object.remove_from_client(**kwargs)
        if self.auto_manage_distributor:
            distributor.system.Distributor.instance().remove_object(obj, **kwargs)

    def remove(self, obj, **kwargs):
        if self.is_removing_object(obj):
            return
        if obj.id not in self:
            logger.warn('Object was not found in object manager: {}', obj)
            return
        if self.supports_parenting:
            obj.remove_reference_from_parent()
            for child_object in tuple(obj.get_all_children_gen()):
                child_object.destroy(source=obj, cause='Removing parent from object manager.')
        zone = services.current_zone()
        if obj.visible_to_client and zone is not None and not zone.is_zone_shutting_down:
            self.remove_from_client(obj, **kwargs)
        super().remove(obj)

    @classproperty
    def supports_parenting(self):
        return False

    def on_location_changed(self, obj):
        pass

class GameObjectManagerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._claimed_items = set()

    def valid_objects(self):
        return [obj for obj in self._objects.values() if not obj._hidden_flags]

    def get_valid_objects_gen(self):
        for obj in self._objects.values():
            if not obj._hidden_flags:
                yield obj

    def get_objects_of_def_id_gen(self, *definition_ids):
        for obj in self._objects.values():
            if any(obj.definition.id == d_id for d_id in definition_ids):
                yield obj

    def get_objects_of_type_gen(self, *definitions):
        for obj in self._objects.values():
            if any(obj.definition is d for d in definitions):
                yield obj

    def get_objects_with_tag_gen(self, tag):
        for obj in self._objects.values():
            if obj.has_tag(tag):
                yield obj

    def get_objects_with_tags_gen(self, *tags):
        for obj in self._objects.values():
            if obj.has_any_tag(tags):
                yield obj

    def get_objects_with_filter_gen(self, object_filter):
        for obj in self._objects.values():
            if object_filter.matches(obj):
                yield obj

    def add_tags_and_object_to_cache(self, tags, obj):
        pass

    def remove_tags_on_object_from_cache(self, tags, obj):
        pass

    def add_active_whim_set(self, whim_set):
        pass

    def remove_active_whim_set(self, whim_set):
        pass

    def set_claimed_item(self, obj_id):
        self._claimed_items.add(obj_id)

    def set_unclaimed_item(self, obj_id):
        self._claimed_items.discard(obj_id)

    def has_item_been_claimed(self, obj_id):
        return obj_id in self._claimed_items

    def has_object_failed_claiming(self, obj):
        if self.has_item_been_claimed(obj.id) or obj.has_component(components.types.OBJECT_CLAIM_COMPONENT) and obj.object_claim_component.requires_claiming:
            return True
        return False

    def has_inventory_item_failed_claiming(self, obj_id, inventory_data):
        for persistable_data in inventory_data:
            if persistable_data.type == persistable_data.InventoryItemComponent:
                data = persistable_data.Extensions[protocols.PersistableInventoryItemComponent.persistable_data]
                if data.requires_claiming and not self.has_item_been_claimed(obj_id):
                    return True
            if persistable_data.type == persistable_data.ObjectClaimComponent:
                data = persistable_data.Extensions[protocols.PersistableObjectClaimComponent.persistable_data]
                if data.requires_claiming and not self.has_item_been_claimed(obj_id):
                    return True
        return False

    def destroy_unclaimed_objects(self):
        objs_to_remove = []
        for obj_id in self:
            obj = self.get(obj_id)
            if obj is not None and obj.has_component(components.types.OBJECT_CLAIM_COMPONENT) and obj.object_claim_component.has_not_been_reclaimed():
                objs_to_remove.append(obj)
        for obj in objs_to_remove:
            self.remove(obj)

class PartyManager(IndexedManager):
    pass

class SocialGroupManager(DistributableObjectManager):
    pass

class InventoryManager(DistributableObjectManager, GameObjectManagerMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._variant_group_stack_id_map = {}
        self._definition_stack_id_map = {}
        self._dynamic_stack_scheme_id_map = {}
        self._last_stack_id = 0
        self._availability_rules = EMPTY_SET

    def on_client_connect(self, client):
        all_objects = list(self._objects.values())
        for game_object in all_objects:
            game_object.on_client_connect(client)
        self._availability_rules = get_available_rules()

    def on_all_households_and_sim_infos_loaded(self, _):
        for game_object in self.objects:
            inventory_item_component = game_object.get_component(INVENTORY_ITEM_COMPONENT)
            if inventory_item_component is not None:
                inventory_item_component.refresh_decay_modifiers()

    def move_to_world(self, obj, object_manager):
        logger.assert_raise(isinstance(object_manager, ObjectManager), 'Trying to move object to a non-object manager: {}', object_manager, owner='tingyul')
        logger.assert_raise(obj.id, 'Attempting to move an object that was never added or has already been removed', owner='tingyul')
        logger.assert_raise(self._objects.get(obj.id) is obj, 'Attempting to move an object that is not in this manager', owner='tingyul')
        del self._objects[obj.id]
        obj.manager = object_manager
        object_manager._objects[obj.id] = obj
        object_manager.add_object_to_object_tags_cache(obj)
        object_manager.add_object_to_posture_providing_cache(obj)

    def remove(self, obj, *args, **kwargs):
        inventory = obj.get_inventory()
        if inventory is not None:
            inventory.try_remove_object_by_id(obj.id, count=obj.stack_count(), on_manager_remove=True)
        super().remove(obj, *args, **kwargs)

    def get_stack_id(self, obj, stack_scheme, custom_key=None):
        if stack_scheme == StackScheme.NONE:
            return self._get_new_stack_id()
        if stack_scheme == StackScheme.VARIANT_GROUP:
            variant_group_id = build_buy.get_variant_group_id(obj.definition.id)
            return self.get_stack_id_from_key(variant_group_id, custom_key, stack_scheme)
        if stack_scheme == StackScheme.DEFINITION:
            definition_id = obj.definition.id
            return self.get_stack_id_from_key(definition_id, custom_key, stack_scheme)
        return self.get_stack_id_from_key(stack_scheme, custom_key, stack_scheme)

    def get_stack_id_from_key(self, key, custom_key, stack_scheme):
        if stack_scheme == StackScheme.NONE:
            logger.error('Attempting to get stack id from key {} with StackScheme.NONE', key)
            return
        key = key if custom_key is None else (key, custom_key)
        if stack_scheme == StackScheme.VARIANT_GROUP:
            if key not in self._variant_group_stack_id_map:
                self._variant_group_stack_id_map[key] = self._get_new_stack_id()
            return self._variant_group_stack_id_map[key]
        if stack_scheme == StackScheme.DEFINITION:
            if key not in self._definition_stack_id_map:
                self._definition_stack_id_map[key] = self._get_new_stack_id()
            return self._definition_stack_id_map[key]
        if key not in self._dynamic_stack_scheme_id_map:
            self._dynamic_stack_scheme_id_map[key] = self._get_new_stack_id()
        return self._dynamic_stack_scheme_id_map[key]

    def _get_new_stack_id(self):
        self._last_stack_id += 1
        if self._last_stack_id > sims4.math.MAX_UINT64:
            logger.warn('stack id reached MAX_UINT64. Rolling back to 0, which might cause stacking errors..', owner='tingyul')
            self._last_stack_id = 0
        return self._last_stack_id

    def is_inventory_item_available(self, definition):
        if not self._availability_rules:
            return True
        elif all(is_available(definition) for is_available in self._availability_rules):
            return True
        return False

    @classproperty
    def supports_parenting(self):
        return True
BED_PREFIX_FILTER = ('buycat', 'buycatee', 'buycatss', 'func')
class ObjectManager(DistributableObjectManager, GameObjectManagerMixin, AttractorManagerMixin):
    FIREMETER_DISPOSABLE_OBJECT_CAP = Tunable(int, 5, description='Number of disposable objects a lot can have at any given moment.')
    BED_TAGS = TunableTuple(description='\n        Tags to check on an object to determine what type of bed an object is.\n        ', beds=TunableSet(description='\n            Tags that consider an object as a bed other than double beds.\n            ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=BED_PREFIX_FILTER)), double_beds=TunableSet(description='\n            Tags that consider an object as a double bed\n            ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=BED_PREFIX_FILTER)), kid_beds=TunableSet(description='\n            Tags that consider an object as a kid bed\n            ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=BED_PREFIX_FILTER)), other_sleeping_spots=TunableSet(description='\n            Tags that considered sleeping spots.\n            ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=BED_PREFIX_FILTER)))
    HOUSEHOLD_INVENTORY_OBJECT_TAGS = TunableTags(description='\n        List of tags to apply to every household inventory proxy object.\n        ')
    INVALID_UNPARENTED_OBJECT_TAGS = TunableTags(description='\n        Objects with these tags should not exist without a parent. An obvious\n        case is for transient objects. They should only exist as a carried object,\n        thus parented to a sim, when loading into a save game.\n        ')
    GLOBAL_SPAWN_FIREMETER = TunableTuple(description="\n        This firemeter is to control the amount of objects can be spawned (usually spawned by system).\n        For example we can tag SP18 Specters as Func_SystemSpawned_Haunted so we can limit the number\n        using Object Spawn Firemeter Test when it's spawned by system.\n        ", overall_quota=TunableRange(description='\n            This is the total number of all system spawned objects we need to enforce in our game at any point.\n            ', tunable_type=int, default=0, minimum=0), firemeter_entries=TunableMapping(key_name='tag', key_type=TunableEnumWithFilter(description='\n                This is the tag of system spawned objects, we should make sure they have the prefix "Func_SystemSpawned".\n                ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=('Func_SystemSpawned',)), value_name='settings', value_type=TunableTuple(tag_weight=TunableRange(description='\n                    The weight assigned to this tag, say if we have 3 objects having weights 2,3,4, and the first two \n                    passed tests, and we have overall_quota 50, then the quota of first two tags will be 20 and 30\n                    ', tunable_type=int, default=0, minimum=0), tests_to_opt_in=TunableTestSet(description='\n                    These tests need to pass for the tag to be opted in for weight calculation. If tests fail, quota \n                    for this tag will be 0.\n                    '))))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._crafting_cache = CraftingObjectCache()
        self._sim_spawn_conditions = collections.defaultdict(set)
        self._water_terrain_object_cache = WaterTerrainObjectCache()
        self._client_connect_callbacks = CallableList()
        self._portal_cache = WeakSet()
        self._portal_added_callbacks = CallableList()
        self._portal_removed_callbacks = CallableList()
        self._front_door_candidates_changed_callback = CallableList()
        self._all_bed_tags = self.BED_TAGS.beds | self.BED_TAGS.double_beds | self.BED_TAGS.kid_beds | self.BED_TAGS.other_sleeping_spots
        self._tag_to_object_list = defaultdict(set)
        self._whim_set_cache = Counter()
        self._posture_providing_object_cache = None
        self._objects_to_ignore_portal_validation_cache = []

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_OBJECT_MANAGER

    @property
    def crafting_cache(self):
        return self._crafting_cache

    @property
    def water_terrain_object_cache(self):
        return self._water_terrain_object_cache

    def portal_cache_gen(self):
        yield from self._portal_cache

    def on_client_connect(self, client):
        all_objects = list(self._objects.values())
        for game_object in all_objects:
            game_object.on_client_connect(client)

    def move_to_inventory(self, obj, inventory_manager):
        logger.assert_raise(isinstance(inventory_manager, InventoryManager), 'Trying to move object to a non-inventory manager: {}', inventory_manager, owner='tingyul')
        logger.assert_raise(obj.id, 'Attempting to move an object that was never added or has already been removed', owner='tingyul')
        logger.assert_raise(self._objects.get(obj.id) is obj, 'Attempting to move an object {} that is not in this manager or not the same object {} in manager', obj, self._objects.get(obj.id), owner='tingyul')
        del self._objects[obj.id]
        obj.manager = inventory_manager
        inventory_manager._objects[obj.id] = obj
        self.remove_object_from_object_tags_cache(obj)
        self.remove_object_from_posture_providing_cache(obj)

    def add(self, obj, *args, **kwargs):
        super().add(obj, *args, **kwargs)
        self.add_object_to_object_tags_cache(obj)
        self.add_object_to_posture_providing_cache(obj)

    def remove(self, obj, *args, **kwargs):
        super().remove(obj, *args, **kwargs)
        current_zone = services.current_zone()
        if not current_zone.is_zone_shutting_down:
            self.remove_object_from_object_tags_cache(obj)
            self.remove_object_from_posture_providing_cache(obj)

    def add_object_to_object_tags_cache(self, obj):
        self.add_tags_and_object_to_cache(obj.get_tags(), obj)

    def add_tags_and_object_to_cache(self, tags, obj):
        if obj.id not in self:
            logger.error("Trying to add object to tag cache when the object isn't in the manager: {}", obj, owner='tingyul')
            return
        for tag in tags:
            object_list = self._tag_to_object_list[tag]
            object_list.add(obj)

    def remove_tags_on_object_from_cache(self, tags, obj):
        if obj.id not in self:
            logger.error("Trying to remove cached tags from an object that isn't in the manager: {}", obj, owner='rrodgers')
            return
        for tag in tags:
            object_list = self._tag_to_object_list[tag]
            object_list.remove(obj)

    def remove_object_from_object_tags_cache(self, obj):
        for tag in obj.get_tags():
            if tag not in self._tag_to_object_list:
                pass
            else:
                object_list = self._tag_to_object_list[tag]
                if obj not in object_list:
                    pass
                else:
                    object_list.remove(obj)
                    if not object_list:
                        del self._tag_to_object_list[tag]

    def _should_save_object_on_lot(self, obj):
        parent = obj.parent
        if parent is not None and parent.is_sim:
            inventory = parent.inventory_component
            if inventory.should_save_parented_item_to_inventory(obj):
                return False
            else:
                vehicle_component = obj.vehicle_component
                if vehicle_component is not None:
                    driver = vehicle_component.driver
                    if driver is not None and driver.is_sim:
                        inventory = driver.inventory_component
                        if inventory.should_save_parented_item_to_inventory(obj):
                            return False
        else:
            vehicle_component = obj.vehicle_component
            if vehicle_component is not None:
                driver = vehicle_component.driver
                if driver is not None and driver.is_sim:
                    inventory = driver.inventory_component
                    if inventory.should_save_parented_item_to_inventory(obj):
                        return False
        return True

    def add_object_to_posture_providing_cache(self, obj):
        if not obj.provided_mobile_posture_affordances:
            return
        if self._posture_providing_object_cache is None:
            self._posture_providing_object_cache = set()
        self._posture_providing_object_cache.add(obj)
        posture_graph_service = services.posture_graph_service()
        if not posture_graph_service.has_built_for_zone_spin_up:
            posture_graph_service.on_mobile_posture_object_added_during_zone_spinup(obj)

    def remove_object_from_posture_providing_cache(self, obj):
        if not obj.provided_mobile_posture_affordances:
            return
        self._posture_providing_object_cache.remove(obj)
        if not self._posture_providing_object_cache:
            self._posture_providing_object_cache = None

    def get_posture_providing_objects(self):
        return self._posture_providing_object_cache or ()

    def rebuild_objects_to_ignore_portal_validation_cache(self):
        self._objects_to_ignore_portal_validation_cache.clear()
        for obj in self._objects.values():
            if not obj.inventoryitem_component is not None:
                if obj.live_drag_component is not None:
                    self._objects_to_ignore_portal_validation_cache.append(obj.id)
            self._objects_to_ignore_portal_validation_cache.append(obj.id)

    def clear_objects_to_ignore_portal_validation_cache(self):
        self._objects_to_ignore_portal_validation_cache.clear()

    def get_objects_to_ignore_portal_validation_cache(self):
        return self._objects_to_ignore_portal_validation_cache

    def clear_caches_on_teardown(self):
        self._tag_to_object_list.clear()
        self._water_terrain_object_cache.clear()
        if self._posture_providing_object_cache is not None:
            self._posture_providing_object_cache.clear()
        self.clear_objects_to_ignore_portal_validation_cache()
        build_buy.unregister_build_buy_exit_callback(self._water_terrain_object_cache.refresh)

    def pre_save(self):
        all_objects = list(self._objects.values())
        lot = services.current_zone().lot
        for (_, inventory) in lot.get_all_object_inventories_gen(shared_only=True):
            for game_object in inventory:
                all_objects.append(game_object)
        for game_object in all_objects:
            game_object.update_all_commodities()

    @staticmethod
    def save_game_object(game_object, object_list, open_street_objects):
        save_result = None
        if game_object.persistence_group == objects.persistence_groups.PersistenceGroups.OBJECT:
            save_result = game_object.save_object(object_list.objects, ItemLocation.ON_LOT, 0)
        else:
            if game_object.item_location == ItemLocation.ON_LOT or game_object.item_location == ItemLocation.INVALID_LOCATION:
                item_location = ItemLocation.FROM_OPEN_STREET
            else:
                item_location = game_object.item_location
            save_result = game_object.save_object(open_street_objects.objects, item_location, 0)
        return save_result

    def save(self, object_list=None, zone_data=None, open_street_data=None, **kwargs):
        if object_list is None:
            return
        open_street_objects = file_serialization.ObjectList()
        total_beds = 0
        double_bed_exist = False
        kid_bed_exist = False
        alternative_sleeping_spots = 0
        university_roommate_beds = 0
        current_zone = services.current_zone()
        neighborhood_protocol_buffer = services.get_persistence_service().get_neighborhood_proto_buff(current_zone.neighborhood_id)
        region_tuning = Region.REGION_DESCRIPTION_TUNING_MAP.get(neighborhood_protocol_buffer.region_id)
        store_region_travel_group_placed_objects = region_tuning is not None and region_tuning.store_travel_group_placed_objects
        venue_instance = services.get_current_venue()
        store_zone_travel_group_placed_objects = venue_instance is not None and venue_instance.store_travel_group_placed_objects
        if store_region_travel_group_placed_objects or store_zone_travel_group_placed_objects:
            objects_to_save_for_clean_up = []
        roommate_bed_tags = set()
        roommate_service = services.get_roommate_service()
        if roommate_service is not None:
            roommate_bed_tags = roommate_service.BED_TAGS
        for game_object in self._objects.values():
            if self._should_save_object_on_lot(game_object):
                save_result = ObjectManager.save_game_object(game_object, object_list, open_street_objects)
                if not save_result:
                    pass
                elif zone_data is None:
                    pass
                else:
                    if save_result.owner_id != 0 and game_object.get_lost_and_found_registration_info() is None and (store_region_travel_group_placed_objects or store_zone_travel_group_placed_objects and save_result.loc_type == ItemLocation.ON_LOT):
                        placement_flags = build_buy.get_object_placement_flags(game_object.definition.id)
                        if build_buy.PlacementFlags.NON_INVENTORYABLE not in placement_flags:
                            objects_to_save_for_clean_up.append(save_result)
                    if not game_object.definition.has_build_buy_tag(*self._all_bed_tags):
                        pass
                    else:
                        if game_object.definition.has_build_buy_tag(*self.BED_TAGS.double_beds):
                            double_bed_exist = True
                            total_beds += 1
                        elif game_object.definition.has_build_buy_tag(*self.BED_TAGS.kid_beds):
                            total_beds += 1
                            kid_bed_exist = True
                        elif game_object.definition.has_build_buy_tag(*self.BED_TAGS.other_sleeping_spots):
                            alternative_sleeping_spots += 1
                        elif game_object.definition.has_build_buy_tag(*self.BED_TAGS.beds):
                            total_beds += 1
                        if len(roommate_bed_tags) > 0 and game_object.definition.has_build_buy_tag(*roommate_bed_tags):
                            university_roommate_beds += 1
        if open_street_data is not None:
            open_street_data.objects = open_street_objects
        if zone_data is not None:
            bed_info_data = gameplay_serialization.ZoneBedInfoData()
            bed_info_data.num_beds = total_beds
            bed_info_data.double_bed_exist = double_bed_exist
            bed_info_data.kid_bed_exist = kid_bed_exist
            bed_info_data.alternative_sleeping_spots = alternative_sleeping_spots
            if roommate_service is not None:
                household_and_roommate_cap = roommate_service.HOUSEHOLD_AND_ROOMMATE_CAP
                bed_info_data.university_roommate_beds = min(household_and_roommate_cap, university_roommate_beds)
            zone_data.gameplay_zone_data.bed_info_data = bed_info_data
            if store_region_travel_group_placed_objects or store_zone_travel_group_placed_objects:
                save_game_protocol_buffer = services.get_persistence_service().get_save_game_data_proto()
                self._clear_clean_up_data_for_zone(current_zone, save_game_protocol_buffer)
                self._save_clean_up_destination_data(current_zone, objects_to_save_for_clean_up, save_game_protocol_buffer)
        lot = services.current_zone().lot
        for (inventory_type, inventory) in lot.get_all_object_inventories_gen(shared_only=True):
            for game_object in inventory:
                game_object.save_object(object_list.objects, ItemLocation.OBJECT_INVENTORY, inventory_type)

    def _clear_clean_up_data_for_zone(self, current_zone, save_game_protocol_buffer):
        current_zone_id = current_zone.id
        current_open_street_id = current_zone.open_street_id
        destination_clean_up_data = save_game_protocol_buffer.destination_clean_up_data
        for clean_up_save_data in destination_clean_up_data:
            indexes_to_clean_up = []
            for (index, old_object_clean_up_data) in enumerate(clean_up_save_data.object_clean_up_data_list):
                if not old_object_clean_up_data.zone_id == current_zone_id:
                    if old_object_clean_up_data.world_id == current_open_street_id:
                        indexes_to_clean_up.append(index)
                indexes_to_clean_up.append(index)
            if len(indexes_to_clean_up) == len(clean_up_save_data.object_clean_up_data_list):
                clean_up_save_data.ClearField('object_clean_up_data_list')
            else:
                for index in reversed(indexes_to_clean_up):
                    del clean_up_save_data.object_clean_up_data_list[index]

    def _save_clean_up_destination_data(self, current_zone, objects_to_save_for_clean_up, save_game_protocol_buffer):
        household_manager = services.household_manager()
        travel_group_manager = services.travel_group_manager()
        clean_up_save_data = None
        for object_data in sorted(objects_to_save_for_clean_up, key=lambda x: x.owner_id):
            owner_id = object_data.owner_id
            if clean_up_save_data is None or clean_up_save_data.household_id != owner_id:
                household = household_manager.get(owner_id)
                travel_group = None
                if household is not None:
                    travel_group = household.get_travel_group()
                for clean_up_save_data in save_game_protocol_buffer.destination_clean_up_data:
                    if clean_up_save_data.household_id != owner_id:
                        pass
                    else:
                        if travel_group.id == clean_up_save_data.travel_group_id:
                            break
                        if travel_group is not None and clean_up_save_data.travel_group_id in travel_group_manager:
                            pass
                        else:
                            break
                with ProtocolBufferRollback(save_game_protocol_buffer.destination_clean_up_data) as clean_up_save_data:
                    clean_up_save_data.household_id = owner_id
                    clean_up_save_data.travel_group_id = travel_group.id if travel_group is not None else 0
            with ProtocolBufferRollback(clean_up_save_data.object_clean_up_data_list) as object_clean_up_data:
                if object_data.loc_type == ItemLocation.ON_LOT:
                    object_clean_up_data.zone_id = current_zone.id
                else:
                    object_clean_up_data.world_id = current_zone.open_street_id
                object_clean_up_data.object_data = object_data

    def add_sim_spawn_condition(self, sim_id, callback):
        for sim in services.sim_info_manager().instanced_sims_gen():
            if sim.id == sim_id:
                logger.error('Sim {} is already in the world, cannot add the spawn condition', sim)
                return
        self._sim_spawn_conditions[sim_id].add(callback)

    def remove_sim_spawn_condition(self, sim_id, callback):
        if callback not in self._sim_spawn_conditions.get(sim_id, ()):
            logger.error('Trying to remove sim spawn condition with invalid id-callback pair ({}-{}).', sim_id, callback)
            return
        self._sim_spawn_conditions[sim_id].remove(callback)

    def trigger_sim_spawn_condition(self, sim_id):
        if sim_id in self._sim_spawn_conditions:
            for callback in self._sim_spawn_conditions[sim_id]:
                callback()
            del self._sim_spawn_conditions[sim_id]

    def add_portal_lock(self, sim, callback):
        self.register_portal_added_callback(callback)
        for portal in self.portal_cache_gen():
            portal.lock_sim(sim)

    def register_portal_added_callback(self, callback):
        if callback not in self._portal_added_callbacks:
            self._portal_added_callbacks.append(callback)

    def unregister_portal_added_callback(self, callback):
        if callback in self._portal_added_callbacks:
            self._portal_added_callbacks.remove(callback)

    def register_portal_removed_callback(self, callback):
        if callback not in self._portal_removed_callbacks:
            self._portal_removed_callbacks.append(callback)

    def unregister_portal_removed_callback(self, callback):
        if callback in self._portal_removed_callbacks:
            self._portal_removed_callbacks.remove(callback)

    def _is_valid_portal_object(self, portal):
        portal_component = portal.get_component(PORTAL_COMPONENT)
        if portal_component is None:
            return False
        return portal.has_portals()

    def add_portal_to_cache(self, portal):
        if portal not in self._portal_cache and self._is_valid_portal_object(portal):
            self._portal_cache.add(portal)
            self._portal_added_callbacks(portal)

    def remove_portal_from_cache(self, portal):
        if portal in self._portal_cache:
            self._portal_cache.remove(portal)
            self._portal_removed_callbacks(portal)

    def register_front_door_candidates_changed_callback(self, callback):
        if callback not in self._front_door_candidates_changed_callback:
            self._front_door_candidates_changed_callback.append(callback)

    def unregister_front_door_candidates_changed_callback(self, callback):
        if callback in self._front_door_candidates_changed_callback:
            self._front_door_candidates_changed_callback.remove(callback)

    def on_front_door_candidates_changed(self):
        self._front_door_candidates_changed_callback()

    def cleanup_build_buy_transient_objects(self):
        household_inventory_proxy_objects = self.get_objects_matching_tags(self.HOUSEHOLD_INVENTORY_OBJECT_TAGS)
        for obj in household_inventory_proxy_objects:
            self.remove(obj)

    def get_objects_matching_tags(self, tags:set, match_any=False):
        matching_objects = None
        for tag in tags:
            objs = self._tag_to_object_list[tag] if tag in self._tag_to_object_list else set()
            if matching_objects is None:
                matching_objects = set(objs)
            elif match_any:
                matching_objects |= objs
            else:
                matching_objects &= objs
                if not matching_objects:
                    break
        if matching_objects:
            return frozenset(matching_objects)
        return EMPTY_SET

    def get_num_objects_matching_tags(self, tags:set, match_any=False):
        matching_objects = self.get_objects_matching_tags(tags, match_any)
        return len(matching_objects)

    @contextmanager
    def batch_commodity_flags_update(self):
        default_fn = self.clear_commodity_flags_for_objs_with_affordance
        try:
            affordances = set()
            self.clear_commodity_flags_for_objs_with_affordance = affordances.update
            yield None
        finally:
            self.clear_commodity_flags_for_objs_with_affordance = default_fn
            self.clear_commodity_flags_for_objs_with_affordance(affordances)

    def clear_commodity_flags_for_objs_with_affordance(self, affordances):
        for obj in self.valid_objects():
            if not obj.has_updated_commodity_flags():
                pass
            elif any(affordance in affordances for affordance in obj.super_affordances()):
                obj.clear_commodity_flags()

    def get_all_objects_with_component_gen(self, component_definition):
        if component_definition is None:
            return
        for obj in self.valid_objects():
            if obj.has_component(component_definition):
                yield obj

    def get_objects_with_tag_gen(self, tag):
        yield from self.get_objects_matching_tags((tag,))

    def get_objects_with_tags_gen(self, *tags):
        yield from self.get_objects_matching_tags(tags, match_any=True)

    def on_location_changed(self, obj):
        self._registered_callbacks[CallbackTypes.ON_OBJECT_LOCATION_CHANGED](obj)

    def process_invalid_unparented_objects(self):
        invalid_objects = self.get_objects_matching_tags(self.INVALID_UNPARENTED_OBJECT_TAGS, match_any=True)
        for invalid_object in invalid_objects:
            if invalid_object.parent is None:
                logger.error('Invalid unparented object {} existed in game. Cleaning up.', invalid_object)
                invalid_object.destroy(source=invalid_object, cause='Invalid unparented object found on zone spin up.')

    @classproperty
    def supports_parenting(self):
        return True

    def add_active_whim_set(self, whim_set):
        self._whim_set_cache[whim_set] += 1

    def remove_active_whim_set(self, whim_set):
        self._whim_set_cache[whim_set] -= 1
        if self._whim_set_cache[whim_set] <= 0:
            del self._whim_set_cache[whim_set]

    @property
    def active_whim_sets(self):
        return set(self._whim_set_cache.keys())

    def remaining_quota_from_global_spawn_firemeter(self, tag_to_test):
        resolver = GlobalResolver()
        current_firemeter = self.GLOBAL_SPAWN_FIREMETER.firemeter_entries.get(tag_to_test)
        if current_firemeter is None:
            logger.error('Tag tested is not an entry in GLOBAL_SPAWN_FIREMETER tuning: {}', tag_to_test, owner='yozhang')
            return 0
        all_weights = 0
        current_firemeter_passed = False
        for (firemeter_tag, firemeter) in self.GLOBAL_SPAWN_FIREMETER.firemeter_entries.items():
            if firemeter.tests_to_opt_in.run_tests(resolver):
                all_weights += firemeter.tag_weight
                if firemeter_tag == tag_to_test:
                    current_firemeter_passed = True
        if not current_firemeter_passed:
            return 0
        tag_quota = current_firemeter.tag_weight*self.GLOBAL_SPAWN_FIREMETER.overall_quota//all_weights
        num_matching = self.get_num_objects_matching_tags((tag_to_test,))
        return max(tag_quota - num_matching, 0)
