import servicesfrom event_testing.tests import TunableTestSetfrom interactions.interaction_finisher import FinishingTypefrom interactions import ParticipantTypefrom objects import HiddenReasonFlag, ALL_HIDDEN_REASONSfrom sims.daycare import DaycareLiabilityimport placementimport sims4from sims4.tuning.tunable import Tunable, TunableReference, TunableMappinglogger = sims4.log.Logger('HideSimLiability')HIDE_SIM_LIABILTIY = 'HideSimLiability'
class HideSimLiability(DaycareLiability):
    LIABILITY_TOKEN = HIDE_SIM_LIABILTIY
    ROUTING_SLAVE_ENTRY_STATE = TunableMapping(description='\n        Possible states to set on the routing slave on entry. The state is set if\n        its tuned tests pass. The first state with tests that pass will be set.\n        ', key_type=TunableReference(description='\n            The state that the routing slave will be put into when their owner is hidden.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True), key_name='Routing Slave Entry State', value_type=TunableTestSet(description='\n            The result of the tests determines if this state is set.\n            '))
    ROUTING_SLAVE_EXIT_STATE = TunableMapping(description='\n        Possible states to set on the routing slave on entry. The state is set if\n        its tuned tests pass. The first state with tests that pass will be set.\n        ', key_type=TunableReference(description='\n            The state that the routing slave will be put into when their owner is unhidden.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True), key_name='Routing Slave Exit State', value_type=TunableTestSet(description='\n            The result of the tests determines if this state is set.\n            '))
    FACTORY_TUNABLES = {'should_transfer_liabilities': Tunable(description='\n            True if the liability should transfer to continuations, False otherwise.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, should_transfer_liabilities=False, **kwargs):
        super().__init__(*args, should_transfer_liabilities=should_transfer_liabilities, **kwargs)
        self._interaction = None
        self._has_hidden = False

    def should_transfer(self, continuation):
        return self.should_transfer_liabilities

    def transfer(self, new_interaction):
        super().transfer(new_interaction)
        old_routing_slave_participants_set = self._interaction.get_participants(ParticipantType.RoutingSlaves)
        new_routing_slave_participants_set = new_interaction.get_participants(ParticipantType.RoutingSlaves)
        if old_routing_slave_participants_set != new_routing_slave_participants_set:
            logger.error("Mismatch between interaction: {}'s routing slave participants and interaction: {}'s routing slave participants.", self._interaction, new_interaction)
        self._interaction = new_interaction

    def on_add(self, interaction):
        super().on_add(interaction)
        self._interaction = interaction
        for sim_info in self._sim_infos:
            sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is not None:
                sim.ignore_blocking_near_destination = True
            familiar_tracker = sim_info.familiar_tracker
            if familiar_tracker is not None:
                familiar = familiar_tracker.get_active_familiar()
                if familiar is not None and not familiar.is_sim:
                    familiar.ignore_blocking_near_destination = True

    def get_sims(self, sim):
        if not self._carried_sim_infos:
            self._update_carried_participants()
        carried_sims = tuple(carried_sim_info.get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE) for carried_sim_info in self._carried_sim_infos.get(sim.sim_info, ()))
        return tuple(carried_sim for carried_sim in carried_sims if carried_sim is not None) + (sim,)

    def on_run(self):
        for sim_info in self._sim_infos:
            sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is None:
                return
            sims_to_hide = self.get_sims(sim)
            for sim in sims_to_hide:
                sim.fade_out()
                sim.hide(HiddenReasonFlag.RABBIT_HOLE)
                sim.client.selectable_sims.notify_dirty()
            valid_sims = (self._interaction.sim, self._interaction.target) + sims_to_hide
            for interaction in tuple(sim.interaction_refs):
                if interaction not in sim.interaction_refs:
                    pass
                elif interaction.sim in valid_sims:
                    pass
                else:
                    interaction.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Target Sim was hidden by the HideSimLiability')
            for sim in sims_to_hide:
                sim.remove_location_from_quadtree(placement.ItemType.SIM_POSITION)
                sim.remove_location_from_quadtree(placement.ItemType.SIM_INTENDED_POSITION)
            for routing_slave in self._interaction.get_participants(ParticipantType.RoutingSlaves):
                for (state_value, tests) in self.ROUTING_SLAVE_ENTRY_STATE.items():
                    if state_value is not None and tests.run_tests(resolver=self._interaction.get_resolver()):
                        routing_slave.set_state(state_value.state, state_value)
                        break
                routing_slave.fade_out()
                routing_slave.hide(HiddenReasonFlag.RABBIT_HOLE)
                routing_slave.remove_location_from_quadtree(placement.ItemType.SIM_POSITION)
                routing_slave.remove_location_from_quadtree(placement.ItemType.SIM_INTENDED_POSITION)
            self._has_hidden = True
        super().on_run()

    def release(self):
        if not self._has_hidden:
            return
        for sim_info in self._sim_infos:
            sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is None:
                return
            for sim in self.get_sims(sim):
                sim.show(HiddenReasonFlag.RABBIT_HOLE)
                sim.client.selectable_sims.notify_dirty()
                sim.add_location_to_quadtree(placement.ItemType.SIM_POSITION)
                sim.fade_in()
            for routing_slave in self._interaction.get_participants(ParticipantType.RoutingSlaves):
                routing_slave.show(HiddenReasonFlag.RABBIT_HOLE)
                routing_slave.add_location_to_quadtree(placement.ItemType.SIM_POSITION)
                routing_slave.ignore_blocking_near_destination = False
                for (state_value, tests) in self.ROUTING_SLAVE_EXIT_STATE.items():
                    if state_value is not None and tests.run_tests(resolver=self._interaction.get_resolver()):
                        routing_slave.set_state(state_value.state, state_value)
                        break
                routing_slave.fade_in()
            self._has_hidden = False
            sim.ignore_blocking_near_destination = False
        super().release()
