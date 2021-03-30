from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesfrom venues.venue_service import VenueServicevenue_game_schema = GsiGridSchema(label='Venue Game Service')venue_game_schema.add_field('zone', label='Venue', width=1, unique_field=True)venue_game_schema.add_field('voting_open', label='Voting Open', width=1)venue_game_schema.add_field('active', label='Active', width=1)with venue_game_schema.add_has_many('civic_policies', GsiGridSchema, label='Civic Policies') as sub_schema:
    sub_schema.add_field('civic_policy', label='Civic Policy')
    sub_schema.add_field('status', label='Status')
    sub_schema.add_field('votes', label='Votes')
@GsiHandler('venue_game_service', venue_game_schema)
def generate_venue_game_service_data(*args, zone_id:int=None, **kwargs):
    service_info = []
    venue_game_service = services.venue_game_service()
    venue_service = services.venue_service()
    street_service = services.street_service()
    zone_manager = services.get_zone_manager()
    if venue_game_service is None:
        return service_info
    active_zone = services.current_zone()
    voting_open = street_service.voting_open
    for (zone_id, instance) in venue_game_service._zone_provider.items():
        zone = zone_manager.get(zone_id, allow_uninstantiated_zones=True)
        if zone is None:
            pass
        else:
            lot_name = zone.lot.get_lot_name()
            try:
                household = zone.lot.get_household()
            except:
                household = None
            household_name = '' if household is None else '(' + household.name + ')'
            zone_str = lot_name + household_name + ' ' + str(zone)
            civic_policy_entry = []
            enacted_policies = instance.get_enacted_policies(tuning=True)
            balloted_policies = instance.get_balloted_policies(tuning=True)
            up_for_repeal = instance.get_up_for_repeal_policies(tuning=True)
            source_venue = None
            for policy in instance.get_civic_policies(tuning=True):
                status_str = ''
                if not enacted_policies:
                    source_venue = VenueService.get_variable_venue_source_venue(policy.sub_venue)
                    if policy.sub_venue is source_venue:
                        status_str += '[Enacted by default] '
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
            entry = {'zone': zone_str, 'voting_open': 'Yes' if voting_open else 'No', 'active': str(type(venue_service.active_venue)) if zone is active_zone else '', 'civic_policies': civic_policy_entry}
            service_info.append(entry)
    service_info = sorted(service_info, key=lambda entry: entry['zone'])
    return service_info
