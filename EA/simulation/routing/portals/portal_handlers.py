from objects.components.types import PORTAL_COMPONENT
    cheat.add_token_param('object_id')
    cheat.add_token_param('object_id')
    cheat.add_token_param('object_id')
    cheat.add_token_param('there_id')
    cheat.add_token_param('back_id')
    cheat.add_token_param('object_id')
    cheat.add_token_param('object_id')
    sub_schema.add_field('object_id', label='Object Id', hidden=True)
    sub_schema.add_field('portal_tuning', label='Portal Tuning', width=3)
    sub_schema.add_field('required_flags', label='Required Flags', width=3)
    sub_schema.add_field('discouragement_flags', label='Discouragement Flags', width=3)
    sub_schema.add_field('cost_override', label='Cost Override', width=1.5)
    sub_schema.add_field('cost_override_map', label='Cost Override Map', width=3)
    sub_schema.add_field('there_id', label='There Id', width=1)
    sub_schema.add_field('there_entry_location', label='There Entry Location', width=2)
    sub_schema.add_field('there_exit_location', label='There Exit Location', width=2)
    sub_schema.add_field('there_cost', label='There Cost', width=1.5)
    sub_schema.add_field('back_id', label='Back Id', width=1)
    sub_schema.add_field('back_entry_location', label='Back Entry Location', width=2)
    sub_schema.add_field('back_exit_location', label='Back Exit Location', width=2)
    sub_schema.add_field('back_cost', label='Back Cost', width=1.5)
    sub_schema.add_field('field', label='Field')
    sub_schema.add_field('data', label='Data')
@GsiHandler('portals', portal_schema)
def generate_portal_data(zone_id:int=None):
    portals = []
    obj_manager = services.object_manager(zone_id=zone_id)
    for portal in obj_manager.portal_cache_gen():
        portal_data_items = portal.get_gsi_portal_items_list('field', 'data')
        instance_data = []
        num_sims_cost_override = 0
        portal_component = portal.get_component(PORTAL_COMPONENT)
        for portal_instance in portal_component.get_portal_instances():

            def format_portal_location(portal_location):
                if portal_location is None:
                    return ''
                return '{}, Routing Surface: {}'.format(str(portal_location.transform), str(portal_location.routing_surface))

            there_entry_location = format_portal_location(portal_instance.there_entry)
            there_exit_location = format_portal_location(portal_instance.there_exit)
            back_entry_location = format_portal_location(portal_instance.back_entry)
            back_exit_location = format_portal_location(portal_instance.back_exit)
            required_flags = portal_instance.portal_template.required_flags or 0
            required_flags |= portal_instance.portal_template.traversal_type.get_additional_required_portal_flags(portal_instance.there_entry, portal_instance.there_exit)
            required_flags |= portal_instance.portal_template.traversal_type.get_additional_required_portal_flags(portal_instance.back_entry, portal_instance.back_exit)
            instance_data.append({'object_id': str(portal.id), 'portal_tuning': str(portal_instance.portal_template.traversal_type), 'required_flags': PortalFlags(required_flags).name if required_flags else 'None', 'discouragement_flags': str(portal_instance.portal_template.discouragement_flags), 'cost_override': str(portal_instance._cost_override), 'cost_override_map': str(dict(portal_instance._cost_override_map.items()) if portal_instance._cost_override_map is not None else {}), 'there_id': portal_instance.there, 'there_entry_location': there_entry_location, 'there_exit_location': there_exit_location, 'there_cost': portal_instance.there_cost, 'back_id': portal_instance.back, 'back_entry_location': back_entry_location, 'back_exit_location': back_exit_location, 'back_cost': portal_instance.back_cost})
            if portal_instance._cost_override_map is not None:
                num_sims_cost_override += len(portal_instance._cost_override_map)
        portal_pos = portal.position
        portals.append({'object_id': str(portal.id), 'portal_provider': portal.__class__.__name__, 'definition': portal.definition.name, 'loc_x': round(portal_pos.x, 3), 'loc_y': round(portal_pos.y, 3), 'loc_z': round(portal_pos.z, 3), 'on_active_lot': portal.is_on_active_lot(), 'num_sims_cost_override': num_sims_cost_override, 'Data': portal_data_items, 'Instances': instance_data})
    return portals
