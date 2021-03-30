from animation.procedural_animation_helpers import control_rotation_lookat, ProceduralAnimationRotationMixinfrom animation.animation_utils import flush_all_animationsfrom animation.object_animation import ObjectAnimationElementfrom element_utils import build_element, build_critical_sectionfrom elements import FunctionElement, SoftSleepElement, OverrideResultElementfrom event_testing.resolver import DoubleObjectResolver, SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions.utils.exit_condition_manager import ConditionalActionManagerfrom interactions.utils.loot import LootActionsfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableRange, TunableSimMinute, TunableList, TunableVariant, TunableTuplefrom statistics.statistic_conditions import TunableStatisticCondition, TunableStateCondition, TunableEventBasedCondition, TunableTimeRangeConditionfrom tag import TunableTagsimport date_and_timeimport element_utilsimport services
class _ObjectRoutingActionAnimation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'reference': ObjectAnimationElement.TunableReference(description='\n            The animation to play.\n            '), 'event_id': OptionalTunable(description='\n            If enabled, loot and actions for this route destination is\n            blocked on this event.\n            ', tunable=TunableRange(tunable_type=int, default=100, minimum=1)), 'loop_time': TunableSimMinute(description='\n            For looping content, how long to idle for. For one-shot content,\n            leave this as zero.\n            ', default=0), 'loop_exit_conditions': TunableList(description='\n            A list of exit conditions to end a looping animation. When exit\n            conditions are met then the looping animation ends.\n            ', tunable=TunableTuple(conditions=TunableList(description='\n                    A list of conditions that all must be satisfied for the\n                    group to be considered satisfied.\n                    ', tunable=TunableVariant(description='\n                        A condition that must be satisfied.\n                        ', stat_based=TunableStatisticCondition(description='\n                            A condition based on the status of a statistic.\n                            '), state_based=TunableStateCondition(description='\n                            A condition based on the state of an object.\n                            '), event_based=TunableEventBasedCondition(description='\n                            A condition based on listening for an event.\n                            '), time_based=TunableTimeRangeCondition(description='\n                            A condition based on a time range.\n                            '), default='time_based')), tests=TunableTestSet(description='\n                    A set of tests. If these tests do not pass, this condition\n                    will not be attached.\n                    ')))}

    def __call__(self, timeline, obj, target, callback=None):
        executed_actions = False
        action_event_handle = None
        sleep_element = None
        _conditional_actions_manager = ConditionalActionManager()

        def _execute_actions(_):
            nonlocal executed_actions
            executed_actions = True
            if sleep_element and sleep_element.attached_to_timeline:
                sleep_element.trigger_soft_stop()
            if callback is not None:
                callback(None)
            if action_event_handle is not None:
                action_event_handle.release()

        if self.event_id is not None:
            animation_context = obj.get_idle_animation_context()
            action_event_handle = animation_context.register_event_handler(_execute_actions, handler_id=self.event_id)
        if self.loop_time > 0:
            sleep_element = OverrideResultElement(SoftSleepElement(date_and_time.create_time_span(minutes=self.loop_time)), True)
            sequence = build_element(sleep_element)
        else:
            sequence = ()
        if self.loop_exit_conditions is not None:
            if target is None:
                exit_condition_test_resolver = SingleObjectResolver(obj)
            else:
                exit_condition_test_resolver = DoubleObjectResolver(obj, target)
            exit_conditions = (exit_condition for exit_condition in self.loop_exit_conditions if exit_condition.tests.run_tests(exit_condition_test_resolver))
            if exit_conditions:
                if not sleep_element:
                    sleep_element = OverrideResultElement(SoftSleepElement(date_and_time.create_time_span(days=1000)), True)
                _conditional_actions_manager.attach_conditions(obj, exit_conditions, _execute_actions)
        animation_element = self.reference(obj, target=target, sequence=sequence)
        animation_element = build_critical_section((animation_element, flush_all_animations))
        result = yield from element_utils.run_child(timeline, animation_element)
        if self.loop_exit_conditions:
            _conditional_actions_manager.detach_conditions(obj)
        if not result:
            return result
        if executed_actions or callback is not None:
            fn_element = FunctionElement(callback)
            yield from element_utils.run_child(timeline, fn_element)
        return True

class ObjectRoutingBehaviorAction(HasTunableSingletonFactory, AutoFactoryInit):

    def run_action_gen(self, timeline, obj, target):
        raise NotImplementedError

class ObjectRoutingBehaviorActionAnimation(ObjectRoutingBehaviorAction):
    FACTORY_TUNABLES = {'animation': _ObjectRoutingActionAnimation.TunableFactory()}

    def run_action_gen(self, timeline, obj, target):
        result = yield from self.animation(timeline, obj, target)
        if not result:
            return result
        return True

class _DestroyObjectSelectionRule(HasTunableSingletonFactory, AutoFactoryInit):

    def get_objects(self, obj, target):
        raise NotImplementedError

class _DestroyObjectSelectionRuleTags(_DestroyObjectSelectionRule):
    FACTORY_TUNABLES = {'tags': TunableTags(description='\n            Only objects with these tags are considered.\n            ', filter_prefixes=('Func',)), 'radius': TunableDistanceSquared(description='\n            Only objects within this distance are considered.\n            ', default=1)}

    def get_objects(self, obj, target):
        objects = tuple(o for o in services.object_manager().get_objects_matching_tags(self.tags, match_any=True) if (o.position - obj.position).magnitude_squared() <= self.radius)
        return objects

class _DestroyObjectSelectionRuleTargetObject(_DestroyObjectSelectionRule):
    FACTORY_TUNABLES = {}

    def get_objects(self, obj, target):
        objects = (target,) if target is not None else None
        return objects

class ObjectRoutingBehaviorActionDestroyObjects(ObjectRoutingBehaviorAction):
    FACTORY_TUNABLES = {'animation_success': OptionalTunable(description='\n            If enabled, the animation to play if there are objects to destroy.\n            ', tunable=_ObjectRoutingActionAnimation.TunableFactory()), 'animation_failure': OptionalTunable(description='\n            If enabled, the animation to play if there are no objects to destroy.\n            ', tunable=_ObjectRoutingActionAnimation.TunableFactory()), 'loot_success': TunableList(description='\n            For each destroyed object, apply this loot between the routing\n            object (Actor) and the destroyed object (Object).\n            ', tunable=LootActions.TunableReference()), 'object_selection_method': TunableVariant(tags=_DestroyObjectSelectionRuleTags.TunableFactory(), target_object=_DestroyObjectSelectionRuleTargetObject.TunableFactory(), default='tags')}

    def run_action_gen(self, timeline, obj, target):
        objects = self.object_selection_method.get_objects(obj, target)
        if not objects:
            if self.animation_failure is not None:
                result = yield from self.animation_failure(timeline, obj, target)
                return result
            return True

        def _callback(_):
            for o in objects:
                resolver = DoubleObjectResolver(obj, o)
                for loot_action in self.loot_success:
                    loot_action.apply_to_resolver(resolver)
                o.remove_from_client(fade_duration=obj.FADE_DURATION)
                o.destroy(source=self, cause='Object being destroyed by ObjectRoutingBehaviorActionDestroyObjects')

        if self.animation_success is not None:
            result = yield from self.animation_success(timeline, obj, target, callback=_callback)
            if not result:
                return result
        else:
            _callback(timeline)
        return True

class ObjectRoutingBehaviorActionApplyLoot(ObjectRoutingBehaviorAction):
    FACTORY_TUNABLES = {'loot_actions': TunableList(description="\n            Loot to apply.\n            Participant type 'Actor' refers to the object that is routing (ie, the 'bot').\n            Participant type 'Object' refers to the target object the bot is acting upon.\n            ", tunable=LootActions.TunableReference())}

    def run_action_gen(self, timeline, obj, target):
        if self.loot_actions is None:
            return True
        if target is None:
            resolver = SingleObjectResolver(obj)
        else:
            resolver = DoubleObjectResolver(obj, target)
        for loot_action in self.loot_actions:
            loot_action.apply_to_resolver(resolver)
        return True

class ObjectRoutingBehaviorActionProceduralAnimationRotation(ObjectRoutingBehaviorAction, ProceduralAnimationRotationMixin):
    FACTORY_TUNABLES = {'animation': OptionalTunable(description='\n            If enabled, the animation to play when we set rotation.\n            ', tunable=_ObjectRoutingActionAnimation.TunableFactory())}

    def run_action_gen(self, timeline, obj, target):

        def _callback(_):
            control_rotation_lookat(obj, self.procedural_animation_control_name, target, self.target_joint, self.duration, self.rotation_around_facing)

        if self.animation is not None:
            result = yield from self.animation(timeline, obj, target, callback=_callback)
            if not result:
                return result
        else:
            _callback(timeline)
        return True
