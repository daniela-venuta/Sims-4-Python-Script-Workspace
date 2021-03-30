import servicesimport sims4from animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom event_testing.resolver import SingleObjectResolverfrom interactions import ParticipantTypefrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import TunableEnumEntry, TunableList, TunableTuple, TunableReferencefrom tunable_multiplier import TunableMultiplierlogger = sims4.log.Logger('AnimationXevtElement', default_owner='miking')
class AnimationXevtElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant on which to play the animation.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'animations': TunableList(description='\n            A tunable list of weighted animations. When choosing an animation\n            one of the modifiers in this list will be applied. The weight\n            will be used to run a weighted random selection.\n            ', tunable=TunableTuple(description='\n                A Modifier to apply and weight for the weighted random \n                selection.\n                ', animation_element=TunableAnimationReference(description='\n                    The animation to play during the XEvent.\n                    ', callback=None, class_restrictions=()), loots=TunableList(description='\n                    A list of loots applied when this animation is chosen to be \n                    played during an XEvent.\n                    ', tunable=TunableReference(description='\n                        A loot to be applied when this animation is chosen to be \n                        played during an XEvent.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'))), weight=TunableMultiplier.TunableFactory(description='\n                    A weight with testable multipliers that is used to \n                    determine how likely this entry is to be picked when \n                    selecting randomly.\n                    ')))}

    def _choose_animation_element(self, resolver):
        weighted_animations = [(entry.weight.get_multiplier(resolver), (entry.animation_element, entry.loots)) for entry in self.animations]
        if not weighted_animations:
            return
        (animation_element, loots) = weighted_random_item(weighted_animations)
        return (animation_element, loots)

    def _do_behavior(self):
        participant = self.interaction.get_participant(self.participant)
        if participant is None:
            logger.error('Got a None participant trying to run an AnimationXevtElement.')
            return False
        resolver = SingleObjectResolver(participant)
        (animation_element, loots) = self._choose_animation_element(resolver)
        if animation_element is None:
            return False
        animation = animation_element(self.interaction)
        asm = animation.get_asm()
        if asm is None:
            logger.warn('Unable to get a valid ASM for Xevt ({}) for {}.', animation_element, self.interaction)
            return False
        asm.set_actor(animation_element.actor_name, participant)
        arb = Arb()
        animation_element.append_to_arb(asm, arb)
        animation_element.append_exit_to_arb(asm, arb)
        distribute_arb_element(arb)
        resolver = self.interaction.get_resolver()
        for loot in loots:
            loot.apply_to_resolver(resolver)
        return True
