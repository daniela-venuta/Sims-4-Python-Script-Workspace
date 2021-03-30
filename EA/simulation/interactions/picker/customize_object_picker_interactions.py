import servicesimport sims4.hash_utilfrom distributor.shared_messages import IconInfoDatafrom interactions.base.picker_interaction import PickerSuperInteractionfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import TunableList, TunableReference, TunableMapping, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import flexmethodfrom singletons import UNSETfrom ui.ui_dialog_picker import ObjectPickerRowlogger = sims4.log.Logger('CustomizeObjectMultiPicker', default_owner='yozhang')
class CustomizeObjectDefinitionPicker(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'object_definitions': TunableList(description="\n            A list of object definitions for players to select, player's selection will update geo/mat picker.\n            ", tunable=TunableReference(manager=services.definition_manager(), pack_safe=True), tuning_group=GroupNames.PICKERTUNING), 'object_thumbnail_geo_state_override': OptionalTunable(description='\n            object\'s geometry state shown in this picker. If disabled, thumbnails use default geo state.\n            For example, for droids we tune this to "HeadOnly" so first picker only show droid heads\n            ', tunable=TunableStringHash32(), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for (index, obj_def) in enumerate(inst_or_cls.object_definitions):
            name = LocalizationHelperTuning.get_object_name(obj_def)
            yield ObjectPickerRow(name=name, icon_info=IconInfoData(obj_def_id=obj_def.id, obj_geo_hash=inst_or_cls.object_thumbnail_geo_state_override), tag=obj_def, is_selected=index == 0)

    def on_choice_selected(self, choice_tag, **kwargs):
        pass

class CustomizeObjectGeoMatPicker(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'geo_mat_combinations': TunableMapping(description='\n            A mapping of geometry state to a list of material states. So we can\n            use them to generate a list of different objects which have one object\n            definition id and different geometry and material states.\n            ', key_name='geometry_state', key_type=TunableReference(description='\n                An object state that has geometry state to apply.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), value_name='material_state_list', value_type=TunableList(tunable=TunableReference(description='\n                    An object state that has material state to apply.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue')), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _verify_tuning_callback(cls):
        for (geo_stat, mat_states) in cls.geo_mat_combinations.items():
            geo_op = geo_stat.new_client_state.ops['geometry_state']
            if geo_op is None or geo_op is UNSET:
                logger.error("object state ({}) doesn't set geometry_state client op.\n{}", geo_stat, cls)
            for mat_state in mat_states:
                mat_op = mat_state.new_client_state.ops['material_state']
                if not mat_op is None:
                    if mat_op is UNSET:
                        logger.error("object state ({}) doesn't set material_state client op\n{}", mat_state, cls)
                logger.error("object state ({}) doesn't set material_state client op\n{}", mat_state, cls)

    def _setup_dialog(self, dialog, **kwargs):
        pass

    def update_dialog(self, dialog, obj_def):
        dialog.picker_rows.clear()
        for row in self.picker_rows_gen(self.target, self.context, obj_def):
            dialog.add_row(row)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, obj_def, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        name = LocalizationHelperTuning.get_object_name(obj_def)
        for (geo_stat, mat_states) in inst_or_cls.geo_mat_combinations.items():
            for mat_state in mat_states:
                yield ObjectPickerRow(name=name, icon_info=IconInfoData(obj_def_id=obj_def.id, obj_geo_hash=sims4.hash_util.hash32(geo_stat.new_client_state.ops['geometry_state']), obj_material_hash=mat_state.new_client_state.ops['material_state'].state_name_hash), tag=(obj_def, geo_stat, mat_state))

    def on_choice_selected(self, choice_tag, **kwargs):
        pass
