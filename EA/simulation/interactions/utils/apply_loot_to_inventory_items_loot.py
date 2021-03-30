from event_testing.resolver import SingleActorAndObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableList, TunableReferenceimport servicesimport sims4.resourceslogger = sims4.log.Logger('ApplyLootToInventoryItemsLoot')
class ApplyLootToHiddenInventoryItemsLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'loot_list': TunableList(description='\n            A list of loot operations.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'object_tests': TunableTestSet(description='\n           Tests that will run on each object, if passes loot_actions will be run\n           with that object as Object participant.\n           ')}

    @classmethod
    def _verify_tuning_callback(cls):
        if not cls.object_tests:
            logger.error('No object tests tuned for {}', cls)

    def __init__(self, *args, loot_list, object_tests, **kwargs):
        super().__init__(*args, **kwargs)
        self.loot_list = loot_list
        self.object_tests = object_tests

    def _apply_to_subject_and_target(self, subject, target, resolver):
        source_inventory = None
        if subject.is_sim:
            sim = subject.get_sim_instance()
            if sim is not None:
                source_inventory = sim.inventory_component.hidden_storage
        else:
            source_inventory = subject.inventory_component.hidden_storage
        if source_inventory is None:
            return
        for obj in list(source_inventory):
            obj_resolver = SingleActorAndObjectResolver(subject, obj, source=self)
            if not self.object_tests.run_tests(obj_resolver):
                pass
            else:
                for loot_action in self.loot_list:
                    loot_action.apply_to_resolver(obj_resolver)
