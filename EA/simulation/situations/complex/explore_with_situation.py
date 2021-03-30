from collections import defaultdictfrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.loot import LootActionsfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableRange, TunableList, TunableReference, TunableTuplefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, CommonInteractionStartingSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionimport sims4import serviceslogger = sims4.log.Logger('Explore With Situation', default_owner='shipark')
class _PrepareToExploreState(CommonInteractionStartingSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        if self.situation_sims_running_interaction_of_interest():
            self.owner._change_state(self.owner.explore_state())

    def timer_expired(self):
        if self.num_situation_sims_running_interaction_of_interest() < self.owner.sim_running_interaction_threshold:
            self.owner._self_destruct()
            return
        for left_behind_situation_sim in self.sims_not_running_interaction_of_interest():
            self.owner._on_remove_sim_from_situation(left_behind_situation_sim)
        self.owner._change_state(self.owner.explore_state())

class _ExploreState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        leader_sim = self.owner.leader_sim()
        if leader_sim is None:
            logger.error('Failed to push Explore Interaction of Interest on None value leader sim in situation {}', self.owner)
            return
        prep_interaction_set = leader_sim.get_running_and_queued_interactions_by_tag_or_affordance_type(type_affordances=tuple(self.owner.prepare_to_explore_state._tuned_values.interaction_of_interest.affordances), tags=self.owner.prepare_to_explore_state._tuned_values.interaction_of_interest.tags)
        prep_interaction_id = None
        prep_interaction_target = None
        if not prep_interaction_set:
            logger.error('Failed to push Explore Interaction as a continuation of the Prep Interaction.')
        else:
            prep_interaction = prep_interaction_set.pop()
            prep_interaction_id = prep_interaction.id
            prep_interaction_target = prep_interaction.target
        prep_interaction.cancel(FinishingType.KILLED, cancel_reason_msg='Interaction canceled by the transition to the Explore State phase.')
        interaction_context = InteractionContext(leader_sim, InteractionContext.SOURCE_SCRIPT, Priority.Critical)
        explore_interaction_type = None
        resolver = SingleSimResolver(leader_sim.sim_info)
        for explore_test_and_interaction in self.owner.explore_interaction:
            if explore_test_and_interaction.test.run_tests(resolver):
                explore_interaction_type = explore_test_and_interaction.interaction
                break
        if explore_interaction_type is None:
            logger.error('None of the explore interactions passed tests.')
            self.owner._self_destruct()
            return
        enqueue_result = leader_sim.push_super_affordance(explore_interaction_type, prep_interaction_target, interaction_context)
        if enqueue_result and enqueue_result.interaction.is_finishing:
            logger.error('Leader :{} failed to push explore interaction', leader_sim)
            self.owner._self_destruct()
            return
        explore_interaction = enqueue_result.interaction
        explore_interaction.register_on_finishing_callback(self._on_explore_complete)

    def _on_explore_complete(self, *args):
        if self.owner is None:
            return
        situation_sims = set(self.owner.all_sims_in_situation_gen())
        rel_pair_granted = defaultdict(list)
        for sim in situation_sims:
            for target_sim in situation_sims:
                if sim is target_sim or not target_sim in rel_pair_granted[sim]:
                    if sim in rel_pair_granted[target_sim]:
                        pass
                    else:
                        rel_pair_granted[sim].append(target_sim)
                        resolver = DoubleSimResolver(sim.sim_info, target_sim.sim_info)
                        self.owner.rel_loot.apply_to_resolver(resolver)
        self.owner._self_destruct()

class ExploreWithSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'leader_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the leader.\n            '), 'guest_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the guests.\n            '), 'explore_interaction': TunableList(description='\n            A list of interaction/test tuples. The situation pushes the explore\n            interaction of the first tuple in the list with passing tests on the\n            leader. \n            ', tunable=TunableTuple(interaction=TunableReference(description='\n                    Interaction pushed on the leader during the explore state. When the explore interaction finishes,\n                    so does the situation.\n                    ', manager=services.affordance_manager()), test=TunableTestSet(description='\n                    Tests for whitelist channel states. Note that we also have tests on listen affordances, please\n                    make sure they are not duplicated so to save performance.\n                    '))), 'prepare_to_explore_state': _PrepareToExploreState.TunableFactory(description='\n            The initial situation state. The transition to the next phase occurs when all situation members\n            are running the interaction of interest.\n            ', display_name='1. Prepare to Explore State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'explore_state': _ExploreState.TunableFactory(description='\n            The main situation state. The leader is pushed to run the explore interaction and the phase completes\n            when it is over.\n            \n            Tuned loot is rewarded at the end.\n            ', display_name='2. Explore State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'rel_loot': LootActions.TunableReference(description='\n            Loot to apply to every situation sim with each other situation sim as a target.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'sim_running_interaction_threshold': TunableRange(description='\n            If the Pre-Explore situation state duration expires, the Explore situation state will be triggered only if\n            the sims-running-interaction-threshold is met. \n            ', tunable_type=int, default=2, minimum=1, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}

    @classmethod
    def default_job(cls):
        return cls.guest_job_and_role.job

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PrepareToExploreState, factory=cls.prepare_to_explore_state), SituationStateData(2, _ExploreState, factory=cls.explore_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.leader_job_and_role.job, cls.leader_job_and_role.role_state), (cls.guest_job_and_role.job, cls.guest_job_and_role.role_state)]

    def leader_sim(self):
        return next(self.all_sims_in_job_gen(self.leader_job_and_role.job), None)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.prepare_to_explore_state())

    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
lock_instance_tunables(ExploreWithSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)