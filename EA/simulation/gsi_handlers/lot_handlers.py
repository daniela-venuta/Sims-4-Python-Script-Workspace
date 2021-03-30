from gsi_handlers.commodity_tracker_gsi_util import generate_data_from_commodity_tracker, create_schema_for_commodity_trackerfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesimport sims4import build_buylot_info_schema = GsiGridSchema(label='Lot Info', auto_refresh=False)lot_info_schema.add_field('neighborhood', label='Neighborhood', unique_field=True)lot_info_schema.add_field('cur_lot', label='Current Lot', width=0.4)lot_info_schema.add_field('region_id', label='Region ID', type=GsiFieldVisualizers.INT, width=0.5)lot_info_schema.add_field('lot_desc_id', label='Description ID', type=GsiFieldVisualizers.INT, width=0.5)lot_info_schema.add_field('zone_id', label='Zone ID')lot_info_schema.add_field('venue', label='Venue')lot_info_schema.add_field('lot_name', label='Lot Name')with lot_info_schema.add_has_many('statistics', GsiGridSchema, label='Statistics (Current Lot Only)') as sub_schema:
    sub_schema.add_field('statistic', label='Statistic')
    sub_schema.add_field('value', label='Statistic Value', type=GsiFieldVisualizers.FLOAT, width=0.5)
@GsiHandler('lot_info', lot_info_schema)
def generate_lot_info_data(*args, zone_id:int=None, **kwargs):
    lot_infos = []
    current_zone = services.current_zone()
    lot = current_zone.lot
    venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
    for neighborhood_proto in services.get_persistence_service().get_neighborhoods_proto_buf_gen():
        for lot_owner_info in neighborhood_proto.lots:
            zone_id = lot_owner_info.zone_instance_id
            if zone_id is not None:
                venue_tuning_id = build_buy.get_current_venue(zone_id)
                venue_tuning = venue_manager.get(venue_tuning_id)
                if venue_tuning is not None:
                    is_current_lot = lot_owner_info.zone_instance_id == lot.zone_id
                    cur_info = {'neighborhood': neighborhood_proto.name, 'region_id': neighborhood_proto.region_id, 'lot_desc_id': lot_owner_info.lot_description_id, 'zone_id': str(hex(zone_id)), 'venue': venue_tuning.__name__, 'lot_name': lot_owner_info.lot_name, 'cur_lot': 'X' if is_current_lot else ''}
                    if is_current_lot:
                        stat_entries = []
                        for stat in lot.get_all_stats_gen():
                            stat_entries.append({'statistic': stat.stat_type.__name__, 'value': stat.get_value()})
                        cur_info['statistics'] = stat_entries
                    lot_infos.append(cur_info)
    return lot_infos
commodity_data_schema = create_schema_for_commodity_tracker('Lot Statistics/Continuous Statistic Data')
@GsiHandler('lot_commodity_data_view', commodity_data_schema)
def generate_lot_commodity_data_view():
    lot = services.active_lot()
    return generate_data_from_commodity_tracker(lot.commodity_tracker)
