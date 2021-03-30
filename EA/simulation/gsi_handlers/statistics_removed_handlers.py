from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersremoved_statistics_archive_schema = GsiGridSchema(label='Removed Statistics Archive', sim_specific=False)removed_statistics_archive_schema.add_field('statistic', label='Statistic', type=GsiFieldVisualizers.STRING)removed_statistics_archive_schema.add_field('owner', label='Owner', type=GsiFieldVisualizers.STRING)archiver = GameplayArchiver('removed_statistics', removed_statistics_archive_schema, add_to_archive_enable_functions=True, max_records=10000, enable_archive_by_default=True)
def is_archive_enabled():
    return archiver.enabled

def archive_removed_statistic(statistic, owner):
    archive_data = {'statistic': statistic, 'owner': owner}
    archiver.archive(archive_data)
