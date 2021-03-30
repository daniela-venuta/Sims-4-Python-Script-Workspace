from event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuplefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom ui.ui_dialog import UiDialogOkCancelfrom venues.venue_constants import NPCSummoningPurposefrom world import regionimport services
class SimInfoInteraction(ImmediateSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'confirmation_dialogs': TunableList(description='\n            A list of one or more confirmation dialogs that can be displayed before running the interaction.\n            ', tunable=TunableTuple(description='\n                A set of tests and the corresponding dialog to show.\n                ', tests=TunableTestSet(description='\n                    If these test pass (or are omitted), the corresponding confirmation dialog will show before running.\n                    '), dialog=UiDialogOkCancel.TunableFactory(description='\n                    The ok/cancel dialog that will display to the user.\n                    ')), tuning_group=GroupNames.UI)}

    def __init__(self, *args, sim_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim_info = sim_info
        self._next_dialog_idx = 0

    @flexmethod
    def get_participants(cls, inst, participant_type:ParticipantType, sim=DEFAULT, target=DEFAULT, sim_info=None, **interaction_parameters) -> set:
        result = super(ImmediateSuperInteraction, inst if inst is not None else cls).get_participants(participant_type, sim=sim, target=target, **interaction_parameters)
        result = set(result)
        if participant_type & ParticipantType.Actor:
            if inst is not None:
                sim_info = inst._sim_info
            if sim_info is not None:
                result.add(sim_info)
        return tuple(result)

    def _run_interaction_gen(self, timeline):
        if not self.confirmation_dialogs:
            self._run_interaction()
            return True
        resolver = SingleSimResolver(self._sim_info)

        def try_show_next_dialog():
            for (idx, entry) in enumerate(self.confirmation_dialogs[self._next_dialog_idx:], start=self._next_dialog_idx):
                if entry.tests:
                    if entry.tests.run_tests(resolver):
                        dialog = entry.dialog(self._sim_info, resolver)
                        dialog.show_dialog(on_response=on_response)
                        self._next_dialog_idx = idx + 1
                        return
                dialog = entry.dialog(self._sim_info, resolver)
                dialog.show_dialog(on_response=on_response)
                self._next_dialog_idx = idx + 1
                return
            self._run_interaction()

        def on_response(dialog_response):
            if dialog_response.accepted:
                try_show_next_dialog()

        try_show_next_dialog()
        return True
lock_instance_tunables(SimInfoInteraction, simless=True)
class BringHereInteraction(SimInfoInteraction):
    INSTANCE_TUNABLES = {'check_region_compatibility': Tunable(description='\n            If checked then we will check for region compatibility.\n            ', tunable_type=bool, default=True)}

    @classmethod
    def _test(cls, *args, sim_info=None, **kwargs):
        if sim_info.zone_id == services.current_zone_id():
            return TestResult(False, 'Cannot bring a sim to a zone that is already the current zone.')
        if cls.check_region_compatibility:
            current_region = services.current_region()
            sim_region = region.get_region_instance_from_zone_id(sim_info.zone_id)
            if sim_region is None or not sim_region.is_region_compatible(current_region):
                return TestResult(False, 'Cannot bring a sim to an incompatible region.')
        return super()._test(*args, **kwargs)

    def _run_interaction(self):
        household = self._sim_info.household
        current_zone_id = services.current_zone_id()
        sim_infos_to_bring = [sim_info for sim_info in services.daycare_service().get_abandoned_toddlers(household, sims_infos_to_ignore=(self._sim_info,)) if sim_info.vacation_or_home_zone_id == current_zone_id]
        sim_infos_to_bring.append(self._sim_info)
        caretaker_zone_ids = set()
        offlot_pets = set()
        for sim_info in household:
            if sim_info is self._sim_info:
                pass
            elif sim_info.is_human:
                if sim_info.is_child_or_older:
                    caretaker_zone_ids.add(sim_info.zone_id)
                    if sim_info.zone_id == current_zone_id:
                        pass
                    elif sim_info.zone_id == sim_info.vacation_or_home_zone_id:
                        pass
                    else:
                        offlot_pets.add(sim_info)
            elif sim_info.zone_id == current_zone_id:
                pass
            elif sim_info.zone_id == sim_info.vacation_or_home_zone_id:
                pass
            else:
                offlot_pets.add(sim_info)
        for pet in offlot_pets:
            if pet.zone_id not in caretaker_zone_ids:
                sim_infos_to_bring.append(pet)
        daycare_service = services.daycare_service()
        if daycare_service.is_sim_info_at_daycare(self._sim_info):
            daycare_service.remove_sim_info_from_daycare(self._sim_info)
        services.current_zone().venue_service.active_venue.summon_npcs(tuple(sim_infos_to_bring), NPCSummoningPurpose.BRING_PLAYER_SIM_TO_LOT)

class SwitchToZoneInteraction(SimInfoInteraction):

    @classmethod
    def _test(cls, *args, sim_info=None, **kwargs):
        if sim_info.zone_id == 0:
            return TestResult(False, 'Cannot travel to a zone of 0.')
        if sim_info.zone_id == services.current_zone_id():
            return TestResult(False, 'Cannot switch to zone that is the current zone.')
        if sim_info in services.daycare_service().get_sim_infos_for_nanny(sim_info.household):
            return TestResult(False, 'Cannot switch to a sim that should be with the nanny.')
        return super()._test(*args, **kwargs)

    def _run_interaction(self):
        self._sim_info.send_travel_switch_to_zone_op()
        return True
