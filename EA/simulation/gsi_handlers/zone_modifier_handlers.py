from gsi_handlers.gsi_utils import parse_filter_to_listfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom sims4.resources import Typesfrom tag import Tagimport servicesFILTER_SHOW_ACTIVE_ZONE_MODIFIERS = 'only_active'zone_modifier_view_schema = GsiGridSchema(label='Zone Modifiers')zone_modifier_view_schema.add_field('id', label='Id', width=1, unique_field=True)zone_modifier_view_schema.add_field('name', label='Zone Modifier')zone_modifier_view_schema.add_field('assigned_to_zone', label='Assigned to Zone')zone_modifier_view_schema.add_field('event_tests', label='Event Test Count', type=GsiFieldVisualizers.INT, width=1)zone_modifier_view_schema.add_field('enter_loots', label='Enter Loot Count', type=GsiFieldVisualizers.INT, width=1)zone_modifier_view_schema.add_field('exit_loots', label='Exit Loot Count', type=GsiFieldVisualizers.INT, width=1)zone_modifier_view_schema.add_field('scheduled_entries', label='Scheduled Entry Count', type=GsiFieldVisualizers.INT, width=1)zone_modifier_view_schema.add_field('hidden', label='Hidden', width=1)zone_modifier_view_schema.add_filter(FILTER_SHOW_ACTIVE_ZONE_MODIFIERS)with zone_modifier_view_schema.add_view_cheat('zone_modifier.add_zone_modifier', label='Add Modifier') as cheat:
    cheat.add_token_param('id')with zone_modifier_view_schema.add_view_cheat('zone_modifier.remove_zone_modifier', label='Remove Modifier') as cheat:
    cheat.add_token_param('id')with zone_modifier_view_schema.add_has_many('Event Tests', GsiGridSchema) as sub_schema:
    sub_schema.add_field('event_name', label='Event Name')
    sub_schema.add_field('custom_key', label='Custom Key')with zone_modifier_view_schema.add_has_many('Schedule Event Time', GsiGridSchema) as sub_schema:
    sub_schema.add_field('start_time', label='Start Time')
    sub_schema.add_field('end_time', label='End Time')with zone_modifier_view_schema.add_has_many('Architectural Objects Effects', GsiGridSchema) as sub_schema:
    sub_schema.add_field('tag', label='Object Tag')
    sub_schema.add_field('statistic', label='Statistic')
    sub_schema.add_field('count', label='Object Count')
    sub_schema.add_field('multiplier', label='Multiplier')
    sub_schema.add_field('value', label='Added Value (Object Count * Multiplier)')
@GsiHandler('zone_modifier_modifier_view', zone_modifier_view_schema)
def generate_zone_modifiers_view_data(zone_id:int=None, filter=None):
    filter_list = parse_filter_to_list(filter)
    zone_modifier_service = services.get_zone_modifier_service()
    venue_service = services.venue_service()
    zone_modifiers = set(services.get_instance_manager(Types.ZONE_MODIFIER).types.values())
    zone_id = services.current_zone_id()
    current_zones_modifiers = zone_modifier_service.get_zone_modifiers(zone_id, force_cache=True)
    current_venue_zones_modifiers = venue_service.get_additional_zone_modifiers(zone_id)
    registered_event_map = _get_registered_events(zone_modifiers)
    event_times_map = _get_next_event_times(zone_modifiers)
    objects_effects = _get_objects_effects(zone_modifiers)
    zone_modifier_list = list()
    for zone_modifier in zone_modifiers:
        is_active_zone_modifier = zone_modifier in current_zones_modifiers
        if filter_list is not None and FILTER_SHOW_ACTIVE_ZONE_MODIFIERS in filter_list and not is_active_zone_modifier:
            pass
        else:
            zone_modifier_list.append({'id': zone_modifier.guid64, 'name': zone_modifier.__name__, 'assigned_to_zone': is_active_zone_modifier, 'enter_loots': len(zone_modifier.enter_lot_loot), 'exit_loots': len(zone_modifier.exit_lot_loot), 'scheduled_entries': len(zone_modifier.schedule(init_only=True).get_schedule_entries()), 'event_tests': len(registered_event_map[zone_modifier]), 'hidden': zone_modifier in current_venue_zones_modifiers, 'Event Tests': registered_event_map[zone_modifier], 'Schedule Event Time': event_times_map[zone_modifier], 'Architectural Objects Effects': objects_effects[zone_modifier]})
    return zone_modifier_list

def _get_registered_events(zone_modifiers):
    event_mgr = services.get_event_manager()
    events_handlers_map = dict()
    for zone_modifier in zone_modifiers:
        events_handlers_map[zone_modifier] = list()
    for ((event_enum, custom_key), handlers) in event_mgr._test_event_callback_map.items():
        registered_handlers = zone_modifiers & handlers
        if not registered_handlers:
            pass
        else:
            for handler in registered_handlers:
                events_handlers_map[handler].append({'event_name': str(event_enum), 'custom_key': str(custom_key)})
    return events_handlers_map

def _get_next_event_times(zone_modifiers):
    event_times_map = dict()
    for zone_modifier in zone_modifiers:
        scheduled_entries = list()
        weekly_schedule = zone_modifier.schedule(init_only=True)
        for (start, end) in weekly_schedule.get_schedule_entries():
            scheduled_entries.append({'start_time': '{0:D} {0:h}:{0:m}'.format(start), 'end_time': '{0:D} {0:h}:{0:m}'.format(end)})
        event_times_map[zone_modifier] = scheduled_entries
    return event_times_map

def _get_objects_effects(zone_modifiers):
    effects_map = dict()
    for zone_modifier in zone_modifiers:
        entries = list()
        if zone_modifier.obj_tag_id_to_count:
            for (tag_id, count) in zone_modifier.obj_tag_id_to_count.items():
                tag = Tag(tag_id)
                for (index, action) in enumerate(zone_modifier.object_tag_to_actions[tag]):
                    entries.append({'tag': str(tag) if index == 0 else '', 'count': count if index == 0 else '', 'statistic': action.stat.__name__, 'multiplier': action.multiplier, 'value': action.multiplier*count})
        effects_map[zone_modifier] = entries
    return effects_map
