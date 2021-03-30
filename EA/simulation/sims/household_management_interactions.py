from event_testing.resolver import DataResolverfrom interactions import ParticipantTypefrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.utils.tested_variant import TunableTestedVariantfrom server_commands.household_commands import trigger_move_in_move_out, household_splitfrom ui.ui_dialog import TunableUiDialogOkCancelSnippetimport event_testing.test_variantsimport services
class MoveInMoveOutSuperInteraction(SuperInteraction):

    def _run_interaction_gen(self, timeline):
        trigger_move_in_move_out()
        return True

class MoveInSuperInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'dialog': TunableTestedVariant(description='\n            The dialog box presented to ask if the player should move their Sims in together.', tunable_type=TunableUiDialogOkCancelSnippet(pack_safe=True), is_noncallable_type=True), 'situation_blacklist': event_testing.test_variants.TunableSituationRunningTest()}

    def _run_interaction_gen(self, timeline):
        services.sim_info_manager().set_default_genealogy()
        resolver = DataResolver(self.sim.sim_info)
        if not resolver(self.situation_blacklist):
            return True
        if not self.target.is_sim:
            return True
        if self.sim.household_id == self.target.household_id:
            return True

        def on_response(dialog):
            if not dialog.accepted:
                self.cancel_user(cancel_reason_msg='Move-In. Player canceled, or move in together dialog timed out from client.')
                return
            actor = self.get_participant(ParticipantType.Actor)
            src_household_id = actor.sim_info.household.id
            target = self.target
            tgt_household_id = target.sim_info.household.id
            if src_household_id is not None and tgt_household_id is not None:
                household_split(src_household_id, tgt_household_id)

        interaction_resolver = self.get_resolver()
        chosen_dialog = self.dialog(resolver=interaction_resolver)
        dialog = chosen_dialog(self.sim, resolver=interaction_resolver)
        dialog.show_dialog(on_response=on_response)
        return True
