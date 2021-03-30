from civic_policies import street_civic_policy_testsfrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom event_testing.tests import TunableTestSetfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom interactions.utils.outcome_enums import OutcomeResultfrom interactions.utils.object_definition_or_tags import ObjectDefinitonsOrTagsVariantfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableSimMinute, TunableReferencefrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationState, SituationStateData, CommonInteractionCompletedSituationState, TunableInteractionOfInterestfrom statistics.commodity import Commodityfrom ui.ui_dialog_notification import UiDialogNotificationimport enumimport servicesimport sims4from sims4.localization import TunableLocalizedString, LocalizationHelperTuningWAIT_TO_BE_LET_IN_TIMEOUT = 'wait_to_be_let_in_timeout'
class PolicyFollowing(enum.IntFlags):
    FULL_FOLLOWED = 0
    PARTIAL_FOLLOWED = 1
    NOT_FOLLOWED = 3

class _WaitState(SituationState):
    pass

class _InspectorEntryState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'timeout': TunableSimMinute(description='\n                The amount of time to wait in this situation state before it\n                times out and tell inspector to self-inspect.\n                ', default=10, minimum=1)}

    def __init__(self, timeout, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._create_or_load_alarm(WAIT_TO_BE_LET_IN_TIMEOUT, self._timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        self._change_state(self.owner.civic_inspect_outside())

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.civic_inspect_inside())

class _BaseInspectionClass(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for custom_key in self.owner.overlook_issues_success_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete and resolver(self.owner.overlook_issues_success_interaction):
            if resolver.interaction.global_outcome_result == OutcomeResult.SUCCESS:
                self.owner.follow_status = PolicyFollowing.FULL_FOLLOWED
                self._change_state(self.owner.leave())
            else:
                self._change_state(self.owner.final_checks())

class _InspectorInsideState(_BaseInspectionClass):
    FACTORY_TUNABLES = {'interaction_to_push': TunableReference(description='\n                The interaction that will be pushed on all non-selectable sims\n                when this situation state begins if there is a front door.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), display_name='Interaction To Push If Front Door Exists.')}

    def __init__(self, interaction_to_push, **kwargs):
        super().__init__(**kwargs)
        self._interaction_to_push = interaction_to_push

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if not services.get_door_service().has_front_door():
            return
        for sim in self.owner.all_sims_in_situation_gen():
            if sim.is_selectable:
                pass
            else:
                context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
                sim.push_super_affordance(self._interaction_to_push, sim, context)

    def timer_expired(self):
        self._change_state(self.owner.final_checks())

class _InspectorOutsideState(_BaseInspectionClass):

    def timer_expired(self):
        self._change_state(self.owner.final_checks())

class _FinalChecksState(CommonSituationState):
    FACTORY_TUNABLES = {'civic_policy_follow_rules': TunableList(description='\n                a civic policy would pass if either civic policy is not enabled\n                or (is enabled and objects are placed and not broken)\n                ', tunable=TunableTuple(street_civic_policy_test=street_civic_policy_tests.StreetCivicPolicyTest.TunableFactory(), skip_test_condition=TunableTestSet(description="\n                        If these tests return true, we need to skip the civic policy test.\n                        Example use: In apartments, certain civic policies shouldn't be tested.\n                        "), whitelist_filter=ObjectDefinitonsOrTagsVariant(description='\n                        Either a list of tags or definitions that objects can be considered.\n                        ', tuning_group=GroupNames.PICKERTUNING), test=TunableTestSet(description='\n                        Tests on the whitelisted objects.\n                        '), policy_display_name=TunableLocalizedString(description='\n                        Display name of the policy, used to display failure reasons.\n                        ', allow_none=False)))}

    def __init__(self, civic_policy_follow_rules, **kwargs):
        super().__init__(**kwargs)
        self.civic_policy_follow_rules = civic_policy_follow_rules

    def check_if_policies_followed(self):
        object_manager = services.object_manager()
        followed = 0
        total_policies = 0
        inspector_resolver = SingleSimResolver(self.owner.inspector_person())
        for policy in self.civic_policy_follow_rules:
            current_policy_followed = False
            if len(policy.skip_test_condition) > 0:
                if not policy.skip_test_condition.run_tests(inspector_resolver):
                    if not policy.street_civic_policy_test():
                        pass
                    else:
                        total_policies += 1
                        for obj in object_manager.get_objects_with_filter_gen(policy.whitelist_filter):
                            resolver = SingleObjectResolver(obj)
                            if policy.test.run_tests(resolver):
                                followed += 1
                                current_policy_followed = True
                                break
                        if not current_policy_followed:
                            self.owner.policies_not_followed.append(policy.policy_display_name)
            if not policy.street_civic_policy_test():
                pass
            else:
                total_policies += 1
                for obj in object_manager.get_objects_with_filter_gen(policy.whitelist_filter):
                    resolver = SingleObjectResolver(obj)
                    if policy.test.run_tests(resolver):
                        followed += 1
                        current_policy_followed = True
                        break
                if not current_policy_followed:
                    self.owner.policies_not_followed.append(policy.policy_display_name)
        if total_policies == 0:
            return PolicyFollowing.FULL_FOLLOWED
        follow_fraction = float(followed)/total_policies
        if follow_fraction == 0:
            return PolicyFollowing.NOT_FOLLOWED
        if follow_fraction < 1:
            return PolicyFollowing.PARTIAL_FOLLOWED
        else:
            return PolicyFollowing.FULL_FOLLOWED

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self.owner.follow_status = self.check_if_policies_followed()

    def timer_expired(self):
        self._change_state(self.owner.leave())

class _LeaveState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        inspector = self.owner.inspector_person()
        self.owner.notify_result_and_push_bill_modifier()
        if inspector is not None:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(inspector)
        self.owner._self_destruct()

class CivicInspectorSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'inspector_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the eco-inspector.\n            ', tuning_group=GroupNames.ROLES), 'inspector_entry': _InspectorEntryState.TunableFactory(description='\n           Inspector Entry State. Listens for portal allowance.\n            ', display_name='1. Inspector Entry State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'civic_inspect_outside': _InspectorOutsideState.TunableFactory(description='\n           Inspecting from outside, not allowed inside.\n            ', display_name='2. Civic Inspect Outside', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'civic_inspect_inside': _InspectorInsideState.TunableFactory(description='\n            Allowed inside, but may inspect outside if not objects.\n            ', display_name='3. Civic Inspect Inside', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'final_checks': _FinalChecksState.TunableFactory(description='\n            Checks if civic policy is being followed using the conditions\n            described in tuning. \n            ', display_name='4. Final Checks', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave': _LeaveState.TunableFactory(description='\n            Final checks before leaving.\n            ', display_name='5. Leaving state.', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'inspection_successful_notification': UiDialogNotification.TunableFactory(description='\n            A TNS that is displayed to inform of successful inspection.\n            '), 'inspection_failure_notification': UiDialogNotification.TunableFactory(description='\n            A TNS that is displayed to inform of failed inspection.\n            '), 'inspection_partial_success_notification': UiDialogNotification.TunableFactory(description='\n            A TNS that is displayed to inform of failed inspection.\n            '), 'commodity_notfollow': Commodity.TunableReference(description='\n            lot commodity that we set when we want a multiplier for bill modifier.\n                '), 'commodity_follow': Commodity.TunableReference(description='\n            lot commodity that we set when we want a multiplier for bill modifier.\n                '), 'overlook_issues_success_interaction': TunableInteractionOfInterest(description='\n            Interaction pushed to indicate success of overlooking issues.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.follow_status = PolicyFollowing.FULL_FOLLOWED
        self.policies_not_followed = []

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _WaitState), SituationStateData(2, _InspectorEntryState, factory=cls.inspector_entry), SituationStateData(3, _InspectorInsideState, factory=cls.civic_inspect_inside), SituationStateData(4, _InspectorOutsideState, factory=cls.civic_inspect_outside), SituationStateData(5, _FinalChecksState, factory=cls.final_checks), SituationStateData(6, _LeaveState, factory=cls.leave))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.inspector_job_and_role_state.job, cls.inspector_job_and_role_state.role_state)]

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if self.inspector_person() is not None:
            self._change_state(self.inspector_entry())

    def _show_inspection_notification(self, inspection_notification, **kwargs):
        inspector = self.inspector_person()
        if inspector is not None:
            dialog = inspection_notification(inspector, resolver=SingleSimResolver(inspector.sim_info))
            dialog.show_dialog(**kwargs)

    def notify_result_and_push_bill_modifier(self):
        lot = services.active_lot()
        additional_tokens = ()
        if self.policies_not_followed:
            additional_tokens = (LocalizationHelperTuning.get_bulleted_list((None,), self.policies_not_followed),)
        if self.follow_status == PolicyFollowing.NOT_FOLLOWED:
            lot.set_stat_value(self.commodity_notfollow, self.commodity_notfollow.max_value_tuning)
            self._show_inspection_notification(self.inspection_failure_notification, additional_tokens=additional_tokens)
        elif self.follow_status == PolicyFollowing.PARTIAL_FOLLOWED:
            self._show_inspection_notification(self.inspection_partial_success_notification, additional_tokens=additional_tokens)
        else:
            lot.set_stat_value(self.commodity_follow, self.commodity_follow.max_value_tuning)
            self._show_inspection_notification(self.inspection_successful_notification)

    def inspector_person(self):
        sim = next(self.all_sims_in_job_gen(self.inspector_job_and_role_state.job), None)
        return sim

    def start_situation(self):
        super().start_situation()
        self._change_state(_WaitState())
