from protocolbuffers import Audio_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom element_utils import build_critical_sectionfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import InteractionContextfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.conditional_animation import conditional_animationfrom objects.components.state import with_on_state_changed, TunableStateValueReferencefrom objects.components.state_change import StateChangefrom objects.components.types import STEREO_COMPONENTfrom sims4.tuning.tunable import TunableReference, Tunable, TunableTuple, OptionalTunable, TunableListfrom sims4.utils import flexmethodimport element_utilsimport event_testing.state_testsimport objects.components.stateimport servicesimport sims4logger = sims4.log.Logger('Stereo')
class ListenSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'required_station': OptionalTunable(description="\n            If enabled, specifies the radio station this affordance listens to.\n            Normally this is provided by the object's Stereo component and does \n            not need to be tuned here.\n            ", tunable=objects.components.state.TunableStateValueReference(description='\n                The station that this affordance listens to.\n                '), enabled_by_default=True), 'off_states': TunableList(description="\n            If tuned, specifies the channels that represents the off state, and\n            can cancel this interaction. Normally this is provided by the\n            object's Stereo component and does not need to be tuned here.\n            ", tunable=TunableStateValueReference()), 'remote_animation': TunableAnimationReference(description='\n            The animation for using the stereo remote.\n            '), 'remote_animation_overrides': OptionalTunable(description='\n            If enabled, apply the first remote animation reference that passes \n            its corresponding tests, instead of the default remote animation. \n            If none pass, then the default applies.\n            ', tunable=TunableList(description='\n                A list of remote animation references and test tuples.\n                ', tunable=TunableTuple(description='\n                    An animation override and test tuple.\n                    ', override=TunableAnimationReference(description='\n                        The animation reference override to apply if the tests \n                        pass.\n                        ', pack_safe=True, callback=None), tests=TunableTestSet(description='\n                        A series of tests that must pass in order for this \n                        animation reference override to be applied.\n                        '))))}
    CHANGE_CHANNEL_XEVT_ID = 101

    def __init__(self, aop, context, required_station=None, off_state=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        self.required_station = self.affordance.required_station
        self.off_state = off_state
        if required_station is not None:
            self.required_station = required_station
        elif self.required_station is None:
            stereo_component = self.target.get_component(STEREO_COMPONENT)
            if stereo_component is not None:
                current_channel = self.target.get_state(stereo_component.channel_state)
                if current_channel != stereo_component.off_state:
                    self.required_station = current_channel
                    if self.off_state is None:
                        self.off_state = stereo_component.off_state
        if self.required_station is None:
            logger.error('Listen interaction {} does not have a required station. This must be tuned on the interaction or on the stereo component', self, owner='thomaskenney')
        if self.off_state is None and not self.off_states:
            logger.error('Listen interaction {} does not have an off state. This must be tuned on the interaction or the stereo component', self, owner='thomaskenney')

    def _get_remote_animation_overrides(self):
        resolver = SingleSimResolver(self._sim.sim_info)
        for overrides in self.remote_animation_overrides:
            if overrides.tests.run_tests(resolver):
                return overrides.override

    def ensure_state(self, desired_station):
        stereo_component = self.target.get_component(STEREO_COMPONENT)
        if stereo_component is None:
            logger.error('object {} being used as stereo but has no stereo component', self.target, owner='thomaskenney')
            return
        audio_state_args = {'immediate_audio': stereo_component.immediate, 'play_on_active_sim_only': stereo_component.play_on_active_sim_only}
        attr_args_dict = {'audio_state': audio_state_args}
        remote_animation = self.affordance.remote_animation
        if self.remote_animation_overrides:
            animation_override = self._get_remote_animation_overrides()
            if animation_override is not None:
                remote_animation = animation_override
        return conditional_animation(self, desired_station, self.CHANGE_CHANNEL_XEVT_ID, remote_animation, attr_args_dict=attr_args_dict)

    def _changed_state_callback(self, target, state, old_value, new_value):
        if self.off_state and new_value != self.off_state or new_value not in self.off_states:
            object_callback = getattr(new_value, 'on_interaction_canceled_from_state_change', None)
            if object_callback is not None:
                object_callback(self)
        self.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='state: interaction canceled on state change ({} != {})'.format(new_value.value, self.required_station.value))

    def _run_interaction_gen(self, timeline):
        result = yield from element_utils.run_child(timeline, build_critical_section(self.ensure_state(self.required_station), objects.components.state.with_on_state_changed(self.target, self.required_station.state, self._changed_state_callback, super()._run_interaction_gen)))
        return result

    @flexmethod
    def _get_name(cls, inst, *args, required_station=None, **interaction_parameters):
        station_name = None
        if inst is not None:
            station_name = inst.required_station.display_name
        elif required_station is not None:
            station_name = required_station.display_name
        elif cls.required_station is not None:
            station_name = cls.required_station.display_name
        return cls.display_name(station_name)

    def get_rallyable_interaction_parameters(self):
        interaction_parameters = {'required_station': self.required_station, 'off_state': self.off_state}
        return interaction_parameters

class CancelOnStateChangeInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'cancel_state_test': event_testing.state_tests.TunableStateTest(description="the state test to run when the object's state changes. If this test passes, the interaction will cancel"), 'required_station': OptionalTunable(description="\n            If enabled, specifies the radio station this affordance listens to.\n            Normally this is provided by the object's Stereo component and does \n            not need to be tuned here.\n            ", tunable=objects.components.state.TunableStateValueReference(description='\n                The station that this affordance listens to.\n                '), enabled_by_default=False)}

    def __init__(self, aop, context, required_station=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        self.required_station = self.affordance.required_station
        if required_station is not None:
            self.required_station = required_station

    def _run_interaction_gen(self, timeline):
        result = yield from element_utils.run_child(timeline, element_utils.build_element([self._cancel_on_state_test_pass(self.cancel_state_test, super()._run_interaction_gen)]))
        return result

    def _cancel_on_state_test_pass(self, cancel_on_state_test, *sequence):
        value = cancel_on_state_test.value

        def callback_fn(target, state, old_value, new_value):
            resolver = self.get_resolver(target=target)
            if resolver(cancel_on_state_test):
                self.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='state: interaction canceled on state change because new state:{} {} required state:{}'.format(new_value, cancel_on_state_test.operator, value))
                object_callback = getattr(new_value, 'on_interaction_canceled_from_state_change', None)
                if object_callback is not None:
                    object_callback(self)

        return with_on_state_changed(self.target, value.state, callback_fn, sequence)

    @flexmethod
    def _get_name(cls, inst, *args, required_station=None, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        station = required_station if required_station is not None else inst_or_cls.required_station
        if station is not None:
            return inst_or_cls.display_name(station.display_name)
        else:
            return super(SuperInteraction, inst_or_cls)._get_name(*args, **interaction_parameters)

class SkipToNextSongSuperInteraction(ImmediateSuperInteraction):

    def _run_gen(self, timeline):
        stereo_component = self.target.get_component(STEREO_COMPONENT)
        if stereo_component is None:
            logger.error('object {} being used as stereo but has no stereo component', self.target, owner='thomaskenney')
            return False
        play_audio_primative = self.target.get_component_managed_state_distributable('audio_state', stereo_component.channel_state)
        if play_audio_primative is not None:
            msg = Audio_pb2.SoundSkipToNext()
            msg.object_id = self.target.id
            if self.target.inventoryitem_component is not None:
                forward_to_owner_list = self.target.inventoryitem_component.forward_client_state_change_to_inventory_owner
                if self.target.inventoryitem_component.inventory_owner is not None:
                    msg.object_id = self.target.inventoryitem_component.inventory_owner.id
            msg.channel = play_audio_primative.channel
            distributor = Distributor.instance()
            distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.OBJECT_AUDIO_PLAYLIST_SKIP_TO_NEXT, msg))
        return True

class StereoPieMenuChoicesInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'push_additional_affordances': Tunable(bool, True, description="Whether to push affordances specified by the channel. This is used for stereo's turn on and listen to... interaction"), 'off_state_pie_menu_category': TunableTuple(pie_menu_category=TunableReference(description='\n                Pie menu category so we can display a submenu for each outfit category\n                ', manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True), pie_menu_category_on_forwarded=TunableReference(description='\n                Pie menu category so when this interaction is forwarded from inventory\n                object to inventory owner.\n                ', manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True))}

    def __init__(self, aop, context, audio_channel=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        self.audio_channel = audio_channel

    @flexmethod
    def get_pie_menu_category(cls, inst, stereo=None, from_inventory_to_owner=False, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if stereo is not None:
            stereo_component = stereo.get_component(STEREO_COMPONENT)
            if stereo_component is None:
                logger.error('object {} being used as stereo but has no stereo component', stereo, owner='thomaskenney')
                return inst_or_cls.category
            if not stereo_component.is_stereo_turned_on():
                if from_inventory_to_owner and inst_or_cls.off_state_pie_menu_category.pie_menu_category_on_forwarded is not None:
                    return inst_or_cls.off_state_pie_menu_category.pie_menu_category_on_forwarded
                if inst_or_cls.off_state_pie_menu_category.pie_menu_category is not None:
                    return inst_or_cls.off_state_pie_menu_category.pie_menu_category
        if from_inventory_to_owner:
            return inst_or_cls.category_on_forwarded
        return inst_or_cls.category

    @flexmethod
    def _get_name(cls, inst, *args, audio_channel=None, **interaction_parameters):
        if inst is not None:
            return inst.audio_channel.display_name
        return audio_channel.display_name

    @classmethod
    def potential_interactions(cls, target, context, from_inventory_to_owner=False, **kwargs):
        if context.source == InteractionContext.SOURCE_AUTONOMY:
            return
        stereo_component = target.get_component(STEREO_COMPONENT)
        if stereo_component is None:
            logger.error('object {} being used as stereo but has no stereo component', target, owner='thomaskenney')
            return
        for client_state in stereo_component.get_available_picker_channel_states(context):
            yield AffordanceObjectPair(cls, target, cls, None, stereo=target, audio_channel=client_state, from_inventory_to_owner=from_inventory_to_owner)

    def _run_interaction_gen(self, timeline):
        self.audio_channel.activate_channel(interaction=self, push_affordances=self.push_additional_affordances)
