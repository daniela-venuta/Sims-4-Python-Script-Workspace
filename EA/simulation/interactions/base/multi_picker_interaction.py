from interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.tunable import TunableContinuationfrom sims4.tuning.tunable import OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_multi_picker import UiMultiPickerfrom ui.ui_dialog_notification import UiDialogNotification
class MultiPickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiMultiPicker.TunableFactory(description='\n           Tuning for the ui multi picker. \n           ', tuning_group=GroupNames.PICKERTUNING), 'continuation': OptionalTunable(description="\n            If enabled, you can tune a continuation to be pushed on successfully editing.\n            Do not use PickedObjects or PickedSims as we are not setting those\n            directly.\n            Exception: Customize Object Multi Picker's continuation can use PickedObjects.\n            ", tunable=TunableContinuation(description='\n                If specified, a continuation to push.\n                '), tuning_group=GroupNames.PICKERTUNING), 'success_notification': OptionalTunable(description='\n            When enabled this dialog will be displayed when the multi picker\n            is accepted and has changes new information.\n            ', tunable=UiDialogNotification.TunableFactory(description='\n                The notification that is displayed when a multi picker interaction\n                is accepted with new information.\n                '), tuning_group=GroupNames.PICKERTUNING), 'cancel_continuation': OptionalTunable(description='\n            If enabled, you can tune a continuation to be pushed on cancelling the dialog.\n            Do not use PickedObjects or PickedSims as we are not setting those\n            directly.\n            ', tunable=TunableContinuation(description='\n                If specified, a continuation to push.\n                '), tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picked_item_ids = set()

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        return ()

    def on_choice_selected(self, choice_tag, **kwargs):
        if choice_tag:
            self._handle_successful_editing()
        else:
            self._handle_unsuccessful_editing()

    def on_multi_choice_selected(self, choice_tags, **kwargs):
        if choice_tags:
            self._handle_successful_editing()
        else:
            self._handle_unsuccessful_editing()

    def _push_continuation(self):
        if self.continuation is not None:
            self.push_tunable_continuation(self.continuation)

    def _handle_successful_editing(self):
        if self.picked_item_ids:
            self._push_picked_continuation(self.picked_item_ids)
        else:
            self._push_continuation()
        if self.success_notification is not None:
            resolver = self.get_resolver()
            dialog = self.success_notification(self.sim, resolver)
            dialog.show_dialog()

    def _handle_unsuccessful_editing(self):
        if self.cancel_continuation is not None:
            self.push_tunable_continuation(self.cancel_continuation)

    def _push_picked_continuation(self, picked_item_ids):
        if self.continuation is not None:
            self.interaction_parameters['picked_item_ids'] = picked_item_ids
            self.push_tunable_continuation(self.continuation, picked_item_ids=picked_item_ids)
