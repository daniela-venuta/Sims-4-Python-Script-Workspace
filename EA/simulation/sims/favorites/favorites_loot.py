from interactions.utils.loot_basic_op import BaseTargetedLootOperationimport sims4.logfrom sims4.tuning.tunable import Tunable, TunableVariant, TunableTuple, OptionalTunable, TunableReferencefrom tag import TunableTagimport serviceslogger = sims4.log.Logger('FavoritesLoot', default_owner='trevor')
class SetFavoriteLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'favorite_type': TunableVariant(description="\n            The type of favorite action to apply.\n            \n            Preferred Object: Sets the object as a sim's preferred object\n            to use for a specific func tag.\n            Favorite Stack: Sets the object's stack of the sim's favorites\n            in their inventory.\n            ", preferred_object=TunableTuple(description="\n                Data for setting this item as preferred.\n                Use tag to search in the Sim's inventory.\n                If you want to set an object by definition id that's not in inventory, \n                use favorite_definition also.\n                ", tag=TunableTag(description='\n                    The tag that represents this type of favorite.\n                    ', filter_prefixes=('Func',)), favorite_definition=OptionalTunable(description="\n                    Optional: An object reference that will be set as favorite instead \n                    of an object in the Sim's inventory.\n                    ", tunable=TunableReference(manager=services.definition_manager()))), locked_args={'favorite_stack': None}, default='preferred_object'), 'unset': Tunable(description='\n            If checked, this will unset the target as the favorite instead of setting\n            it.\n            ', tunable_type=bool, default=False)}

    def __init__(self, favorite_type, unset, **kwargs):
        super().__init__(**kwargs)
        self._favorite_type = favorite_type
        self._unset = unset

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Trying to run a SetFavorite loot without a valid Subject')
            return
        if target is None and (self._favorite_type is None or self._favorite_type.favorite_definition is None):
            logger.error('Trying to run a SetFavorite loot without a valid Target')
            return
        if target is not None and target.is_sim:
            logger.error("Trying to set a Sim {} as a Favorite of another Sim {}. This isn't possible.", target, subject)
            return
        favorites_tracker = subject.sim_info.favorites_tracker
        if favorites_tracker is None:
            logger.error('Trying to set a favorite for Sim {} but they have no favorites tracker.', subject)
            return
        if self._favorite_type is not None:
            if self._favorite_type.favorite_definition:
                definition_id = self._favorite_type.favorite_definition.id
                target_id = None
            else:
                definition_id = target.definition.id
                target_id = target.id
            if self._unset:
                favorites_tracker.unset_favorite(self._favorite_type.tag, target_id, definition_id)
            else:
                favorites_tracker.set_favorite(self._favorite_type.tag, target_id, definition_id)
            return
        if self._unset:
            favorites_tracker.unset_favorite_stack(target)
        else:
            favorites_tracker.set_favorite_stack(target)
        if target is not None:
            target.inventoryitem_component.get_inventory().push_inventory_item_stack_update_msg(target)
