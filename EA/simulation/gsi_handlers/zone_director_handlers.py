import sims4.logfrom gsi_handlers.gameplay_archiver import GameplayArchiverimport sims4.resourcesimport servicesfrom sims4.gsi.schema import GsiGridSchemafrom sims4.gsi.dispatcher import GsiHandlerwildlife_encounters = GsiGridSchema(label='Active Wildlife Encounters')wildlife_encounters.add_field('area_object', label='Encounter Object')
@GsiHandler('wildlife_encounters', wildlife_encounters)
def generate_wildlife_encounters_view():
    encounter_data = []
    ambient_service = services.current_zone().ambient_service
    walkby_director = ambient_service.get_walkby_director()
    if walkby_director is not None:
        encounter_list = walkby_director.get_active_encounter_list()
        for encounter in encounter_list:
            encounter_data.append({'area_object': str(encounter)})
    return encounter_data
zone_director_schema = GsiGridSchema(label='Zone Director')zone_director_schema.add_field('zone_director_type', label='Zone Director Type')zone_director_schema.add_field('zone_id', label='Zone Id')zone_director_schema.add_field('op', label='Op')zone_director_schema.add_field('neighborhood', label='Neighborhood')zone_director_schema.add_field('lot_id', label='Lot Id')zone_director_schema.add_field('active_venue', label='Venue')zone_director_schema.add_field('source_venue', label='Source Venue')with zone_director_schema.add_has_many('lot preparations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('action', label='Action')
    sub_schema.add_field('description', label='Description')with zone_director_schema.add_has_many('spawn objects', GsiGridSchema) as sub_schema:
    sub_schema.add_field('obj_id', label='Obj Id')
    sub_schema.add_field('obj_def', label='Obj Def')
    sub_schema.add_field('parent_id', label='Parent Id')
    sub_schema.add_field('position', label='Position')
    sub_schema.add_field('states', label='States')with zone_director_schema.add_has_many('civic_policies', GsiGridSchema, label='Civic Policies') as sub_schema:
    sub_schema.add_field('civic_policy', label='Civic Policy')
    sub_schema.add_field('enacted', label='Enacted')
    sub_schema.add_field('votes', label='Votes')archiver = GameplayArchiver('zone_director', zone_director_schema, max_records=100, add_to_archive_enable_functions=True)
def log_zone_director_event(zone_director, zone, op):
    if not archiver.enabled:
        return
    venue_service = services.venue_service()
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': op, 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'active_venue': type(venue_service.active_venue).__name__, 'source_venue': type(venue_service.source_venue).__name__}
    archive_data['lot preparations'] = []
    archive_data['spawn objects'] = []
    archive_data['civic_policies'] = []
    archiver.archive(archive_data)

def log_lot_preparations(zone_director, zone, lot_preparation_log):
    if not archiver.enabled:
        return
    venue_service = services.venue_service()
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': 'prepare lot', 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'active_venue': type(venue_service.active_venue).__name__, 'source_venue': type(venue_service.source_venue).__name__}
    archive_data['lot preparations'] = lot_preparation_log
    archive_data['spawn objects'] = []
    archive_data['civic_policies'] = []
    archiver.archive(archive_data)

def log_spawn_objects(zone_director, zone, spawn_objects_log):
    if not archiver.enabled:
        return
    venue_service = services.venue_service()
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': 'spawn objects', 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'active_venue': type(venue_service.active_venue).__name__, 'source_venue': type(venue_service.source_venue).__name__}
    archive_data['lot preparations'] = []
    archive_data['spawn objects'] = spawn_objects_log
    archive_data['civic_policies'] = []
    archiver.archive(archive_data)

def log_civic_policy_update(zone_director, zone, op):
    if not archiver.enabled:
        return
    venue_service = services.venue_service()
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': op, 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'active_venue': type(venue_service.active_venue).__name__, 'source_venue': type(venue_service.source_venue).__name__}
    civic_policies = []
    provider = venue_service.source_venue.civic_policy_provider
    if provider:
        enacted_policies = provider.get_enacted_policies(tuning=True)
        for policy in provider.get_civic_policies(tuning=True):
            if policy.vote_count_statistic is None:
                votes = 'n/a'
            else:
                votes = provider.get_stat_value(policy.vote_count_statistic)
            entry = {'civic_policy': str(policy), 'enacted': 'X' if policy in enacted_policies else '', 'votes': votes}
            civic_policies.append(entry)
    archive_data['lot preparations'] = []
    archive_data['spawn objects'] = []
    archive_data['civic_policies'] = civic_policies
    archiver.archive(archive_data)
