import weakrefimport servicesimport sims4.gsi.archivewith sims4.reload.protected(globals()):
    tracked_objects_dict = {}
    deleted_objs = []logger = sims4.log.Logger('GameplayArchiver')MAX_DELETED_SIM_RECORDS = 10
def logged_gsi_object_deleted(obj):
    deleted_id = tracked_objects_dict[obj]
    del tracked_objects_dict[obj]
    deleted_objs.append(deleted_id)
    if len(deleted_objs) > MAX_DELETED_SIM_RECORDS:
        obj_to_cleanup = deleted_objs.pop(0)
        for archive_entries in sims4.gsi.archive.archive_data.values():
            if isinstance(archive_entries, dict) and obj_to_cleanup in archive_entries:
                del archive_entries[obj_to_cleanup]

def print_num_archive_records(cheat_output):
    if cheat_output is None:
        return False
    cheat_output('---------- Enabled GSI Archives  ----------')
    for (archive_type, archive_entries) in sims4.gsi.archive.archive_data.items():
        if not sims4.gsi.archive.is_archive_enabled(archive_type):
            pass
        elif isinstance(archive_entries, list):
            cheat_output('Type: {}, Entries: {}'.format(archive_type, len(archive_entries)))
        elif isinstance(archive_entries, dict):
            cheat_output('Type: {}'.format(archive_type))
            for (sim_id, sim_data_entries) in archive_entries.items():
                cheat_output('    Sim Id: {}, Num Entries: {}'.format(sim_id, len(sim_data_entries)))
        else:
            cheat_output('I have no idea what this entry is....{}'.format(archive_type))
    cheat_output('---------- End GSI Archive Dump ----------')

class GameplayArchiver(sims4.gsi.archive.Archiver):

    def archive(self, *args, object_id=None, **kwargs):
        if self._sim_specific:
            cur_sim = services.object_manager().get(object_id)
            if cur_sim is not None:
                if not cur_sim.is_sim:
                    return
                if not cur_sim.is_selectable:
                    cur_sim_ref = weakref.ref(cur_sim, logged_gsi_object_deleted)
                    tracked_objects_dict[cur_sim_ref] = object_id
                    if cur_sim_ref not in tracked_objects_dict and object_id in deleted_objs:
                        deleted_objs.remove(object_id)
        time_service = services.time_service()
        if time_service.sim_timeline is not None:
            game_time = str(time_service.sim_now)
        else:
            game_time = str(services.game_clock_service().now())
        super().archive(*args, object_id=object_id, game_time=game_time, **kwargs)
