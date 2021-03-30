from _weakrefset import WeakSetfrom builtins import propertyfrom collections import defaultdictfrom objects.game_object_properties import GameObjectPropertyfrom objects.hovertip import TooltipFieldsCompletefrom protocolbuffers import UI_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import GenericProtocolBufferOpfrom distributor.shared_messages import build_icon_info_msgfrom distributor.system import Distributorfrom objects import componentsfrom objects.components.inventory_enums import InventoryTypefrom objects.components.inventory_type_tuning import InventoryTypeTuningfrom objects.object_enums import ItemLocationfrom sims4.common import Packfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, Tunable, TunableVariant, TunableEnumSetfrom sims4.tuning.tunable_base import ExportModes, EnumBinaryExportTypefrom tag import TunableTagsimport servicesimport sims4.loglogger = sims4.log.Logger('Inventory', default_owner='tingyul')
class InventoryStorage:
    UI_SORT_TYPES = TunableList(description="\n        A list of gameplay-based sort types used in the sim's inventory in the UI.\n        ", tunable=TunableTuple(description='\n            Data that defines this sort for the inventory UI.\n            ', sort_name=TunableLocalizedString(description='\n                The name displayed in the UI for this sort type.\n                '), object_data=TunableVariant(description='\n                The object data that determines the sort order of\n                this sort type.\n                ', states=TunableList(description='\n                    States whose values are used to sort on for this sort type. \n                    ', tunable=TunableReference(description='\n                        A State to sort on.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState')), default='states'), is_ascending=Tunable(description='\n                Whether a higher value from object_data will sort first.\n                If a high value means that the object should sort lower \n                (E.G. brokenness), this should be false.\n                ', tunable_type=bool, default=True), debug_name=Tunable(description='\n                A unique name used to select this inventory sort type through \n                the console command ui.inventory.set_sort_filter when the inventory\n                ui is open.\n                ', tunable_type=str, default='NONE'), export_class_name='InventoryUISortTypeTuple', export_modes=ExportModes.ClientBinary))

    @staticmethod
    def _tuning_loaded_callback(instance_class, tunable_name, source, value):
        InventoryStorage.INVENTORY_FILTER_TAGS = set()
        for filter_category in InventoryStorage.UI_FILTER_TYPES:
            for filter in filter_category.filters:
                InventoryStorage.INVENTORY_FILTER_TAGS.update(filter.tags)
                InventoryStorage.INVENTORY_FILTER_TAGS.update(filter.disqualifying_tags)

    UI_FILTER_TYPES = TunableList(description="\n        A list of filter categories containing filter types used to filter the sim's\n        inventory in the UI. The inventory can also be sorted by filter type; \n        filters lower on this list will sort lower when sorted by filter type.\n        ", tunable=TunableTuple(description='\n            A category of filters in the UI. Contains a name and a list of filters.\n            ', filters=TunableList(description='\n                The filters used in this category. \n                ', tunable=TunableTuple(description='\n                    Data that defines a filter type in the inventory UI.\n                    ', tags=TunableTags(description='\n                        Tags that should be considered part of this filter.\n                        ', binary_type=EnumBinaryExportType.EnumUint32), disqualifying_tags=TunableTags(description='\n                        If an object has any of these tags, it will fail this\n                        filter even if it would otherwise pass.\n                        ', binary_type=EnumBinaryExportType.EnumUint32), filter_name=TunableLocalizedString(description='\n                        The name displayed in the UI for this filter type.            \n                        '), debug_name=Tunable(description='\n                        A unique name used to select this inventory filter type through \n                        the console command ui.inventory.set_sort_filter when the inventory\n                        ui is open.\n                        ', tunable_type=str, default='NONE'), required_packs=TunableEnumSet(description='\n                        If any packs are tuned here, at least one of them must\n                        be present for this filter to appear in the UI.\n                        ', enum_type=Pack, enum_default=Pack.BASE_GAME), export_class_name='InventoryUIFilterTypeTuple')), category_name=TunableLocalizedString(description='\n                The name displayed in the UI for this filter category.\n                '), export_class_name='InventoryUIFilterCategoryTuple', export_modes=ExportModes.ClientBinary), callback=_tuning_loaded_callback)

    def __init__(self, inventory_type, item_location, max_size=None, allow_compaction=True, allow_ui=True, hidden_storage=False):
        self._objects = {}
        self._owners = WeakSet()
        self._inventory_type = inventory_type
        self._item_location = item_location
        self._max_size = max_size
        self._allow_compaction = allow_compaction
        self._allow_ui = allow_ui
        self._hidden_storage = hidden_storage
        self._stacks_with_options_counter = None

    def __len__(self):
        return len(self._objects)

    def __iter__(self):
        yield from iter(self._objects.values())

    def __contains__(self, obj_id):
        return obj_id in self._objects

    def __getitem__(self, obj_id):
        if obj_id in self._objects:
            return self._objects[obj_id]

    def __repr__(self):
        return 'InventoryStorage<{},{}>'.format(self._inventory_type, self._get_inventory_id())

    def register(self, owner):
        self._owners.add(owner)

    def unregister(self, owner):
        self._owners.discard(owner)

    def has_owners(self):
        if self._owners:
            return True
        return False

    def get_owners(self):
        return tuple(self._owners)

    @property
    def allow_ui(self):
        return self._allow_ui

    @allow_ui.setter
    def allow_ui(self, value):
        self._allow_ui = value

    def discard_object_id(self, obj_id):
        if obj_id in self._objects:
            del self._objects[obj_id]

    def discard_all_objects(self):
        for obj in self._objects.values():
            self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_REMOVE, obj)
            obj.inventoryitem_component.set_inventory_type(None, None)
        self._objects.clear()

    def can_insert(self, obj):
        if not obj.can_go_in_inventory_type(self._inventory_type):
            return False
        elif self._max_size is not None and sum(inventory_obj.stack_count() for inventory_obj in self) >= self._max_size:
            return False
        return True

    def insert(self, obj, inventory_object=None, compact=True):
        if not self.can_insert(obj):
            return False
        try:
            obj.on_before_added_to_inventory()
        except:
            logger.exception('Exception invoking on_before_added_to_inventory. obj: {}', obj)
        self._insert(obj, inventory_object)
        try:
            obj.on_added_to_inventory()
        except:
            logger.exception('Exception invoking on_added_to_inventory. obj: {}', obj)
        compacted_obj_id = None
        compacted_count = None
        if compact:
            (compacted_obj_id, compacted_count) = self._try_compact(obj)
        if compacted_obj_id is None:
            for owner in self._owners:
                try:
                    owner.on_object_inserted(obj)
                except:
                    logger.exception('Exception invoking on_object_inserted. obj: {}, owner: {}', obj, owner)
            self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_ADD, obj)
            sent_stack_update = False
            if obj.inventoryitem_component.has_stack_option:
                if self._stacks_with_options_counter is None:
                    self._stacks_with_options_counter = defaultdict(int)
                stack_id = obj.inventoryitem_component.get_stack_id()
                stack_objects = self._stacks_with_options_counter[stack_id]
                if stack_objects == 0:
                    self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_SET_STACK_OPTION, obj)
                    sent_stack_update = True
                self._stacks_with_options_counter[stack_id] += 1
            if not sent_stack_update:
                obj_owner = obj.inventoryitem_component.get_inventory().owner
                if obj_owner.is_sim and obj_owner.sim_info.favorites_tracker is not None and obj_owner.sim_info.favorites_tracker.is_favorite_stack(obj):
                    self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_SET_STACK_OPTION, obj)
        else:
            for owner in self._owners:
                try:
                    owner.on_object_id_changed(obj, compacted_obj_id, compacted_count)
                except:
                    logger.exception('Exception invoking on_object_id_changed. obj: {}, owner: {}', obj, owner)
            self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_UPDATE, obj, obj_id=compacted_obj_id)
        return True

    def update_object_stack_by_id(self, obj_id, new_stack_id):
        if obj_id not in self._objects:
            return
        obj = self._objects[obj_id]
        self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_REMOVE, obj)
        obj.set_stack_id(new_stack_id)
        self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_ADD, obj)

    def remove(self, obj, count=1, move_to_object_manager=True):
        if obj.id not in self._objects:
            return False
        old_stack_count = obj.stack_count()
        split_obj = self._try_split(obj, count)
        try:
            obj.on_before_removed_from_inventory()
        except:
            logger.exception('Exception invoking on_before_removed_from_inventory. obj: {}', obj)
        self._remove(obj, move_to_object_manager=move_to_object_manager)
        try:
            obj.on_removed_from_inventory()
        except:
            logger.exception('Exception invoking on_removed_from_inventory. obj: {}', obj)
        if split_obj is None:
            for owner in self._owners:
                try:
                    owner.on_object_removed(obj)
                except:
                    logger.exception('Exception invoking on_object_removed. obj: {}, owner: {}', obj, owner)
            self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_REMOVE, obj)
            if obj.inventoryitem_component.has_stack_option and self._stacks_with_options_counter is not None:
                stack_id = obj.inventoryitem_component.get_stack_id()
                self._stacks_with_options_counter[stack_id] -= 1
                if stack_id in self._stacks_with_options_counter and self._stacks_with_options_counter[stack_id] <= 0:
                    if self._stacks_with_options_counter[stack_id] < 0:
                        logger.error('Counter went negative for stack_id {} with scheme {}', stack_id, obj.inventoryitem_component.get_stack_scheme(), owner='jdimailig')
                    del self._stacks_with_options_counter[stack_id]
        else:
            for owner in self._owners:
                try:
                    owner.on_object_id_changed(split_obj, obj.id, old_stack_count)
                except:
                    logger.exception('Exception invoking on_object_id_changed. obj: {}, owner: {}', obj, owner)
            self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_UPDATE, split_obj, obj_id=obj.id)
        return True

    def try_split_from_stack(self, obj, count):
        old_stack_count = obj.stack_count()
        split_obj = self._try_split(obj, count)
        if split_obj is not None:
            for owner in self._owners:
                try:
                    owner.on_object_id_changed(split_obj, obj.id, old_stack_count)
                except:
                    logger.exception('Exception invoking on_object_id_changed. obj: {}, owner: {}', obj, owner)
            self._distribute_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_UPDATE, split_obj, obj_id=obj.id)
        return split_obj

    def _insert(self, obj, inventory_object):
        self._objects[obj.id] = obj
        obj.inventoryitem_component.set_inventory_type(self._inventory_type, inventory_object)
        obj.item_location = self._item_location
        if self._inventory_type == InventoryType.SIM:
            obj.inventoryitem_component.is_hidden = self._hidden_storage
        object_manager = services.object_manager()
        if obj.id in object_manager:
            object_manager.move_to_inventory(obj, services.current_zone().inventory_manager)
            obj.set_parent(None)

    def _remove(self, obj, move_to_object_manager=False):
        if move_to_object_manager:
            services.current_zone().inventory_manager.move_to_world(obj, services.object_manager())
        obj.item_location = ItemLocation.ON_LOT
        obj.inventoryitem_component.set_inventory_type(None, None, from_removal=not move_to_object_manager)
        del self._objects[obj.id]

    def _get_compact_data(self, obj):
        try:
            obj.inventoryitem_component.save_for_stack_compaction = True
            return obj.get_attribute_save_data()
        finally:
            obj.inventoryitem_component.save_for_stack_compaction = False
            obj.post_tooltip_save_data_stored()

    def _try_compact(self, obj):
        if not self._allow_compaction:
            return (None, None)
        if len(self._objects) < 2:
            return (None, None)
        if not obj.inventoryitem_component.allow_compaction:
            return (None, None)
        if obj.has_component(components.types.OBJECT_CLAIM_COMPONENT) and obj.object_claim_component.requires_claiming:
            return (None, None)
        similar = None
        def_id = obj.definition.id
        data = self._get_compact_data(obj)
        stack_id = obj.inventoryitem_component.get_stack_id()
        for other in self._objects.values():
            if def_id != other.definition.id:
                pass
            elif other is obj:
                pass
            elif stack_id != other.inventoryitem_component.get_stack_id():
                pass
            elif not any(interaction.should_reset_based_on_pipeline_progress for interaction in other.interaction_refs):
                other_data = self._get_compact_data(other)
                if data == other_data:
                    similar = other
                    break
        if similar is None:
            return (None, None)
        similar_id = similar.id
        similar_count = similar.stack_count()
        self._remove(similar)
        similar.destroy(source=self, cause='InventoryStorage compaction')
        obj.update_stack_count(similar_count)
        return (similar_id, similar_count)

    def _try_split(self, obj, count):
        if count >= obj.stack_count():
            return
        clone = obj.inventoryitem_component.get_clone_for_stack_split()
        self._insert(clone, obj.inventoryitem_component.last_inventory_owner)
        clone.update_stack_count(-count)
        obj.set_stack_count(count)
        clone.on_added_to_inventory()
        return clone

    def _get_inventory_id(self):
        if InventoryTypeTuning.is_shared_between_objects(self._inventory_type):
            return int(self._inventory_type)
        if self._owners:
            return next(iter(self._owners)).owner.id
        logger.error("Non-shared storage that's missing an owner: InventoryStorage<{},{}>", self._inventory_type, 0)
        return 0

    def _get_inventory_ui_type(self):
        if InventoryTypeTuning.is_shared_between_objects(self._inventory_type):
            return UI_pb2.InventoryItemUpdate.TYPE_SHARED
        return UI_pb2.InventoryItemUpdate.TYPE_OBJECT

    def _get_inventory_update_message(self, update_type, obj, obj_id=None, allow_while_zone_not_running=False):
        if not self._allow_ui:
            return
        if services.current_zone().is_zone_running or not allow_while_zone_not_running:
            return
        if services.current_zone().is_zone_shutting_down:
            return
        msg = UI_pb2.InventoryItemUpdate()
        msg.type = update_type
        msg.inventory_id = self._get_inventory_id()
        msg.inventory_type = self._get_inventory_ui_type()
        msg.stack_id = obj.inventoryitem_component.get_stack_id()
        if obj_id is None:
            msg.object_id = obj.id
        else:
            msg.object_id = obj_id
        if update_type == UI_pb2.InventoryItemUpdate.TYPE_ADD:
            add_data = UI_pb2.InventoryItemData()
            add_data.definition_id = obj.definition.id
            msg.add_data = add_data
        if update_type == UI_pb2.InventoryItemUpdate.TYPE_ADD or update_type == UI_pb2.InventoryItemUpdate.TYPE_UPDATE:
            dynamic_data = UI_pb2.DynamicInventoryItemData()
            dynamic_data.value = obj.current_value
            dynamic_data.dynamic_tags.extend(obj.get_dynamic_tags() & self.INVENTORY_FILTER_TAGS)
            dynamic_data.count = obj.stack_count()
            dynamic_data.new_object_id = obj.id
            dynamic_data.is_new = obj.new_in_inventory
            dynamic_data.sort_order = obj.get_stack_sort_order()
            icon_info = obj.get_icon_info_data()
            build_icon_info_msg(icon_info, None, dynamic_data.icon_info)
            recipe_name = obj.get_tooltip_field(TooltipFieldsComplete.recipe_name) or obj.get_craftable_property(GameObjectProperty.RECIPE_NAME)
            if recipe_name is not None:
                dynamic_data.recipe_name = recipe_name
            if obj.custom_name is not None:
                dynamic_data.custom_name = obj.custom_name
            visual_state = obj.get_inventory_visual_state()
            if visual_state is not None:
                dynamic_data.visual_state = visual_state
            if InventoryStorage.UI_SORT_TYPES:
                sort_type = 0
                for sort_type_data in InventoryStorage.UI_SORT_TYPES:
                    value = None
                    try:
                        abs_value = None
                        state_component = obj.state_component
                        if state_component is None:
                            continue
                        for state in sort_type_data.object_data:
                            if state_component.has_state(state):
                                test_value = float(state_component.get_state(state).value)
                                abs_test_value = abs(test_value)
                                if value is None:
                                    value = test_value
                                elif abs_value < abs_test_value:
                                    value = test_value
                                    abs_value = abs_test_value
                    except TypeError:
                        pass
                    if value is not None:
                        sort_data_item = UI_pb2.InventoryItemSortData()
                        sort_data_item.type = sort_type
                        sort_data_item.value = value
                        dynamic_data.sort_data.append(sort_data_item)
                    sort_type += 1
            if update_type == UI_pb2.InventoryItemUpdate.TYPE_ADD:
                msg.add_data.dynamic_data = dynamic_data
            else:
                msg.update_data = dynamic_data
        if update_type == UI_pb2.InventoryItemUpdate.TYPE_SET_STACK_OPTION:
            dynamic_data = UI_pb2.DynamicInventoryItemData()
            if obj.inventoryitem_component.has_stack_option:
                obj.inventoryitem_component.populate_stack_icon_info_data(dynamic_data.icon_info)
            obj_owner = obj.inventoryitem_component.get_inventory().owner
            if obj_owner.is_sim:
                favorites_tracker = obj_owner.sim_info.favorites_tracker
                if favorites_tracker.is_favorite_stack(obj):
                    dynamic_data.is_favorite = True
            msg.update_data = dynamic_data
        return msg

    def _distribute_inventory_update_message(self, update_type, obj, obj_id=None):
        msg = self._get_inventory_update_message(update_type, obj, obj_id=obj_id)
        if msg is not None:
            op = GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, msg)
            Distributor.instance().add_op_with_no_owner(op)

    def distribute_inventory_update_message(self, obj):
        if obj.id not in self._objects:
            return False
        msg = self._get_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_UPDATE, obj)
        if msg is not None:
            op = GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, msg)
            Distributor.instance().add_op_with_no_owner(op)

    def distribute_inventory_stack_update_message(self, obj):
        if obj.id not in self._objects:
            return
        msg = self._get_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_SET_STACK_OPTION, obj)
        if msg is not None:
            op = GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, msg)
            Distributor.instance().add_op_with_no_owner(op)

    def distribute_owned_inventory_update_message(self, obj, owner):
        if obj.id not in self._objects:
            return False
        msg = self._get_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_UPDATE, obj)
        if msg is not None:
            op = GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, msg)
            Distributor.instance().add_op(owner, op)

    def get_item_update_ops_gen(self):
        stack_options_set = set()
        for obj in self._objects.values():
            message = self._get_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_ADD, obj, allow_while_zone_not_running=True)
            if message is None:
                pass
            else:
                yield (obj, GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, message))
                if not obj.inventoryitem_component.has_stack_option:
                    obj_owner = obj.inventoryitem_component.get_inventory().owner
                    if obj_owner.is_sim:
                        if obj_owner.sim_info.favorites_tracker is None:
                            pass
                        else:
                            stack_id = obj.inventoryitem_component.get_stack_id()
                            if stack_id in stack_options_set:
                                pass
                            else:
                                option_msg = self._get_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_SET_STACK_OPTION, obj, allow_while_zone_not_running=True)
                                if option_msg is not None:
                                    stack_options_set.add(stack_id)
                                    yield (obj, GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, option_msg))
                else:
                    stack_id = obj.inventoryitem_component.get_stack_id()
                    if stack_id in stack_options_set:
                        pass
                    else:
                        option_msg = self._get_inventory_update_message(UI_pb2.InventoryItemUpdate.TYPE_SET_STACK_OPTION, obj, allow_while_zone_not_running=True)
                        if option_msg is not None:
                            stack_options_set.add(stack_id)
                            yield (obj, GenericProtocolBufferOp(Operation.INVENTORY_ITEM_UPDATE, option_msg))

    def open_ui_panel(self, obj):
        if not self._allow_ui:
            return False
        msg = UI_pb2.OpenInventory()
        msg.object_id = obj.id
        msg.inventory_id = self._get_inventory_id()
        msg.inventory_type = self._get_inventory_ui_type()
        op = GenericProtocolBufferOp(Operation.OPEN_INVENTORY, msg)
        Distributor.instance().add_op_with_no_owner(op)
        return True
