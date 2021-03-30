from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, TunableTuple, TunableRange, Tunableimport sims4.logfrom event_testing.tests import TunableTestSetfrom objects.components import Component, componentmethodfrom objects.components.types import SITUATION_SCHEDULER_COMPONENTfrom scheduler import SituationWeeklyScheduleVariantfrom situations.situation_guest_list import SituationGuestListfrom tag import TunableTag, Tagimport serviceslogger = sims4.log.Logger('SituationSchedulerComponent', default_owner='mkartika')
class SituationSchedulerComponent(Component, HasTunableFactory, AutoFactoryInit, allow_dynamic=True, component_name=SITUATION_SCHEDULER_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.SituationSchedulerComponent):
    FACTORY_TUNABLES = {'object_based_situations_schedule': OptionalTunable(description='\n            If enabled, the object provides its own situation schedule.\n            ', tunable=TunableTuple(description='\n                Data associated with situations schedule.\n                ', tag=TunableTag(description='\n                    An object tag. If the object exist on the zone lot, situations\n                    will be scheduled. The basic assumption is that this tag matches\n                    one of the tags associated with this object, but this is not \n                    enforced.\n                    ', filter_prefixes=('func',)), situation_schedule=SituationWeeklyScheduleVariant(description='\n                    The schedule to trigger the different situations.\n                    ', pack_safe=True, affected_object_cap=True), schedule_immediate=Tunable(description='\n                    This controls the behavior of scheduler if the current time\n                    happens to fall within a schedule entry. If this is True, \n                    a start_callback will trigger immediately for that entry.\n                    If False, the next start_callback will occur on the next entry.\n                    ', tunable_type=bool, default=False), consider_off_lot_objects=Tunable(description='\n                    If True, consider all objects in lot and the open street for\n                    this object situation. If False, only consider objects on\n                    the active lot.\n                    ', tunable_type=bool, default=True), tests=TunableTestSet(description="\n                    Tests to determine if this Tag should be added to the active\n                    Zone Director's Situations Schedule.  Test is performed\n                    when the schedule is rebuilt.  This is currently on Zone\n                    Spin Up and Build Buy Exit.\n                    ")))}

    def __init__(self, *args, scheduler=None, **kwargs):
        if 'object_based_situations_schedule' not in kwargs:
            kwargs['object_based_situations_schedule'] = None
        super().__init__(*args, **kwargs)
        self._situation_scheduler = scheduler
        self._generated_situation_ids = set()

    @componentmethod
    def set_situation_scheduler(self, scheduler):
        self._destroy_situation_scheduler()
        self._situation_scheduler = scheduler

    @componentmethod
    def create_situation(self, situation_type, **params):
        if not situation_type.situation_meets_starting_requirements():
            return
        situation_manager = services.get_zone_situation_manager()
        self._cleanup_generated_situations(situation_manager)
        running_situation = self._get_same_situation_running(situation_manager, situation_type)
        if running_situation is not None:
            situation_manager.destroy_situation_by_id(running_situation.id)
        guest_list = situation_type.get_predefined_guest_list() or SituationGuestList(invite_only=True)
        merged_params = dict(params, guest_list=guest_list, user_facing=False, scoring_enabled=False, spawn_sims_during_zone_spin_up=True, creation_source=str(self), default_target_id=self.owner.id)
        situation_id = situation_manager.create_situation(situation_type, **merged_params)
        if situation_id is None:
            return
        self._generated_situation_ids.add(situation_id)

    def on_remove(self, *_, **__):
        self.destroy_scheduler_and_situations()

    def destroy_scheduler_and_situations(self):
        self._destroy_situation_scheduler()
        self._destroy_generated_situations()

    def _cleanup_generated_situations(self, situation_manager):
        for situation_id in list(self._generated_situation_ids):
            running_situation = situation_manager.get(situation_id)
            if running_situation is None:
                self._generated_situation_ids.remove(situation_id)

    def _get_same_situation_running(self, situation_manager, situation_type):
        for situation_id in self._generated_situation_ids:
            running_situation = situation_manager.get(situation_id)
            if situation_type is type(running_situation):
                return running_situation

    def _destroy_situation_scheduler(self):
        if self._situation_scheduler is not None:
            self._situation_scheduler.destroy()
            self._situation_scheduler = None

    def _destroy_generated_situations(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._generated_situation_ids:
            situation_manager.destroy_situation_by_id(situation_id)
        self._generated_situation_ids.clear()

    @property
    def can_remove_component(self):
        return not hasattr(self, 'object_based_situations_schedule') or (self.object_based_situations_schedule is None or (self.object_based_situations_schedule.tag == Tag.INVALID or not self.object_based_situations_schedule.situation_schedule))

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.SituationSchedulerComponent
        component_data = persistable_data.Extensions[protocols.PersistableSituationSchedulerComponent.persistable_data]
        if self._generated_situation_ids:
            component_data.situation_ids.extend(self._generated_situation_ids)
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        component_data = persistable_data.Extensions[protocols.PersistableSituationSchedulerComponent.persistable_data]
        for situation_id in component_data.situation_ids:
            self._generated_situation_ids.add(situation_id)
