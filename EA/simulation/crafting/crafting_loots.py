from interactions.utils.loot_basic_op import BaseLootOperationfrom objects.components import types
class RefundCraftingProcessLoot(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        subject = resolver.get_participant(self.subject)
        if subject is None:
            return
        crafting_component = subject.get_component(types.CRAFTING_COMPONENT)
        if crafting_component is None:
            return
        crafting_process = crafting_component.get_crafting_process()
        if crafting_process is None:
            return
        crafting_process.refund_payment(explicit=True)
