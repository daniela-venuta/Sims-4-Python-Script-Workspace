import build_buyimport servicesimport sims4.logfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.test_events import TestEventfrom objects.components.inventory_enums import StackSchemefrom protocolbuffers import SimObjectAttributes_pb2from sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.utils import classpropertylogger = sims4.log.Logger('FavoritesTracker', default_owner='trevor')OBJ_ID = 0DEF_ID = 1KEY_ID = 0CUSTOM_KEY_ID = 1STACK_TYPE_ID = 2
class FavoritesTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._owner = sim_info
        self._favorites = None
        self._favorite_stacks = []

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.BACKGROUND

    @property
    def favorites(self):
        return self._favorites

    @property
    def favorite_stacks(self):
        return self._favorite_stacks

    def has_favorite(self, tag):
        return self._favorites and tag in self._favorites

    def set_favorite(self, tag, obj_id=None, obj_def_id=None):
        if self._favorites is None:
            self._favorites = {}
            services.get_event_manager().register_single_event(self, TestEvent.ObjectDestroyed)
        if tag in self._favorites:
            logger.debug('Old favorite with object ID {} object definition ID {} is being overwritten by object ID {} object definition ID {} for tag {}.', self._favorites[tag][OBJ_ID], self._favorites[tag][DEF_ID], obj_id, obj_def_id, tag)
        if obj_def_id is None:
            obj = services.object_manager().get(obj_id)
            if obj is not None:
                obj_def_id = obj.definition.id
        self._favorites[tag] = (obj_id, obj_def_id)
        return True

    def unset_favorite(self, tag, obj_id=None, obj_def_id=None):
        (fav_obj_id, fav_def_id) = self.get_favorite(tag)
        del self._favorites[tag]
        if (fav_obj_id is not None and fav_obj_id == obj_id or fav_def_id is not None) and fav_def_id == obj_def_id and not self._favorites:
            self.clean_up()

    def clear_favorite_type(self, tag):
        del self._favorites[tag]
        if tag in self._favorites and not self._favorites:
            self.clean_up()

    def _unset_favorite_object(self, obj_id=None, obj_def_id=None):
        if self._favorites is None:
            return
        favorite_types = []
        for (favorite_type, fav) in self._favorites.items():
            if not fav[OBJ_ID] == obj_id:
                if fav[DEF_ID] is not None and fav[DEF_ID] == obj_def_id:
                    favorite_types.append(favorite_type)
            favorite_types.append(favorite_type)
        for favorite_type in favorite_types:
            self.unset_favorite(favorite_type, obj_id, obj_def_id)

    def get_favorite(self, tag):
        if self._favorites is None:
            return (None, None)
        return self._favorites.get(tag, (None, None))

    def get_favorite_object_id(self, tag):
        (fav_obj_id, _) = self.get_favorite(tag)
        return fav_obj_id

    def is_favorite(self, tag, obj, instance_must_match=True):
        (fav_obj_id, fav_def_id) = self.get_favorite(tag)
        if fav_obj_id is not None and fav_obj_id == obj.id:
            return True
        elif instance_must_match or fav_def_id is not None and fav_def_id == obj.definition.id:
            return True
        return False

    def get_favorite_definition_id(self, tag):
        (_, fav_def_id) = self.get_favorite(tag)
        return fav_def_id

    def set_favorite_stack(self, obj):
        key = self._get_stack_key(obj)
        if key is None or key in self._favorite_stacks:
            return
        self._favorite_stacks.append(key)

    def unset_favorite_stack(self, obj):
        if len(self._favorite_stacks) == 0:
            return
        key = self._get_stack_key(obj)
        if key is None or key not in self._favorite_stacks:
            return
        self._favorite_stacks.remove(key)

    def is_favorite_stack(self, obj):
        key = self._get_stack_key(obj)
        return key is not None and key in self._favorite_stacks

    def _get_stack_key(self, obj):
        inv_component = obj.inventoryitem_component
        if inv_component is None:
            return
        stack_scheme = inv_component.get_stack_scheme()
        custom_key = None
        if inv_component.stack_scheme_object_state is not None:
            state_value = obj.state_component.get_state(inv_component.stack_scheme_object_state)
            if obj.state_component.state_value_active(state_value):
                custom_key = state_value.guid64
        if stack_scheme == StackScheme.NONE:
            key = obj.id
        elif stack_scheme == StackScheme.VARIANT_GROUP:
            key = build_buy.get_variant_group_id(obj.definition.id)
        elif stack_scheme == StackScheme.DEFINITION:
            key = obj.definition.id
        else:
            key = stack_scheme
        return [key, custom_key, stack_scheme]

    def clean_up(self):
        if self._favorites is not None:
            self._favorites = None
            services.get_event_manager().unregister_single_event(self, TestEvent.ObjectDestroyed)
        if len(self._favorite_stacks) > 0:
            self._favorite_stacks = []

    def handle_event(self, _, event, resolver):
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj_id = resolver.get_resolved_arg('obj').id
            self._unset_favorite_object(destroyed_obj_id)

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.clean_up()
        elif old_lod < self._tracker_lod_threshold:
            msg = services.get_persistence_service().get_sim_proto_buff(self._owner.id)
            if msg is not None:
                self.load(msg.attributes.favorites_tracker)

    def save(self):
        data = SimObjectAttributes_pb2.PersistableFavoritesTracker()
        if self._favorites is not None:
            for (tag, (object_id, object_def_id)) in self._favorites.items():
                with ProtocolBufferRollback(data.favorites) as entry:
                    entry.favorite_type = tag
                    if object_id is not None:
                        entry.favorite_id = object_id
                    if object_def_id is not None:
                        entry.favorite_def_id = object_def_id
        if not len(self._favorite_stacks):
            return data
        sim = self._owner.get_sim_instance()
        if sim is None:
            logger.warn('Failed to get sim {}. Unable to save stack favorites.', sim)
            return data
        inventory = sim.inventory_component
        inventory_manager = services.inventory_manager()
        zone = services.current_zone()
        for key_data in self._favorite_stacks:
            key = key_data[KEY_ID]
            custom_key = key_data[CUSTOM_KEY_ID]
            stack_type = key_data[STACK_TYPE_ID]
            if stack_type == StackScheme.NONE:
                obj = zone.find_object(key)
                if obj is None:
                    pass
                elif obj.get_sim_owner_id() != sim.id and obj.get_household_owner_id() != sim.household_id:
                    pass
                else:
                    stack_msg = data.stack_favorites.add()
                    if key is not None:
                        stack_msg.key = key
                    if custom_key is not None:
                        stack_msg.custom_key = custom_key
                    stack_msg.stack_scheme = stack_type
            elif inventory is None:
                logger.warn('Sim {} has no inventory component. Unable to save stack data: {}.', sim, key_data)
            else:
                stack_id = inventory_manager.get_stack_id_from_key(key, custom_key, stack_type)
                if len(inventory.get_stack_items(stack_id)) == 0:
                    pass
                else:
                    stack_msg = data.stack_favorites.add()
                    if key is not None:
                        stack_msg.key = key
                    if custom_key is not None:
                        stack_msg.custom_key = custom_key
                    stack_msg.stack_scheme = stack_type
            stack_msg = data.stack_favorites.add()
            if key is not None:
                stack_msg.key = key
            if custom_key is not None:
                stack_msg.custom_key = custom_key
            stack_msg.stack_scheme = stack_type
        return data

    def load(self, data):
        self.clean_up()
        for favorite in data.favorites:
            favorite_id = favorite.favorite_id
            if favorite_id is 0:
                favorite_id = None
            favorite_def_id = favorite.favorite_def_id
            if favorite_def_id is 0:
                favorite_def_id = None
            self.set_favorite(favorite.favorite_type, favorite_id, favorite_def_id)
        for stack_favorite in data.stack_favorites:
            key = stack_favorite.key
            if key is 0:
                key = None
            custom_key = stack_favorite.custom_key
            if custom_key is 0:
                custom_key = None
            stack_scheme = stack_favorite.stack_scheme
            self._favorite_stacks.append([key, custom_key, stack_scheme])
