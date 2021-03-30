import posturesfrom collections import OrderedDictimport copyfrom animation.tunable_animation_overrides import TunableAnimationOverridesfrom objects.components.state import TunableStateValueReferencefrom objects.part import ObjectPartfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableList, OptionalTunable, Tunable, TunableMapping, TunableEnumEntry, TunableRangefrom sims4.tuning.tunable_base import TunableBaseimport sims4.loglogger = sims4.log.Logger('Parts')
class _PartData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'part_definition': ObjectPart.TunableReference(description='\n            The part definition associated with this part instance.\n            \n            The part definition defines supported postures and interactions,\n            disallowed buffs and portal data.\n            ', pack_safe=True), 'disabling_states': TunableList(description='\n            A list of state values which, if active on this object, will\n            disable this part.\n            ', tunable=TunableStateValueReference(pack_safe=True)), 'disabling_model_suite_indices': TunableList(description='\n            A list of model suite "state indices" which, if active on\n            this object, will disable this part.\n            ', tunable=TunableRange(tunable_type=int, default=0, minimum=0)), 'adjacent_parts': TunableList(description='\n            The parts that are adjacent to this part. You must reference a part\n            that is tuned in this mapping.\n            \n            An empty list indicates that no part is adjacent to this part.\n            ', tunable=Tunable(tunable_type=str, default=None), unique_entries=True), 'overlapping_parts': TunableList(description='\n            The parts that are unusable when this part is in use. You must\n            reference a part that is tuned in this mapping.\n            ', tunable=Tunable(tunable_type=str, default=None), unique_entries=True), 'subroot_index': OptionalTunable(description='\n            If enabled, this part will have a subroot index associated with it.\n            This will affect the way Sims animate, i.e. they will animate\n            relative to the position of the part, not relative to the object.\n            ', tunable=Tunable(description='\n                The subroot suffix associated with this part.\n                ', tunable_type=int, default=0, needs_tuning=False), enabled_by_default=True), 'anim_overrides': TunableAnimationOverrides(description='\n            Animation overrides for this part.\n            '), 'is_mirrored': OptionalTunable(description='\n            Specify whether or not solo animations played on this part\n            should be mirrored or not.\n            ', tunable=Tunable(description='\n                If checked, mirroring is enabled. If unchecked,\n                mirroring is disabled.\n                ', tunable_type=bool, default=False)), 'forward_direction_for_picking': TunableVector2(description="\n            When you click on the object this part belongs to, this offset will\n            be applied to this part when determining which part is closest to\n            where you clicked.\n            \n            By default, the object's forward vector will be used. It should only\n            be necessary to tune this value if multiple parts overlap at the\n            same location (e.g. the single bed).\n            ", default=TunableVector2.DEFAULT_Z, x_axis_name='x', y_axis_name='z'), 'disable_sim_aop_forwarding': Tunable(description='\n            If checked, Sims using this specific part will never forward\n            AOPs.\n            ', tunable_type=bool, default=False), 'disable_child_aop_forwarding': Tunable(description='\n            If checked, objects parented to this specific part will\n            never forward AOPs.\n            ', tunable_type=bool, default=False), 'restrict_autonomy_preference': Tunable(description='\n            If checked, this specific part can be used for use only autonomy preference\n            restriction.\n            ', tunable_type=bool, default=False), 'name': OptionalTunable(description='\n            Name of this part.  For use if the part name needs to be surfaced\n            to the player.  (i.e. when assigning sim to specific side of bed.)\n            ', tunable=TunableLocalizedString()), 'posture_transition_target_tag': OptionalTunable(description='\n            If enabled, a tag to apply to this part so that it is taken into\n            account for posture transition preference scoring.  For example, \n            you could tune this part to be a DINING_SURFACE.  Any SI that is \n            set up to have posture preference scoring can override the score \n            for any objects/parts that are tagged with DINING_SURFACE.\n    \n            For a more detailed description of how posture preference scoring\n            works, see the posture_target_preference tunable field description\n            in SuperInteraction.\n            ', tunable=TunableEnumEntry(tunable_type=postures.PostureTransitionTargetPreferenceTag, default=postures.PostureTransitionTargetPreferenceTag.INVALID))}

class TunablePartDataMapping(TunableMapping):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, key_type=Tunable(description='\n                A unique, arbitrary identifier for this part. Use this to define\n                adjacent and overlapping parts.\n                ', tunable_type=str, default=None), value_type=_PartData.TunableFactory(), **kwargs)

    @property
    def export_class(self):
        return 'TunableMapping'

    def load_etree_node(self, node, source, expect_error):
        value = super().load_etree_node(node, source, expect_error)
        value = OrderedDict(sorted(value.items()))
        index_map = {k: i for (i, k) in enumerate(value)}
        values = []
        for (k, v) in value.items():
            v = copy.copy(v)
            adjacent_parts = tuple(index_map[i] for i in v.adjacent_parts if i in index_map)
            setattr(v, 'adjacent_parts', adjacent_parts)
            overlapping_parts = tuple(index_map[i] for i in v.overlapping_parts if i in index_map)
            setattr(v, 'overlapping_parts', overlapping_parts)
            values.append(v)
        return tuple(values)

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        TunableBase.invoke_callback(self, instance_class, tunable_name, source, value)
        if value is not None:
            template = self._template.tunable_items['value']
            for tuned_value in value:
                template.invoke_callback(instance_class, tunable_name, source, tuned_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        TunableBase.invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value)
        if value is not None:
            template = self._template.tunable_items['value']
            for tuned_value in value:
                template.invoke_verify_tunable_callback(instance_class, tunable_name, source, tuned_value)
