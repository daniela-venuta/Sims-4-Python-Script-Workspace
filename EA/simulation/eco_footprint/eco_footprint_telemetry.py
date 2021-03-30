import sims4import telemetry_helperTELEMETRY_GROUP_ECO_FOOTPRINT = 'NBHD'TELEMETRY_HOOK_ECO_FOOTPRINT_STATE_CHANGE = 'FOOT'TELEMETRY_FIELD_NEIGHBORHOOD = 'nbhd'TELEMETRY_FIELD_OLD_FOOTPRINT_STATE = 'oldf'TELEMETRY_FIELD_NEW_FOOTPRINT_STATE = 'newf'TELEMETRY_FIELD_CONVERGENCE_VALUE = 'cnvg'_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_ECO_FOOTPRINT)
def send_eco_footprint_state_change_telemetry(world_description_id, old_state, new_state, convergence_value):
    with telemetry_helper.begin_hook(_telemetry_writer, TELEMETRY_HOOK_ECO_FOOTPRINT_STATE_CHANGE) as hook:
        hook.write_guid(TELEMETRY_FIELD_NEIGHBORHOOD, world_description_id)
        hook.write_enum(TELEMETRY_FIELD_OLD_FOOTPRINT_STATE, old_state)
        hook.write_enum(TELEMETRY_FIELD_NEW_FOOTPRINT_STATE, new_state)
        hook.write_float(TELEMETRY_FIELD_CONVERGENCE_VALUE, convergence_value)
