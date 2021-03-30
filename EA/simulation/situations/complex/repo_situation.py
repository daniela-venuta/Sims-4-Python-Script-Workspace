import enumimport operatorimport randomfrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions.utils.outcome_enums import OutcomeResultfrom interactions.utils.success_chance import SuccessChancefrom sims.loan_tuning import LoanTunablesfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, TunableInterval, TunablePercent, TunableList, OptionalTunable, TunableEnumEntry, Tunable, TunableRangefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, CommonInteractionCompletedSituationState, SituationStateData, TunableInteractionOfInterest, SituationStatefrom situations.situation_types import SituationCreationUIOptionfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.loglogger = sims4.log.Logger('RepoSituation', default_owner='nsavalani')
class DebtSource(enum.Int):
    SCHOOL_LOAN = ...
    BILLS = ...

class _WaitForRepoPersonState(SituationState):
    pass

class _FindObjectState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        current_object = None
        while self.owner.objects_to_take:
            obj_id = self.owner.objects_to_take.pop(0)[0]
            obj = services.object_manager().get(obj_id)
            if not obj.self_or_part_in_use:
                current_object = obj
                break
        if current_object is not None:
            self.owner.set_current_object(current_object)
            self._change_state(self.owner.idle_at_object_state())
        else:
            self._change_state(self.owner.nothing_to_take_state())

    def timer_expired(self):
        self._change_state(self.owner.leave_state())

class _NothingToTakeState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, resolver=None, **kwargs):
        self._change_state(self.owner.leave_state())

    def timer_expired(self):
        self._change_state(self.owner.leave_state())

class _IdleAtObjectState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for custom_key in self.owner.bribe_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        for custom_key in self.owner.ask_not_to_take_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        repo_person = self.owner.repo_person()
        if event == TestEvent.InteractionComplete and repo_person is not None and sim_info is repo_person.sim_info:
            if resolver(self.owner.bribe_interaction):
                if resolver.interaction.global_outcome_result == OutcomeResult.SUCCESS:
                    self.owner.clear_current_object()
                    self._change_state(self.owner.leave_state())
            elif resolver(self.owner.ask_not_to_take_interaction):
                if self.owner.ask_not_to_take_success_chances_list:
                    ask_not_to_take_chance = self.owner.ask_not_to_take_success_chances_list.pop(0).get_chance(resolver)
                else:
                    ask_not_to_take_chance = 0
                if random.random() < ask_not_to_take_chance:
                    self.owner.clear_current_object()
                    if self.owner.ask_not_to_take_success_notification is not None:
                        notification = self.owner.ask_not_to_take_success_notification(repo_person.sim_info, resolver=SingleSimResolver(repo_person.sim_info))
                        notification.show_dialog()
                    self._change_state(self.owner.find_object_state())
                elif self.owner.ask_not_to_take_failure_notification is not None:
                    notification = self.owner.ask_not_to_take_failure_notification(repo_person.sim_info, resolver=SingleSimResolver(repo_person.sim_info))
                    notification.show_dialog()

    def timer_expired(self):
        self._change_state(self.owner.repossess_object_state())

class _RepossessObjectState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, resolver=None, **kwargs):
        self.owner.reduce_debt(self.owner.current_object.depreciated_value)
        self.owner.clear_current_object()
        self.owner.on_object_repossessed()

    def timer_expired(self):
        self._change_state(self.owner.find_object_state())

class _LeaveState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        repo_person = self.owner.repo_person()
        if repo_person is not None:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(repo_person)
        self.owner._self_destruct()

class RepoSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'repo_person_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the repo-person.\n            ', tuning_group=GroupNames.ROLES), 'debtor_sim_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the Sim from the active household whose\n            unpaid debt is being collected by the repo-person.\n            ', tuning_group=GroupNames.ROLES), 'repo_amount': TunableTuple(description='\n            Tuning that determines the simoleon amount the repo-person is\n            trying to collect.\n            ', target_amount=TunablePercent(description='\n                The percentage of current debt which determines the base\n                amount the repo-person will try to collect.\n                ', default=10), min_and_max_collection_range=TunableInterval(description='\n                Multipliers that define the range around the target amount\n                that determine which objects should be taken.\n                ', tunable_type=float, default_lower=1, default_upper=1), tuning_group=GroupNames.SITUATION), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip to show when the player tries to save the game while\n            this situation is running. The save is locked when the situation\n            starts.\n            ', tuning_group=GroupNames.SITUATION), 'find_object_state': _FindObjectState.TunableFactory(description='\n            The state that picks an object for the repo-person to take.\n            ', display_name='1. Find Object State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'nothing_to_take_state': _NothingToTakeState.TunableFactory(description='\n            The state at which there is nothing for the repo-person to take.\n            ', display_name='2. Nothing To Take State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'idle_at_object_state': _IdleAtObjectState.TunableFactory(description='\n            The state at which the repo-person waits near the picked object\n            and can be asked not to take the object.\n            ', display_name='3. Idle At Object State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'repossess_object_state': _RepossessObjectState.TunableFactory(description='\n            The state at which the repo-person will repossess the picked object.\n            ', display_name='4. Repossess Object State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _LeaveState.TunableFactory(description='\n            The state at which the repo-person leaves the lot.\n            ', display_name='5. Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'valid_object_tests': TunableTestSet(description='\n            Test set that determines if an object on the lot is valid for\n            repossession.\n            ', tuning_group=GroupNames.SITUATION), 'ask_not_to_take_success_chances': TunableList(description='\n            List of values that determine the chance of success of the ask\n            not to take interaction, with each chance being used once and then\n            moving to the next. After using all the tuned chances the next\n            ask not to take interaction will always fail.\n            ', tunable=SuccessChance.TunableFactory(description='\n                Chance of success of the "Ask Not To Take" interaction.\n                '), tuning_group=GroupNames.SITUATION), 'bribe_interaction': TunableInteractionOfInterest(description='\n            If this interaction completes successfully, the repo-person will\n            leave the lot without repossessing anything.\n            '), 'ask_not_to_take_interaction': TunableInteractionOfInterest(description='\n            When this interaction completes, the situation will determine if\n            the repo-person should find another object to repossess or not\n            based on the tuned success chances.\n            '), 'ask_not_to_take_failure_notification': OptionalTunable(description='\n            A TNS that displays when an ask-not-to-take interaction fails, if enabled.\n            ', tunable=UiDialogNotification.TunableFactory()), 'ask_not_to_take_success_notification': OptionalTunable(description='\n            A TNS that displays when an ask-not-to-take interaction succeeds, if enabled.\n            ', tunable=UiDialogNotification.TunableFactory()), 'debt_source': TunableEnumEntry(description="\n            The source of where the debt is coming from and where it'll be removed.\n            ", tunable_type=DebtSource, default=DebtSource.SCHOOL_LOAN), 'maximum_object_to_repossess': OptionalTunable(description='\n            The total maximum objects that the situation will take.\n            ', tunable=TunableRange(description='\n                The total maximum objects that the situation will take.\n                If Use Debt Amount is specified then the situation will keep taking objects\n                until there are no more valid objects to take or we have removed all of the\n                debt.\n                ', tunable_type=int, default=1, minimum=1), enabled_by_default=True, enabled_name='has_maximum_value', disabled_name='use_debt_amount'), 'auto_clear_debt_event': OptionalTunable(description='\n            If enabled then we will have an even we listen to to cancel the debt.\n            ', tunable=TunableEnumEntry(description='\n                The event that when triggered will cause all the debt to be cancelled and the\n                repo man to leave.\n                ', tunable_type=TestEvent, default=TestEvent.Invalid, invalid_enums=(TestEvent.Invalid,)))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.objects_to_take = []
        self.current_object = None
        self.ask_not_to_take_success_chances_list = list(self.ask_not_to_take_success_chances)
        self._reservation_handler = None
        self._objects_repossessed = 0

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _WaitForRepoPersonState), SituationStateData(2, _FindObjectState, factory=cls.find_object_state), SituationStateData(3, _NothingToTakeState, factory=cls.nothing_to_take_state), SituationStateData(4, _IdleAtObjectState, factory=cls.idle_at_object_state), SituationStateData(5, _RepossessObjectState, factory=cls.repossess_object_state), SituationStateData(6, _LeaveState, factory=cls.leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.repo_person_job_and_role_state.job, cls.repo_person_job_and_role_state.role_state), (cls.debtor_sim_job_and_role_state.job, cls.debtor_sim_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def repo_person(self):
        sim = next(self.all_sims_in_job_gen(self.repo_person_job_and_role_state.job), None)
        return sim

    def debtor_sim(self):
        sim = next(self.all_sims_in_job_gen(self.debtor_sim_job_and_role_state.job), None)
        return sim

    def _cache_valid_objects(self):
        debt_value = self.get_debt_value()
        if debt_value is None:
            self._self_destruct()
            return
        target_amount = debt_value*self.repo_amount.target_amount
        unsorted = []
        plex_service = services.get_plex_service()
        check_common_area = plex_service.is_active_zone_a_plex()
        debtor_household_id = self.debtor_sim().household_id
        for obj in services.object_manager().valid_objects():
            if not obj.get_household_owner_id() == debtor_household_id:
                pass
            elif not obj.is_on_active_lot():
                pass
            elif check_common_area and plex_service.get_plex_zone_at_position(obj.position, obj.level) is None:
                pass
            elif not obj.is_connected(self.repo_person()):
                pass
            elif obj.children:
                pass
            else:
                resolver = SingleObjectResolver(obj)
                if self.valid_object_tests.run_tests(resolver):
                    delta = abs(obj.depreciated_value - target_amount)
                    unsorted.append((obj.id, delta))
        self.objects_to_take = sorted(unsorted, key=operator.itemgetter(1))

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if self.debtor_sim() is not None and self.repo_person() is not None:
            self._cache_valid_objects()
            self._change_state(self.find_object_state())

    def _destroy(self):
        super()._destroy()
        self.clear_current_object()
        services.get_persistence_service().unlock_save(self)
        if self.auto_clear_debt_event is not None:
            services.get_event_manager().unregister_single_event(self, self.auto_clear_debt_event)

    def start_situation(self):
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(_WaitForRepoPersonState())
        if self.auto_clear_debt_event is not None:
            services.get_event_manager().register_single_event(self, self.auto_clear_debt_event)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if self.auto_clear_debt_event is None:
            return
        if event != self.auto_clear_debt_event:
            return
        self.clear_debt()
        self._change_state(self.leave_state())

    def reduce_debt(self, amount):
        if self.debt_source == DebtSource.SCHOOL_LOAN:
            host_sim_info = services.sim_info_manager().get(self._guest_list.host_sim_id)
            statistic = host_sim_info.get_statistic(LoanTunables.DEBT_STATISTIC, add=False)
            if statistic is None:
                return
            else:
                statistic.add_value(-amount)
        elif self.debt_source == DebtSource.BILLS:
            services.active_household().bills_manager.reduce_amount_owed(amount)
        else:
            logger.error('Attempting to use a debt source that is not handled', owner='jjacobson')
            return

    def clear_debt(self):
        if self.debt_source == DebtSource.SCHOOL_LOAN:
            host_sim_info = services.sim_info_manager().get(self._guest_list.host_sim_id)
            statistic = host_sim_info.get_statistic(LoanTunables.DEBT_STATISTIC, add=False)
            if statistic is None:
                return
            else:
                statistic.set_value(0)
        elif self.debt_source == DebtSource.BILLS:
            services.active_household().bills_manager.pay_bill(clear_bill=True)
        else:
            logger.error('Attempting to use a debt source {} that is not handled', self.debt_source, owner='jjacobson')
            return

    def get_debt_value(self):
        if self.debt_source == DebtSource.SCHOOL_LOAN:
            host_sim_info = services.sim_info_manager().get(self._guest_list.host_sim_id)
            statistic = host_sim_info.get_statistic(LoanTunables.DEBT_STATISTIC, add=False)
            if statistic is None:
                return
            return statistic.get_value()
        if self.debt_source == DebtSource.BILLS:
            return services.active_household().bills_manager.current_payment_owed
        else:
            logger.error('Attempting to use a debt source that is not handled', owner='jjacobson')
            return

    def on_object_repossessed(self):
        self._objects_repossessed += 1
        if self.maximum_object_to_repossess is None or self._objects_repossessed < self.maximum_object_to_repossess:
            debt_value = self.get_debt_value()
            if debt_value is not None and debt_value > 0:
                self._change_state(self.find_object_state())
                return
        self._change_state(self.leave_state())

    def get_target_object(self):
        return self.current_object

    def get_lock_save_reason(self):
        return self.save_lock_tooltip

    def set_current_object(self, obj):
        self.current_object = obj
        if self._reservation_handler is not None:
            logger.error('Trying to reserve an object when an existing reservation already exists: {}', self._reservation_handler)
            self._reservation_handler.end_reservation()
        self._reservation_handler = self.current_object.get_reservation_handler(self.repo_person())
        self._reservation_handler.begin_reservation()

    def clear_current_object(self):
        self.current_object = None
        if self._reservation_handler is not None:
            self._reservation_handler.end_reservation()
            self._reservation_handler = None
lock_instance_tunables(RepoSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)