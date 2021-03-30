import sims4.telemetry
def write_travel_group_telemetry(group, hook_tag, sim_info):
    with telemetry_helper.begin_hook(travel_group_telemetry_writer, hook_tag, sim_info=sim_info) as hook:
        hook.write_int(TELEMETRY_TRAVEL_GROUP_ID, group.id)
        hook.write_int(TELEMETRY_TRAVEL_GROUP_ZONE_ID, group.zone_id)
        hook.write_int(TELEMETRY_TRAVEL_GROUP_SIZE, len(group))
        hook.write_int(TELEMETRY_TRAVEL_GROUP_DURATION, int(group.duration_time_in_minutes))
        hook.write_int(TELEMETRY_TRAVEL_GROUP_REGION_DESC_ID, int(get_region_description_id_from_zone_id(group.zone_id)))
