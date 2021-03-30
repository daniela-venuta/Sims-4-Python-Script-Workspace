import servicesimport sims4.logimport singletonsfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, TunableReference, TunableFactorylogger = sims4.log.Logger('SetRoutingInfoAndStateOp', default_owner='yozhang')
class SetRoutingInfoAndStateOp(BaseLootOperation):
    FACTORY_TUNABLES = {'routing_target': OptionalTunable(description='\n            The routing target we want to set for the subject, we expect this subject to route\n            to this target.\n            If disabled, we are not setting routing target for the subject.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), enabled_by_default=True), 'routing_owner': OptionalTunable(description='\n            The routing owner we want to set for the subject, so the subject can have ability\n            to route back to the owner.\n            If disabled, we are not setting routing owner for the subject.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), enabled_by_default=True), 'routing_state_to_change': OptionalTunable(description='\n            The routing state we are setting on the subject. So its routing component will use\n            state-behavior map to change routing behavior.\n            If disabled, we are not setting routing state on the subject.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), enabled_by_default=True)}

    def __init__(self, routing_target, routing_owner, routing_state_to_change, **kwargs):
        super().__init__(**kwargs)
        self._routing_target = routing_target
        self._routing_owner = routing_owner
        self._routing_state_to_change = routing_state_to_change

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to set routing info and state to a none object. participant {}. Loot: {}', self.subject, self, owner='yozhang')
            return
        target = resolver.get_participant(self._routing_target) if self._routing_target else None
        owner = resolver.get_participant(self._routing_owner) if self._routing_owner else None
        if subject is not None:
            routing_component = subject.routing_component
            if routing_component is not None:
                if target:
                    routing_component.set_routing_target(target)
                if owner:
                    routing_component.set_routing_owner(owner)
                if self._routing_state_to_change:
                    subject.set_state(self._routing_state_to_change.state, self._routing_state_to_change, force_update=True)
            else:
                logger.error("Trying to run a SetRoutingInfoAndStateOp action with a subject that doesn't have routing component.\nLoot Action: {}\nSubject: {}", self, self.subject, owner='yozhang')

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        if description is singletons.DEFAULT:
            description = 'The object we are setting routing info and state for.'
        return BaseLootOperation.get_participant_tunable(*('subject',), description=description, default_participant=ParticipantType.Object, **kwargs)
