import servicesfrom gsi_handlers.commodity_tracker_gsi_util import create_schema_for_commodity_tracker, generate_data_from_commodityfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaschema = create_schema_for_commodity_tracker(label='Lot Level Commodity Data')schema.add_field('level_index', label='Lot Level')
@GsiHandler('lot_level_commodity_data_view', schema)
def generate_lot_level_commodity_data_view():
    lot = services.active_lot()
    lot_levels = list(lot.lot_levels.values())
    lot_levels.sort(key=lambda level: level.level_index)
    stat_data = []
    for lot_level in lot_levels:
        for stat in lot_level.get_all_stats_gen():
            entry = generate_data_from_commodity(stat, lot_level.statistic_component)
            entry['level_index'] = lot_level.level_index
            stat_data.append(entry)
    return stat_data
