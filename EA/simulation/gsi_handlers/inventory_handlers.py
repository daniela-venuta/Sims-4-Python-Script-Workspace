import itertoolsimport gsi_handlersimport servicesfrom gsi_handlers.gsi_utils import parse_filter_to_listfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemainventory_schema = GsiGridSchema(label='Inventories')inventory_schema.add_field('objId', label='Object Id', width=1, unique_field=True, hidden=True)inventory_schema.add_field('inventoryOwner', label='Inventory Owner', width=3)inventory_schema.add_field('instancedCount', label='Count (Instanced)', width=2)inventory_schema.add_field('shelvedCount', label='Count (Shelved)', width=2)inventory_schema.add_filter('active_household_inventories')inventory_schema.add_filter('npc_sim_inventories')inventory_schema.add_filter('on_lot_object_inventories')inventory_schema.add_filter('off_lot_object_inventories')with inventory_schema.add_view_cheat('objects.focus_camera_on_object', label='Focus On Selected Object') as cheat:
    cheat.add_token_param('objId')with inventory_schema.add_has_many('instanced_contents', GsiGridSchema) as sub_schema:
    sub_schema.add_field('stackId', label='Stack ID')
    sub_schema.add_field('definition', label='Definition', width=3)
    sub_schema.add_field('objectCount', label='Object Count')
    sub_schema.add_field('isHidden', label='Is Hidden')with inventory_schema.add_has_many('shelved_contents', GsiGridSchema) as sub_schema:
    sub_schema.add_field('definition', label='Definition', width=3)
    sub_schema.add_field('objectCount', label='Object Count')
@GsiHandler('inventories', inventory_schema)
def generate_inventories_data(*_, zone_id:int=None, filter=None, **__):
    filter_list = parse_filter_to_list(filter)
    zone = services.get_zone(zone_id)
    all_object_data = []
    active_household = services.active_household()
    def_manager = services.definition_manager()

    def _active_household_sim(obj):
        if active_household is None:
            return False
        return obj.sim_info in active_household

    def _npc_sim(obj):
        if active_household is None:
            return False
        return obj.sim_info not in active_household

    for cur_obj in list(itertools.chain(zone.object_manager.objects, zone.inventory_manager.objects)):
        inventory = cur_obj.inventory_component
        if inventory is None:
            pass
        else:
            on_active_lot = cur_obj.is_on_active_lot() if hasattr(cur_obj, 'is_on_active_lot') else False
            is_sim = cur_obj.is_sim
            if not on_active_lot:
                if 'off_lot_object_inventories' in filter_list and not (is_sim or on_active_lot):
                    obj_entry = {'objId': hex(cur_obj.id), 'inventoryOwner': gsi_handlers.gsi_utils.format_object_name(cur_obj), 'instancedCount': str(len(inventory))}
                    if inventory:
                        instanced_contents = []
                        for item in inventory:
                            item_component = item.inventoryitem_component
                            instanced_contents.append({'stackId': str(item_component.get_stack_id()), 'definition': str(item.definition), 'objectCount': str(item_component.stack_count()), 'isHidden': str(item_component.is_hidden)})
                        obj_entry['instanced_contents'] = instanced_contents
                    if is_sim:
                        obj_entry['shelvedCount'] = str(inventory.get_shelved_object_count())
                        shelved_contents = []
                        for shelved in inventory.get_shelved_object_data():
                            shelved_contents.append({'definition': str(def_manager.get(shelved['guid'])), 'objectCount': str(shelved['objectCount'])})
                        obj_entry['shelved_contents'] = shelved_contents
                    all_object_data.append(obj_entry)
            obj_entry = {'objId': hex(cur_obj.id), 'inventoryOwner': gsi_handlers.gsi_utils.format_object_name(cur_obj), 'instancedCount': str(len(inventory))}
            if (filter_list is None or 'active_household_inventories' in filter_list) and is_sim and (_active_household_sim(cur_obj) or 'npc_sim_inventories' in filter_list) and is_sim and (_npc_sim(cur_obj) or 'on_lot_object_inventories' in filter_list) and (is_sim or inventory):
                instanced_contents = []
                for item in inventory:
                    item_component = item.inventoryitem_component
                    instanced_contents.append({'stackId': str(item_component.get_stack_id()), 'definition': str(item.definition), 'objectCount': str(item_component.stack_count()), 'isHidden': str(item_component.is_hidden)})
                obj_entry['instanced_contents'] = instanced_contents
            if is_sim:
                obj_entry['shelvedCount'] = str(inventory.get_shelved_object_count())
                shelved_contents = []
                for shelved in inventory.get_shelved_object_data():
                    shelved_contents.append({'definition': str(def_manager.get(shelved['guid'])), 'objectCount': str(shelved['objectCount'])})
                obj_entry['shelved_contents'] = shelved_contents
            all_object_data.append(obj_entry)
    return all_object_data
