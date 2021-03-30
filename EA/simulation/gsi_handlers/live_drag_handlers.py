from gsi_handlers import gsi_utils
    _live_drag_index = UniqueIdGenerator()
def archive_live_drag(op_or_command, message_type, location_from, location_to, live_drag_object=None, live_drag_object_id:int=0, live_drag_target=None):
    definition_id = 0
    stack_id = 0
    stack_count = 1
    can_live_drag = False
    current_inventory = None
    if live_drag_object is None:
        live_drag_object = services.current_zone().find_object(live_drag_object_id)
    if live_drag_object is not None:
        definition_id = live_drag_object.definition.id
        live_drag_component = live_drag_object.live_drag_component
        can_live_drag = live_drag_component.can_live_drag
        inventoryitem_component = live_drag_object.inventoryitem_component
        stack_count = live_drag_object.stack_count()
        if inventoryitem_component is not None:
            stack_id = inventoryitem_component.get_stack_id()
            current_inventory = inventoryitem_component.get_inventory()
    entry = {'live_drag_id': _live_drag_index(), 'live_drag_operation': str(op_or_command), 'live_drag_message_type': message_type, 'live_drag_from_where': str(location_from), 'live_drag_to_where': str(location_to), 'live_drag_object': gsi_utils.format_object_name(live_drag_object), 'live_drag_object_id': live_drag_object_id, 'live_drag_definition_id': definition_id, 'live_drag_target': gsi_utils.format_object_name(live_drag_target), 'live_drag_status': str(can_live_drag), 'live_drag_object_inventory': str(current_inventory), 'live_drag_stack_id': stack_id, 'live_drag_stack_count': stack_count}
    live_drag_archiver.archive(data=entry)
