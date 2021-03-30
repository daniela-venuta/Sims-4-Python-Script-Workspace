from event_testing.resolver import SingleSimResolverfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom traits.trait_tracker import TraitPickerSuperInteractionfrom ui.ui_dialog_picker import ObjectPickerRowimport servicesimport sims4logger = sims4.log.Logger('PickCareerByAgentInteraction')
class PickCareerByAgentInteraction(TraitPickerSuperInteraction):
    INSTANCE_TUNABLES = {'pickable_careers': TunableList(description='\n            A list of careers whose available agents will be used to populate\n            the picker. When an available agent is selected, the sim actor will\n            be placed in the associated career. A career may have multiple\n            agents, in which case each will appear and each will correspond to\n            that career.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.CAREER), pack_safe=True), tuning_group=GroupNames.PICKERTUNING, unique_entries=True)}

    @classmethod
    def _get_agent_traits_for_career_gen(cls, sim_info, career):
        career_history = sim_info.career_tracker.career_history
        (entry_level, _, career_track) = career.get_career_entry_level(career_history, SingleSimResolver(sim_info))
        for agent_trait in career_track.career_levels[entry_level].agents_available:
            yield agent_trait

    @classmethod
    def _agent_trait_selection_gen(cls, target):
        for career in cls.pickable_careers:
            if target.sim_info.career_tracker.has_career_by_uid(career.guid64):
                pass
            else:
                career_selectable_result = career.is_career_selectable(sim_info=target.sim_info)
                disabled_tooltip = None
                if not career_selectable_result:
                    if career_selectable_result.tooltip is not None:
                        disabled_tooltip = career_selectable_result.tooltip
                    else:
                        logger.error("{} did not pass career_selectable_tests and doesn't have disabled tooltip.", career, owner='yozhang')
                else:
                    for trait in cls._get_agent_traits_for_career_gen(target.sim_info, career):
                        yield (trait, disabled_tooltip)

    def on_choice_selected(self, choice_tag, **kwargs):
        if choice_tag is None:
            return
        sim_info = self.target.sim_info
        for career in self.pickable_careers:
            if choice_tag in self._get_agent_traits_for_career_gen(sim_info, career):
                sim_info.career_tracker.add_career(career(sim_info), post_quit_msg=False)
                super().on_choice_selected(choice_tag, **kwargs)
                return

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        trait_tracker = target.sim_info.trait_tracker
        for (trait, disabled_tooltip) in cls._agent_trait_selection_gen(target):
            if trait.display_name:
                display_name = trait.display_name(target)
                is_enabled = True
                row_tooltip = None
                if trait_tracker.has_trait(trait):
                    is_enabled = False
                    row_tooltip = None if cls.already_equipped_tooltip is None else lambda *_: cls.already_equipped_tooltip(target)
                else:
                    is_enabled = False
                    row_tooltip = disabled_tooltip
                row = ObjectPickerRow(name=display_name, row_description=trait.trait_description(target), icon=trait.icon, tag=trait, is_enable=is_enabled, row_tooltip=row_tooltip)
                yield row
