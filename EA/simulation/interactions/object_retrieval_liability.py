import build_buyimport enumimport servicesimport sims4from element_utils import build_element, CleanupTypefrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.aop import AffordanceObjectPairfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.context import InteractionContext, QueueInsertStrategy, InteractionBucketTypefrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import PreparationLiabilityfrom interactions.priority import Priorityfrom objects.object_enums import ResetReasonfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, OptionalTunable, TunableReference, TunableEnumEntry, TunableTuple, TunableVariant, HasTunableSingletonFactorylogger = sims4.log.Logger('ObjectRetrievalLiability', default_owner='skorman')
class ObjectRetrievalPhase(enum.Int, export=False):
    PUTTING_DOWN = 1
    USE_AND_RETRIEVE = ...
    PUSHED_RETRIEVAL_AFFORDANCE = ...

class _ObjectRetrievalFallbackBase(HasTunableSingletonFactory):

    def run_fallback(self, actor, obj):
        raise NotImplementedError

class _SendToInventoryFallback(_ObjectRetrievalFallbackBase):

    def run_fallback(self, actor, obj):
        if actor.inventory_component.can_add(obj) and actor.inventory_component.player_try_add_object(obj):
            return
        if not build_buy.move_object_to_household_inventory(actor):
            logger.warn('Failed to move {} to inventory. The object will be destroyed', obj)
            obj.schedule_destroy_asap()

class _DestroyObjectFallback(_ObjectRetrievalFallbackBase):

    def run_fallback(self, actor, obj):
        obj.schedule_destroy_asap()

class ObjectRetrievalLiability(HasTunableFactory, AutoFactoryInit, PreparationLiability):
    LIABILITY_TOKEN = 'ObjectRetrievalLiability'
    FACTORY_TUNABLES = {'put_down_tuning': OptionalTunable(description='\n            If enabled, the liability will push this tuned affordance to place\n            the object before running the owning interaction. \n            ', tunable=TunableTuple(affordance=TunableReference(description='\n                    The affordance to place the object before the owning\n                    interaction runs.\n                    ', manager=services.affordance_manager()), participant=TunableEnumEntry(description='\n                    The target of the put down affordance.\n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object))), 'object_to_retrieve': TunableEnumEntry(description='\n            The target of the retrieval affordance.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'retrieval_affordance': TunableReference(description="\n            The affordance to push after the liability is released to pick up\n            the 'object to retrieve'.\n            ", manager=services.affordance_manager()), 'fallback_behavior': TunableVariant(description='\n            The fallback behavior to use on the retrieval object if the \n            retrieval affordance fails.\n            ', send_to_inventory=_SendToInventoryFallback.TunableFactory(), destroy_object=_DestroyObjectFallback.TunableFactory(), default='send_to_inventory')}

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = interaction
        self._actor = interaction.get_participant(ParticipantType.Actor)
        self._object = interaction.get_participant(self.object_to_retrieve)
        self._phase = ObjectRetrievalPhase.PUTTING_DOWN
        self._pushed_preparation_interactions = []

    def _prepare_gen(self, timeline, *args, **kwargs):
        if self.put_down_tuning is None:
            self._phase = ObjectRetrievalPhase.USE_AND_RETRIEVE
        if self._phase == ObjectRetrievalPhase.PUTTING_DOWN:
            target = self._interaction.get_participant(self.put_down_tuning.participant)
            if target is None:
                cancel_reason = 'ObjectRetrievalLiability: Failed to get participant to put down.'
                self._interaction.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg=cancel_reason)
                return InteractionQueuePreparationStatus.FAILURE
            result = self._push_affordance(self.put_down_tuning.affordance, target)
            if not result:
                cancel_reason = 'ObjectRetrievalLiability: Failed to put down object.'
                self._interaction.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg=cancel_reason)
                return InteractionQueuePreparationStatus.FAILURE
            self._pushed_preparation_interactions.append(result.interaction)
            self._phase = ObjectRetrievalPhase.USE_AND_RETRIEVE
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        self._pushed_preparation_interactions = []
        return InteractionQueuePreparationStatus.SUCCESS

    def release(self):
        if self._object is None or self._object.is_in_inventory():
            if self.put_down_tuning is not None:
                for interaction in self._interaction.sim.get_all_running_and_queued_interactions():
                    if interaction.affordance is self.put_down_tuning.affordance:
                        interaction.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='ObjectRetrievalLiability released.')
            return
        if self._phase < ObjectRetrievalPhase.PUSHED_RETRIEVAL_AFFORDANCE:
            result = self._push_affordance(self.retrieval_affordance, self._object)
            if result:
                retrieval_interaction = result.interaction
                self.transfer(retrieval_interaction)
                retrieval_interaction.add_liability(ObjectRetrievalLiability, self)
                self._phase = ObjectRetrievalPhase.PUSHED_RETRIEVAL_AFFORDANCE
                return
        self._clean_up_object()

    def should_transfer(self, continuation):
        return continuation.affordance is self.retrieval_affordance and self._phase < ObjectRetrievalPhase.PUSHED_RETRIEVAL_AFFORDANCE

    def transfer(self, interaction):
        self._interaction = interaction

    def on_reset(self):
        self._clean_up_object()

    def _push_affordance(self, affordance, target):
        picked_item_ids = self._interaction.interaction_parameters.get('picked_item_ids')
        aop = AffordanceObjectPair(affordance, target, affordance, None, route_fail_on_transition_fail=False, allow_posture_changes=True, picked_item_ids=picked_item_ids)
        context = InteractionContext(self._actor, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST, bucket=InteractionBucketType.DEFAULT)
        return aop.test_and_execute(context)

    def _clean_up_object(self):
        if self._object is None or self._object in self._actor.inventory_component:
            return
        for child_obj in tuple(self._object.children):
            if child_obj.is_sim:
                logger.warn('Trying to clean up object {} that sim {} is using. The sim will be reset.', self._object, child_obj)
                reset_fn = lambda _: child_obj.reset(ResetReason.RESET_EXPECTED, source=self, cause='ObjectRetrievalLiability is cleaning up parent object {}.'.format(self._object))
                element = build_element([reset_fn, lambda _: self._clean_up_object()], critical=CleanupType.OnCancelOrException)
                services.time_service().sim_timeline.schedule(element)
                return
        self.fallback_behavior.run_fallback(self._actor, self._object)

    def path_generation_deferred(self):
        return self._pushed_preparation_interactions
