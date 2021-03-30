import telemetry_helperfrom distributor.system import Distributorfrom protocolbuffers import Consts_pb2, S4Common_pb2from sims4.localization import TunableLocalizedStringFactoryVariant, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableTuple, TunableList, HasTunableFactory, AutoFactoryInit, TunableReference, TunableSet, TunableEnumEntryfrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classproperty, constpropertyimport sims4from ui.ui_dialog_notification import UiDialogNotificationfrom autonomy.autonomy_modes import FullAutonomyfrom autonomy.autonomy_modifier import UNLIMITED_AUTONOMY_RULEfrom bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom date_and_time import TimeSpan, create_date_and_time, sim_ticks_per_week, DateAndTime, sim_ticks_per_dayfrom distributor.ops import CommunityBoardAddPolicyfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions.context import QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.loot import LootActionsfrom objects import ALL_HIDDEN_REASONSfrom objects.components import ComponentContainerfrom objects.components.statistic_component import HasStatisticComponentfrom statistics.static_commodity import StaticCommodityfrom tag import TunableTagfrom tunable_time import TunableTimeOfWeek, Days, TunableTimeSpanfrom ui.ui_dialog_picker import TunablePickerDialogVariant, ObjectPickerTuningFlags, BasePickerRowimport alarmsimport autonomyimport objects.components.typesimport servicesimport randomlogger = sims4.log.Logger('CivicPolicyProvider', default_owner='shouse')TELEMETRY_GROUP_CIVIC_POLICIES = 'CIVC'TELEMETRY_HOOK_CIVIC_POLICY_VOTE = 'VOTE'TELEMETRY_HOOK_CIVIC_POLICY_PROPOSE = 'PRPS'TELEMETRY_HOOK_CIVIC_POLICY_LOBBY = 'LBBY'TELEMETRY_FIELD_NEIGHBORHOOD = 'nbhd'TELEMETRY_FIELD_POLICY = 'plcy'TELEMETRY_FIELD_VOTES = 'vtes'TELEMETRY_FIELD_PLAYER_VOTES = 'pcvt'TELEMETRY_FIELD_OLD_RANK = 'oldr'TELEMETRY_FIELD_NEW_RANK = 'newr'TELEMETRY_FIELD_PROPOSE_ACTION = 'actn'TELEMETRY_FIELD_ACTION_VALUE_BALLOT = 1TELEMETRY_FIELD_ACTION_VALUE_REPEAL = 2TELEMETRY_FIELD_ACTION_VALUE_CANCEL_REPEAL = 3civic_policy_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CIVIC_POLICIES)
class BaseCivicPolicyProvider(ComponentContainer, HasStatisticComponent, HasTunableFactory, AutoFactoryInit):
    CIVIC_POLICY_SCHEDULE = TunableTuple(description='\n        Global schedule to control when voting on civic policies is active.\n        ', voting_open=TunableTimeOfWeek(description='\n            The time of the week that voting for civic policies starts.\n            ', default_day=Days.MONDAY, default_hour=8, default_minute=0), voting_close=TunableTimeOfWeek(description='\n            The time of the week that voting for civic policies ends.  Votes are\n            tallied and policies are modified at this time.\n            ', default_day=Days.SUNDAY, default_hour=16, default_minute=0), voting_close_warning_duration=TunableTimeSpan(description='\n            Duration before the Voting Close to warn players that voting is about to close.\n            ', default_hours=8), schedule_text=TunableLocalizedStringFactory(description='\n            Text for the schedule string.\n            '))
    INFLUENCE_BUCK_TYPE = TunableEnumEntry(description='\n        The type of Bucks used to hold Influence.\n        ', tunable_type=BucksType, default=BucksType.INVALID, pack_safe=True)
    INFLUENCE_TO_VOTE_COST = Tunable(description='\n        The amount of influence used with 1 vote.\n        ', tunable_type=int, default=10, export_modes=ExportModes.All)
    REPEAL_PETITION_THRESHOLD = Tunable(description='\n        The number of petition signatures required to have a policy repealed.\n        ', tunable_type=int, default=10, export_modes=ExportModes.All)
    COMMUNITY_BOARD_TAG = TunableTag(description='\n        The tag of the community boards so we can find them in the world.\n        ')
    VOTING_OPEN_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting period opens.\n        ')
    VOTING_OPEN_MAX_ENABLED_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting period opens with maximum enabled policies.\n        ')
    VOTING_CLOSE_WARNING_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting close approaches.\n        ')
    VOTING_CLOSE_WARNING_MAX_ENABLED_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting close approaches with maximum enabled policies and\n        a policy being repealed.\n        ')
    VOTING_CLOSE_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting period closes.\n        ')
    VOTING_CLOSE_MAX_ENABLED_NOTIFICATION_SUCCESS = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting period closes with maximum enabled\n        policies and a policy being successfully repealed.\n        ')
    VOTING_CLOSE_MAX_ENABLED_NOTIFICATION_FAIL = UiDialogNotification.TunableFactory(description='\n        A TNS that will fire when the voting period closes with maximum enabled\n        policies and a policy being unsuccessfully repealed.\n        ')
    VOTING_CONTINUATION_AUTONOMY_COMMODITIES = TunableList(description='\n        A list of static commodities that will be solved for by autonomy to\n        find and push the vote interaction after viewing the community board.\n        ', tunable=StaticCommodity.TunableReference(description='\n            A static commodity that is solved for by autonomy to find the vote\n            interaction to push. \n            ', pack_safe=True))
    COMMUNITY_BOARD_TEXT = TunableTuple(voting_closed_policy_tooltip_text=TunableLocalizedStringFactory(description="\n            String to insert into the policy tooltips when voting isn't possible\n            because voting is closed.\n            "), voting_open_add_policy_tooltip_text=TunableLocalizedStringFactory(description="\n            Text for the tooltip on the add policy button when it's disabled because\n            voting is open. \n            "), ineligible_voter_policy_tooltip_text=TunableLocalizedStringFactory(description="\n            String to insert into the policy tooltips when voting isn't possible because\n            the sim (first token) lives on a different street.\n            "), ineligible_voter_confirm_tooltip_text=TunableLocalizedStringFactory(description='\n            Text for the tooltip on the confirm button when the button is disabled because\n            the sim (first token) lives on a different street.\n            '), no_room_confirm_tooltip_text=TunableLocalizedStringFactory(description='\n            Text for the tooltip on the confirm button when the button is disabled because\n            already full up on enacted policies.\n            '), no_room_policy_tooltip_text=TunableLocalizedStringFactory(description="\n            String to insert into the policy tooltips when voting isn't possible  because\n            already full up on enacted policies.\n            "), add_policy_picker=TunablePickerDialogVariant(description='\n            The item picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.ITEM))
    CALL_TO_ACTIONS = TunableList(description='\n        List of Call to Action that should be started to introduce the Civic Policy features.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION), pack_safe=True))
    FACTORY_TUNABLES = {'civic_policies': TunableSet(description='\n            The civic policies that may be enacted.\n            ', tunable=TunableReference(description='\n                A civic policy.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('BaseCivicPolicy',), pack_safe=True, export_modes=ExportModes.All)), 'voting_open_loot': TunableList(description='\n            Loot applied to Resident Sims when voting opens.\n            ', tunable=LootActions.TunableReference(description='\n                Loot to apply on voting open.\n                ', pack_safe=True), export_modes=ExportModes.ServerXML), 'voting_close_loot': TunableList(description='\n            Loot applied to Resident Sims when voting opens.\n            ', tunable=LootActions.TunableReference(description='\n                Loot to apply on voting open.\n                ', pack_safe=True), export_modes=ExportModes.ServerXML), 'community_board_dialog_title': TunableLocalizedStringFactoryVariant(description="\n            The Community Board Dialog's title text.\n            ", export_modes=ExportModes.ServerXML), 'initial_vote_test': TunableTestSet(description='\n            If at least one test passes, and the user option is enabled, initial voting will\n            be performed when voting opens.\n            ', export_modes=ExportModes.ServerXML), 'daily_random_vote_test': TunableTestSet(description='\n            If at least one test passes, and the user option is enabled, daily random voting\n            will be performed at midnight.\n            ', export_modes=ExportModes.ServerXML)}
    CIVIC_POLICY_TEST_EVENTS = (TestEvent.CivicPolicyOpenVoting, TestEvent.CivicPolicyDailyRandomVoting, TestEvent.CivicPolicyCloseVoting)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_statistic_component()
        self._enacted_policies = set()
        self._balloted_policies = set()
        self._up_for_repeal_policies = set()
        self._civic_policies = set()
        for policy in self.civic_policies:
            self._civic_policies.add(policy(self))

    @constproperty
    def is_sim():
        return False

    @property
    def is_downloaded(self):
        return False

    def get_enacted_policies(self, tuning=False):
        if tuning:
            return set([type(p) for p in self._enacted_policies])
        return self._enacted_policies

    def get_balloted_policies(self, tuning=False):
        if tuning:
            return set([type(p) for p in self._balloted_policies])
        return self._balloted_policies

    def get_up_for_repeal_policies(self, tuning=False):
        if tuning:
            return set([type(p) for p in self._up_for_repeal_policies])
        return self._up_for_repeal_policies

    def get_dormant_policies(self, tuning=False):
        policies = self._civic_policies - self._enacted_policies - self._balloted_policies - self._up_for_repeal_policies
        if tuning:
            return set([type(p) for p in policies])
        return policies

    def get_civic_policies(self, tuning=False):
        if tuning:
            return self.civic_policies
        return self._civic_policies

    def new_enact_max_count(self):
        return min(len(self.civic_policies), self.max_enacted_policy_count) - len(self._enacted_policies)

    def _reset_voting_statistics(self):
        for policy in self._civic_policies:
            if policy.vote_count_statistic is None:
                logger.error('{} tuned without voting statistic', policy)
            else:
                self.set_stat_value(policy.vote_count_statistic, 0)
        self.commodity_tracker.check_for_unneeded_initial_statistics()
        self.statistic_tracker.check_for_unneeded_initial_statistics()

    def run_sim_voting_loot(self, loot_actions):
        for resolver in self.open_close_voting_loot_resolver_list:
            for loot in loot_actions:
                loot.apply_to_resolver(resolver)

    def run_auto_voting_tests(self, test_set):
        if not services.street_service().enable_automatic_voting:
            return False
        if not test_set:
            return True
        return test_set.run_tests(GlobalResolver())

    def open_voting(self):
        self._reset_voting_statistics()
        self.finalize_startup()
        self.run_sim_voting_loot(self.voting_open_loot)
        if self.run_auto_voting_tests(self.initial_vote_test):
            for policy in self._balloted_policies:
                self.vote(policy, policy.get_initial_vote_count())

    def close_voting(self):

        def get_most_voted_for_policy(policies):
            if not policies:
                return set()
            policy = max(policies, key=lambda policy: self.get_stat_value(policy.vote_count_statistic))
            if self.get_stat_value(policy.vote_count_statistic) <= 0:
                return set()
            return set((policy,))

        balloted_policies = self.get_balloted_policies()
        to_enact = get_most_voted_for_policy(balloted_policies)
        repealable_policies = self.get_up_for_repeal_policies()
        to_repeal = set()
        for policy in repealable_policies:
            if BaseCivicPolicyProvider.REPEAL_PETITION_THRESHOLD <= self.get_stat_value(policy.vote_count_statistic):
                to_repeal.add(policy)
        to_repeal -= to_enact
        to_enact -= self._enacted_policies
        self._enacted_policies -= to_repeal
        for policy in to_repeal:
            policy.repeal()
        to_enact_max_count = self.new_enact_max_count()
        while len(to_enact) > to_enact_max_count:
            to_enact.pop()
        self._enacted_policies.update(to_enact)
        for policy in to_enact:
            policy.enact()
        self._balloted_policies = set()
        self._up_for_repeal_policies = set()
        self._reset_voting_statistics()
        self.finalize_startup()
        self.run_sim_voting_loot(self.voting_close_loot)

    def get_schedule_text(self):
        return self.CIVIC_POLICY_SCHEDULE.schedule_text(self.CIVIC_POLICY_SCHEDULE.voting_open(), self.CIVIC_POLICY_SCHEDULE.voting_close())

    def do_daily_vote(self):
        if self.run_auto_voting_tests(self.daily_random_vote_test):
            for policy in self._balloted_policies:
                self.vote(policy, policy.get_daily_vote_count())

    @property
    def max_enacted_policy_count(self):
        raise NotImplementedError

    @property
    def max_balloted_policy_count(self):
        raise NotImplementedError

    @property
    def initial_balloted_policy_count(self):
        raise NotImplementedError

    @property
    def max_repealable_policy_count(self):
        raise NotImplementedError

    @property
    def open_close_voting_loot_resolver_list(self):
        raise NotImplementedError

    @classproperty
    def provider_type_id(cls):
        raise NotImplementedError

    def get_world_description_id(self):
        return 0

    def is_eligible_voter(self, sim_info):
        raise NotImplementedError

    def is_new_policy_allowed(self, sim_info):
        return False

    def _select_balloted_policies(self):
        self._balloted_policies.clear()
        count_needed = self.initial_balloted_policy_count
        r = random.Random()
        dormant_policies = list(self.get_dormant_policies())
        while dormant_policies and len(self._balloted_policies) < count_needed:
            policy = r.choice(dormant_policies)
            dormant_policies.remove(policy)
            self._balloted_policies.add(policy)

    def finalize_startup(self):
        statistic_component = self.get_component(objects.components.types.STATISTIC_COMPONENT)
        statistic_component.on_finalize_load()
        if not self._civic_policies:
            return
        services.get_event_manager().unregister(self, BaseCivicPolicyProvider.CIVIC_POLICY_TEST_EVENTS)
        services.get_event_manager().register(self, BaseCivicPolicyProvider.CIVIC_POLICY_TEST_EVENTS)
        if not self._balloted_policies:
            self._select_balloted_policies()
        for policy in self._civic_policies:
            policy.finalize_startup()

    def stop_civic_policy_provider(self):
        services.get_event_manager().unregister(self, BaseCivicPolicyProvider.CIVIC_POLICY_TEST_EVENTS)

    def get_policy_instance_for_tuning(self, policy_guid64):
        for inst in self._civic_policies:
            if policy_guid64 == inst.guid64:
                return inst

    def enact(self, policy):
        policy = self.get_policy_instance_for_tuning(policy.guid64)
        if policy is None or policy in self._enacted_policies:
            return False
        if self.new_enact_max_count() == 0:
            return False
        self._enacted_policies.add(policy)
        self._balloted_policies.discard(policy)
        self._up_for_repeal_policies.discard(policy)
        policy.enact()
        return True

    def repeal(self, policy):
        policy = self.get_policy_instance_for_tuning(policy.guid64)
        if policy is None or policy not in self._enacted_policies:
            return False
        self._enacted_policies.discard(policy)
        self._up_for_repeal_policies.discard(policy)
        policy.repeal()
        return True

    def vote(self, policy, count=1, user_directed=False, lobby_interaction=False):
        policy_instance = self.get_policy_instance_for_tuning(policy.guid64)
        if policy_instance is None:
            return False
        return self.vote_by_instance(policy_instance, count, user_directed, lobby_interaction)

    def vote_by_instance(self, policy_instance, count=1, user_directed=False, lobby_interaction=False):
        if policy_instance.vote_count_statistic is not None:
            policy_list = None

            def get_current_rank():
                policy_list.sort(key=lambda policy: (self.get_stat_value(policy.vote_count_statistic), policy.guid64), reverse=True)
                return policy_list.index(policy_instance)

            if user_directed:
                factor = 0
                if policy_instance in self._balloted_policies:
                    policy_list = list(self._balloted_policies)
                    factor = 1
                elif policy_instance in self._up_for_repeal_policies:
                    policy_list = list(self._up_for_repeal_policies)
                    factor = -1
                orig_rank = get_current_rank()
            elif lobby_interaction:
                factor = 0
                if policy_instance in self._balloted_policies:
                    factor = 1
                elif policy_instance in self._up_for_repeal_policies:
                    factor = -1
            value = self.get_stat_value(policy_instance.vote_count_statistic) + count
            self.set_stat_value(policy_instance.vote_count_statistic, value)
            services.street_service().update_community_board_tooltip(self)
            if policy_list is not None:
                with telemetry_helper.begin_hook(civic_policy_telemetry_writer, TELEMETRY_HOOK_CIVIC_POLICY_VOTE) as hook:
                    hook.write_guid(TELEMETRY_FIELD_NEIGHBORHOOD, self.get_world_description_id())
                    hook.write_guid(TELEMETRY_FIELD_POLICY, policy_instance.guid64)
                    hook.write_guid(TELEMETRY_FIELD_VOTES, factor*value)
                    hook.write_guid(TELEMETRY_FIELD_PLAYER_VOTES, factor*count)
                    hook.write_guid(TELEMETRY_FIELD_OLD_RANK, orig_rank)
                    hook.write_guid(TELEMETRY_FIELD_NEW_RANK, get_current_rank())
            if user_directed and lobby_interaction:
                with telemetry_helper.begin_hook(civic_policy_telemetry_writer, TELEMETRY_HOOK_CIVIC_POLICY_LOBBY) as hook:
                    hook.write_guid(TELEMETRY_FIELD_NEIGHBORHOOD, self.get_world_description_id())
                    hook.write_guid(TELEMETRY_FIELD_POLICY, policy_instance.guid64)
                    hook.write_guid(TELEMETRY_FIELD_VOTES, factor*value)
            return True
        return False

    def _log_propose_telemetry(self, policy_instance, action):
        with telemetry_helper.begin_hook(civic_policy_telemetry_writer, TELEMETRY_HOOK_CIVIC_POLICY_PROPOSE) as hook:
            hook.write_guid(TELEMETRY_FIELD_NEIGHBORHOOD, self.get_world_description_id())
            hook.write_guid(TELEMETRY_FIELD_POLICY, policy_instance.guid64)
            hook.write_guid(TELEMETRY_FIELD_PROPOSE_ACTION, action)

    def add_to_ballot(self, policy_instance):
        if policy_instance.vote_count_statistic is not None and policy_instance not in self._balloted_policies:
            self._balloted_policies.add(policy_instance)
            self._log_propose_telemetry(policy_instance, TELEMETRY_FIELD_ACTION_VALUE_BALLOT)
            return True
        return False

    def add_for_repeal(self, policy):
        policy = self.get_policy_instance_for_tuning(policy.guid64)
        if policy is None:
            return False
        if policy not in self._enacted_policies:
            return False
        if policy in self._up_for_repeal_policies:
            return False
        self._up_for_repeal_policies.add(policy)
        self._log_propose_telemetry(policy, TELEMETRY_FIELD_ACTION_VALUE_REPEAL)
        return True

    def remove_from_repeal(self, policy):
        policy = self.get_policy_instance_for_tuning(policy.guid64)
        if policy is None:
            return False
        if policy not in self._up_for_repeal_policies:
            return False
        self._up_for_repeal_policies.discard(policy)
        self._log_propose_telemetry(policy, TELEMETRY_FIELD_ACTION_VALUE_CANCEL_REPEAL)
        return True

    def save(self, parent_data_msg):
        parent_data_msg.ClearField('policy_data')
        for policy in self._civic_policies:
            policy.save(parent_data_msg)
        parent_data_msg.ClearField('balloted_policy_ids')
        for policy in self._balloted_policies:
            parent_data_msg.balloted_policy_ids.append(policy.guid64)
        parent_data_msg.ClearField('up_for_repeal_policy_ids')
        for policy in self._up_for_repeal_policies:
            parent_data_msg.up_for_repeal_policy_ids.append(policy.guid64)
        parent_data_msg.ClearField('commodity_tracker')
        parent_data_msg.ClearField('statistics_tracker')
        parent_data_msg.ClearField('ranked_statistic_tracker')
        self.update_all_commodities()
        (commodites, _, ranked_statistics) = self.commodity_tracker.save()
        parent_data_msg.commodity_tracker.commodities.extend(commodites)
        regular_statistics = self.statistic_tracker.save()
        parent_data_msg.statistics_tracker.statistics.extend(regular_statistics)
        parent_data_msg.ranked_statistic_tracker.ranked_statistics.extend(ranked_statistics)

    def load(self, parent_data_msg):
        self.commodity_tracker.load(parent_data_msg.commodity_tracker.commodities)
        self.statistic_tracker.load(parent_data_msg.statistics_tracker.statistics)
        self.commodity_tracker.load(parent_data_msg.ranked_statistic_tracker.ranked_statistics)
        self._enacted_policies.clear()
        for policy_data in parent_data_msg.policy_data:
            policy = self.get_policy_instance_for_tuning(policy_data.policy_id)
            if policy:
                policy.load(policy_data)
                if policy.enacted:
                    self._enacted_policies.add(policy)
        for policy_id in parent_data_msg.balloted_policy_ids:
            policy = self.get_policy_instance_for_tuning(policy_id)
            if policy:
                self._balloted_policies.add(policy)
        for policy_id in parent_data_msg.up_for_repeal_policy_ids:
            policy = self.get_policy_instance_for_tuning(policy_id)
            if policy:
                self._up_for_repeal_policies.add(policy)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.CivicPolicyDailyRandomVoting:
            self.do_daily_vote()
        elif event == TestEvent.CivicPolicyOpenVoting:
            self.open_voting()
        elif event == TestEvent.CivicPolicyCloseVoting:
            self.close_voting()

    def get_influence(self, sim_info):
        tracker = BucksUtils.get_tracker_for_bucks_type(self.INFLUENCE_BUCK_TYPE, owner_id=sim_info.id, add_if_none=False)
        if tracker is None:
            return 0
        return tracker.get_bucks_amount_for_type(self.INFLUENCE_BUCK_TYPE)

    def modify_influence(self, sim_info, delta):
        if delta == 0:
            return
        tracker = BucksUtils.get_tracker_for_bucks_type(self.INFLUENCE_BUCK_TYPE, owner_id=sim_info.id, add_if_none=True)
        if tracker is None:
            return
        tracker.try_modify_bucks(self.INFLUENCE_BUCK_TYPE, delta)

    def populate_community_board_op(self, sim_info, op, target_id):
        op.sim_id = sim_info.id
        op.target_id = target_id
        op.influence_points = self.get_influence(sim_info)
        op.title = self.community_board_dialog_title()
        if hasattr(op, 'schedule_text'):
            op.schedule_text = self.get_schedule_text()
        for policy in self._enacted_policies:
            with ProtocolBufferRollback(op.enacted_policies) as enacted_policy:
                enacted_policy.policy_id = policy.guid64
                if policy in self._up_for_repeal_policies:
                    if policy.vote_count_statistic is None:
                        enacted_policy.count = 0
                    else:
                        enacted_policy.count = int(self.get_stat_value(policy.vote_count_statistic))
        for policy in self._balloted_policies:
            with ProtocolBufferRollback(op.balloted_policies) as balloted_policy:
                balloted_policy.policy_id = policy.guid64
                stat = policy.vote_count_statistic
                if stat is None:
                    balloted_policy.count = 0
                else:
                    balloted_policy.count = int(self.get_stat_value(stat))
                    balloted_policy.max_count = stat.max_value
        op.provider_type = self.provider_type_id
        op.new_policy_allowed = self.is_new_policy_allowed(sim_info)
        if not services.street_service().voting_open:
            op.policy_disabled_tooltip = self.COMMUNITY_BOARD_TEXT.voting_closed_policy_tooltip_text()
        if not self.is_eligible_voter(sim_info):
            op.disabled_tooltip = self.COMMUNITY_BOARD_TEXT.ineligible_voter_confirm_tooltip_text(sim_info)
            op.policy_disabled_tooltip = self.COMMUNITY_BOARD_TEXT.ineligible_voter_policy_tooltip_text(sim_info)

    def _on_add_picker_selected(self, dialog):
        tag_objs = dialog.get_result_tags()
        if not tag_objs:
            return
        num_tags = len(tag_objs)
        can_add_more = dialog.max_selectable.number_selectable - num_tags > 0
        if can_add_more:
            can_add_more = len(dialog.picker_rows) > num_tags
        op = CommunityBoardAddPolicy(tag_objs, dialog.target_sim.sim_id, can_add_more)
        Distributor.instance().add_op_with_no_owner(op)

    def create_add_policy_picker(self, sim_info, used_policy_ids):
        resolver = SingleSimResolver(sim_info)
        dialog = self.COMMUNITY_BOARD_TEXT.add_policy_picker(sim_info, resolver=resolver)
        for policy in self.get_dormant_policies():
            if policy.guid64 not in used_policy_ids:
                tooltip = lambda *_, tooltip=policy.display_description: tooltip(sim_info)
                dialog.add_row(BasePickerRow(name=policy.display_name(sim_info), icon=policy.display_icon, tag=policy.guid64, row_tooltip=tooltip))
        dialog.max_selectable.number_selectable = min(len(dialog.picker_rows), self.max_balloted_policy_count - len(self._balloted_policies) - len(used_policy_ids))
        dialog.set_target_sim(sim_info)
        dialog.add_listener(self._on_add_picker_selected)
        dialog.show_dialog()

    def handle_vote_interaction(self, sim_info, target_id, push_continuation):
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        target_object = services.object_manager().get(target_id)
        if not target_object:
            return
        for current_interaction in sim.si_state:
            interaction_target = current_interaction.target
            if interaction_target is None:
                pass
            else:
                if interaction_target.part_owner is target_object:
                    target_object = interaction_target
                    break
                if interaction_target.is_part and interaction_target is target_object:
                    break
        return
        if push_continuation:
            context = current_interaction.context.clone_for_continuation(current_interaction)
            autonomy_request = autonomy.autonomy_request.AutonomyRequest(sim, FullAutonomy, static_commodity_list=self.VOTING_CONTINUATION_AUTONOMY_COMMODITIES, object_list=(target_object,), insert_strategy=QueueInsertStrategy.NEXT, apply_opportunity_cost=False, is_script_request=True, ignore_user_directed_and_autonomous=True, context=context, si_state_view=sim.si_state, limited_autonomy_allowed=True, autonomy_mode_label_override='ParameterizedAutonomy', off_lot_autonomy_rule_override=UNLIMITED_AUTONOMY_RULE)
            autonomy_service = services.autonomy_service()
            results = autonomy_service.score_all_interactions(autonomy_request)
            chosen_interaction = autonomy_service.choose_best_interaction(results, autonomy_request)
            autonomy_request.invalidate_created_interactions(excluded_si=chosen_interaction)
            if chosen_interaction:
                target_affordance = current_interaction.generate_continuation_affordance(chosen_interaction.affordance)
                sim.push_super_affordance(target_affordance, target_object, context)
        current_interaction.cancel(FinishingType.NATURAL, 'Finished viewing board')

class BaseCivicPolicyProviderServiceMixin:
    CLOSE_VOTING_SUSPEND_REASON = 'Close Voting Suspend Reason'

    def __init__(self):
        self._voting_open_time = None
        self._voting_open_alarm = None
        self._voting_close_time = None
        self._voting_close_alarm = None
        self._voting_warn_alarm = None
        self._voting_daily_random_alarm = None
        self.enable_automatic_voting = True
        self._cache_suspended_key = None
        self._call_to_actions_needed = True

    @property
    def voting_open(self):
        now = services.time_service().sim_now
        return self._voting_open_time is not None and (self._voting_close_time is not None and (now.time_to_week_time(self._voting_close_time) != TimeSpan.ZERO and now.time_between_week_times(self._voting_open_time, self._voting_close_time)))

    @property
    def voting_open_time(self):
        return self._voting_open_time

    @property
    def voting_close_time(self):
        return self._voting_close_time

    def save_options(self, options_proto):
        options_proto.npc_civic_voting_enabled = self.enable_automatic_voting

    def load_options(self, options_proto):
        self.enable_automatic_voting = options_proto.npc_civic_voting_enabled

    def update_community_board_tooltip(self, provider=None):
        if provider is not None:
            current_zone = services.current_zone()
            if current_zone is None:
                return
            if provider.get_world_description_id() != services.get_world_description_id(current_zone.world_id):
                return
        for board in services.object_manager().get_objects_with_tag_gen(BaseCivicPolicyProvider.COMMUNITY_BOARD_TAG):
            board.update_object_tooltip()

    def _start_call_to_actions(self):
        if self._call_to_actions_needed:
            call_to_action_service = services.call_to_action_service()
            for call_to_action_fact in BaseCivicPolicyProvider.CALL_TO_ACTIONS:
                call_to_action_service.begin(call_to_action_fact, None)
            self._call_to_actions_needed = False

    def _show_notification(self, notification):
        active_sim = services.active_sim_info()
        if active_sim is None:
            return
        dialog = notification(active_sim, SingleSimResolver(active_sim))
        dialog.show_dialog()

    def _get_open_notification(self):
        return BaseCivicPolicyProvider.VOTING_OPEN_NOTIFICATION

    def _open_voting(self, suppress_dialog=False):
        self.update_community_board_tooltip()
        if not suppress_dialog:
            notification = self._get_open_notification()
            if notification is not None:
                self._show_notification(notification)
        services.get_event_manager().process_event(TestEvent.CivicPolicyOpenVoting)
        self._set_next_open_alarm()
        self._set_next_daily_random_voting_alarm()

    def _get_warn_notification(self):
        return BaseCivicPolicyProvider.VOTING_CLOSE_WARNING_NOTIFICATION

    def _warn_voting(self):
        notification = self._get_warn_notification()
        if notification is not None:
            self._show_notification(notification)
        self._set_next_warn_alarm()

    def _get_close_notification(self):
        return BaseCivicPolicyProvider.VOTING_CLOSE_NOTIFICATION

    def _close_voting(self):
        self.update_community_board_tooltip()
        notification = self._get_close_notification()
        if notification is not None:
            self._show_notification(notification)
        self.start_bulk_policy_update(BaseCivicPolicyProviderServiceMixin.CLOSE_VOTING_SUSPEND_REASON)
        services.get_event_manager().process_event(TestEvent.CivicPolicyCloseVoting)
        self.end_bulk_policy_update(BaseCivicPolicyProviderServiceMixin.CLOSE_VOTING_SUSPEND_REASON)
        self._set_next_close_alarm()

    def _do_daily_random_voting(self):
        if self.enable_automatic_voting and self.voting_open:
            services.get_event_manager().process_event(TestEvent.CivicPolicyDailyRandomVoting)
        self._set_next_daily_random_voting_alarm()
        self.update_community_board_tooltip()

    def _times_from_voting_time_of_week(self, relative_to_time, voting_time_of_week):
        day = voting_time_of_week.day
        hour = voting_time_of_week.hour
        minute = voting_time_of_week.minute
        time = create_date_and_time(days=day, hours=hour, minutes=minute)
        time_span = relative_to_time.time_to_week_time(time)
        return (time, time_span)

    def _start_voting_timer(self, voting_time_of_week, callback):
        (time, voting_time) = self._times_from_voting_time_of_week(services.time_service().sim_now, voting_time_of_week)
        if voting_time.in_ticks() <= 0:
            voting_time = TimeSpan(voting_time.in_ticks() + sim_ticks_per_week())
        voting_alarm = alarms.add_alarm(self, voting_time, callback, cross_zone=True)
        return (time, voting_alarm)

    def _set_next_daily_random_voting_alarm(self):
        if self._voting_daily_random_alarm is not None:
            alarms.cancel_alarm(self._voting_daily_random_alarm)
        if not self.voting_open:
            self._voting_daily_random_alarm = None
            return
        time_of_day = create_date_and_time(hours=0)
        now = services.time_service().sim_now
        daily_random_voting_span = now.time_till_next_day_time(time_of_day)
        if daily_random_voting_span == TimeSpan.ZERO:
            daily_random_voting_span += TimeSpan(sim_ticks_per_day())
        self._voting_daily_random_alarm = alarms.add_alarm(self, daily_random_voting_span, lambda _: self._do_daily_random_voting(), cross_zone=True)

    def _set_next_open_alarm(self):
        if self._voting_open_alarm is not None:
            alarms.cancel_alarm(self._voting_open_alarm)
        (self._voting_open_time, self._voting_open_alarm) = self._start_voting_timer(BaseCivicPolicyProvider.CIVIC_POLICY_SCHEDULE.voting_open, lambda _: self._open_voting())

    def _set_next_warn_alarm(self):
        if self._voting_warn_alarm is not None:
            alarms.cancel_alarm(self._voting_warn_alarm)
        if self._voting_close_time is None:
            return
        now = services.time_service().sim_now
        time_until_close = self._voting_close_time - now
        time_until_warning = time_until_close - BaseCivicPolicyProvider.CIVIC_POLICY_SCHEDULE.voting_close_warning_duration()
        if TimeSpan.ZERO < time_until_warning:
            self._voting_warn_alarm = alarms.add_alarm(self, time_until_warning, lambda _: self._warn_voting(), cross_zone=True)
        else:
            self._voting_warn_alarm = None

    def _set_next_close_alarm(self):
        if self._voting_close_alarm is not None:
            alarms.cancel_alarm(self._voting_close_alarm)
        (self._voting_close_time, self._voting_close_alarm) = self._start_voting_timer(BaseCivicPolicyProvider.CIVIC_POLICY_SCHEDULE.voting_close, lambda _: self._close_voting())

    def _reset_alarms(self):
        self._set_next_open_alarm()
        self._set_next_close_alarm()
        self._set_next_warn_alarm()
        self._set_next_daily_random_voting_alarm()

    def start_bulk_policy_update(self, suspend_reason):
        if self._cache_suspended_key is None:
            self._cache_suspended_key = suspend_reason
            msg = S4Common_pb2.BoolValue()
            distributor = Distributor.instance()
            msg.value = True
            distributor.add_event(Consts_pb2.MSG_SUSPEND_CACHE_UPDATES, msg, immediate=True)

    def end_bulk_policy_update(self, suspend_reason):
        if self._cache_suspended_key is suspend_reason:
            msg = S4Common_pb2.BoolValue()
            distributor = Distributor.instance()
            msg.value = False
            distributor.add_event(Consts_pb2.MSG_SUSPEND_CACHE_UPDATES, msg, immediate=True)
            self._cache_suspended_key = None
