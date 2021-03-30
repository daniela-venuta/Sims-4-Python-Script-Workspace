import distributorfrom protocolbuffers import Dialog_pb2, Consts_pb2from interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionSourcefrom interactions.priority import Priorityfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.tuning.tunable import TunableReference, TunableList, OptionalTunable, TunableTuplefrom sims4.tuning.tunable_base import GroupNamesfrom ui.ui_dialog import UiDialogOkCancel, ButtonTypefrom ui.ui_text_input import UiTextInputimport servicesimport sims4.resourcesTEXT_INPUT_NEW_NAME = 'new_name'
class UiMultiPicker(UiDialogOkCancel):
    FACTORY_TUNABLES = {'pickers': TunableList(description='\n            A list of picker interactions to use to build pickers.\n            ', tunable=TunableTuple(description='\n            \n                ', picker_interaction=TunableReference(description='\n                    The interaction that will be used to generate a picker.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True), disabled_tooltip=TunableLocalizedString(description='\n                    The string that will be displayed when an item in the \n                    associated picker is not available.\n                    ')), tuning_group=GroupNames.PICKERTUNING), 'text_input': OptionalTunable(description='\n            If enabled then this dialog will also support a text input box.\n            ', tunable=UiTextInput.TunableFactory(description='\n                The tuning for the Text Input part of the dialog.\n                ', locked_args={'sort_order': 1}))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._picker_dialogs = {}
        self._text_listeners = CallableList()
        self.existing_text = None
        self.ingredient_check = None
        self._changes_made = False

    def add_text_listener(self, listener):
        self._text_listeners.append(listener)

    def set_target_sim(self, target_sim):
        self.target_sim = target_sim

    def set_target(self, target):
        self.target = target

    def build_multi_picker_msg(self, picker_data, multi_picker_msg, context):
        aop = AffordanceObjectPair(picker_data.picker_interaction, None, picker_data.picker_interaction, None)
        result = aop.interaction_factory(context)
        if not result:
            return (None, None)
        interaction = result.interaction
        picker_tuning = picker_data.picker_interaction.picker_dialog
        if picker_tuning.title is None:
            title = lambda *_, **__: interaction.get_name(apply_name_modifiers=False)
        else:
            title = self.picker_dialog.title
        dialog = picker_tuning(self._owner(), title=title, resolver=interaction.get_resolver(context=context))
        interaction._setup_dialog(dialog)
        dialog.add_listener(interaction._on_picker_selected)
        self._picker_dialogs[dialog.dialog_id] = dialog
        new_message = dialog.build_msg()
        multi_picker_item = multi_picker_msg.multi_picker_items.add()
        multi_picker_item.picker_data = new_message.picker_data
        multi_picker_item.picker_id = new_message.dialog_id
        multi_picker_item.disabled_tooltip = picker_data.disabled_tooltip
        return (dialog, interaction)

    def build_msg(self, **kwargs):
        message = super().build_msg(**kwargs)
        message.dialog_type = Dialog_pb2.UiDialogMessage.MULTI_PICKER
        if self.text_input is not None:
            (text_name, text) = self.existing_text if self.existing_text else (TEXT_INPUT_NEW_NAME, None)
            text_input_overrides = {}
            if text:
                text_input_overrides[text_name] = lambda *_, **__: LocalizationHelperTuning.get_raw_text(text)
            self.text_input.build_msg(self, message, name=text_name, text_input_overrides=text_input_overrides if text_input_overrides else None)
        context = InteractionContext(self._owner(), InteractionSource.SCRIPT, Priority.Low)
        multi_picker_msg = Dialog_pb2.UiDialogMultiPicker()
        for picker_data in self.pickers:
            self.build_multi_picker_msg(picker_data, multi_picker_msg, context)
        message.multi_picker_data = multi_picker_msg
        return message

    def on_text_input(self, text_input_name='', text_input=''):
        self._text_listeners(self, text_input_name, text_input)
        return True

    @property
    def multi_select(self):
        return False

    def multi_picker_result(self, response_proto):
        for picker_result in response_proto.picker_responses:
            if picker_result.picker_id in self._picker_dialogs:
                dialog = self._picker_dialogs[picker_result.picker_id]
                if self._check_for_changes(dialog, picker_result.choices):
                    self._changes_made = True
                dialog.pick_results(picker_result.choices)
                dialog.respond(ButtonType.DIALOG_RESPONSE_OK)
        if self.existing_text[1] != response_proto.text_input:
            self._changes_made = True
        self.on_text_input(text_input=response_proto.text_input)

    def _check_for_changes(self, dialog, choices):
        for (index, row) in enumerate(dialog.picker_rows):
            if row.is_selected is not index in choices:
                return True
        return False

    def get_single_result_tag(self):
        if self.response == ButtonType.DIALOG_RESPONSE_OK and self._changes_made:
            return True
        return False

    def get_result_tags(self):
        if self.response == ButtonType.DIALOG_RESPONSE_OK and self._changes_made:
            return True
        return False

class UiCustomizeObjectMultiPicker(UiMultiPicker):
    FACTORY_TUNABLES = {'customize_object_pickers': TunableTuple(description='\n            A list of picker interactions to use to build pickers.\n            ', def_picker=TunableTuple(description='\n                A definition picker for players to select a definition ID and\n                send to gameplay.\n                ', picker_interaction=TunableReference(description='\n                    The interaction that will be used to generate a picker.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), disabled_tooltip=TunableLocalizedString(description='\n                    The string that will be displayed when an item in the \n                    associated picker is not available.\n                    ')), geo_mat_picker=TunableTuple(description='\n                A geometry/material picker that will generate a list of final objects\n                using object definition id selected by the player and geo/mat combinations\n                tuned on picker interaction.\n                ', picker_interaction=TunableReference(description='\n                    The interaction that will be used to generate a geometry/material picker.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), disabled_tooltip=TunableLocalizedString(description='\n                    The string that will be displayed when an item in the \n                    associated picker is not available.\n                    ')), tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._def_dialog = None
        self._def_interaction = None
        self._geo_mat_dialog = None
        self._geo_mat_interaction = None
        self.customized_obj_info = None

    def build_msg(self, **kwargs):
        message = super().build_msg(**kwargs)
        message.dialog_type = Dialog_pb2.UiDialogMessage.CUSTOMIZE_OBJECT_MULTI_PICKER
        context = InteractionContext(self._owner(), InteractionSource.SCRIPT, Priority.Low)
        (self._def_dialog, self._def_interaction) = self.build_multi_picker_msg(self.customize_object_pickers.def_picker, message.multi_picker_data, context)
        (self._geo_mat_dialog, self._geo_mat_interaction) = self.build_multi_picker_msg(self.customize_object_pickers.geo_mat_picker, message.multi_picker_data, context)
        return message

    def multi_picker_selection_update(self, response_item_proto):
        if response_item_proto.picker_id != self._def_dialog.dialog_id:
            return
        self._def_dialog.pick_results(response_item_proto.choices)
        obj_def = self._def_dialog.get_single_result_tag()
        if obj_def is None:
            return
        self._geo_mat_interaction.update_dialog(self._geo_mat_dialog, obj_def)
        picker_item_msg = Dialog_pb2.UiDialogMultiPickerItem()
        picker_item_msg.picker_data = self._geo_mat_dialog.build_object_picker()
        picker_item_msg.picker_id = self._geo_mat_dialog.dialog_id
        picker_item_msg.disabled_tooltip = self.customize_object_pickers.geo_mat_picker.disabled_tooltip
        distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_MULTI_PICKER_CONTENT_UPDATE, picker_item_msg)

    def multi_picker_result(self, response_proto):
        super().multi_picker_result(response_proto)
        self.customized_obj_info = self._geo_mat_dialog.get_single_result_tag() + (response_proto.text_input,)
        self._changes_made = True
