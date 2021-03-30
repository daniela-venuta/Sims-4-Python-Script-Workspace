from buffs.appearance_modifier.appearance_modifier import AppearanceModifier, AppearanceModifierPriorityfrom sims.fixup.sim_info_fixup_action import _SimInfoFixupActionfrom sims4.tuning.tunable import TunableList, TunableCasPart, Tunablefrom cas.cas import OutfitOverrideOptionFlags
class _SimInfoAppearanceFixupAction(_SimInfoFixupAction):
    FACTORY_TUNABLES = {'cas_parts_add': TunableList(description='\n            All CAS parts in this list will be applied to the sim permanently.\n            ', tunable=TunableCasPart()), 'apply_to_all_outfits': Tunable(description='\n            If checked, the appearance modifiers will be applied to all outfits,\n            otherwise they will only be applied to the current outfit.\n            ', tunable_type=bool, default=True)}

    def __call__(self, sim_info):
        modifiers = []
        for cas_part in self.cas_parts_add:
            modifier = AppearanceModifier.SetCASPart(cas_part=cas_part, should_toggle=False, replace_with_random=False, update_genetics=True, _is_combinable_with_same_type=True, remove_conflicting=False, outfit_type_compatibility=None, appearance_modifier_tag=None, expect_invalid_parts=False)
            modifiers.append(modifier)
        sim_info.appearance_tracker.apply_permanent_appearance_modifiers(modifiers, self.fixup_guid, AppearanceModifierPriority.INVALID, self.apply_to_all_outfits, OutfitOverrideOptionFlags.DEFAULT)
