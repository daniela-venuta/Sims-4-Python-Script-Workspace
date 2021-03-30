import sims4import telemetry_helperfrom interactions import ParticipantTypefrom interactions.utils.has_display_text_mixin import HasDisplayTextMixinfrom rewards.reward_enums import RewardDestinationfrom sims4.tuning.tunable import HasTunableFactoryfrom sims4.utils import constpropertyTELEMETRY_GROUP_UNLOCK = 'UNLK'TELEMETRY_HOOK_UNLOCK_ITEM = 'ITEM'TELEMETRY_FIELD_UNLOCK_SOURCE = 'trgr'TELEMETRY_FIELD_UNLOCK_ITEM = 'itid'unlock_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_UNLOCK)
class TunableRewardBase(HasTunableFactory, HasDisplayTextMixin):

    @constproperty
    def reward_type():
        pass

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, **kwargs):
        raise NotImplementedError

    def valid_reward(self, sim_info):
        return True

    @classmethod
    def send_unlock_telemetry(cls, sim_info, item_id, reward_source_guid):
        with telemetry_helper.begin_hook(unlock_telemetry_writer, TELEMETRY_HOOK_UNLOCK_ITEM, sim_info=sim_info) as hook:
            hook.write_int(TELEMETRY_FIELD_UNLOCK_SOURCE, reward_source_guid)
            hook.write_int(TELEMETRY_FIELD_UNLOCK_ITEM, item_id)

    def _get_display_text_tokens(self, resolver=None):
        if resolver is None:
            return super()._get_display_text_tokens()
        return resolver.get_participants(participant_type=ParticipantType.Actor)
