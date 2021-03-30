from interactions.utils.interaction_elements import XevtTriggeredElementfrom open_street_director.open_street_conditional_layer_change import DirectManipulateConditionalLayer
class ManipulateConditionalLayer(XevtTriggeredElement, DirectManipulateConditionalLayer):

    def _do_behavior(self):
        self.change_conditional_layer()
