import sims4from animation import get_throwaway_animation_context, animation_constantsfrom animation.arb import Arbfrom animation.asm import create_asmfrom routing.portals.build_ladders_mixin import _BuildLaddersMixinfrom routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_enums import PortalAlignmentfrom routing.portals.portal_location import _PortalBoneLocationfrom routing.portals.portal_tuning import PortalTypefrom routing.portals.variable_jump_mixin import _VariableJumpMixinlogger = sims4.log.Logger('BuildLaddersSlidePortalData', default_owner='bnguyen')
class _PortalTypeDataBuildLaddersSlide(_PortalTypeDataBase, _BuildLaddersMixin, _VariableJumpMixin):
    FACTORY_TUNABLES = {'slide_end_location': _PortalBoneLocation.TunableFactory(description='\n            The bone location where the slide portion of the animation ends.\n            This should be different than the portal exit location.\n            ')}

    @property
    def portal_type(self):
        return PortalType.PortalType_Animate

    @property
    def requires_los_between_points(self):
        return False

    @property
    def lock_portal_on_use(self):
        return False

    def add_portal_data(self, actor, portal_instance, is_mirrored, walkstyle):
        return self._add_variable_jump_portal_data(actor, portal_instance, is_mirrored, walkstyle)

    def get_portal_duration(self, portal_instance, is_mirrored, walkstyle, age, gender, species):
        return self._get_variable_jump_portal_duration(portal_instance, is_mirrored, species)

    def get_portal_locations(self, obj):
        return self._get_ladder_portal_locations(obj)

    def _get_arb(self, actor, portal_instance, *, is_mirrored):
        arb = Arb()
        asm = create_asm(self.animation_element.asm_key, context=get_throwaway_animation_context())
        asm.set_actor(self.animation_element.actor_name, actor)
        slide_end_location = self.slide_end_location(portal_instance.obj)
        if is_mirrored:
            entry_location = slide_end_location
            exit_location = portal_instance.back_exit
        else:
            entry_location = portal_instance.there_entry
            exit_location = slide_end_location
        initial_translation = sims4.math.Vector3(exit_location.position.x, entry_location.position.y, exit_location.position.z)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_INITIAL_TRANSLATION, initial_translation)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_INITIAL_ORIENTATION, entry_location.orientation)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_TARGET_TRANSLATION, exit_location.position)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_TARGET_ORIENTATION, exit_location.orientation)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_LADDER_PORTAL_ALIGNMENT, PortalAlignment.get_asm_parameter_string(self.portal_alignment))
        self.animation_element.append_to_arb(asm, arb)
        return arb
