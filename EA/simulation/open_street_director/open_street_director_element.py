from interactions.utils.interaction_elements import XevtTriggeredElement
class ManipulateConditionalLayer(XevtTriggeredElement, DirectManipulateConditionalLayer):

    def _do_behavior(self):
        self.change_conditional_layer()
