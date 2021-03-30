from gsi_handlers.gameplay_archiver import GameplayArchiver
@GsiHandler('story_progression_view', story_progression_view_schema)
def generate_story_progression_view_data(sim_id:int=None):
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return
    sim_info = sim_info_manager.get(sim_id)
    if sim_info is None:
        return
    data = []
    if sim_info.story_progression_tracker is None:
        return data
    for story_progression_action in sim_info.story_progression_tracker.get_actions_gen():
        data.append({'action_id': story_progression_action.action_id, 'action_name': str(story_progression_action), 'action_duration': str(story_progression_action.get_duration())})
    return data

    sub_schema.add_field('demographic_name', label='Demographic', width=4)
    sub_schema.add_field('demographic_previous_error', label='Previous Error', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('demographic_current_error', label='Current Error', type=GsiFieldVisualizers.FLOAT, width=2)
def archive_sim_story_progression(sim_info, action, *, result, global_demographics=(), action_demographics=()):
    archive_data = {'action_name': str(action), 'action_result': str(result), 'action_duration': str(action.get_duration()), 'action_demographics': []}
    for (global_demographic, action_demographic) in zip(global_demographics, action_demographics):
        archive_data['action_demographics'].append({'demographic_name': str(action_demographic), 'demographic_previous_error': str(global_demographic.get_demographic_error()), 'demographic_current_error': str(action_demographic.get_demographic_error())})
    story_progression_sim_archiver.archive(data=archive_data, object_id=sim_info.sim_id)

def archive_story_progression(action, message, *args):
    entry = {'action_type': str(action), 'action_message': message.format(*args)}
    story_progression_archiver.archive(data=entry)
