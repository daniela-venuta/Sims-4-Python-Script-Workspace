from protocolbuffers import SimObjectAttributes_pb2from sims.fixup.sim_info_fixup_action import SimInfoFixupActionTimingfrom sims.sim_info_tracker import SimInfoTrackerimport servicesimport sims4.resources
class FixupTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._pending_fixups = []

    def __iter__(self):
        return self._pending_fixups.__iter__()

    def add_fixup(self, fixup):
        if fixup.sim_info_fixup_actions_timing == SimInfoFixupActionTiming.ON_SIM_INFO_CREATED:
            fixup.apply_fixup_actions(self._sim_info)
            return
        self._pending_fixups.append(fixup)

    def remove_fixup(self, fixup):
        self._pending_fixups.remove(fixup)

    def has_fixup(self, fixup):
        return fixup in self._pending_fixups

    def apply_all_appropriate_fixups(self, fixup_source):
        fixups_to_apply = [fixup for fixup in self._pending_fixups if fixup.should_apply_fixup_actions(fixup_source)]
        for fixup in fixups_to_apply:
            fixup.apply_fixup_actions(self._sim_info)
            self.remove_fixup(fixup)

    def save(self):
        data = SimObjectAttributes_pb2.PersistableFixupTracker()
        fixup_ids = [fixup.guid64 for fixup in self._pending_fixups]
        data.pending_fixups.extend(fixup_ids)
        return data

    def load(self, data):
        sim_info_fixup_manager = services.get_instance_manager(sims4.resources.Types.SIM_INFO_FIXUP)
        for fixup_id in data.pending_fixups:
            fixup = sim_info_fixup_manager.get(fixup_id)
            if fixup is not None:
                self._pending_fixups.append(fixup)
