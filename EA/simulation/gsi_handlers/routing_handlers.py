import tracebackfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.route_event_handlers import get_path_route_events_logfrom objects import ALL_HIDDEN_REASONSfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport objects.systemimport routingimport servicesplanner_archive_schema = GsiGridSchema(label='Path Planner Log')planner_archive_schema.add_field('result', label='Result', width=2)planner_archive_schema.add_field('planner_name', label='Source', width=2)planner_archive_schema.add_field('planner_id', label='Planner ID', width=2, hidden=True)planner_archive_schema.add_field('x', label='Start X', type=GsiFieldVisualizers.FLOAT, width=2)planner_archive_schema.add_field('y', label='Start Y', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)planner_archive_schema.add_field('z', label='Start Z', type=GsiFieldVisualizers.FLOAT, width=2)planner_archive_schema.add_field('qx', label='Start QX', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)planner_archive_schema.add_field('qy', label='Start QY', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)planner_archive_schema.add_field('qz', label='Start QZ', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)planner_archive_schema.add_field('qw', label='Start QW', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)planner_archive_schema.add_field('level', label='Start Level', type=GsiFieldVisualizers.STRING, width=2)planner_archive_schema.add_field('ticks', label='Sleep Count', type=GsiFieldVisualizers.INT, width=2)planner_archive_schema.add_field('time', label='Sleep Time ms', type=GsiFieldVisualizers.FLOAT, width=2)planner_archive_schema.add_field('plan_time', label='Plan Time ms', type=GsiFieldVisualizers.FLOAT, width=2)planner_archive_schema.add_field('dist', label='Distance', type=GsiFieldVisualizers.FLOAT, width=2)planner_archive_schema.add_field('num_goals', label='Num Goals', type=GsiFieldVisualizers.INT, width=2)planner_archive_schema.add_field('num_starts', label='Num Starts', type=GsiFieldVisualizers.INT, width=2)planner_archive_schema.add_view_cheat('routing.serialize_pathplanner_data', label='Serialize Path Planner Data')with planner_archive_schema.add_has_many('Goals', GsiGridSchema) as sub_schema:
    sub_schema.add_field('index', label='Index', type=GsiFieldVisualizers.INT, width=2)
    sub_schema.add_field('x', label='X', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('z', label='Z', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('level', label='Level', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('cost', label='Cost', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('valid', label='Valid', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('final_cost', label='Final Cost (lower==better)', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('result', label='Result', width=2)
    sub_schema.add_field('raw_result', label='Raw Result', type=GsiFieldVisualizers.INT, width=2)
    sub_schema.add_field('group', label='Group', type=GsiFieldVisualizers.INT, width=2)with planner_archive_schema.add_has_many('Starts', GsiGridSchema) as sub_schema:
    sub_schema.add_field('x', label='X', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('z', label='Z', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('level', label='Level', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('cost', label='Cost', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('result', label='Result', width=2)with planner_archive_schema.add_has_many('Nodes', GsiGridSchema) as sub_schema:
    sub_schema.add_field('x', label='X', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('z', label='Z', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('level', label='Level', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('portal', label='Portal', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('qx', label='QX', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)
    sub_schema.add_field('qy', label='QY', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)
    sub_schema.add_field('qz', label='QZ', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)
    sub_schema.add_field('qw', label='QW', type=GsiFieldVisualizers.FLOAT, width=2, hidden=True)with planner_archive_schema.add_has_many('Details', GsiGridSchema) as sub_schema:
    sub_schema.add_field('name', label='Name', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('value', label='Value', type=GsiFieldVisualizers.FLOAT, width=2)with planner_archive_schema.add_has_many('Callstack', GsiGridSchema) as sub_schema:
    sub_schema.add_field('callstack', label='Callstack', width=2)archiver = GameplayArchiver('Planner', planner_archive_schema, add_to_archive_enable_functions=True)
def surface_string(surface_id):
    out_str = str(surface_id.secondary_id) + '/'
    if surface_id.type == routing.SurfaceType.SURFACETYPE_WORLD:
        out_str = out_str + 'WORLD'
    elif surface_id.type == routing.SurfaceType.SURFACETYPE_OBJECT:
        out_str = out_str + 'OBJECT:' + str(surface_id.primary_id)
    elif surface_id.type == routing.SurfaceType.SURFACETYPE_POOL:
        out_str = out_str + 'POOL'
    else:
        out_str = out_str + 'UNKNOWN'
    return out_str

def archive_plan(planner, path, ticks, time):
    result = 'Success'
    if path.is_route_fail() or path.status == routing.Path.PLANSTATUS_FAILED:
        result = 'Failed'
    plan_time = 0.0
    plan_record = path.nodes.record
    if plan_record is not None:
        plan_time = plan_record['total_time_ms']
    entry = {'planner_name': str(planner), 'planner_id': str(hex(planner.id)), 'result': result, 'x': round(path.route.origin.position.x, 4), 'y': round(path.route.origin.position.y, 4), 'z': round(path.route.origin.position.z, 4), 'qx': round(path.route.origin.orientation.x, 4), 'qy': round(path.route.origin.orientation.y, 4), 'qz': round(path.route.origin.orientation.z, 4), 'qw': round(path.route.origin.orientation.w, 4), 'level': surface_string(path.route.origin.routing_surface), 'ticks': ticks, 'time': round(time*1000, 4), 'plan_time': round(plan_time, 4), 'dist': round(path.nodes.length, 4), 'num_goals': len(path.route.goals), 'num_starts': len(path.route.origins)}
    goal_mask_success = routing.GOAL_STATUS_SUCCESS | routing.GOAL_STATUS_SUCCESS_TRIVIAL | routing.GOAL_STATUS_SUCCESS_LOCAL
    goal_mask_input_error = routing.GOAL_STATUS_INVALID_SURFACE | routing.GOAL_STATUS_INVALID_POINT
    goal_mask_unreachable = routing.GOAL_STATUS_CONNECTIVITY_GROUP_UNREACHABLE | routing.GOAL_STATUS_COMPONENT_DIFFERENT | routing.GOAL_STATUS_IMPASSABLE | routing.GOAL_STATUS_BLOCKED
    goals = []
    index = 0
    for (goal, result) in zip(path.route.goals, path.nodes.goal_results()):
        result_str = 'UNKNOWN'
        if result[1] & goal_mask_success > 0:
            if result[1] & routing.GOAL_STATUS_LOWER_SCORE > 0:
                result_str = 'SUCCESS (Not Picked)'
            else:
                result_str = 'PICKED'
        if result[1] & goal_mask_unreachable > 0:
            result_str = 'UNREACHABLE'
        if result[1] & goal_mask_input_error > 0:
            result_str = 'INVALID'
        if result[1] & routing.GOAL_STATUS_NOTEVALUATED > 0:
            result_str = 'NOT EVALUATED'
        cost = round(result[2], 4)
        if cost >= 1000000.0:
            cost = 999999
        goals.append({'index': index, 'x': round(goal.location.position.x, 4), 'z': round(goal.location.position.z, 4), 'level': surface_string(goal.location.routing_surface), 'cost': round(goal.cost, 4), 'valid': goal.failure_reason.name, 'final_cost': cost, 'result': result_str, 'raw_result': result[1], 'group': goal.group})
        index += 1
    entry['Goals'] = goals
    selected_start_tag = path.nodes.selected_start_tag_tuple
    starts = []
    for start in path.route.origins:
        result = 'Not Chosen'
        starts.append({'x': round(start.location.position.x, 4), 'z': round(start.location.position.z, 4), 'level': surface_string(start.location.routing_surface), 'cost': round(start.cost, 4), 'result': result})
    entry['Starts'] = starts
    nodes = []
    cur_path = path
    while cur_path is not None:
        for node in cur_path.nodes:
            nodes.append({'x': node.position[0], 'z': node.position[2], 'level': surface_string(node.routing_surface_id), 'portal': str(node.portal_id) + '/' + str(node.portal_object_id), 'qx': node.orientation[0], 'qy': node.orientation[1], 'qz': node.orientation[2], 'qw': node.orientation[3]})
        cur_path = cur_path.next_path
    entry['Nodes'] = nodes
    details = []
    if plan_record is not None:
        for (name, value) in plan_record.items():
            details.append({'name': name, 'value': value})
    entry['Details'] = details
    callstack = []
    for line in traceback.format_stack():
        callstack.append({'callstack': line.strip()})
    callstack.reverse()
    entry['Callstack'] = callstack
    archiver.archive(data=entry, object_id=planner.id)
build_archive_schema = GsiGridSchema(label='Navmesh Build Log')build_archive_schema.add_field('build_id', label='ID', width=2)build_archive_schema.add_field('total_time_ms', label='Total Time ms', type=GsiFieldVisualizers.FLOAT, width=2)with build_archive_schema.add_has_many('Details', GsiGridSchema) as sub_schema:
    sub_schema.add_field('name', label='Name', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('value', label='Value', type=GsiFieldVisualizers.FLOAT, width=2)build_archiver = GameplayArchiver('Build', build_archive_schema, add_to_archive_enable_functions=True)
def archive_build(build_id):
    entry = {}
    build_record = routing.planner_build_record(build_id)
    if build_record is not None:
        entry = {'build_id': build_record['id'], 'total_time_ms': build_record['total_time_ms']}
    details = []
    if build_record is not None:
        for (name, value) in build_record.items():
            details.append({'name': name, 'value': value})
    entry['Details'] = details
    build_archiver.archive(data=entry)
FGL_archive_schema = GsiGridSchema(label='FGL Log')FGL_archive_schema.add_field('fgl_id', label='ID', width=2)FGL_archive_schema.add_field('object', label='Object', type=GsiFieldVisualizers.STRING, width=2)FGL_archive_schema.add_field('result', label='Result', type=GsiFieldVisualizers.STRING, width=2)FGL_archive_schema.add_field('total_time_s', label='Total Time s', type=GsiFieldVisualizers.FLOAT, width=2)with FGL_archive_schema.add_has_many('Details', GsiGridSchema) as sub_schema:
    sub_schema.add_field('name', label='Name', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('value', label='Value', type=GsiFieldVisualizers.STRING, width=2)with FGL_archive_schema.add_has_many('Callstack', GsiGridSchema) as sub_schema:
    sub_schema.add_field('callstack', label='Callstack', width=2)with FGL_archive_schema.add_has_many('Results', GsiGridSchema) as sub_schema:
    sub_schema.add_field('loc', label='Loc', type=GsiFieldVisualizers.STRING, width=2)FGL_archiver = GameplayArchiver('FGL', FGL_archive_schema, add_to_archive_enable_functions=True)
def archive_FGL(fgl_id, context, result, time_s):
    obj = None
    if context.search_strategy.object_id != 0:
        obj = objects.system.find_object(context.search_strategy.object_id)
    if context.routing_context is not None:
        obj = objects.system.find_object(context.routing_context.agent_id)
    entry = {'fgl_id': fgl_id, 'object': str(obj), 'result': str(result), 'total_time_s': time_s}
    details = []
    for (name, value) in context.__dict__.items():
        details.append({'name': name, 'value': str(value)})
    entry['Details'] = details
    callstack = []
    for line in traceback.format_stack():
        callstack.append({'callstack': line.strip()})
    callstack.reverse()
    entry['Callstack'] = callstack
    results = []
    results_list = context.search.get_results()
    for loc in results_list:
        results.append({'loc': str(loc)})
    entry['Results'] = results
    FGL_archiver.archive(data=entry)

def add_route_archive_fields(schema):
    schema.add_field('path_id', label='Path Id', width=2)
    schema.add_field('duration', label='Duration', type=GsiFieldVisualizers.FLOAT, width=2)
    schema.add_field('length', label='Length', type=GsiFieldVisualizers.FLOAT, width=2)
    schema.add_field('stall_for_slaves_length', label='Seconds Stalled for Slaves', type=GsiFieldVisualizers.FLOAT, width=3)
    schema.add_field('route_string', label='Nodes to Draw', type=GsiFieldVisualizers.STRING, width=5, hidden=True)
    with schema.add_has_many('Nodes', GsiGridSchema) as sub_schema:
        sub_schema.add_field('segment_duration', label='Segment Duration', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('x', label='X', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('y', label='Y', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('z', label='Z', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('routing_surface', label='Routing Surface', type=GsiFieldVisualizers.STRING, width=3)
        sub_schema.add_field('portal_id', label='Portal ID', width=0.5)
        sub_schema.add_field('portal_object', label='Portal Object', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('portal_object_id', label='Portal Object ID', type=GsiFieldVisualizers.STRING, width=2)
    with schema.add_view_cheat('debugvis.object_route.draw_path', label='Draw Path') as cheat:
        cheat.add_token_param('path_id')
        cheat.add_token_param('route_string')
    with schema.add_view_cheat('debugvis.object_route.draw_additional_path', label='Draw Additional Path') as cheat:
        cheat.add_token_param('path_id')
        cheat.add_token_param('route_string')
    schema.add_view_cheat('debugvis.object_route.erase_all_paths', label='Erase All Paths')

def archive_node_data(entry, path):
    path_nodes = path.nodes
    nodes_entry = []
    portals_entry = []
    object_manager = services.object_manager()
    for index in range(len(path_nodes) - 1, 0, -1):
        cur_node = path_nodes[index]
        prev_node = path_nodes[index - 1]
        portal_object = object_manager.get(cur_node.portal_object_id)
        nodes_entry.append({'segment_duration': cur_node.time - prev_node.time, 'x': cur_node.position[0], 'y': cur_node.position[1], 'z': cur_node.position[2], 'routing_surface': surface_string(cur_node.routing_surface_id), 'portal_id': cur_node.portal_id, 'portal_object': str(portal_object), 'portal_object_id': str(cur_node.portal_object_id)})
    entry['Nodes'] = nodes_entry
    entry['Portals'] = portals_entry
    entry['route_string'] = path.get_contents_as_string(path_nodes)
object_route_archive_schema = GsiGridSchema(label='Object Route Archive')object_route_archive_schema.add_field('object_name', label='Object Name', width=2)add_route_archive_fields(object_route_archive_schema)object_route_archiver = GameplayArchiver('object_route', object_route_archive_schema, enable_archive_by_default=True)
def archive_object_route(object_info, path, stall_for_slaves_length):
    object_id = object_info.id
    object_info = str(object_info)
    entry = {'object_name': str(object_info), 'path_id': id(path), 'duration': path.duration() if path is not None else None, 'length': path.length() if path is not None else None, 'stall_for_slaves_length': stall_for_slaves_length.in_real_world_seconds()}
    archive_node_data(entry, path)
    object_route_archiver.archive(data=entry, object_id=object_id)
sim_route_archive_schema = GsiGridSchema(label='Sim Route Archive', sim_specific=True)sim_route_archive_schema.add_field('interaction', label='Interaction', type=GsiFieldVisualizers.STRING, width=2)add_route_archive_fields(sim_route_archive_schema)with sim_route_archive_schema.add_has_many('Route Events', GsiGridSchema) as sub_schema:
    sub_schema.add_field('time', label='Time', type=GsiFieldVisualizers.FLOAT, width=1)
    sub_schema.add_field('event_type', label='Event Type', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('tuning_instance', label='Tuning Instance', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('duration', label='Duration', type=GsiFieldVisualizers.FLOAT, width=1)
    sub_schema.add_field('executed', label='Executed', type=GsiFieldVisualizers.STRING, width=1)with sim_route_archive_schema.add_has_many('Routing Formations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('master', label='Master', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('slave', label='Slave', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('formation_type', label='Formation Type', type=GsiFieldVisualizers.STRING, width=2)with sim_route_archive_schema.add_has_many('Portals', GsiGridSchema) as sub_schema:
    sub_schema.add_field('portal_obj_id', label='Portal Object ID', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('portal_obj', label='Portal Object', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('portal_id', label='Portal ID', width=1)
    sub_schema.add_field('portal_type', label='Portal Type', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('portal_entry_surface', label='Entry Routing Surface', type=GsiFieldVisualizers.STRING, width=3)
    sub_schema.add_field('portal_entry_orientation', label='Entry Orientation', type=GsiFieldVisualizers.STRING, width=3)
    sub_schema.add_field('portal_entry_position', label='Entry Position', type=GsiFieldVisualizers.STRING, width=3)
    sub_schema.add_field('portal_exit_surface', label='Exit Routing Surface', type=GsiFieldVisualizers.STRING, width=3)
    sub_schema.add_field('portal_exit_orientation', label='Exit Orientation', type=GsiFieldVisualizers.STRING, width=3)
    sub_schema.add_field('portal_exit_position', label='Exit Position', type=GsiFieldVisualizers.STRING, width=3)sim_route_archiver = GameplayArchiver('sim_route', sim_route_archive_schema, enable_archive_by_default=True)
def _archive_sim_route_node_portals(entry, node, portal_object):
    if portal_object is None:
        return
    portal = portal_object.get_portal_by_id(node.portal_id)
    if portal is None:
        return
    (portal_entry, portal_exit) = portal.get_portal_locations(node.portal_id)
    entry.append({'portal_obj_id': str(node.portal_object_id), 'portal_obj': str(portal_object), 'portal_id': node.portal_id, 'portal_type': str(portal_object.get_portal_type(node.portal_id)), 'portal_entry_surface': surface_string(portal_entry.routing_surface if portal_entry is not None else None), 'portal_entry_orientation': str(portal_entry.orientation if portal_entry is not None else None), 'portal_entry_position': str(portal_entry.position if portal_entry is not None else None), 'portal_exit_surface': surface_string(portal_exit.routing_surface if portal_exit is not None else None), 'portal_exit_orientation': str(portal_exit.orientation if portal_exit is not None else None), 'portal_exit_position': str(portal_exit.position if portal_exit is not None else None)})

def _archive_sim_routing_formations(entry, sim_info):
    sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
    if sim is None:
        return
    routing_component = sim.routing_component
    if routing_component is None:
        return
    entry.append({'master': str(routing_component.routing_master)})
    slave_data_list = routing_component.get_routing_slave_data()
    for slave_data in slave_data_list:
        entry.append({'slave': str(slave_data.slave), 'formation_type': str(slave_data.formation_type)})

def archive_sim_route(sim_info, interaction, path, stall_for_slaves_length):
    entry = {'path_id': id(path), 'interaction': repr(interaction), 'duration': path.duration() if path is not None else None, 'length': path.length() if path is not None else None, 'stall_for_slaves_length': stall_for_slaves_length.in_real_world_seconds()}
    archive_node_data(entry, path)
    route_events_entry = []
    route_events = get_path_route_events_log(path).route_events
    for event in route_events.values():
        route_events_entry.append({'time': event['time'], 'event_type': event['event_type'], 'tuning_instance': event['event_cls'], 'duration': event['duration'], 'executed': event['executed']})
    entry['Route Events'] = route_events_entry
    routing_formations_entry = []
    _archive_sim_routing_formations(routing_formations_entry, sim_info)
    entry['Routing Formations'] = routing_formations_entry
    sim_route_archiver.archive(data=entry, object_id=sim_info.id)

def set_goal_archive_schema(goal_archive_schema):
    goal_archive_schema.add_field('count', label='Count', type=GsiFieldVisualizers.INT, width=2)
    goal_archive_schema.add_field('constraint', label='Constraint', width=2)
    goal_archive_schema.add_field('geometry', label='Geometry', width=2)
    goal_archive_schema.add_field('args', label='Args', width=2)
    with goal_archive_schema.add_has_many('Goals', GsiGridSchema) as sub_schema:
        sub_schema.add_field('x', label='X', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('y', label='Y', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('z', label='Z', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('routing_surface', label='Routing Surface', type=GsiFieldVisualizers.STRING, width=3)
        sub_schema.add_field('cost', label='Cost', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('height_clearance', label='Height Clearance', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('tag', label='Tag', type=GsiFieldVisualizers.INT, width=2)
        sub_schema.add_field('requires_los_check', label='LOS?', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('error', label='Error', type=GsiFieldVisualizers.STRING, width=2)
    with goal_archive_schema.add_has_many('Discarded Goals', GsiGridSchema) as sub_schema:
        sub_schema.add_field('x', label='X', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('y', label='Y', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('z', label='Z', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('routing_surface', label='Routing Surface', type=GsiFieldVisualizers.STRING, width=3)
        sub_schema.add_field('cost', label='Cost', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('height_clearance', label='Height Clearance', type=GsiFieldVisualizers.FLOAT, width=2)
        sub_schema.add_field('error', label='Error', type=GsiFieldVisualizers.STRING, width=2)
        sub_schema.add_field('info', label='Info', type=GsiFieldVisualizers.STRING, width=2)
    with goal_archive_schema.add_has_many('Callstack', GsiGridSchema) as sub_schema:
        sub_schema.add_field('callstack', label='Callstack', width=2)
goal_archive_schema = GsiGridSchema(label='Goals Archive')set_goal_archive_schema(goal_archive_schema)goals_archiver = GameplayArchiver('goals_archive', goal_archive_schema, add_to_archive_enable_functions=True)sim_goal_archive_schema = GsiGridSchema(label='Goals Archive', sim_specific=True)set_goal_archive_schema(sim_goal_archive_schema)sim_goals_archiver = GameplayArchiver('sim_goals_archive', sim_goal_archive_schema, add_to_archive_enable_functions=True)
def archive_goals_enabled():
    return goals_archiver.enabled or sim_goals_archiver.enabled

def archive_goals(handle, goal_list, discarded_goals, **kwargs):
    entry = {'count': len(goal_list), 'constraint': str(handle.constraint), 'geometry': str(handle.geometry), 'args': str(kwargs)}
    goals = []
    entry['Goals'] = goals
    for goal in goal_list:
        position = goal.location.world_transform.translation
        goals.append({'x': position.x, 'y': position.y, 'z': position.z, 'routing_surface': surface_string(goal.location.routing_surface), 'cost': goal.cost, 'height_clearance': goal.height_clearance, 'tag': goal.tag, 'requires_los_check': 'X' if goal.requires_los_check else '', 'error': goal.failure_reason.name})
    discarded_goals_entry = []
    for discarded_goal in discarded_goals:
        if discarded_goal.location is None:
            x_str = ''
            y_str = ''
            z_str = ''
            routing_surface_str = ''
        else:
            position = discarded_goal.location.world_transform.translation
            x_str = str(position.x)
            y_str = str(position.y)
            z_str = str(position.z)
            routing_surface_str = surface_string(discarded_goal.location.routing_surface)
        if discarded_goal.cost is None:
            cost_str = ''
        else:
            cost_str = str(discarded_goal.cost)
        discarded_goals_entry.append({'x': x_str, 'y': y_str, 'z': z_str, 'routing_surface': routing_surface_str, 'cost': cost_str, 'height_clearance': discarded_goal.height_clearance, 'error': discarded_goal.failure.name, 'info': discarded_goal.info})
    entry['Discarded Goals'] = discarded_goals_entry
    callstack = []
    for line in traceback.format_stack():
        callstack.append({'callstack': line.strip()})
    callstack.reverse()
    entry['Callstack'] = callstack
    if handle.sim is None or not handle.sim.is_sim:
        goals_archiver.archive(data=entry)
    else:
        sim_goals_archiver.archive(data=entry, object_id=handle.sim.sim_info.id)
