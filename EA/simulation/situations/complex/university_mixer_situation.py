from situations.situation_complex import SituationComplex, CommonInteractionCompletedSituationState, CommonSituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom sims4.tuning.tunable import TunableReference, TunableEnumWithFilterfrom tag import Tagimport servicesfrom objects.object_manager import ObjectManagerfrom sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_request import exclusivity_comparefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_types import SituationCreationUIOptionfrom situations.situation import Situation
class _MixerParty(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.cleanup_party_state())

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self.owner.juice_keg is not None:
            self.owner._claim_object(self.owner.juice_keg.id)

class _CleanupJuiceKeg(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self.owner.juice_keg is None:
            self.owner._self_destruct()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

class _SetupJuiceKeg(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.mixer_party_state())

class UniversityMixerPartySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'juice_keg_bearer_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the bearer of the juice keg.\n            '), 'setup_juice_keg_state': _SetupJuiceKeg.TunableFactory(description='\n            The state to bring in the keg bearer and have the juice keg set up on the lot.\n            ', display_name='1. Setup Juice Keg State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'mixer_party_state': _MixerParty.TunableFactory(description='\n            The state to represent the party itself.\n            ', display_name='2. Mixer Party State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'cleanup_party_state': _CleanupJuiceKeg.TunableFactory(description='\n            The state to cleanup the juice keg and end the party\n            ', display_name='3. Party Cleanup State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'juice_keg_tag': TunableEnumWithFilter(description='\n            Tag used to find the juice keg supplied by the situation.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=Tag.INVALID, filter_prefixes=('func',))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._juice_keg_object_id = None

    def start_situation(self):
        super().start_situation()
        if self.juice_keg is not None:
            self._claim_object(self.juice_keg.id)
        self._change_state(self.setup_juice_keg_state())

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _SetupJuiceKeg, factory=cls.setup_juice_keg_state), SituationStateData(2, _MixerParty, factory=cls.mixer_party_state), SituationStateData(3, _CleanupJuiceKeg, factory=cls.cleanup_party_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.juice_keg_bearer_job_and_role.job, cls.juice_keg_bearer_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @property
    def juice_keg(self):
        object_manager = services.object_manager()
        juice_keg = None
        if self._juice_keg_object_id is not None:
            juice_keg = object_manager.get(self._juice_keg_object_id)
        if self.juice_keg_bearer is not None:
            for obj in object_manager.get_objects_with_tag_gen(self.juice_keg_tag):
                if obj.get_sim_owner_id() is self.juice_keg_bearer.id:
                    juice_keg = obj
                    self._juice_keg_object_id = juice_keg.id
                    break
        return juice_keg

    @property
    def juice_keg_bearer(self):
        sim = next(self.all_sims_in_job_gen(self.juice_keg_bearer_job_and_role.job), None)
        return sim
lock_instance_tunables(UniversityMixerPartySituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)