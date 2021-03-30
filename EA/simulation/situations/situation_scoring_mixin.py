import sims4from distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom situations.situation_types import SituationMedallogger = sims4.log.Logger('Situations')
class SituationScoringMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._score = 0
        self.situation_level_data = None

    @property
    def score(self):
        return self._score

    def level_data_gen(self):
        for level in self.situation_level_data:
            yield level

    def get_level(self, score=None):
        if score is None:
            score = self._score
        effective_score = self._get_effective_score_for_levels(score)
        for level in self.level_data_gen():
            if effective_score < level.min_score_threshold:
                break
            last_level = level
        return last_level.level_data.medal

    def score_update_internal(self, situation, score_delta, should_display_score=None):
        if score_delta < self._score*-1:
            score_delta = self._score*-1
        if should_display_score is None:
            should_display_score = situation.is_user_facing and situation.should_display_score
        if should_display_score:
            if score_delta < 0:
                logger.error('Trying to add negetive score to a situation that is being displayed to the user.  If you want this functionality people talk to your producer as it is a feature.')
            target_score = self._score + score_delta
            current_level = self.get_level()
            target_level = self.get_level(score=target_score)
            if int(target_level) - int(current_level) > 1:
                skipped_level = current_level + 1
                while skipped_level < target_level:
                    level_threshold = self.get_level_min_threshold(skipped_level)
                    delta = level_threshold - self._score
                    situation.add_situation_score_update_message(self.build_situation_score_update_message_internal(delta=delta))
                    skipped_level += 1
            self._score = target_score
            situation.add_situation_score_update_message(self.build_situation_score_update_message_internal())
        else:
            self._score += score_delta
        return score_delta

    def build_situation_score_update_message_internal(self, delta=0, sim=None):
        from protocolbuffers import Situations_pb2
        msg = Situations_pb2.SituationScoreUpdate()
        msg.score = int(round(self._score + delta))
        if sim:
            msg.sim_id = sim.id
        else:
            msg.sim_id = 0
        msg.current_level = self.build_situation_level_update_message_internal(delta=delta)
        return msg

    def build_situation_level_update_message_internal(self, delta=0):
        from protocolbuffers import Situations_pb2
        level_msg = Situations_pb2.SituationLevelUpdate()
        current_level = self.get_level(score=self._score + delta)
        if current_level == SituationMedal.GOLD:
            new_lower_bound = self.get_level_min_threshold(current_level - 1)
            new_upper_bound = self.get_level_min_threshold(current_level)
        else:
            new_lower_bound = self.get_level_min_threshold(current_level)
            new_upper_bound = self.get_level_min_threshold(current_level + 1)
        level_msg.score_lower_bound = new_lower_bound
        level_msg.score_upper_bound = new_upper_bound
        level_msg.current_level = current_level
        icon = self.get_level_icon(current_level)
        if icon is not None:
            build_icon_info_msg(IconInfoData(icon_resource=icon), None, level_msg.level_icon)
        return level_msg
