import sims4.telemetryimport telemetry_helperfrom world.region import get_region_description_id_from_zone_idTELEMETRY_GROUP_TRAVEL_GROUPS = 'TGRP'TELEMETRY_HOOK_TRAVEL_GROUP_ADD = 'TGAD'TELEMETRY_HOOK_TRAVEL_GROUP_START = 'TGST'TELEMETRY_HOOK_TRAVEL_GROUP_EXTEND = 'TGEX'TELEMETRY_HOOK_TRAVEL_GROUP_END = 'TGEN'TELEMETRY_HOOK_TRAVEL_GROUP_REMOVE = 'TGRM'TELEMETRY_TRAVEL_GROUP_ID = 'tgid'TELEMETRY_TRAVEL_GROUP_ZONE_ID = 'tgzo'TELEMETRY_TRAVEL_GROUP_SIZE = 'tgsz'TELEMETRY_TRAVEL_GROUP_DURATION = 'tgdu'TELEMETRY_TRAVEL_GROUP_REGION_DESC_ID = 'rgni'travel_group_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_TRAVEL_GROUPS)
def write_travel_group_telemetry(group, hook_tag, sim_info):
    with telemetry_helper.begin_hook(travel_group_telemetry_writer, hook_tag, sim_info=sim_info) as hook:
        hook.write_int(TELEMETRY_TRAVEL_GROUP_ID, group.id)
        hook.write_int(TELEMETRY_TRAVEL_GROUP_ZONE_ID, group.zone_id)
        hook.write_int(TELEMETRY_TRAVEL_GROUP_SIZE, len(group))
        hook.write_int(TELEMETRY_TRAVEL_GROUP_DURATION, int(group.duration_time_in_minutes))
        hook.write_int(TELEMETRY_TRAVEL_GROUP_REGION_DESC_ID, int(get_region_description_id_from_zone_id(group.zone_id)))
