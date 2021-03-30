import itertoolsfrom filters.tunable import TunableAggregateFilterfrom role.role_state import RoleStatefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, TunableList, TunableEnumWithFilterfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobfrom situations.sub_situation_mixin import SubSituationOwnerMixinfrom tag import Tag, SPAWN_PREFIXfrom world.spawn_point import SpawnPointfrom world.spawn_point_enums import SpawnPointRequestReasonimport services
class GetSimsState(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

class WaitforSubSituationEnd(CommonSituationState):

    def timer_expired(self):
        self.owner._end_situation()

class SoakerFamilySituation(SituationComplexCommon, SubSituationOwnerMixin):
    INSTANCE_TUNABLES = {'group_filter': TunableAggregateFilter.TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            '), 'soaker': TunableTuple(situation_job=SituationJob.TunableReference(description='\n                The Situation Job of the soaker in this owner situation.\n                '), initial_role_state=RoleState.TunableReference(description='\n                The initial Role State of the soaker in this owner situation.\n                ')), 'soaker_situation': Situation.TunableReference(description='\n            Sub situation tuned for each of the soaker sims spawned.\n            ', tuning_group=GroupNames.SITUATION), 'sim_spawner_tags': TunableList(description='\n            A list of tags that represent where to spawn Sims for this\n            Situation when they come onto the lot.  This tuning will be used\n            instead of the tuning on the jobs.\n            NOTE: Tags will be searched in order of tuning. Tag [0] has\n            priority over Tag [1] and so on.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=SPAWN_PREFIX)), 'wait_for_sub_situation_state': WaitforSubSituationEnd.TunableFactory(description='\n            A state for getting the Sims to \n            ', locked_args={'allow_join_situation': False})}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sub_situation_ids = []

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GetSimsState), SituationStateData(2, WaitforSubSituationEnd, cls.wait_for_sub_situation_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.soaker.situation_job, cls.soaker.initial_role_state)]

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist_soaker = situation_manager.get_auto_fill_blacklist(sim_job=cls.soaker.situation_job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist_soaker))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls.group_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            return
        if len(filter_results) != cls.group_filter.get_filter_count():
            return
        for result in filter_results:
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, cls.soaker.situation_job, RequestSpawningOption.DONT_CARE, cls.soaker.situation_job.sim_auto_invite_allow_priority))
        return guest_list

    def start_situation(self):
        super().start_situation()
        self._change_state(GetSimsState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return cls.group_filter.get_filter_count()

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    def on_all_sims_spawned(self):
        self._change_state(self.wait_for_sub_situation_state())
        for sim_id in list(self._guest_list.get_invited_sim_ids()):
            guest_list = SituationGuestList(False)
            guest_list.add_guest_info(SituationGuestInfo(sim_id, self.soaker.situation_job, RequestSpawningOption.DONT_CARE, self.soaker.situation_job.sim_auto_invite_allow_priority))
            sub_situation_id = self._create_sub_situation(self.soaker_situation, guest_list=guest_list, user_facing=False)
            self._sub_situation_ids.append(sub_situation_id)

    def _on_sub_situation_end(self, sub_situation_id):
        self._end_situation()

    def _end_situation(self):
        for sim in self.all_sims_in_situation_gen():
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self._self_destruct()

    def _issue_requests(self):
        zone = services.current_zone()
        if SpawnPoint.ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags or SpawnPoint.VISITOR_ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags:
            lot_id = zone.lot.lot_id
        else:
            lot_id = None
        spawn_point = zone.get_spawn_point(lot_id=lot_id, sim_spawner_tags=self.sim_spawner_tags, spawn_point_request_reason=SpawnPointRequestReason.SPAWN)
        super()._issue_requests(spawn_point_override=spawn_point)
lock_instance_tunables(SoakerFamilySituation, exclusivity=BouncerExclusivityCategory.LEAVE)