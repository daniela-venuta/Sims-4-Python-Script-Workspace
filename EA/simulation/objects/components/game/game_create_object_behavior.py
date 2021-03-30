from objects.system import create_objectfrom sims4.tuning.tunable import AutoFactoryInit, Tunable, TunableMapping, HasTunableFactory, TunableVariant, TunableReferenceimport servicesimport sims4logger = sims4.log.Logger('CreateObjectBehavior', default_owner='nabaker')
class CreateObjectBehavior(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'objects': TunableMapping(description='\n            Mapping of object definition to where to create it.\n            ', key_type=TunableReference(description='\n                The definition of the object that will be created/destroyed/altered\n                by the game.\n                ', manager=services.definition_manager()), value_type=TunableVariant(description='\n                The slot on the parent object where the target_game_object object should go. This\n                may be either the exact name of a bone on the parent object or a\n                slot type, in which case all the slots of the specified type\n                in which the child object fits will be used.\n                ', by_name=Tunable(description='\n                    The exact name of a slot on the parent object in which the object should go.  \n                    ', tunable_type=str, default='_ctnm_'), by_reference=TunableReference(description='\n                    A particular slot type in which the target game object should go.\n                    Enough objects will be created to fill all the slots.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))))}

    def on_player_added(self, sim, target):
        pass

    def on_setup_game(self, game_object):
        for (target_object, parent_slot) in self.objects.items():
            bone_name_hash = None
            slot_types = None
            if isinstance(parent_slot, str):
                bone_name_hash = sims4.hash_util.hash32(parent_slot)
            else:
                slot_types = {parent_slot}
            for runtime_slot in game_object.get_runtime_slots_gen(slot_types=slot_types, bone_name_hash=bone_name_hash):
                valid_object_in_slot = False
                child_objects = runtime_slot.children
                for child in child_objects:
                    if child.definition.id != target_object.id:
                        logger.warn('Incorrect object {} already in slot {} of game object {}', child, parent_slot, game_object)
                        child.set_parent(None)
                        child.destroy(source=self, cause='GameComponent: Invalid object in slot being destroyed.')
                    else:
                        valid_object_in_slot = True
                if valid_object_in_slot or runtime_slot.is_valid_for_placement(definition=target_object, objects_to_ignore=child_objects):
                    runtime_slot.add_child(create_object(target_object))
                else:
                    logger.warn("The target object {} slot {} isn't valid for placement", game_object, parent_slot, owner='nbaker')

    def on_game_ended(self, winning_team, game_object):
        for (target_object, parent_slot) in self.objects.items():
            bone_name_hash = None
            slot_types = None
            if isinstance(parent_slot, str):
                bone_name_hash = sims4.hash_util.hash32(parent_slot)
            else:
                slot_types = {parent_slot}
            for runtime_slot in game_object.get_runtime_slots_gen(slot_types=slot_types, bone_name_hash=bone_name_hash):
                child_objects = runtime_slot.children
                for child in child_objects:
                    if child.definition.id != target_object.id:
                        logger.warn('Incorrect object {} already in slot {} of game object {}', child, parent_slot, game_object)
                    else:
                        child.set_parent(None)
                        child.destroy(source=self, cause='GameComponent: Invalid object in slot being destroyed.')

    def on_player_removed(self, sim, from_game_ended=False):
        pass

    def additional_anim_overrides_gen(self):
        pass
