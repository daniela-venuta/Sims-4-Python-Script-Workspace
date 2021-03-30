import alarmsimport clockimport date_and_timeimport servicesimport sims4.resourcesfrom balloon.balloon_enums import BALLOON_TYPE_LOOKUP, BalloonTypeEnumfrom balloon.balloon_request import BalloonRequestfrom balloon.tunable_balloon import TunableBalloonfrom date_and_time import create_time_span, TimeSpanfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom interactions.utils.tunable_icon import TunableIconVariantfrom objects.components.types import PROXIMITY_COMPONENTfrom relationships.relationship_enums import SentimentSignTypefrom relationships.relationship_enums import SentimentDurationTypefrom relationships.relationship_track_tracker import RelationshipTrackTrackerfrom sims4.math import Thresholdfrom sims4.random import weighted_random_itemfrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import Tunable, TunableRange, TunableSimMinute, TunableTuple, TunableEnumEntry, TunableResourceKeyfrom tunable_multiplier import TunableMultiplierlogger = sims4.log.Logger('Relationship', default_owner='boster')
class DelayedBalloonInfo:

    def __init__(self):
        self.owner_sim_info = None
        self.track_type = None
        self.icon_info = None
        self.alarm_handle = None

class SentimentTrackTracker(RelationshipTrackTracker):
    SENTIMENT_CAP = TunableRange(description='\n        Maximum amount of sentiments that one sim can have towards another individual sim.\n        If someone wants to make this a value higher than 4, please sync up with a GPE lead first.\n        ', tunable_type=int, default=4, maximum=4, minimum=1)
    PROXIMITY_LOOT_COOLDOWN = TunableSimMinute(description='\n        The number of seconds until a sim is allowed to attempt to roll to get a buff from a SentimentTrack that \n        they have towards a specific sim.\n        ', default=100, minimum=0)
    PROXIMITY_NO_LOOT_CHANCE_WEIGHT = TunableMultiplier.TunableFactory(description='\n        The weighted chance that a sim may roll to not get a loot when coming in proximity of a sim that they have a\n        sentiment towards.\n        ')
    NEGATIVE_LONG_TERM_VALUE_THRESHOLD = Tunable(description='\n        The SentimentTrack value below which a positive long-term SentimentTrack can replace a negative \n        long-term SentimentTrack\n        ', tunable_type=int, default=1)
    LONG_TERM_VALUE_ADJUSTMENT = Tunable(description='\n        When failing to add a positive long-term SentimentTrack. This will be a whole number value added to the \n        negative long term SentimentTrack value.\n        ', tunable_type=int, default=1)
    NEGATIVE_SHORT_TERM_VALUE_THRESHOLD = Tunable(description='\n        SentimentTrack value below which a positive short-term SentimentTrack can\n        replace all negative short-term SentimentTracks\n        ', tunable_type=int, default=1)
    SHORT_TERM_VALUE_ADJUSTMENT = Tunable(description='\n        When failing to add a positive short-term SentimentTrack. This will be a whole number value added to the \n        existing negative short term SentimentTrack values.\n        ', tunable_type=int, default=1)
    BALLOON_DATA = TunableTuple(description='\n        Information that will be used to create a balloon when a sentiment gets added to a sim.\n        ', balloon_type=TunableEnumEntry(description='\n            The visual style of the balloon background.\n            ', tunable_type=BalloonTypeEnum, default=BalloonTypeEnum.SENTIMENT), icon=TunableIconVariant(description='\n            The Icon that will be showed within the balloon.\n            '), overlay=TunableResourceKey(description='\n            The overlay for the balloon, if present.\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True), duration=TunableRange(description='\n            The duration, in seconds, that a balloon should last.\n            ', tunable_type=float, default=TunableBalloon.BALLOON_DURATION, minimum=0.0), balloon_view_offset=TunableVector3(description='\n            The Vector3 offset from the balloon bone to the thought balloon. \n            ', default=TunableVector3.DEFAULT_ZERO), balloon_stack_window_seconds=TunableRange(description='\n            The delay in seconds that a sentiment bubble should wait and see\n            if similar sentiments on the same sim is triggered (generally towards multiple other sims).\n            If similar sentiments are detected within the time window, they will be condensed into a \n            "multi-sentiment" visual treatment. Numbers are in sim seconds \n            ', tunable_type=int, default=10, minimum=10), multi_sim_icon=TunableResourceKey(description='\n            The Icon that will be showed within the balloon for sentiments towards multiple sims.\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True))
    _balloon_info_map = {}
    __slots__ = 'proximity_cooldown_end_time'

    def __init__(self, rel_data):
        super().__init__(rel_data)
        self.proximity_cooldown_end_time = None

    def on_sim_creation(self, sim):
        if len(self) > 0:
            instanced_actor = services.sim_info_manager().get(self.rel_data.sim_id_a).get_sim_instance()
            if instanced_actor is sim:
                instanced_actor.get_component(PROXIMITY_COMPONENT).register_proximity_callback(self.rel_data.sim_id_b, self._on_target_in_proximity)

    def on_initial_startup(self):
        self.add_on_remove_callback(self._on_num_sentiments_changed)

    def _try_add_sentiment_longterm(self, new_track, current_short_term_list, current_long_term):
        if current_short_term_list[0].sign != new_track.sign:
            self._remove_sentiment_list(current_short_term_list)
            current_short_term_list = []
        if len(current_short_term_list) > 0 and current_long_term is None:
            if len(self) >= SentimentTrackTracker.SENTIMENT_CAP and len(current_short_term_list) > 0:
                self.remove_statistic(current_short_term_list[0].stat_type)
            return True
        if new_track.sign == current_long_term.sign or current_long_term.sign is SentimentSignType.POSITIVE:
            self.remove_statistic(current_long_term.stat_type)
            return True
        minutes_to_decay = current_long_term.get_decay_time(Threshold(value=0))
        if minutes_to_decay < SentimentTrackTracker.NEGATIVE_LONG_TERM_VALUE_THRESHOLD:
            self.remove_statistic(current_long_term.stat_type)
            return True
        self.add_value(current_long_term.stat_type, SentimentTrackTracker.LONG_TERM_VALUE_ADJUSTMENT)
        return False

    def _remove_sentiment_list(self, sentiment_list):
        for sentiment_track in sentiment_list:
            self.remove_statistic(sentiment_track.stat_type)

    def _try_add_sentiment_shortterm(self, new_track, current_short_term_list, current_long_term):
        if len(current_short_term_list) > 0:
            if new_track.sign == current_short_term_list[0].sign:
                if new_track.stat_type in current_short_term_list:
                    self.remove_statistic(new_track.stat_type)
                elif len(self) >= SentimentTrackTracker.SENTIMENT_CAP:
                    self.remove_statistic(current_short_term_list[0].stat_type)
                return True
            if new_track.sign is SentimentSignType.NEGATIVE:
                self._remove_sentiment_list(current_short_term_list)
                return True
            furthest_from_decay = current_short_term_list[-1]
            if self.get_value(furthest_from_decay.stat_type) < SentimentTrackTracker.NEGATIVE_SHORT_TERM_VALUE_THRESHOLD:
                self._remove_sentiment_list(current_short_term_list)
                return True
            for short_term_track in current_short_term_list:
                self.add_value(short_term_track.stat_type, SentimentTrackTracker.SHORT_TERM_VALUE_ADJUSTMENT)
            return False
        return current_long_term is None or SentimentTrackTracker.SENTIMENT_CAP >= 2

    def set_max(self, stat_type):
        stat = self.add_statistic(stat_type)
        if stat is not None:
            self.set_value(stat_type, stat.max_value)

    def add_statistic(self, new_track, owner=None, **kwargs):
        if self.rel_data.is_object_rel():
            logger.error('Error, can not apply a sentiment towards an object. \n                            Implement an ObjectSentimentTrackTracker class if we need to support\n                            sim->object sentiments')
            return
        current_short_term_list = []
        current_long_term = None
        for current_track in self:
            if current_track.duration == SentimentDurationType.LONG:
                current_long_term = current_track
            else:
                current_short_term_list.append(current_track)
        if current_short_term_list:
            current_short_term_list.sort(key=lambda t: self.get_value(t))
        if new_track.duration == SentimentDurationType.LONG:
            can_add = self._try_add_sentiment_longterm(new_track, current_short_term_list, current_long_term)
        else:
            can_add = self._try_add_sentiment_shortterm(new_track, current_short_term_list, current_long_term)
        stat = None
        if can_add:
            stat = super().add_statistic(new_track, owner, **kwargs)
        if stat is not None:
            self._on_num_sentiments_changed()
            self.show_sentiment_balloon(stat)
        return stat

    def _cancel_alarm(self):
        balloon_info = SentimentTrackTracker._balloon_info_map.get(self.rel_data.sim_id_a)
        if balloon_info.alarm_handle is not None:
            alarms.cancel_alarm(balloon_info.alarm_handle)
            balloon_info.alarm_handle = None

    def _unregister_proximity_callback(self):
        actor_sim_info = services.sim_info_manager().get(self.rel_data.sim_id_a)
        if actor_sim_info is None:
            return
        instanced_actor = actor_sim_info.get_sim_instance()
        if instanced_actor:
            instanced_actor.get_component(PROXIMITY_COMPONENT).unregister_proximity_callback(self.rel_data.sim_id_b, self._on_target_in_proximity)

    def destroy(self):
        self._cancel_alarm()
        self._unregister_proximity_callback()
        if self.rel_data.sim_id_a in SentimentTrackTracker._balloon_info_map:
            del SentimentTrackTracker._balloon_info_map[self.rel_data.sim_id_a]
        super().destroy()

    def _show_delayed_balloon(self, handle):
        balloon_info = SentimentTrackTracker._balloon_info_map.get(self.rel_data.sim_id_a)
        (balloon_type, priority) = BALLOON_TYPE_LOOKUP[self.BALLOON_DATA.balloon_type]
        request = BalloonRequest(balloon_info.owner_sim_info, None, None, self.BALLOON_DATA.overlay, balloon_type, priority, self.BALLOON_DATA.duration, None, None, balloon_info.icon_info, self.BALLOON_DATA.balloon_view_offset, balloon_info.track_type)
        request.distribute()
        self._cancel_alarm()
        del SentimentTrackTracker._balloon_info_map[self.rel_data.sim_id_a]

    def show_sentiment_balloon(self, new_track_stat):
        balloon_owner_sim_info = services.object_manager().get(self.rel_data.sim_id_a)
        sentiment_target_sim_info = services.object_manager().get(self.rel_data.sim_id_b)
        if balloon_owner_sim_info is None or sentiment_target_sim_info is None:
            return
        balloon_info = SentimentTrackTracker._balloon_info_map.get(self.rel_data.sim_id_a)
        if balloon_info is None:
            SentimentTrackTracker._balloon_info_map[self.rel_data.sim_id_a] = balloon_info = DelayedBalloonInfo()
            resolver = SingleSimResolver(sentiment_target_sim_info)
            balloon_info.icon_info = self.BALLOON_DATA.icon(resolver, balloon_target_override=None)
            balloon_info.track_type = new_track_stat
            balloon_info.owner_sim_info = balloon_owner_sim_info
        else:
            balloon_info.icon_info = IconInfoData(self.BALLOON_DATA.multi_sim_icon)
        self._cancel_alarm()
        alarm_duration = TimeSpan(self.BALLOON_DATA.balloon_stack_window_seconds*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
        balloon_info.alarm_handle = alarms.add_alarm(self, alarm_duration, self._show_delayed_balloon)

    def set_value(self, stat_type, value, apply_initial_modifier=False, **kwargs):
        super().set_value(stat_type, value, apply_initial_modifier, **kwargs)

    def _on_num_sentiments_changed(self, *_):
        actor_sim_info = services.sim_info_manager().get(self.rel_data.sim_id_a)
        if actor_sim_info is None:
            return
        instanced_actor = actor_sim_info.get_sim_instance()
        if instanced_actor is not None:
            num_sentiments = len(self)
            if num_sentiments == 0:
                instanced_actor.get_component(PROXIMITY_COMPONENT).unregister_proximity_callback(self.rel_data.sim_id_b, self._on_target_in_proximity)
            elif num_sentiments == 1:
                target_sim_id = self.rel_data.sim_id_b
                callback = self._on_target_in_proximity
                proximity_component = instanced_actor.get_component(PROXIMITY_COMPONENT)
                if not proximity_component.has_proximity_callback(target_sim_id, callback):
                    proximity_component.register_proximity_callback(self.rel_data.sim_id_b, self._on_target_in_proximity)
                    self.proximity_cooldown_end_time = services.time_service().sim_now + create_time_span(minutes=self.PROXIMITY_LOOT_COOLDOWN)

    def _on_target_in_proximity(self, _):
        sim_now = services.time_service().sim_now
        if self.proximity_cooldown_end_time is not None and sim_now < self.proximity_cooldown_end_time:
            return
        self.proximity_cooldown_end_time = sim_now + clock.interval_in_sim_minutes(self.PROXIMITY_LOOT_COOLDOWN)
        actor_sim_info = services.sim_info_manager().get(self.rel_data.sim_id_a)
        target_sim_info = services.sim_info_manager().get(self.rel_data.sim_id_b)
        resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        weighted_loots = [(sentiment.proximity_loot_chance_weight.get_multiplier(resolver), sentiment.loot_on_proximity) for sentiment in self]
        weighted_loots.append((self.PROXIMITY_NO_LOOT_CHANCE_WEIGHT.get_multiplier(resolver), None))
        random_loots = weighted_random_item(weighted_loots)
        if random_loots is not None:
            for loot in random_loots:
                loot.apply_to_resolver(resolver)
