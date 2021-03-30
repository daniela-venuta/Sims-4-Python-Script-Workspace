from collections import defaultdictfrom interactions import ParticipantType, ParticipantTypeSingleSim, ParticipantTypeSingle, ParticipantTypeSavedActorfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import PreparationLiabilityfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects.components.utils.inventory_helpers import transfer_object_to_lot_or_object_inventoryfrom objects.slots import RuntimeSlotfrom sims4.tuning.tunable import TunableVariant, TunableEnumEntry, TunableReference, Tunable, TunableList, TunableTuple, HasTunableFactory, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunablefrom singletons import EMPTY_SETfrom sims.sim_dialogs import SimPersonalityAssignmentDialogimport itertoolsimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Parent Object Elements')
def parent_object(child_object, parent_object, slot_type=None, bone_name_hash=None, ignore_object_placmenent_verification=False):
    current_child_object_parent_slot = child_object.parent_slot
    if slot_type is not None:
        for runtime_slot in parent_object.get_runtime_slots_gen(slot_types={slot_type}):
            if runtime_slot == current_child_object_parent_slot:
                return True
            result = runtime_slot.is_valid_for_placement(obj=child_object)
            if ignore_object_placmenent_verification or result:
                runtime_slot.add_child(child_object)
                return True
            logger.warn("runtime_slot isn't valid for placement: {}", result, owner='nbaker')
        logger.error('The parent object: ({}) does not have the requested slot type: ({}) required for this parenting, or the child ({}) is not valid for this slot type.', parent_object, slot_type, child_object, owner='nbaker')
    elif bone_name_hash is not None:
        if parent_object.has_slot(bone_name_hash):
            if current_child_object_parent_slot is not None and current_child_object_parent_slot.slot_name_hash == bone_name_hash:
                return True
            runtime_slot = RuntimeSlot(parent_object, bone_name_hash, EMPTY_SET)
            if ignore_object_placmenent_verification or runtime_slot.empty:
                runtime_slot.add_child(child_object, joint_name_or_hash=bone_name_hash)
                return True
            else:
                logger.error('The parent object: ({}) does not have the requested slot type: ({}) required for this parenting, or the child ({}) is not valid for this slot type.  Slot is empty: {}', parent_object, bone_name_hash, child_object, runtime_slot.empty, owner='nbaker')
        try:
            child_object.set_parent(parent_object, joint_name_or_hash=bone_name_hash)
        except (ValueError, KeyError):
            logger.error('Error setting the location of ({}) to be a child of ({}) by referencing bone-name ({})', child_object, parent_object, bone_name_hash, owner='shipark')
        return True
    return False

class ParentObjectElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'description': "\n            This element parents one participant of an interaction to another in\n            a way that doesn't necessarily depend on animation.  Most parenting\n            should be handled by animation or the posture transition system, so\n            make sure you know why you aren't using one of those systems for\n            your feature before tuning this.\n        \n            Examples include positioning objects that move but aren't carryable by\n            Sims (like the canvas on the easel) or objects that should be positioned\n            as a result of an immediate interaction.\n            ", '_parent_object': TunableEnumEntry(description='\n            The participant of an interaction to which an object will be\n            parented.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), '_check_part_owner': Tunable(description='\n            If enabled and parent object is a part, the test will be run on\n            the part owner instead.\n            ', tunable_type=bool, default=False), '_parent_slot': TunableVariant(description='\n            The slot on the parent object where the child object should go. This\n            may be either the exact name of a bone on the parent object or a\n            slot type, in which case the first empty slot of the specified type\n            in which the child object fits will be used.\n            ', by_name=Tunable(description="\n                The exact name of a slot on the parent object in which the child\n                object should go.  No placement validation will be done on this\n                slot, as long as it is empty the child will always be placed\n                there.  This should only be used on slots the player isn't\n                allowed to use in build mode, as in the original design for the\n                service slots on the bar, or by GPEs testing out functionality\n                before modelers and designers have settled on slot types and\n                names for a particular design.\n                ", tunable_type=str, default='_ctnm_'), by_reference=TunableReference(description='\n                A particular slot type in which the child object should go.  The\n                first empty slot found on the parent of the specified type in\n                which the child object fits will be used.  If no such slot is\n                found, the parenting will not occur and the interaction will be\n                canceled.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))), '_child_object': TunableEnumEntry(description='\n            The participant of the interaction which will be parented to the\n            parent object.\n            ', tunable_type=ParticipantType, default=ParticipantType.CarriedObject)}

    def __init__(self, interaction, get_child_object_fn=None, ignore_object_placmenent_verification=False, **kwargs):
        super().__init__(interaction, **kwargs)
        _parent_object = kwargs['_parent_object']
        _parent_slot = kwargs['_parent_slot']
        _child_object = kwargs['_child_object']
        self._child_object = None
        self._parent_object = interaction.get_participant(_parent_object)
        self._ignore_object_placmenent_verification = ignore_object_placmenent_verification
        if self._parent_object.is_part:
            self._parent_object = self._parent_object.part_owner
        self.child_participant_type = _child_object
        if self._check_part_owner and get_child_object_fn is None:
            self._child_participant_type = _child_object
        else:
            self._get_child_object = get_child_object_fn
        if isinstance(_parent_slot, str):
            self._slot_type = None
            self._bone_name_hash = sims4.hash_util.hash32(_parent_slot)
        else:
            self._slot_type = _parent_slot
            self._bone_name_hash = None

    def _parent_object_fn(self):
        result = parent_object(self._child_object, self._parent_object, slot_type=self._slot_type, bone_name_hash=self._bone_name_hash, ignore_object_placmenent_verification=self._ignore_object_placmenent_verification)
        if not result:
            logger.error('Failed to parent object {} to {} with Parent Object Element run from {}.', self._child_object, self._parent_object, self.interaction)
        return result

    def _get_child_object(self):
        self._child_object = self.interaction.get_participant(self._child_participant_type)
        return self._child_object

    def _do_behavior(self):
        self._child_object = self._get_child_object()
        if self._child_object is None:
            logger.error('Child object is None and cannot be parented to: ({}). Parent action failed.', self._parent_object)
            return False
        return self._parent_object_fn()

class ParentObjectWithRoutingFormationSlave(ParentObjectElement):
    FACTORY_TUNABLES = {'description': '\n            This will handle cancelling the interaction running the routing formation liability\n            and parenting the routing formation slave to the tuned parent object.\n\n            Note: This assumes the routing formation is tied to an interaction,\n            which should always be the case.\n            ', 'object_states': TunableList(description='\n            List of object states set on the routing slave after exiting the owning interaction. \n            ', tunable=TunableReference(description='\n                Object state set on the routing slave.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), pack_safe=True)), 'idle_animation_object_state_delay': OptionalTunable(description="\n            If tuned, delay parenting to after the child object's idle component finishes\n            the animation triggered by the tuned object state.\n            \n            This is preferable when the object has a long animation transition between its initial\n            state and its state value after it's parented.\n             Example: the party bot needs to complete the transition : {hover -> grounded} before it is parented.\n            ", tunable=TunableReference(description="\n                Object state value mapped in the child's idle component.\n                ", manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), pack_safe=True)), 'locked_args': {'_child_object': ParticipantType.RoutingSlaves}}

    def schedule_parent_in_idle_component(self, object_state):
        child_idle_component = self._child_object.idle_component
        if child_idle_component is None or object_state not in child_idle_component.idle_animation_map:
            logger.error('Attempting to time parent behavior after setting an idle anim state                         on {}, but there is no Idle Animation Component.', self._child_object)
            return False
        child_idle_component.add_scheduled_after_callback(object_state, self._parent_object_fn)
        self.interaction.register_on_finishing_callback(lambda _: child_idle_component.remove_scheduled_after_callback(object_state, self._parent_object_fn))
        return True

    def _trigger_states(self):
        for object_state in self.object_states:
            if object_state is None:
                pass
            else:
                self._child_object.set_state(object_state.state, object_state)

    def _cancel_routing_formations(self, actor_routing_component):
        for rf_data in actor_routing_component.get_all_routing_slave_data_gen():
            rf_data.release_formation_data()
            route_interaction = rf_data.interaction
            result = route_interaction.cancel(FinishingType.KILLED, cancel_reason_msg='Routing formation cancelled by Parent Object With Routing Slave element.')
            if not result:
                logger.warn('Routing Interaction running on {} failed to cancel from ParentObjectWithRoutingFormationSlave.', self.interaction)

    def _do_behavior(self):
        self._child_object = self._get_child_object()
        actor = self.interaction.get_participant(ParticipantType.Actor)
        actor_routing_component = actor.routing_component
        if actor_routing_component is None:
            logger.error('Actor {} running interaction with Parent Object With Routing Formation                                  Slave does not have a routing component.', actor)
        self._cancel_routing_formations(actor_routing_component)
        self._trigger_states()
        should_parent_immediately = True
        if self.idle_animation_object_state_delay:
            result = self.schedule_parent_in_idle_component(self.idle_animation_object_state_delay)
            if result:
                should_parent_immediately = False
        if not should_parent_immediately:
            return True
        return self._parent_object_fn()
