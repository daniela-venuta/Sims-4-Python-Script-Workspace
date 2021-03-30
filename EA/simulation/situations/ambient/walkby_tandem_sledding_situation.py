import itertoolsfrom filters.tunable import FilterTermTag, TunableAggregateFilterfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, TunableMapping, TunableEnumEntry, TunableEnumWithFilter, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobfrom situations.situation_types import SituationSerializationOption, SituationCreationUIOptionfrom tag import Tag, SPAWN_PREFIXfrom world.spawn_point import SpawnPointfrom world.spawn_point_enums import SpawnPointRequestReasonimport filters.tunableimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('WalkbyTandemSleddingSituation', default_owner='jedwards')SIMS_RAN_INTERACTION = 'sims_ran_interaction'
class GetSimsState(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

class GoToSportSlopeSituationState(CommonInteractionCompletedSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sims_ran_interaction = set()

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if reader is not None:
            self._sims_ran_interaction = set(reader.read_uint64s(SIMS_RAN_INTERACTION, ()))

    def save_state(self, writer):
        super().save_state(writer)
        writer.write_uint64s(SIMS_RAN_INTERACTION, self._sims_ran_interaction)

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, sim_info=None, **kwargs):
        self._sims_ran_interaction.add(sim_info.sim_id)
        if len(self._sims_ran_interaction) >= self.owner.get_sims_expected_to_be_in_situation():
            self._change_state(self.owner.sled_state())

class TandemSledSituationState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

class WalkbyTandemSleddingSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'group_filter': TunableAggregateFilter.TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            '), 'go_to_sport_slope_state': GoToSportSlopeSituationState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'sled_state': TandemSledSituationState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'sled_leader': TunableTuple(situation_job=SituationJob.TunableReference(description='\n                The Situation Job of the sled leader.\n                '), initial_role_state=RoleState.TunableReference(description='\n                The initial Role State of the sled leader.\n                ')), 'sled_passenger': TunableTuple(situation_job=SituationJob.TunableReference(description='\n                The Situation Job of the passenger.\n                '), initial_role_state=RoleState.TunableReference(description='\n                The initial Role State of the passenger.\n                ')), 'situation_job_mapping': TunableMapping(description='\n            A mapping of filter term tag to situation job.\n\n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular situation.\n\n            The situation job is the job that the Sim will be assigned to in\n            the background situation.\n            ', key_name='filter_tag', key_type=TunableEnumEntry(description='\n               The filter term tag returned with the filter results.\n               ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job', value_type=TunableReference(description='\n                The job the Sim will receive when added to the this situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), 'sim_spawner_tags': TunableList(description='\n            A list of tags that represent where to spawn Sims for this\n            Situation when they come onto the lot.  This tuning will be used\n            instead of the tuning on the jobs.\n            NOTE: Tags will be searched in order of tuning. Tag [0] has\n            priority over Tag [1] and so on.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=SPAWN_PREFIX))}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GetSimsState), SituationStateData.from_auto_factory(2, cls.go_to_sport_slope_state), SituationStateData.from_auto_factory(3, cls.sled_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.go_to_sport_slope_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.OPEN_STREETS

    def start_situation(self):
        super().start_situation()
        if self._guest_list.guest_info_count != self.group_filter.get_filter_count():
            self._self_destruct()
        else:
            self._change_state(GetSimsState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return cls.group_filter.get_filter_count()

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        instanced_sim_ids = [sim.id for sim in services.sim_info_manager().instanced_sims_gen()]
        auto_fill_blacklist_leader = situation_manager.get_auto_fill_blacklist(sim_job=cls.sled_leader.situation_job)
        auto_fill_blacklist_passenger = situation_manager.get_auto_fill_blacklist(sim_job=cls.sled_passenger.situation_job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, auto_fill_blacklist_leader, auto_fill_blacklist_passenger))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls.group_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            return
        if len(filter_results) != cls.group_filter.get_filter_count():
            return
        for result in filter_results:
            job = cls.situation_job_mapping.get(result.tag, None)
            if job is None:
                logger.error('Could not find job for tag:{} in situation {}', result.tag, cls)
            else:
                guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.DONT_CARE, job.sim_auto_invite_allow_priority))
        return guest_list

    def on_all_sims_spawned(self):
        self._change_state(self.go_to_sport_slope_state())

    @classmethod
    def _can_start_walkby(cls, lot_id:int):
        return True

    def _issue_requests(self):
        zone = services.current_zone()
        if SpawnPoint.ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags or SpawnPoint.VISITOR_ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags:
            lot_id = zone.lot.lot_id
        else:
            lot_id = None
        spawn_point = zone.get_spawn_point(lot_id=lot_id, sim_spawner_tags=self.sim_spawner_tags, spawn_point_request_reason=SpawnPointRequestReason.SPAWN)
        super()._issue_requests(spawn_point_override=spawn_point)
sims4.tuning.instances.lock_instance_tunables(WalkbyTandemSleddingSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)