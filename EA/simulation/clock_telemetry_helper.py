import sims4.reload
    g_num_times_max_tick_spike_telemetry_sent = 0
    g_num_times_game_clock_fell_behind_telemetry_sent = 0
def report_change_speed(speed, time_spent_in_speed, precentage_time_in_speed, household=None):
    with telemetry_helper.begin_hook(clock_telemetry_writer, TELEMETRY_HOOK_CHANGE_SPEED_REPORT, household=household) as hook:
        hook.write_int(TELEMETRY_FIELD_CLOCK_SPEED, speed)
        hook.write_int(TELEMETRY_FIELD_TIME_SPENT_IN_SPEED, time_spent_in_speed)
        hook.write_float(TELEMETRY_FIELD_PERCENTAGE_TIME_SPENT_IN_SPEED, precentage_time_in_speed)

def report_max_tick_spike(current_game_speed, ticks_behind, max_tick):
    global g_num_times_max_tick_spike_telemetry_sent
    if g_num_times_max_tick_spike_telemetry_sent < MAX_TELEMETRY_FOR_SPIKE:
        with telemetry_helper.begin_hook(clock_telemetry_writer, TELEMETRY_HOOK_MAX_TICK_SPIKE) as hook:
            hook.write_int(TELEMETRY_FIELD_TIME_DIFF, ticks_behind)
            hook.write_int(TELEMETRY_FIELD_CURRENT_CLOCK_SPEED, int(current_game_speed))
            hook.write_int(TELEMETRY_FIELD_MAX_TICKS, max_tick)
            g_num_times_max_tick_spike_telemetry_sent += 1

def report_game_clock_is_behind(current_game_speed, ticks_behind):
    global g_num_times_game_clock_fell_behind_telemetry_sent
    if g_num_times_game_clock_fell_behind_telemetry_sent < MAX_TELEMETRY_FOR_GAME_CLOCK_BEHIND:
        with telemetry_helper.begin_hook(clock_telemetry_writer, TELEMETRY_HOOK_GAME_CLOCK_BEHIND) as hook:
            hook.write_int(TELEMETRY_FIELD_TIME_DIFF, ticks_behind)
            hook.write_int(TELEMETRY_FIELD_CURRENT_CLOCK_SPEED, int(current_game_speed))
            g_num_times_game_clock_fell_behind_telemetry_sent += 1
