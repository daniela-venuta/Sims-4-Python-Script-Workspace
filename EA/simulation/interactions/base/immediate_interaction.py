from types import SimpleNamespacefrom autonomy.autonomy_interaction_priority import AutonomyInteractionPriorityfrom business.business_elements import BusinessBuyLot, BusinessEmployeeActionfrom crafting.create_photo_memory import CreatePhotoMemoryfrom event_testing.tests import TunableTestSetfrom interactions.base.basic import TunableBasicContentSetfrom interactions.base.interaction import InteractionIntensityfrom interactions.base.super_interaction import SuperInteractionfrom interactions.payment.payment_element import PaymentElementfrom interactions.push_npc_leave_lot_now import PushNpcLeaveLotNowInteractionfrom interactions.utils.adventure import Adventurefrom interactions.utils.camera import CameraFocusElement, SetWallsUpOverrideElementfrom interactions.utils.creation import ObjectCreationElement, SimCreationElementfrom interactions.utils.destruction import ObjectDestructionElementfrom interactions.utils.interaction_elements import AddToHouseholdElement, SaveParticipantElementfrom interactions.utils.notification import NotificationElementfrom interactions.utils.tunable import DoCommandfrom interactions.utils.visual_effect import PlayVisualEffectElementfrom notebook.notebook_entry_elements import NotebookDisplayElementfrom objects.components.state import TunableStateChangefrom sims.pregnancy.pregnancy_element import PregnancyElementfrom sims.university.university_elements import UniversityEnrollmentElementfrom sims4.collections import frozendictfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableVariantfrom sims4.utils import classpropertyfrom situations.tunable import CreateSituationElement, JoinSituationElementfrom tag import Tagfrom travel_group.travel_group_elements import TravelGroupAdd, TravelGroupRemove
class ImmediateSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(no_content=True, default='no_content'), 'basic_extras': TunableList(description='Additional elements to run around the basic content of the interaction.', tunable=TunableVariant(add_to_household=AddToHouseholdElement.TunableFactory(), adventure=Adventure.TunableFactory(), business_buy_lot=BusinessBuyLot.TunableFactory(), business_employee_action=BusinessEmployeeAction.TunableFactory(), camera_focus=CameraFocusElement.TunableFactory(), create_object=ObjectCreationElement.TunableFactory(), create_photo_memory=CreatePhotoMemory.TunableFactory(), create_sim=SimCreationElement.TunableFactory(), create_situation=CreateSituationElement.TunableFactory(), destroy_object=ObjectDestructionElement.TunableFactory(), display_notebook_ui=NotebookDisplayElement.TunableFactory(), do_command=DoCommand.TunableFactory(), join_situation=JoinSituationElement.TunableFactory(), notification=NotificationElement.TunableFactory(), payment=PaymentElement.TunableFactory(), pregnancy=PregnancyElement.TunableFactory(), push_leave_lot_interaction=PushNpcLeaveLotNowInteraction.TunableFactory(), remove_from_travel_group=TravelGroupRemove.TunableFactory(), add_to_travel_group=TravelGroupAdd.TunableFactory(), save_participant=SaveParticipantElement.TunableFactory(), state_change=TunableStateChange(), university_enrollment_ui=UniversityEnrollmentElement.TunableFactory(), vfx=PlayVisualEffectElement.TunableFactory(), walls_up_override=SetWallsUpOverrideElement.TunableFactory()))}

    @classproperty
    def immediate(cls):
        return True
lock_instance_tunables(ImmediateSuperInteraction, allow_autonomous=False, _cancelable_by_user=False, _must_run=True, visible=False, _constraints=frozendict(), basic_reserve_object=None, basic_focus=None, intensity=InteractionIntensity.Default, super_affordance_compatibility=None, animation_stat=None, _provided_posture_type=None, supported_posture_type_filter=(), force_autonomy_on_inertia=False, force_exit_on_inertia=False, disallow_as_mixer_target=False, attention_cost=0.5, _false_advertisements=(), _hidden_false_advertisements=(), _static_commodities=(), _affordance_key_override_for_autonomy=None, apply_autonomous_posture_change_cost=True, disable_autonomous_multitasking_if_user_directed=False, test_autonomous=TunableTestSet.DEFAULT_LIST, pre_add_autonomy_commodities=(), pre_run_autonomy_commodities=(), post_guaranteed_autonomy_commodities=(), post_run_autonomy_commodities=SimpleNamespace(requests=(), fallback_notification=None), scoring_priority=AutonomyInteractionPriority.INVALID, duplicate_affordance_group=Tag.INVALID, time_overhead=1, use_best_scoring_aop=True, opportunity_cost_multiplier=1, autonomy_can_overwrite_similar_affordance=False, subaction_selection_weight=1, relationship_scoring=False, _party_size_weight_tuning=(), joinable=(), rallyable=None, autonomy_preference=None, outfit_priority=None, outfit_change=None, object_reservation_tests=(), cancel_replacement_affordances=None, privacy=None, provided_affordances=(), canonical_animation=None, ignore_group_socials=False, confirmation_dialog=None)