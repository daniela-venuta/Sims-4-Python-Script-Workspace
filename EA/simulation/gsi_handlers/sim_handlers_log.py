from gsi_handlers.gameplay_archiver import GameplayArchiver
def archive_skill_change(sim, skill, time_delta, old_skill_value, new_skill_value, new_level, last_update):
    if time_delta != 0:
        skill_per_time = (new_skill_value - old_skill_value)/time_delta
    else:
        skill_per_time = 0
    archive_data = {'skill_name': skill.skill_type.__name__, 'current_game_time': str(services.time_service().sim_now), 'old_skill_value': old_skill_value, 'new_skill_value': new_skill_value, 'new_level': new_level, 'time_delta': str(time_delta), 'skill_delta': skill_per_time}
    skill_change_archiver.archive(data=archive_data, object_id=sim.id)

    sub_schema.add_field('object', label='Object')
    sub_schema.add_field('object_id', label='Object ID', type=GsiFieldVisualizers.INT)
    sub_schema.add_field('definition', label='Definition')
    sub_schema.add_field('object_moods', label='Moods Contributed')
    sub_schema.add_field('object_scores', label='Mood Scores')
    sub_schema.add_field('object_negative_score', label='Negative Score', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('object_positive_score', label='Positive Score', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('object', label='Object')
    sub_schema.add_field('object_id', label='Object ID', type=GsiFieldVisualizers.INT)
    sub_schema.add_field('source', label='Source of Contribution')
    sub_schema.add_field('score_affected', label='Score Affected')
    sub_schema.add_field('adder', label='Adder', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('multiplier', label='Multiplier', type=GsiFieldVisualizers.FLOAT)
def get_environment_score_object_contributions(obj, source, modifiers):
    contributions = []
    for mood in modifiers.mood_modifiers.keys():
        mood_modifiers = modifiers.get_mood_modifiers(mood)
        if not mood_modifiers[0] != 0:
            if mood_modifiers[1] != 1:
                contributions.append({'object': gsi_handlers.gsi_utils.format_object_name(obj), 'object_id': obj.id, 'source': source, 'score_affected': mood.__name__, 'adder': mood_modifiers[0], 'multiplier': mood_modifiers[1]})
        contributions.append({'object': gsi_handlers.gsi_utils.format_object_name(obj), 'object_id': obj.id, 'source': source, 'score_affected': mood.__name__, 'adder': mood_modifiers[0], 'multiplier': mood_modifiers[1]})
    negative_mods = modifiers.get_negative_modifiers()
    if negative_mods[0] != 0 or negative_mods[1] != 1:
        contributions.append({'object': gsi_handlers.gsi_utils.format_object_name(obj), 'object_id': obj.id, 'source': source, 'score_affected': 'NEGATIVE SCORING', 'adder': negative_mods[0], 'multiplier': negative_mods[1]})
    positive_mods = modifiers.get_positive_modifiers()
    if positive_mods[0] != 0 or positive_mods[1] != 1:
        contributions.append({'object': gsi_handlers.gsi_utils.format_object_name(obj), 'object_id': obj.id, 'source': source, 'score_affected': 'POSITIVE SCORING', 'adder': positive_mods[0], 'multiplier': negative_mods[1]})
    return contributions

def log_environment_score(sim_id, primary_mood, score, mood_commodity, negative_score, negative_commodity, positive_score, positive_commodity, contributing_objects, object_contributions):
    if primary_mood is not None:
        mood_name = primary_mood.__name__
    elif negative_score > positive_score:
        mood_name = 'NEGATIVE SCORING ONLY'
    elif positive_score is not None:
        mood_name = 'POSITIVE SCORING ONLY'
    else:
        mood_name = 'None'
    mood_commodity_name = mood_commodity.__name__ if mood_commodity is not None else 'None'
    negative_commodity_name = negative_commodity.__name__ if negative_commodity is not None else 'None'
    positive_commdity_name = positive_commodity.__name__ if positive_commodity is not None else 'None'
    log_entry = {'primary_mood': mood_name, 'score': score, 'mood_commodity': mood_commodity_name, 'negative_score': negative_score, 'negative_commodity': negative_commodity_name, 'positive_score': positive_score, 'positive_commodity': positive_commdity_name, 'object_contributions': object_contributions}
    object_data = []
    for (obj, mood_scores, negative_score, positive_score) in contributing_objects:
        valid_scores = {k: v for (k, v) in mood_scores.items() if v != 0}
        if not positive_score != 0:
            if valid_scores:
                keys = [str(key.__name__) for key in valid_scores.keys()]
                values = [str(value) for value in valid_scores.values()]
                object_data.append({'object': gsi_handlers.gsi_utils.format_object_name(obj), 'object_id': obj.id, 'definition': obj.definition.name, 'object_moods': str(keys), 'object_scores': str(values), 'object_negative_score': negative_score, 'object_positive_score': positive_score})
        keys = [str(key.__name__) for key in valid_scores.keys()]
        values = [str(value) for value in valid_scores.values()]
        object_data.append({'object': gsi_handlers.gsi_utils.format_object_name(obj), 'object_id': obj.id, 'definition': obj.definition.name, 'object_moods': str(keys), 'object_scores': str(values), 'object_negative_score': negative_score, 'object_positive_score': positive_score})
    log_entry['contributing_objects'] = object_data
    environment_score_archiver.archive(log_entry, object_id=sim_id)

    sub_schema.add_field('aop_name', label='AOP')
    sub_schema.add_field('test_result', label='Test Result', width=2)
    sub_schema.add_field('scored_aop', label='Affordance')
    sub_schema.add_field('base_score', label='Base Score', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('buff_score_adjustment', label='Buff Score', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('topic_score', label='Topic Score', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('score_modifier', label='Score Modifier', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('total_score', label='Total Score', type=GsiFieldVisualizers.INT, width=1)
def log_aop_result(sim, aop, return_result, test_result):
    if sim is None:
        return
    if sim.id not in menu_generation_log:
        menu_generation_log[sim.id] = {}
    aop_name = aop.affordance.__name__
    if test_result is None:
        test_result = return_result
    menu_generation_log[sim.id][aop_name] = str(test_result)

def archive_pie_menu_option(sim, target, logged_scores):
    if sim is None:
        return
    current_menu_data = menu_generation_log[sim.id]
    menu_options = []
    for (aop_name, aop_result) in current_menu_data.items():
        menu_options.append({'aop_name': aop_name, 'test_result': aop_result})
    archive_data = {'menu_target': str(target), 'possible_options': menu_options, 'options_scores': list(logged_scores.values())}
    pie_menu_generation_archiver.archive(data=archive_data, object_id=sim.id)
    menu_generation_log[sim.id].clear()

def archive_sim_reservation(reservation_handler, reservation_result):
    archive_data = {'reservation_handler': str(reservation_handler), 'reservation_sim': str(reservation_handler.sim), 'reservation_target': str(reservation_handler.target), 'reservation_interaction': str(reservation_handler.reservation_interaction), 'reservation_result': str(reservation_result)}
    sim_reservation_archiver.archive(data=archive_data, object_id=reservation_handler.sim.id)
