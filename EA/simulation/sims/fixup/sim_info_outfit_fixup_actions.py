from sims.fixup.sim_info_fixup_action import _SimInfoFixupActionfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.outfits.outfit_generator import TunableOutfitGeneratorSnippet, OutfitGeneratorfrom sims4.tuning.tunable import TunableEnumEntry, Tunable
class _SimInfoOutfitTransferFixupAction(_SimInfoFixupAction):
    FACTORY_TUNABLES = {'source_outfit_category': TunableEnumEntry(description='\n            ', tunable_type=OutfitCategory, default=OutfitCategory.SITUATION, invalid_enums=(OutfitCategory.CURRENT_OUTFIT,)), 'destination_outfit_category': TunableEnumEntry(description='\n            ', tunable_type=OutfitCategory, default=OutfitCategory.CAREER, invalid_enums=(OutfitCategory.CURRENT_OUTFIT, OutfitCategory.SPECIAL)), 'set_destination_outfit': Tunable(description='\n            Whether to immediately set the destination outfit upon add to household.\n            ', tunable_type=bool, default=False)}

    def __call__(self, sim_info):
        destination_outfit = (self.destination_outfit_category, 0)
        sim_info.generate_merged_outfit(sim_info, destination_outfit, sim_info.get_current_outfit(), (self.source_outfit_category, 0), preserve_outfit_flags=True)
        if self.set_destination_outfit:
            sim_info.set_current_outfit(destination_outfit)

class _SimInfoRandomizeOutfitFixupAction(_SimInfoFixupAction):
    FACTORY_TUNABLES = {'outfit_to_randomize': TunableEnumEntry(description='\n            ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY, invalid_enums=(OutfitCategory.CURRENT_OUTFIT, OutfitCategory.SPECIAL)), 'generator': TunableOutfitGeneratorSnippet()}

    def __call__(self, sim_info):
        OutfitGenerator.generate_outfit(self, sim_info, self.outfit_to_randomize)
