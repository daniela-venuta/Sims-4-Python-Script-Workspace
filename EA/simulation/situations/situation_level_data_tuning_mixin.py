import sims4from collections import namedtuplefrom rewards.reward import Rewardfrom sims4 import collectionsfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableTuple, TunableEnumEntry, TunableRange, TunableResourceKeyfrom sims4.utils import flexmethodfrom situations.situation_types import SituationMedallogger = sims4.log.Logger('SituationLevelData')
class TunableSituationLevel(TunableTuple):

    def __init__(self, description='A single tunable Situation level.', **kwargs):
        super().__init__(medal=TunableEnumEntry(description='\n                The corresponding medal (Tin, Bronze, etc.) associated with this level.\n                ', tunable_type=SituationMedal, default=SituationMedal.TIN), score_delta=TunableRange(description='\n                The amount of score from the previous Situation Level that the\n                player need to acquire before the situation is considered in\n                this Situation Level.\n                ', tunable_type=int, default=30, minimum=0), level_description=TunableLocalizedString(description='\n                Description of situation at level. This message is passed to UI\n                whenever we complete the situation.\n                ', allow_none=True), reward=Reward.TunableReference(description="\n                The Reward received when reaching this level of the Situation.\n                To give a specific SituationJobReward for a specific job, \n                you can tune that information at SituationJob's rewards field.\n                ", allow_none=True), audio_sting_on_end=TunableResourceKey(description='\n                The sound to play when a situation ends at this level.\n                ', resource_types=(sims4.resources.Types.PROPX,), default=None, allow_none=True), icon=TunableResourceKey(description="\n                Icon that is displayed on the situation UI's progress bar when\n                this level has been reached. If left unspecified, icon will\n                default to a generic medal icon appropriate for the level.\n                ", resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True), description=description, **kwargs)

class SituationLevelDataTuningMixin:

    @staticmethod
    def _verify_situation_level_tuning(instance_class, tunable_name, source, bronze, gold, silver, tin):
        gold_reward = gold.reward
        if gold_reward is not None and gold_reward.reward_description is None:
            logger.error('Situation "{}" has a Gold tier reward that has no Reward Description tuned. Bronze and Silver are optional, but Gold requires a description.', source, owner='asantos')

    INSTANCE_TUNABLES = FACTORY_TUNABLES = {'_level_data': TunableTuple(tin=TunableSituationLevel(description='\n                Tuning for the Tin level of this situation.  This level has\n                a score delta of 0 as it is considered the default level\n                of any situation.\n                ', locked_args={'medal': SituationMedal.TIN, 'score_delta': 0}), bronze=TunableSituationLevel(description='\n                Tuning for the Bronze level of this situation.\n                ', locked_args={'medal': SituationMedal.BRONZE}), silver=TunableSituationLevel(description='\n                Tuning for the Silver level of this situation.\n                ', locked_args={'medal': SituationMedal.SILVER}), gold=TunableSituationLevel(description='\n                Tuning for the Gold level of this situation.\n                ', locked_args={'medal': SituationMedal.GOLD}), description='\n                Tuning for the different situation levels and rewards that\n                are associated with them.\n                ', verify_tunable_callback=_verify_situation_level_tuning)}
    SituationLevel = namedtuple('SituationLevel', ['min_score_threshold', 'level_data'])

    @staticmethod
    def get_aggregated_situation_level_data(level_data):
        result = []
        required_score = level_data.tin.score_delta
        result.append(SituationLevelDataTuningMixin.SituationLevel(required_score, level_data.tin))
        required_score += level_data.bronze.score_delta
        result.append(SituationLevelDataTuningMixin.SituationLevel(required_score, level_data.bronze))
        required_score += level_data.silver.score_delta
        result.append(SituationLevelDataTuningMixin.SituationLevel(required_score, level_data.silver))
        required_score += level_data.gold.score_delta
        result.append(SituationLevelDataTuningMixin.SituationLevel(required_score, level_data.gold))
        return result

    @flexmethod
    def get_level_data(cls, inst, medal:SituationMedal=SituationMedal.TIN):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.situation_level_data is None:
            return
        return inst_or_cls.situation_level_data[medal].level_data

    @flexmethod
    def get_level_min_threshold(cls, inst, medal:SituationMedal=SituationMedal.TIN):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.situation_level_data is None:
            return
        return inst_or_cls.situation_level_data[medal].min_score_threshold

    @flexmethod
    def get_level_icon(cls, inst, medal:SituationMedal=SituationMedal.TIN):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.situation_level_data is None:
            return
        return inst_or_cls.situation_level_data[medal].level_data.icon
