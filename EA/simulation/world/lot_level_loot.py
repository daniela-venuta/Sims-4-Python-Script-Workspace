import build_buyimport servicesimport sims4from audio.primitive import TunablePlayAudio, play_tunable_audiofrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypeLotLevel, ParticipantTypeLotfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableFactory, TunablePercent, TunableList, TunableReference, TunableTuple, HasTunableSingletonFactory, AutoFactoryInit, TunableVariantfrom tag import TunableTagslogger = sims4.log.Logger('Lot Level Loot', default_owner='jmorrow')
class SetDustOverlayOp(BaseLootOperation):
    FACTORY_TUNABLES = {'dirtiness': TunablePercent(description='\n            The dirtiness of the overlay. The greater the value, the greater\n            the dirtiness.\n            ', default=50)}

    def __init__(self, *args, dirtiness, **kwargs):
        super().__init__(*args, **kwargs)
        self.dirtiness = dirtiness

    def _apply_to_subject_and_target(self, subject, target, resolver):
        zone_id = services.current_zone_id()
        if zone_id is None:
            return
        if subject is None:
            return
        lot = services.active_lot()
        point = lot.center
        success = build_buy.set_floor_feature(zone_id, build_buy.FloorFeatureType.DUST, point, subject.level_index, self.dirtiness)
        if not success:
            logger.error('Failed to set dust overlay on floor at location ({}, {}, {}) on level {}.', point.x, point.y, point.z, subject.level_index)

    @TunableFactory.factory_option
    def subject_participant_type_options(**kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeLotLevel, default_participant=ParticipantTypeLotLevel.ActorLotLevel, **kwargs)

class _Sims(HasTunableSingletonFactory, AutoFactoryInit):

    def generate_resolvers(self, desired_level_index):
        sim_info_man = services.sim_info_manager()
        if sim_info_man is None:
            return
        for sim in sim_info_man.instanced_sims_gen():
            if sim.routing_surface.secondary_id is desired_level_index:
                yield SingleSimResolver(sim.sim_info)

class _TaggedObjects(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tags': TunableTags(description='\n            A set of tags. Any objects on the lot level that have any of these\n            tags will be subject to the tuned Loot List (as long as they pass\n            the tuned Object Tests).\n            ')}

    def generate_resolvers(self, desired_level_index):
        obj_man = services.object_manager()
        if obj_man is None:
            return
        for obj in obj_man.get_objects_matching_tags(self.tags, match_any=True):
            if obj.routing_surface.secondary_id is desired_level_index:
                yield SingleObjectResolver(obj)

class ApplyLootToLotLevel(BaseLootOperation):
    FACTORY_TUNABLES = {'object_loot': TunableTuple(objects=TunableVariant(description='\n                The type of objects to target with the tuned Tests and Loot List.\n                ', sims=_Sims.TunableFactory(), tagged_objects=_TaggedObjects.TunableFactory(), default='sims'), tests=TunableTestSet(description='\n                Tests that will run on each object. For each object, if the \n                tests pass, the tuned Loot List will be applied to the object.\n                '), loot_list=TunableList(description='\n                A list of loot operations to apply to each object.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)))}

    def __init__(self, *args, object_loot, **kwargs):
        super().__init__(*args, **kwargs)
        self.objects = object_loot.objects
        self.tests = object_loot.tests
        self.loot_list = object_loot.loot_list

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        for resolver in self.objects.generate_resolvers(subject.level_index):
            if not self.tests.run_tests(resolver):
                pass
            else:
                for loot_action in self.loot_list:
                    loot_action.apply_to_resolver(resolver)

    @TunableFactory.factory_option
    def subject_participant_type_options(**kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeLotLevel, default_participant=ParticipantTypeLotLevel.ActorLotLevel, **kwargs)

class ApplyLootToAllLotLevels(BaseLootOperation):
    FACTORY_TUNABLES = {'loot_list': TunableList(description='\n            A list of loot operations to apply to each lot level in the lot.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}

    def __init__(self, *args, loot_list, **kwargs):
        super().__init__(*args, **kwargs)
        self.loot_list = loot_list

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        for lot_level in subject.lot_levels.values():
            resolver = SingleObjectResolver(lot_level)
            for loot_action in self.loot_list:
                loot_action.apply_to_resolver(resolver)

    @TunableFactory.factory_option
    def subject_participant_type_options(**kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeLot, default_participant=ParticipantTypeLot.Lot, **kwargs)

class PlayAudioStingOnLotLevel(BaseLootOperation):
    FACTORY_TUNABLES = {'audio_sting': TunablePlayAudio(description='\n            Audio sting to play.\n            ')}

    def __init__(self, *args, audio_sting, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_sting = audio_sting

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        lot = services.active_lot()
        if lot is None:
            return
        zone = services.current_zone()
        if zone is None:
            return
        if not zone.is_zone_running:
            return
        if subject.level_index == lot.display_level:
            play_tunable_audio(self.audio_sting, owner=None)

    @TunableFactory.factory_option
    def subject_participant_type_options(**kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeLotLevel, default_participant=ParticipantTypeLotLevel.ActorLotLevel, **kwargs)
