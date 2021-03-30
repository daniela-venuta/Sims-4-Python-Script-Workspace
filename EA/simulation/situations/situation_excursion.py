import randomimport servicesimport sims4import situationsimport telemetry_helperfrom event_testing.resolver import SingleSimResolverfrom sims4.random import weighted_random_itemfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableMapping, Tunable, TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.custom_states.custom_states_common_tuning import RandomWeightedSituationStateKey, TimeBasedSituationStateKeyfrom situations.custom_states.custom_states_situation import BaseCustomStatesSituationfrom situations.situation import Situationfrom situations.situation_excursion_activity import TunableExcursionActivitySnippetfrom situations.situation_level_data_tuning_mixin import SituationLevelDataTuningMixinfrom situations.situation_types import SituationSerializationOptionlogger = sims4.log.Logger('Excursions', default_owner='miking')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_SITUATION_ACTIVITY = 'ACTV'TELEMETRY_FIELD_SITUATION_TYPE = 'type'TELEMETRY_FIELD_SITUATION_LOT_ID = 'hlid'TELEMETRY_FIELD_SITUATION_ID = 'stid'TELEMETRY_FIELD_SITUATION_SCORE = 'stsc'TELEMETRY_FIELD_SITUATION_ACTIVITY_SCORE = 'ascr'TELEMETRY_FIELD_SITUATION_ACTIVITY_KEY = 'atid'TELEMETRY_FIELD_SITUATION_TELEMETRY_EVENT = 'mmnt'TELEMETRY_FIELD_SITUATION_VENUE_TYPE = 'venu'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)
class ExcursionSituation(BaseCustomStatesSituation):
    INSTANCE_TUNABLES = {'_activities': TunableMapping(description='\n            A tunable mapping between activity keys and activities.\n            ', key_name='Activity Key', key_type=Tunable(description='\n                The key of this activity.  This key will be used when attempting to transition between different\n                situation states.\n                ', tunable_type=str, default=None), value_name='Activity', value_type=TunableExcursionActivitySnippet(description='\n                The activity that is tied to this key.\n                '), tuning_group=GroupNames.CORE), '_starting_activity': TunableVariant(description='\n            The starting activity of this situation.\n            ', random_starting_activity=RandomWeightedSituationStateKey.TunableFactory(), time_based=TimeBasedSituationStateKey.TunableFactory(), default='random_starting_activity', tuning_group=GroupNames.CORE)}
    REMOVE_INSTANCE_TUNABLES = ('compatible_venues', 'duration', 'duration_randomizer') + Situation.SITUATION_SCORING_REMOVE_INSTANCE_TUNABLES
    CURRENT_ACTIVITY_KEY = 'current_activity_key'
    ACTIVITY_SCORE = 'activity_score'
    HAVE_RECEIVED_ACTIVITY_REWARDS = 'have_received_activity_rewards'
    HAVE_APPLIED_ACTIVITY_SETUPS = 'have_applied_activity_setups'
    APPLIED_ACTIVITY_SETUPS_COUNT = 'applied_activity_setups_count'
    APPLIED_ACTIVITY_SETUPS_CLUSTER_KEY = 'applied_activity_setups_cluster_key'
    APPLIED_ACTIVITY_SETUPS_SETUP_KEY = 'applied_activity_setups_setup_key'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._applied_activity_setups = None
        self._current_activity = None
        self._current_activity_key = None
        self._have_received_activity_rewards = False
        self._is_traveling = False

    @property
    def current_activity(self):
        return self._current_activity

    @property
    def current_activity_key(self):
        return self._current_activity_key

    @classproperty
    def allow_user_facing_goals(cls):
        return True

    def get_main_goal(self, **kwargs):
        if self.current_activity.main_goal is not None:
            return self.current_activity.main_goal(**kwargs)
        else:
            return

    def get_main_goal_audio_sting(self):
        return self.current_activity.main_goal_audio_sting

    def get_minor_goal_chains(self):
        return self.current_activity.get_minor_goal_chains()

    def get_goal_sub_text(self):
        return self.current_activity.goal_sub_text

    def get_goal_button_text(self):
        return self.current_activity.goal_button_text

    @property
    def is_goal_button_enabled(self):
        return self.can_advance_to_next_activity()

    @classmethod
    def get_possible_zone_ids_for_situation(cls, host_sim_info=None, guest_ids=None):
        possible_zones = []
        starting_activity_key = cls._starting_activity()
        if starting_activity_key is not None:
            starting_activity = cls._activities.get(starting_activity_key)
            if starting_activity is not None:
                activity = starting_activity()
                possible_zones.extend(activity.get_possible_zone_ids_for_situation_activity())
        return possible_zones

    def _get_duration(self):
        if self._seed.duration_override is not None:
            return self._seed.duration_override
        else:
            return self._get_activity_duration()

    def _get_activity_duration(self):
        return self.current_activity.duration + random.randint(0, self.current_activity.duration_randomizer)

    def _situation_timed_out(self, _):
        logger.debug('Situation activity time expired: {}', self)
        if self.can_advance_to_next_activity() and self.current_activity.timer_expired_dialog is not None:
            resolver = SingleSimResolver(self.initiating_sim_info)
            dialog = self.current_activity.timer_expired_dialog(self.initiating_sim_info, resolver=resolver)
            dialog.show_dialog(on_response=self._handle_timer_expired_dialog)
        else:
            self.try_advance_to_next_activity()

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_string16(ExcursionSituation.CURRENT_ACTIVITY_KEY, self._current_activity_key)
        writer.write_uint32(ExcursionSituation.ACTIVITY_SCORE, self.current_activity.score)
        writer.write_bool(ExcursionSituation.HAVE_RECEIVED_ACTIVITY_REWARDS, self._have_received_activity_rewards)
        if self._applied_activity_setups is not None:
            setups_count = len(self._applied_activity_setups)
            writer.write_uint32(ExcursionSituation.APPLIED_ACTIVITY_SETUPS_COUNT, setups_count)
            for i in range(0, setups_count):
                (cluster_key, setup_key) = self._applied_activity_setups[i]
                writer.write_string16(ExcursionSituation.APPLIED_ACTIVITY_SETUPS_CLUSTER_KEY + str(i), cluster_key)
                writer.write_string16(ExcursionSituation.APPLIED_ACTIVITY_SETUPS_SETUP_KEY + str(i), setup_key)

    @property
    def situation_states(self):
        return self.current_activity.situation_states

    def get_starting_situation_state(self):
        return self.current_activity.get_starting_situation_state()

    def start_situation(self):
        starting_activity_key = self._starting_activity()
        self.start_activity(starting_activity_key)
        self._try_apply_activity_setups()
        super().start_situation()
        self.send_activity_telemetry('start')

    def load_situation(self):
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            activity_key = reader.read_string16(ExcursionSituation.CURRENT_ACTIVITY_KEY, None)
            if not self.start_activity(activity_key):
                return False
            activity_score = reader.read_uint32(ExcursionSituation.ACTIVITY_SCORE, 0)
            self.current_activity.set_score(activity_score)
            self._have_received_activity_rewards = reader.read_bool(ExcursionSituation.HAVE_RECEIVED_ACTIVITY_REWARDS, False)
            setups_count = reader.read_uint32(ExcursionSituation.APPLIED_ACTIVITY_SETUPS_COUNT, None)
            if setups_count is not None:
                self._applied_activity_setups = []
                for i in range(0, setups_count):
                    cluster_key_token = ExcursionSituation.APPLIED_ACTIVITY_SETUPS_CLUSTER_KEY + str(i)
                    setup_key_token = ExcursionSituation.APPLIED_ACTIVITY_SETUPS_SETUP_KEY + str(i)
                    cluster_key = reader.read_string16(cluster_key_token, None)
                    setup_key = reader.read_string16(setup_key_token, None)
                    if self.current_activity.request_activity_setup(cluster_key, setup_key):
                        key_pair = (cluster_key, setup_key)
                        self._applied_activity_setups.append(key_pair)
            self._try_apply_activity_setups()
        return super().load_situation()

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        total_num_sims = self.get_num_sims_in_job()
        if total_num_sims == 1:
            self.refresh_situation_goals()

    def score_update(self, score_delta, should_display_score=None):
        self.current_activity.score_update_internal(self, score_delta, should_display_score)
        score_delta = super().score_update(score_delta, False)
        return score_delta

    def on_remove(self):
        if not self._is_traveling:
            self.try_give_cancellation_rewards_for_current_activity()
        super().on_remove()

    def _get_score_for_ui(self):
        return self.current_activity.score

    @property
    def end_audio_sting(self):
        current_level = self.current_activity.get_level()
        level_data = self.current_activity.get_level_data(current_level)
        if level_data is not None and level_data.audio_sting_on_end is not None:
            return level_data.audio_sting_on_end
        else:
            return

    def build_situation_score_update_message(self, delta=0, sim=None):
        return self.current_activity.build_situation_score_update_message_internal(delta, sim)

    def build_situation_level_update_message(self, delta=0):
        return self.current_activity.build_situation_level_update_message_internal(delta)

    def _gsi_additional_data_gen(self):
        yield ('Current Activity Key', self._current_activity_key)
        if self.current_activity:
            yield ('Current Activity Score', str(self.current_activity.score))
        if self._applied_activity_setups:
            for (cluster_key, setup_key) in self._applied_activity_setups:
                yield ('Activity Setup', cluster_key + ' -> ' + setup_key)

    def start_activity(self, activity_key):
        activity = self._activities.get(activity_key) if activity_key is not None else None
        if activity is None:
            logger.error("Excursion {} tried to start activity '{}', which does not exist.", str(self), activity_key)
            return False
        self.end_current_activity()
        self._current_activity = activity()
        self._current_activity.owner = self
        self._current_activity_key = activity_key
        self._current_activity.situation_level_data = SituationLevelDataTuningMixin.get_aggregated_situation_level_data(self._current_activity._level_data)
        self._goal_tracker = situations.situation_goal_tracker.SituationGoalTracker(self)
        self._applied_activity_setups = None
        self._have_received_activity_rewards = False
        return True

    def end_current_activity(self):
        if self._goal_tracker is not None:
            self._goal_tracker.destroy()
            self._goal_tracker = None

    def end_excursion(self, user_cancel=False):
        if user_cancel:
            self.try_give_cancellation_rewards_for_current_activity()
        else:
            self.try_give_rewards_for_current_activity()
        self._self_destruct()

    def on_situation_goal_button_clicked(self):
        if self.current_activity.move_on_dialog is not None:
            resolver = SingleSimResolver(self.initiating_sim_info)
            dialog = self.current_activity.move_on_dialog(self.initiating_sim_info, resolver=resolver)
            dialog.show_dialog(on_response=self._handle_move_on_dialog)
        else:
            self.try_advance_to_next_activity()

    def _handle_timer_expired_dialog(self, dialog):
        if dialog.accepted:
            self.try_advance_to_next_activity()
        else:
            self.end_excursion(user_cancel=True)

    def _handle_move_on_dialog(self, dialog):
        if dialog.accepted:
            self.try_advance_to_next_activity()

    def try_advance_to_next_activity(self):
        if self.can_advance_to_next_activity():
            self.advance_to_next_activity()
        else:
            self.end_excursion()

    def can_advance_to_next_activity(self):
        required_level = self.current_activity.next_activity_required_level
        current_level = self.current_activity.get_level()
        return current_level >= required_level

    def advance_to_next_activity(self):
        self.try_give_rewards_for_current_activity()
        next_activity_key = self._get_next_activity_key()
        if next_activity_key is None:
            self.excursion_complete()
            return True
        if not self.start_activity(next_activity_key):
            self._self_destruct()
            return False
        self._on_activity_changed()
        return True

    def try_give_rewards_for_current_activity(self):
        if self._have_received_activity_rewards or not services.current_zone().is_zone_shutting_down:
            if self.is_user_facing and self.should_give_rewards:
                medal = self.current_activity.get_level()
                logger.debug('Excursion {} giving rewards for activity: {} medal = {}', self, self._current_activity_key, medal)
                self._give_level_rewards_for_current_activity(medal)
                self._give_job_rewards_for_current_activity(medal)
            self._have_received_activity_rewards = True
            self.send_activity_telemetry('complete')

    def try_give_cancellation_rewards_for_current_activity(self):
        if not self._have_received_activity_rewards:
            if self.is_user_facing and self.should_give_rewards:
                logger.debug('Excursion {} giving cancellation rewards for activity: {}', self, self._current_activity_key)
                cancellation_rewards = self.current_activity.cancellation_rewards
                if cancellation_rewards is not None:
                    self._apply_job_rewards(cancellation_rewards)
            self._have_received_activity_rewards = True
            self.send_activity_telemetry('quit')

    def _give_level_rewards_for_current_activity(self, medal):
        level_data = self.current_activity.get_level_data(medal)
        if level_data is not None:
            level_reward = level_data.reward
            if level_reward is not None:
                level_reward.give_reward(self.initiating_sim_info)

    def _give_job_rewards_for_current_activity(self, medal):
        if self.current_activity.activity_job_rewards:
            level_job_data = self.current_activity.activity_job_rewards.get(medal, None)
            if level_job_data:
                self._apply_job_rewards(level_job_data)

    def _apply_job_rewards(self, job_data):
        for (sim, situation_sim) in self._situation_sims.items():
            job_type = situation_sim.current_job_type
            if not sim.is_selectable:
                if job_type.give_rewards_to_npc:
                    rewards = job_data.get(job_type, None)
                    if rewards is not None:
                        for reward in rewards:
                            if reward is not None:
                                reward.apply(sim, self)
            rewards = job_data.get(job_type, None)
            if rewards is not None:
                for reward in rewards:
                    if reward is not None:
                        reward.apply(sim, self)

    def excursion_complete(self):
        self._self_destruct()

    def _on_activity_changed(self):
        new_state_key = self.get_starting_situation_state()
        self.change_state_by_key(new_state_key)
        self._start_time = services.time_service().sim_now
        new_activity_duration = self._get_activity_duration()
        self.change_duration(new_activity_duration)
        self.send_activity_telemetry('start')
        if self._in_activity_zone():
            self._try_apply_activity_setups()
            self.refresh_situation_goals()
        else:
            self._is_traveling = True
            situation_manager = services.get_zone_situation_manager()
            situation_manager.travel_existing_situation(self, self.current_activity.zone_id)

    @property
    def zone_id(self):
        return self.current_activity.zone_id

    def _in_activity_zone(self):
        current_zone_id = services.current_zone_id()
        return current_zone_id == self.current_activity.zone_id

    def _get_next_activity_key(self):
        next_activity_choices = self.current_activity.next_activity
        resolver = SingleSimResolver(self.initiating_sim_info)
        weighted_activities = [(entry.weight.get_multiplier(resolver), entry.activity_key) for entry in next_activity_choices]
        if not weighted_activities:
            return
        next_activity_key = weighted_random_item(weighted_activities)
        return next_activity_key

    def _try_apply_activity_setups(self):
        if self._in_activity_zone():
            resolver = SingleSimResolver(self.initiating_sim_info)
            self._applied_activity_setups = self.current_activity.apply_activity_setups(resolver)

    def on_conditional_layer_loaded(self, conditional_layer):
        self.current_activity.on_conditional_layer_loaded(conditional_layer)

    def debug_advance_activity(self):
        return self.advance_to_next_activity()

    def debug_goto_activity(self, activity_key):
        if not self.start_activity(activity_key):
            return False
        self._on_activity_changed()
        return True

    def send_activity_telemetry(self, event_str):
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_SITUATION_ACTIVITY, sim=self.initiating_sim_info) as hook:
            hook.write_guid(TELEMETRY_FIELD_SITUATION_TYPE, self.guid64)
            lot_description_id = self.lot_description_id
            if lot_description_id is not None:
                hook.write_int(TELEMETRY_FIELD_SITUATION_LOT_ID, lot_description_id)
            hook.write_int(TELEMETRY_FIELD_SITUATION_ID, self.id)
            hook.write_int(TELEMETRY_FIELD_SITUATION_SCORE, self._score)
            hook.write_int(TELEMETRY_FIELD_SITUATION_ACTIVITY_SCORE, self.current_activity.score)
            hook.write_string(TELEMETRY_FIELD_SITUATION_ACTIVITY_KEY, self._current_activity_key)
            hook.write_string(TELEMETRY_FIELD_SITUATION_TELEMETRY_EVENT, event_str)
            venue_type = self.venue_type
            if venue_type is not None:
                hook.write_int(TELEMETRY_FIELD_SITUATION_VENUE_TYPE, venue_type)
lock_instance_tunables(ExcursionSituation, persistence_option=SituationSerializationOption.LOT)