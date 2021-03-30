import enumfrom interactions.liability import Liabilityfrom objects.components.types import WAITING_LINE_COMPONENTfrom sims4.tuning.tunable import TunableReference, HasTunableFactoryimport servicesimport sims4.resourcesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo
class LineUtils:
    ROUTE_TO_WAITING_IN_LINE = TunableReference(description='\n        A reference to the interaction used for getting Sims to route closer\n        to the target before running the wait in line interaction.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    WAIT_IN_LINE_TOGETHER_ROUTING_FORMATION = TunableReference(description='\n        A reference to the interaction used for getting an interaction\'s "wait \n        in line with participant" to wait near a sim in line. \n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    WAIT_IN_LINE_TOGETHER_SITUATION = TunableReference(description='\n        The situation that will be initiated when a sim joins a line if there\n        are any sims that should wait nearby.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('WaitInLineTogether',))

class LineUpdateTiming(enum.Int):
    STAND_SLOT_RELEASED = 1
    PATH_PLANNED = ...

def start_wait_in_line_together_situation(initiating_sim, picked_sims, stored_interaction_data):
    situation = LineUtils.WAIT_IN_LINE_TOGETHER_SITUATION
    wait_in_line_job = situation.waiting_in_line_sim_job_and_role_state.job
    wait_nearby_job = situation.waiting_near_line_sim_job_and_role_state.job
    guest_list = SituationGuestList(invite_only=True, host_sim_id=initiating_sim.id)
    wait_in_line_host_info = SituationGuestInfo(initiating_sim.sim_id, wait_in_line_job, RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP)
    guest_list.add_guest_info(wait_in_line_host_info)
    for sim in picked_sims:
        wait_nearby_guest_info = SituationGuestInfo(sim.sim_id, wait_nearby_job, RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP)
        guest_list.add_guest_info(wait_nearby_guest_info)
    situation_manager = services.get_zone_situation_manager()
    creation_source = 'LineUtils: WaitInLineTogetherSituation hosted by {}'.format(str(initiating_sim))
    target = stored_interaction_data[0].target
    situation_id = situation_manager.create_situation(LineUtils.WAIT_IN_LINE_TOGETHER_SITUATION, guest_list=guest_list, user_facing=False, creation_source=creation_source, target_id=target.id if target is not None else None, line_key=stored_interaction_data[2])
    return situation_id

def get_wait_in_line_together_situation(sim, target_id, line_key):
    situation_manager = services.get_zone_situation_manager()
    for situation in situation_manager.get_situations_sim_is_in(sim):
        if type(situation) is LineUtils.WAIT_IN_LINE_TOGETHER_SITUATION and situation.line_key == line_key and situation.line_interaction_target_id == target_id:
            return situation

class WaitingLineInteractionChainLiability(Liability, HasTunableFactory):
    LIABILITY_TOKEN = 'WaitingLineInteractionChainLiability'

    def __init__(self, interaction, wait_for_continuations, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction
        self.stored_interaction_finished_callback = None
        self.stand_slot_reservation_removed_callback = None
        self._wait_for_continuations = wait_for_continuations

    def release(self):
        if self.stored_interaction_finished_callback is not None:
            self.stored_interaction_finished_callback(self._interaction)
        if self._interaction.affordance in self._wait_for_continuations and self.stand_slot_reservation_removed_callback is not None:
            self._interaction.sim.routing_component.stand_slot_reservation_removed_callbacks.unregister(self._stand_slot_released_callback)

    def transfer(self, interaction):
        current_target = self._interaction.target
        if interaction.target is not current_target and current_target.has_component(WAITING_LINE_COMPONENT):
            chosen_destinations = current_target.waiting_line_component.chosen_destinations
            if current_target in chosen_destinations:
                chosen_destinations.remove(current_target)
        self._interaction = interaction
        if interaction.affordance in self._wait_for_continuations:
            interaction.sim.routing_component.stand_slot_reservation_removed_callbacks.register(self._stand_slot_released_callback)

    def should_transfer(self, continuation):
        return self._interaction.affordance not in self._wait_for_continuations

    def _stand_slot_released_callback(self, sim, interaction):
        if interaction is not self._interaction:
            return
        if self.stand_slot_reservation_removed_callback is not None:
            self.stand_slot_reservation_removed_callback(unregister_callback=False)
        self.stand_slot_reservation_removed_callback = None
        sim.routing_component.stand_slot_reservation_removed_callbacks.unregister(self._stand_slot_released_callback)
