from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableInterval, TunableEnumEntryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.complex.staffed_object_situation_mixin import StaffedObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_types import SituationCreationUIOptionfrom tag import Tagimport sims4.loglogger = sims4.log.Logger('SalesTableVendorSituation', default_owner='rmccord')
class SalesTableSetupState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        if resolver.interaction.is_finishing_naturally:
            return self.owner.is_sim_in_situation(sim_info.get_sim_instance())
        return False

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._change_state(self.owner.tend_state())

class TendSalesTableState(CommonSituationState):

    def timer_expired(self):
        super().timer_expired()
        self.owner._change_state(self.owner.teardown_state())

class SalesTableTeardownState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        if resolver.interaction.is_finishing_naturally:
            return self.owner.is_sim_in_situation(sim_info.get_sim_instance())
        return False

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def timer_expired(self):
        self.owner._self_destruct()

class SalesTableVendorSituationMixin:
    INSTANCE_TUNABLES = {'setup_state': SalesTableSetupState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_setup_state'), 'tend_state': TendSalesTableState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_tend_state'), 'teardown_state': SalesTableTeardownState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_teardown_state'), 'vendor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the vendor.\n            '), 'sale_object_tags': TunableList(description='\n            A list of tags that tell us the object comes from the vendor. We\n            use these tags to find objects and destroy them when the situation\n            ends or the sim is removed.\n            ', tunable=TunableEnumEntry(description='\n                A tag that denotes the object comes from the craft sales vendor\n                and can be destroyed if the situation ends or the sim leaves.\n                ', tunable_type=Tag, default=Tag.INVALID)), 'number_of_sale_objects': TunableInterval(description='\n            ', tunable_type=int, default_lower=7, default_upper=10, minimum=1, maximum=15)}

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, SalesTableSetupState, factory=cls.setup_state), SituationStateData(2, TendSalesTableState, factory=cls.tend_state), SituationStateData(3, SalesTableTeardownState, factory=cls.teardown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.vendor_job_and_role_state.job, cls.vendor_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.setup_state())

class SalesTableVendorSituation(SalesTableVendorSituationMixin, SituationComplexCommon):
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
lock_instance_tunables(SalesTableVendorSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class StaffedSalesTableVendorSituation(StaffedObjectSituationMixin, SalesTableVendorSituation):
    pass
