from drama_scheduler.drama_node_types import DramaNodeTypefrom interactions import ParticipantType, ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableList, OptionalTunable, TunableFactory, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport servicesimport sims4import singletonslogger = sims4.log.Logger('DramaNode', default_owner='msundaram')
class FestivalContestSubmitElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'success_notification_by_rank': TunableList(description='\n            Notifications displayed if submitted object is large enough to be ranked in\n            the contest. Index refers to the place that the player is in currently.\n            1st, 2nd, 3rd, etc.\n            ', tunable=UiDialogNotification.TunableFactory(), tuning_group=GroupNames.UI), 'unranked_notification': OptionalTunable(description='\n            If enabled, notification displayed if submitted object is not large enough to rank in\n            the contest. \n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that will appear when the submitted object does not rank.\n                '), tuning_group=GroupNames.UI)}

    def _do_behavior(self):
        resolver = self.interaction.get_resolver()
        running_contests = services.drama_scheduler_service().get_running_nodes_by_drama_node_type(DramaNodeType.FESTIVAL)
        for contest in running_contests:
            if hasattr(contest, 'festival_contest_tuning'):
                if contest.festival_contest_tuning is None:
                    pass
                elif contest.is_during_pre_festival():
                    pass
                else:
                    obj = self.interaction.get_participant(ParticipantType.PickedObject)
                    if obj is None:
                        logger.error('{} does not have PickedObject participant', resolver)
                        return False
                    sim = self.interaction.sim
                    if sim is None:
                        logger.error('{} does not have sim participant', resolver)
                        return False
                    return self._enter_object_into_contest(contest, sim, obj, resolver)
        logger.error('{} no valid active Contest', resolver)
        return False

    def _enter_object_into_contest(self, contest, sim, obj, resolver):
        weight_statistic = contest.festival_contest_tuning._weight_statistic
        weight_tracker = obj.get_tracker(weight_statistic)
        if weight_tracker is None:
            logger.error('{} picked object does not have weight stat {}', resolver, weight_statistic)
            return False
        if contest.festival_contest_tuning._destroy_object_on_submit and not self._destroy_object(contest, sim, obj, resolver):
            return False
        elif not self._add_score(contest, sim, obj, resolver):
            return False
        return True

    def _destroy_object(self, contest, sim, obj, resolver):
        obj.make_transient()
        return True

    def _add_score(self, contest, sim, obj, resolver):
        weight_statistic = contest.festival_contest_tuning._weight_statistic
        weight_tracker = obj.get_tracker(weight_statistic)
        if weight_tracker is None:
            logger.error('{} picked object does not have weight stat {}', resolver, weight_statistic)
            return False
        rank = contest.add_score(sim.id, obj.id, weight_tracker.get_value(weight_statistic))
        if rank is not None:
            if rank >= len(self.success_notification_by_rank):
                return False
            notification = self.success_notification_by_rank[rank]
            dialog = notification(sim, target_sim_id=sim.id, resolver=resolver)
            dialog.show_dialog()
        elif self.unranked_notification is not None:
            dialog = self.unranked_notification(sim, target_sim_id=sim.id, resolver=resolver)
            dialog.show_dialog()
        return True

class FestivalContestAwardWinners(BaseLootOperation):
    FACTORY_TUNABLES = {'skip_if_no_entry': Tunable(description='\n            Skip showing the results if the player did not enter the contest.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, skip_if_no_entry=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._skip_if_no_entry = skip_if_no_entry

    def _apply_to_subject_and_target(self, subject, target, resolver):
        running_contests = services.drama_scheduler_service().get_running_nodes_by_drama_node_type(DramaNodeType.FESTIVAL)
        for contest in running_contests:
            if hasattr(contest, 'festival_contest_tuning'):
                if contest.festival_contest_tuning is None:
                    pass
                elif contest.is_during_pre_festival():
                    pass
                else:
                    show_fallback_dialog = contest.has_user_submitted_entry() if self._skip_if_no_entry else True
                    contest.award_winners(show_fallback_dialog=show_fallback_dialog)
                    return
        logger.error('No festival contest is currently running, cannot award winners')

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)
