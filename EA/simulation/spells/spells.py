import services
class Spell(_SpellDisplayMixin, SuperAffordanceProviderMixin, TargetSuperAffordanceProviderMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.SPELL)):
    INSTANCE_TUNABLES = {'locked_description': OptionalTunable(description='\n            Description used in the spellbook if spell is not yet unlocked.\n            If unset, uses display data description.\n            ', tunable=TunableLocalizedString(), tuning_group=GroupNames.UI), 'ingredients': ItemCost.TunableFactory(description='\n            Ingredients needed to cast the spell.  Interactions which specify this spell as the item cost will consume \n            the ingredients specified here.\n            '), 'tags': TunableSet(description='\n            Tags for the spell.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['spell'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True, binary_type=EnumBinaryExportType.EnumUint32), export_modes=ExportModes.All, tuning_group=GroupNames.TAG)}

    @classmethod
    def get_display_name(cls, *_):
        return cls.display_name

    @classproperty
    def unlock_as_new(cls):
        return True

    @classproperty
    def tuning_tags(cls):
        return cls.tags
