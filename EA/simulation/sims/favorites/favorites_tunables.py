import servicesfrom animation.tunable_animation_overrides import TunableAnimationOverridesfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, TunableReference, TunableSet, TunableMapping, TunableList
class FavoriteObjectPropAnimationOverrides(HasTunableSingletonFactory, AutoFactoryInit):

    class _SpecificOverrides(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'anim_overrides': TunableAnimationOverrides(description='\n                Animation overrides to apply if object is selected as a prop.\n                ')}

        def get_overrides(self):
            return self.anim_overrides

    class _FromObjectStateValue(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'state_value': TunableReference(manager=services.get_instance_manager(Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))}

        def get_overrides(self):
            return self.state_value.anim_overrides

    FACTORY_TUNABLES = {'favorite_prop_anim_overrides': TunableVariant(description='\n            Animation overrides to apply.\n            ', specific_overrides=_SpecificOverrides.TunableFactory(), from_object_state_value=_FromObjectStateValue.TunableFactory(), default='specific_overrides')}

    def get_prop_anim_overrides(self):
        return self.favorite_prop_anim_overrides.get_overrides()

class WithObjectDefinitionPropAnimationOverrides(FavoriteObjectPropAnimationOverrides):
    FACTORY_TUNABLES = {'object_definitions': TunableSet(description='\n            A set of object definitions. If any object in this set is used as a \n            favorite, the corresponding Animation Overrides will be applied.\n            ', tunable=TunableReference(description='\n                The definition of the favorite.\n                ', manager=services.definition_manager(), pack_safe=True), minlength=1)}

    def matches(self, obj):
        return obj.definition in self.object_definitions

class WithObjectStatePropAnimationOverrides(FavoriteObjectPropAnimationOverrides):
    FACTORY_TUNABLES = {'object_state_value': TunableReference(description='\n            This override will apply if the object has the associated object state value active.\n            ', manager=services.get_instance_manager(Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True)}

    def matches(self, obj):
        if self.object_state_value:
            return obj.state_value_active(self.object_state_value)
        return False

class FavoriteObjectPropAnimationOverridesVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(matches_definitions=WithObjectDefinitionPropAnimationOverrides.TunableFactory(), matches_state=WithObjectStatePropAnimationOverrides.TunableFactory(), default='matches_definitions')

class FavoritePropAnimationOverrides(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'overrides_by_prop_name': TunableMapping(description='\n            For different props using this object, we will do animation overrides differently.\n            \n            e.g. two Lightsabers in a 2 sim social interaction may have different color VFX overrides\n            for actor x and y depending on what color their favorite Lightsaber is.  \n            ', value_type=TunableList(tunable=FavoriteObjectPropAnimationOverridesVariant()))}

    def get_overrides_for_favorite_object(self, prop_name, obj):
        if prop_name not in self.overrides_by_prop_name:
            return
        fav_obj_anim_overrides = None
        for prop_anim_overrides_data in self.overrides_by_prop_name[prop_name]:
            if prop_anim_overrides_data.matches(obj):
                anim_overrides = prop_anim_overrides_data.get_prop_anim_overrides()
                if anim_overrides is not None:
                    fav_obj_anim_overrides = anim_overrides(fav_obj_anim_overrides)
        return fav_obj_anim_overrides
