import inspectfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport objects.components.types
def create_schema_for_commodity_tracker(label, sim_specific=False):
    schema = GsiGridSchema(label=label, sim_specific=sim_specific)
    schema.add_field('stat_guid', label='Stat GUID', unique_field=True, width=0.5)
    schema.add_field('stat_name', label='Name', width=2)
    schema.add_field('stat_value', label='Value Points', type=GsiFieldVisualizers.FLOAT)
    schema.add_field('instanced', label='Instanced', width=0.5)
    schema.add_field('decay_rate', label='Decay Rate', type=GsiFieldVisualizers.FLOAT, width=0.5)
    schema.add_field('change_rate', label='Change Rate', type=GsiFieldVisualizers.FLOAT, width=0.5)
    schema.add_field('decay_enabled', label='Decay Enabled', width=0.5)
    schema.add_field('convergence_value', label='Convergence Value', width=0.5)
    schema.add_field('time_till_callback', label='Time')
    schema.add_field('active_callback', label='Callback')
    schema.add_field('delayed_decay_timer', label='Delayed Decay Timer')
    with schema.add_has_many('modifiers', GsiGridSchema, label='Modifiers') as sub_schema:
        sub_schema.add_field('modifier', label='Modifier')
        sub_schema.add_field('modifier_value', label='Modifier Value')
    with schema.add_has_many('track_listeners', GsiGridSchema, label='Track Callbacks') as sub_schema:
        sub_schema.add_field('callback_info', label='Callback Info')
    return schema

def _add_modifier_entry(modifier_entries, modifier_name, modifier_value):
    modifier_entries.append({'modifier': modifier_name, 'modifier_value': modifier_value})

def generate_data_from_commodity(stat, statistic_component):
    instanced = not inspect.isclass(stat)
    entry = {'stat_guid': str(stat.guid64), 'stat_name': stat.stat_type.__name__, 'stat_value': stat.get_value(), 'instanced': 'x' if instanced else '', 'decay_rate': stat.get_decay_rate() if instanced else '', 'change_rate': stat.get_change_rate() if instanced else '', 'decay_enabled': 'x' if stat.decay_enabled else '', 'convergence_value': stat.convergence_value if instanced else '', 'time_till_callback': str(stat._alarm_handle.get_remaining_time()) if instanced and stat._alarm_handle is not None else '', 'active_callback': str(stat._active_callback) if instanced and stat._active_callback is not None else '', 'delayed_decay_timer': str(stat.get_time_till_decay_starts()) if instanced else ''}
    lock_reason_list = statistic_component.get_locked_reason_list(stat.stat_type)
    unlock_reason_list = statistic_component.get_unlocked_reason_list(stat.stat_type)
    modifier_entries = []
    _add_modifier_entry(modifier_entries, 'persisted', 'x' if stat.persisted else '')
    _add_modifier_entry(modifier_entries, 'remove_on_convergence', 'x' if stat.remove_on_convergence else '')
    _add_modifier_entry(modifier_entries, 'min_value', stat.min_value)
    _add_modifier_entry(modifier_entries, 'max_value', stat.max_value)
    _add_modifier_entry(modifier_entries, 'statistic_modifier', stat._statistic_modifier if instanced else '')
    _add_modifier_entry(modifier_entries, 'statistic_multiplier_increase', stat._statistic_multiplier_increase if instanced else '')
    _add_modifier_entry(modifier_entries, 'statistic_multiplier_decrease', stat._statistic_multiplier_decrease if instanced else '')
    _add_modifier_entry(modifier_entries, 'decay_rate_multiplier', stat._decay_rate_modifier if instanced else '')
    _add_modifier_entry(modifier_entries, 'locked_reasons', lock_reason_list if lock_reason_list else 'not locked')
    _add_modifier_entry(modifier_entries, 'unlocked_reasons', unlock_reason_list if unlock_reason_list else 'no unlocks')
    entry['modifiers'] = modifier_entries
    callback_infos = []
    if instanced:
        for callback_listener in stat._statistic_callback_listeners:
            callback_infos.append({'callback_info': str(callback_listener)})
    entry['track_listeners'] = callback_infos
    return entry

def generate_data_from_commodity_tracker(commodity_tracker):
    stat_data = []
    if commodity_tracker is None:
        return stat_data
    owner = commodity_tracker.owner
    statistic_component = owner.get_component(objects.components.types.STATISTIC_COMPONENT)
    if statistic_component is None:
        return stat_data
    for stat in commodity_tracker.all_statistics():
        stat_data.append(generate_data_from_commodity(stat, statistic_component))
    return stat_data
