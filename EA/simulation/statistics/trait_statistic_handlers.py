from gsi_handlers.sim_handlers import _get_sim_info_by_idfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizerstrait_statistics_schema = GsiGridSchema(label='Statistics/Trait Statistic', sim_specific=True)trait_statistics_schema.add_field('trait_statistic_name', label='Name')trait_statistics_schema.add_field('trait_statistic_value', label='Value', type=GsiFieldVisualizers.FLOAT)trait_statistics_schema.add_field('trait_statistic_min_daily_cap', label='Min Daily Cap', type=GsiFieldVisualizers.FLOAT)trait_statistics_schema.add_field('trait_statistic_max_daily_cap', label='Max Daily Cap', type=GsiFieldVisualizers.FLOAT)trait_statistics_schema.add_field('trait_statistic_state', label='State')trait_statistics_schema.add_field('trait_statistic_group_limited', label='Group Limited')
@GsiHandler('trait_statistic_view', trait_statistics_schema)
def generate_sim_skill_view_data(sim_id:int=None):
    trait_statistic_data = []
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info is not None:
        for statistic in list(cur_sim_info.trait_statistic_tracker):
            entry = {'trait_statistic_name': type(statistic).__name__, 'trait_statistic_value': statistic.get_value(), 'trait_statistic_min_daily_cap': statistic._get_minimum_decay_level(), 'trait_statistic_max_daily_cap': statistic._get_maximum_decay_level(), 'trait_statistic_state': str(statistic.state), 'trait_statistic_group_limited': str(statistic.group_limited)}
            trait_statistic_data.append(entry)
    return trait_statistic_data
