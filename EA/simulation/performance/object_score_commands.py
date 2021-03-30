from _collections import defaultdictfrom collections import Counterfrom indexed_manager import object_load_timesfrom objects.components.types import STATE_COMPONENT, PORTAL_COMPONENT, INVENTORY_ITEM_COMPONENT, INVENTORY_COMPONENTfrom performance.performance_commands import CLIENT_STATE_OPS_TO_IGNOREfrom sims4.commands import CommandTypefrom sims4.utils import create_csvfrom singletons import UNSETimport indexed_managerimport servicesimport sims4POINTS_PER_INTERACTION = 1.70755e-05POINTS_PER_AUTONOMOUS_INTERACTION = 8.01154e-05POINTS_PER_CLIENT_STATE_TUNING = 0.000460809POINTS_PER_PORTAL_COMPONENT = 0.000460809POINTS_PER_COMMODITY = 0.000770917POINTS_PER_INVENTORY_ITEM_COMPONENT = 0.000961641POINTS_PER_INVENTORY_COMPONENT = -0.000852818POINTS_PER_STATISTIC = 0.00094356POINTS_PER_CLIENT_STATE_CHANGE_TUNING = 0.000273861POINTS_PER_OBJECT_PART = 0POINTS_PER_PROVIDED_POSTURE_INTERACTION = 0HIGHEST_OBJECT_SCORE_ALLOWED = 3
@sims4.commands.Command('performance.score_objects_in_world', command_type=CommandType.Automation)
def score_objects_in_world(verbose:bool=False, use_raw_score=False, _connection=None):
    cheat_output = sims4.commands.Output(_connection)
    object_scores = defaultdict(Counter)
    (on_lot_objects, off_lot_objects) = _score_all_objects(object_scores)
    overall_score = 0
    if verbose:
        cheat_output('Objects On Lot:')
        overall_score += _get_total_object_score(on_lot_objects, object_scores, cheat_output, verbose)
        cheat_output('Objects Off Lot:')
        overall_score += _get_total_object_score(off_lot_objects, object_scores, cheat_output, verbose)
    else:
        on_lot_objects_value = _get_total_object_score(on_lot_objects, object_scores, cheat_output, verbose)
        cheat_output('On Lot Objects Score:  {}'.format(on_lot_objects_value))
        off_lot_objects_value = _get_total_object_score(off_lot_objects, object_scores, cheat_output, verbose)
        cheat_output('Off Lot Objects Score: {}'.format(off_lot_objects_value))
        overall_score = on_lot_objects_value + off_lot_objects_value
    cheat_output('Number of On Lot Objects :  {}'.format(sum(on_lot_objects.values())))
    cheat_output('Number of Off Lot Objects : {}'.format(sum(off_lot_objects.values())))
    cheat_output('Total Lot Score:       {:.02f}%'.format(overall_score))

@sims4.commands.Command('performance.dump_object_scores', command_type=CommandType.Automation)
def dump_object_scores(use_raw_score=False, _connection=None):
    object_scores = defaultdict(Counter)
    (on_lot_objects, off_lot_objects) = _score_all_objects(object_scores, use_raw_score=use_raw_score)

    def _score_objects_callback(file, verbose=False):
        file.write('Object,total,On Lot,Off Lot')
        if verbose:
            file.write(',Interaction,Autonomous,provided posture,state component,client change tuning,parts,stats,commodities,portal,inventory item, inventory, Object, Time Spent Adding, Time Spent Loading, Adds, Loads, Avg Load Time\n')
        else:
            file.write('\n')
        sorted_object_scores = sorted(object_scores, key=lambda obj: sum(object_scores[obj].values()), reverse=True)
        for object_type in sorted_object_scores:
            _dump_object_to_file(object_type, object_scores, on_lot_objects, off_lot_objects, file, verbose=verbose, use_raw_score=use_raw_score)
        _dump_total_score(object_scores, on_lot_objects, off_lot_objects, file, use_raw_score=use_raw_score)

    create_csv('object_scores_verbose', lambda new_file: _score_objects_callback(new_file, verbose=True), _connection)
    create_csv('object_scores_simple', _score_objects_callback, _connection)

@sims4.commands.Command('performance.display_object_load_times', command_type=CommandType.Automation)
def display_object_load_times(_connection=None):
    if not indexed_manager.capture_load_times:
        return False
    cheat_output = sims4.commands.Output(_connection)
    for (object_class, object_load_data) in object_load_times.items():
        if not isinstance(object_class, str):
            cheat_output('{}: Object Manager Add Time {} : Component Load Time {} : Number of times added {} : number of times loaded {}'.format(object_class, object_load_data.time_spent_adding, object_load_data.time_spent_loading, object_load_data.adds, object_load_data.loads))
    time_adding = sum([y.time_spent_adding for (x, y) in object_load_times.items() if not isinstance(x, str)])
    time_loading = sum([y.time_spent_loading for (x, y) in object_load_times.items() if not isinstance(x, str)])
    cheat_output('Total time spent adding objects : {}'.format(time_adding))
    cheat_output('Total time spent loading components : {}'.format(time_loading))
    if 'household' in object_load_times:
        cheat_output('Time spent loading households : {}'.format(object_load_times['household']))
    cheat_output('Time spent building posture graph: {}'.format(object_load_times['posture_graph']))
    cheat_output('Time spent loading into the zone: {}'.format(object_load_times['lot_load']))

@sims4.commands.Command('performance.dump_object_load_times', command_type=CommandType.Automation)
def dump_object_load_times(_connection=None):
    if not indexed_manager.capture_load_times:
        return False

    def _object_load_time_callback(file):
        file.write('Object,AddTime,LoadTime,Adds,Loads\n')
        for (object_class, object_load_data) in object_load_times.items():
            if not isinstance(object_class, str):
                file.write('{},{},{},{},{},{}\n'.format(object_class, object_load_data.time_spent_adding, object_load_data.time_spent_loading, object_load_data.adds, object_load_data.loads, (object_load_data.time_spent_adding + object_load_data.time_spent_loading)/object_load_data.adds if object_load_data.adds > 0 else '0'))
        time_adding = sum([y.time_spent_adding for (x, y) in object_load_times.items() if not isinstance(x, str)])
        time_loading = sum([y.time_spent_loading for (x, y) in object_load_times.items() if not isinstance(x, str)])
        file.write(',{},{}\n'.format(time_adding, time_loading))
        if 'household' in object_load_times:
            file.write('Household,{}\n'.format(object_load_times['household']))
        file.write('Posture Graph,{},'.format(object_load_times['posture_graph']))
        file.write('Lot Load,{}\n'.format(object_load_times['lot_load']))

    create_csv('object_load_times', _object_load_time_callback, _connection)

@sims4.commands.Command('performance.toggle_object_load_capture', command_type=CommandType.Automation)
def _toggle_object_load_capture(enable:bool=True, _connection=None):
    indexed_manager.capture_load_times = enable

@sims4.commands.Command('performance.show_lot_score', command_type=CommandType.Automation)
def show_lot_score(show_load_time:bool=True, use_raw_score=False, _connection=None):
    object_scores = defaultdict(Counter)
    (on_lot_objects, off_lot_objects) = _score_all_objects(object_scores, use_raw_score=use_raw_score)
    total_lot_score = _get_total_object_score(on_lot_objects, object_scores, _connection, False)
    total_lot_score += _get_total_object_score(off_lot_objects, object_scores, _connection, False)
    if use_raw_score:
        output_string = 'Total Lot Score = {}'.format(total_lot_score)
    else:
        output_string = 'Total Lot Score = {:.02f}%'.format(total_lot_score)
    sims4.commands.cheat_output(output_string, _connection)
    if show_load_time and not indexed_manager.capture_load_times:
        sims4.commands.cheat_output('To see lot load time please use the |performance.toggle_object_load_capture and reload the lot.', _connection)
    elif show_load_time:
        lot_load_time = object_load_times['lot_load']
        lot_load_time_string = 'Total Lot Load Time = {}'.format(lot_load_time)
        sims4.commands.cheat_output(lot_load_time_string, _connection)
        output_string += ',' + lot_load_time_string
    sims4.commands.automation_output('ShowLotScore; Result:' + output_string, _connection)

def _score_all_objects(object_score_counter, use_raw_score=False):
    on_lot_objects = Counter()
    off_lot_objects = Counter()

    def _raw_score(score):
        return score

    scoring_function = _raw_score if use_raw_score else _convert_score_to_percentage_of_max
    all_objects = list(services.object_manager().objects)
    for obj in all_objects:
        if obj.is_sim:
            pass
        else:
            obj_type = obj.definition
            if obj.is_on_active_lot():
                on_lot_objects[obj_type] += 1
            else:
                off_lot_objects[obj_type] += 1
            if obj_type in object_score_counter:
                pass
            else:
                for super_affordance in obj.super_affordances():
                    if not super_affordance.allow_autonomous:
                        object_score_counter[obj_type]['interaction'] += scoring_function(POINTS_PER_INTERACTION)
                    else:
                        object_score_counter[obj_type]['autonomous'] += scoring_function(POINTS_PER_AUTONOMOUS_INTERACTION)
                    if super_affordance.provided_posture_type is not None:
                        object_score_counter[obj_type]['provided_posture'] += scoring_function(POINTS_PER_PROVIDED_POSTURE_INTERACTION)
                if obj.has_component(STATE_COMPONENT):
                    for (_, client_state_values) in obj.get_component(STATE_COMPONENT)._client_states.items():
                        client_change_op_count = _num_client_state_ops_changing_client(client_state_values)
                        object_score_counter[obj_type]['state_component'] += 1*scoring_function(POINTS_PER_CLIENT_STATE_TUNING)
                        if client_change_op_count > 0:
                            object_score_counter[obj_type]['client_change_tuning'] += client_change_op_count*scoring_function(POINTS_PER_CLIENT_STATE_CHANGE_TUNING)
                if obj.parts:
                    object_score_counter[obj_type]['parts'] += len(obj.parts)*scoring_function(POINTS_PER_OBJECT_PART)
                if obj.statistic_tracker is not None:
                    object_score_counter[obj_type]['statistics'] += len(obj.statistic_tracker)*scoring_function(POINTS_PER_STATISTIC)
                if obj.commodity_tracker is not None:
                    object_score_counter[obj_type]['commodities'] += len(obj.commodity_tracker)*scoring_function(POINTS_PER_COMMODITY)
                if obj.has_component(PORTAL_COMPONENT):
                    portal_component = obj.get_component(PORTAL_COMPONENT)
                    portal_instances = portal_component.get_portal_instances()
                    object_score_counter[obj_type]['portal_component'] += len(portal_instances)*scoring_function(POINTS_PER_PORTAL_COMPONENT)
                if obj.has_component(INVENTORY_ITEM_COMPONENT):
                    object_score_counter[obj_type]['inventory_item_component'] += 1*scoring_function(POINTS_PER_INVENTORY_ITEM_COMPONENT)
                if obj.has_component(INVENTORY_COMPONENT):
                    object_score_counter[obj_type]['inventory_component'] += 1*scoring_function(POINTS_PER_INVENTORY_COMPONENT)
    return (on_lot_objects, off_lot_objects)

def _num_client_state_ops_changing_client(client_state_values):
    count = 0
    for client_state_value in client_state_values:
        count += _get_num_client_changing_ops(client_state_value.new_client_state.ops)
    for target_client_state_value in client_state_values.values():
        count += _get_num_client_changing_ops(target_client_state_value.ops)
    return count

def _get_num_client_changing_ops(ops):
    count = 0
    for (op, value) in ops.items():
        if _client_state_op_has_client_change(op, value):
            count += 1
    return count

def _client_state_op_has_client_change(op, value):
    if op in CLIENT_STATE_OPS_TO_IGNORE:
        return False
    elif value is UNSET or value is None:
        return False
    return True

def _get_total_object_score(counter, scores, output, verbose):
    overall_score = 0
    for obj_type in counter:
        occurrences = counter[obj_type]
        object_data = scores[obj_type]
        object_score = sum(object_data.values())
        overall_score += occurrences*object_score
        if verbose:
            output('\tObject {} appears {} times at a score of {} for a total contribution of ({})'.format(obj_type.__name__, occurrences, object_score, occurrences*object_score))
    if verbose:
        output('Total Score is {:.02f}%'.format(overall_score))
    return overall_score

def _dump_object_to_file(object_type, object_scores, on_lot_objects, off_lot_objects, file, verbose=True, use_raw_score=False):
    object_counter = object_scores[object_type]
    file.write('{},'.format(object_type))
    if use_raw_score:
        file.write('{},'.format(sum(object_counter.values())))
    else:
        file.write('{:.02}%,'.format(sum(object_counter.values())))
    file.write('{},{}'.format(on_lot_objects[object_type], off_lot_objects[object_type]))
    if not verbose:
        file.write('\n')
        return
    file.write(',{},{},{},{},{},{},{},{},{},{},{}'.format(object_counter['interaction'], object_counter['autonomous'], object_counter['provided_posture'], object_counter['state_component'], object_counter['client_change_tuning'], object_counter['parts'], object_counter['statistics'], object_counter['commodities'], object_counter['portal_component'], object_counter['inventory_item_component'], object_counter['inventory_component']))
    if not indexed_manager.capture_load_times:
        file.write('\n')
        return
    object_load_data = object_load_times[object_type]
    file.write(',{},{},{},{},{},{}\n'.format(object_type, object_load_data.time_spent_adding, object_load_data.time_spent_loading, object_load_data.adds, object_load_data.loads, (object_load_data.time_spent_adding + object_load_data.time_spent_loading)/object_load_data.adds) if object_load_data.adds > 0 else '0')

def _dump_total_score(object_scores, on_lot_objects, off_lot_objects, file, use_raw_score=False):
    total_score = 0
    for (object_type, score_data) in object_scores.items():
        score = sum(score_data.values())
        score *= on_lot_objects[object_type] + off_lot_objects[object_type]
        total_score += score
    if use_raw_score:
        file.write('totals,{},{}\n'.format(total_score, object_load_times['lot_load'] if 'lot_load' in object_load_times else ''))
    else:
        file.write('totals,{:.02f}%,{}\n'.format(total_score, object_load_times['lot_load'] if 'lot_load' in object_load_times else ''))

def _convert_score_to_percentage_of_max(score):
    return score/HIGHEST_OBJECT_SCORE_ALLOWED*100
