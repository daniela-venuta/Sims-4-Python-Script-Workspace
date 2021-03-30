from sims4.gsi.dispatcher import GsiHandler
    sub_schema.add_field('name', label='Name')
    sub_schema.add_field('value', label='Value')
@GsiHandler('region_service', region_schema)
def generate_region_service_data(*args, zone_id:int=None, **kwargs):
    region_service_data = []
    region_service = services.region_service()
    if region_service is None:
        return region_service_data
    for region_inst in region_service._region_instances.values():
        commodities_entry = []
        for commodity in region_inst.commodity_tracker.get_all_commodities():
            entry = {'name': type(commodity).__name__, 'value': commodity.get_value()}
            commodities_entry.append(entry)
        entry = {'region_name': type(region_inst).__name__, 'commodities': commodities_entry}
        region_service_data.append(entry)
    return region_service_data
