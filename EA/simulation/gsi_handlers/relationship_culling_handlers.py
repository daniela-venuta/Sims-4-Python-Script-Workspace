from collections import namedtuple
    sub_schema.add_field('culled_status', label='Culled Status')
    sub_schema.add_field('culled_reason', label='Culled Reason')
    sub_schema.add_field('sim_info', label='Sim A')
    sub_schema.add_field('target_sim_info', label='Sim B')
    sub_schema.add_field('total_depth', label='Total Depth', type=GsiFieldVisualizers.INT, width=0.2)
    sub_schema.add_field('rel_bits', label='Relationship Bits')
    sub_schema.add_field('culled_status', label='Culled Status')
    sub_schema.add_field('culled_reason', label='Culled Reason')
    sub_schema.add_field('sim_info', label='Sim A')
    sub_schema.add_field('target_sim_info', label='Sim B')
    sub_schema.add_field('total_depth', label='Total Depth', type=GsiFieldVisualizers.INT, width=0.2)
    sub_schema.add_field('rel_bits', label='Relationship Bits')
    sub_schema.add_field('culled_status', label='Culled Status')
    sub_schema.add_field('culled_reason', label='Culled Reason')
    sub_schema.add_field('sim_info', label='Sim A')
    sub_schema.add_field('target_sim_info', label='Sim B')
    sub_schema.add_field('total_depth', label='Total Depth', type=GsiFieldVisualizers.INT, width=0.2)
    sub_schema.add_field('rel_bits', label='Relationship Bits')
def is_archive_enabled():
    return archiver.enabled

def _add_rel_data(rel_data:RelationshipGSIData, relationships_data):
    rel_entry = {'sim_info': str(rel_data.sim_info), 'target_sim_info': str(rel_data.target_sim_info), 'total_depth': rel_data.total_depth, 'rel_bits': rel_data.formated_rel_bits, 'culled_status': rel_data.culled_status, 'culled_reason': rel_data.culled_reason}
    relationships_data.append(rel_entry)

def archive_relationship_culling(total_culled_count, relationship_data, culled_relationship_data):
    entry = {'relationships_culled': total_culled_count, 'game_time': str(services.time_service().sim_now)}
    all_relationship_data = relationship_data + culled_relationship_data
    all_relationaships = []
    entry['all_relationships'] = all_relationaships
    for rel_data in all_relationship_data:
        _add_rel_data(rel_data, all_relationaships)
    not_culled_relationships = []
    entry['not_culled_relationships'] = not_culled_relationships
    for rel_data in relationship_data:
        _add_rel_data(rel_data, not_culled_relationships)
    culled_relationaships = []
    entry['culled_relationships'] = culled_relationaships
    for rel_data in culled_relationship_data:
        _add_rel_data(rel_data, culled_relationaships)
    archiver.archive(entry)
