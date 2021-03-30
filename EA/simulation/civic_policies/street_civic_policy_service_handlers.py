from eco_footprint.eco_footprint_tuning import EcoFootprintTunablesfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemafrom world.street import get_lot_id_to_zone_ids_dictimport servicesimport sims4street_schema = GsiGridSchema(label='Street Service')street_schema.add_field('street', label='Street', width=1, unique_field=True)street_schema.add_field('voting_open', label='Voting Open', width=1)street_schema.add_field('active', label='Active', width=1)street_schema.add_field('eco_footprint_state', label='Eco Footprint State')street_schema.add_field('eco_footprint', label='Eco Footprint Value')street_schema.add_field('eco_footprint_convergence', label='Eco Footprint Convergence')with street_schema.add_has_many('civic_policies', GsiGridSchema, label='Civic Policies') as sub_schema:
    sub_schema.add_field('civic_policy', label='Civic Policy')
    sub_schema.add_field('status', label='Status')
    sub_schema.add_field('votes', label='Votes')with street_schema.add_has_many('lot_eco_footprint', GsiGridSchema, label='Lot Eco Footprint') as sub_schema:
    sub_schema.add_field('lot_name', label='Lot Name')
    sub_schema.add_field('lot_description_id', label='Lot Description ID')
    sub_schema.add_field('category', label='Category')
    sub_schema.add_field('footprint', label='Eco Footprint')
@GsiHandler('street_service', street_schema)
def generate_street_civic_policy_data(*args, zone_id:int=None, **kwargs):
    service_info = []
    street_service = services.street_service()
    if street_service is None:
        return service_info
    persistence_service = services.get_persistence_service()
    household_manager = services.household_manager()
    statistics_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
    active_lot_id = services.active_lot_id()
    active_street = services.current_zone().street
    voting_open = street_service.voting_open
    for (street, instance) in street_service._provider_instances.items():
        civic_policy_entry = []
        enacted_policies = instance.get_enacted_policies(tuning=True)
        balloted_policies = instance.get_balloted_policies(tuning=True)
        up_for_repeal = instance.get_up_for_repeal_policies(tuning=True)
        for policy in instance.get_civic_policies(tuning=True):
            status_str = ''
            if policy in enacted_policies:
                status_str += 'Enacted '
            if policy in balloted_policies:
                status_str += 'Balloted '
            if policy in up_for_repeal:
                status_str += 'Up for Repeal'
            if status_str == '':
                status_str = 'Dormant'
            if policy.vote_count_statistic is None:
                votes = 'n/a'
            else:
                votes = instance.get_stat_value(policy.vote_count_statistic)
            entry = {'civic_policy': str(policy), 'status': status_str, 'votes': votes}
            civic_policy_entry.append(entry)
        street_footprint = instance.get_street_footprint(add=False)
        has_eco_footprint = street_footprint is not None
        eco_footprint_state = 'None'
        eco_footprint_value = 'None'
        eco_footprint_convergence = 'None'
        if has_eco_footprint:
            eco_footprint_state = instance.current_eco_footprint_state.name
            eco_footprint_value = street_footprint.get_value() if has_eco_footprint else None
            eco_footprint_convergence = street_footprint.convergence_value
        lot_eco_footprint_entry = []
        if street is not None:
            lot_id_to_zone_id_dict = get_lot_id_to_zone_ids_dict(street)
            for (lot_id, zone_ids) in lot_id_to_zone_id_dict.items():
                is_played_lot = False
                for zone_id in zone_ids:
                    household_id = persistence_service.get_household_id_from_zone_id(zone_id)
                    if household_id:
                        household = household_manager.get(household_id)
                        if household is not None and household.is_played_household:
                            is_played_lot = True
                            break
                footprint_value = EcoFootprintTunables.LOT_FOOTPRINT.default_value
                if active_lot_id == lot_id:
                    lot = services.active_lot()
                    footprint_value = lot.commodity_tracker.get_value(EcoFootprintTunables.LOT_FOOTPRINT)
                else:
                    zone_data = persistence_service.get_zone_proto_buff(zone_ids[0])
                    if zone_data is not None:
                        stat_tracker_data = zone_data.gameplay_zone_data.commodity_tracker
                        for stat_data in stat_tracker_data.commodities:
                            stat_cls = statistics_manager.get(stat_data.name_hash)
                            if stat_cls is EcoFootprintTunables.LOT_FOOTPRINT:
                                footprint_value = stat_data.value
                                break
                        house_desc_id = services.get_house_description_id(zone_data.lot_template_id, zone_data.lot_description_id, zone_data.active_plex)
                        footprint_value = services.get_eco_footprint_value(house_desc_id)
                zone_data = persistence_service.get_zone_proto_buff(zone_ids[0])
                lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
                lot_name = lot_data.lot_name
                if lot_name is '':
                    lot_name = 'Unavailable'
                lot_desc_id = lot_data.lot_description_id if lot_data is not None else None
                entry = {'lot_name': lot_name, 'lot_description_id': lot_desc_id, 'category': 'Played' if is_played_lot else 'Unplayed', 'footprint': footprint_value}
                lot_eco_footprint_entry.append(entry)
        entry = {'street': str(street), 'voting_open': 'Yes' if voting_open else 'No', 'active': 'X' if street is active_street else '', 'civic_policies': civic_policy_entry, 'eco_footprint_state': eco_footprint_state, 'eco_footprint': eco_footprint_value, 'eco_footprint_convergence': eco_footprint_convergence, 'lot_eco_footprint': lot_eco_footprint_entry}
        service_info.append(entry)
    service_info = sorted(service_info, key=lambda entry: entry['street'])
    return service_info
