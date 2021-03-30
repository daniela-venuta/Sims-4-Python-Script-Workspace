from build_buy import ObjectOriginLocationfrom interactions import ParticipantTypefrom objects import HiddenReasonFlagfrom objects.components.inventory_enums import InventoryTypefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableVariant, TunableEnumEntryimport build_buyimport servicesimport simsimport sims4.loglogger = sims4.log.Logger('Inventory', default_owner='tingyul')
def transfer_object_to_lot_or_object_inventory(obj, recipient_inventory, recipient_object=None):
    pre_add_func = None
    if recipient_object.is_sim:
        pre_add_func = lambda obj: obj.update_ownership(recipient_object)
    transfer_object_to_recipient_inventory(obj, recipient_inventory, pre_add_func=pre_add_func)

def transfer_object_to_recipient_inventory(obj, recipient_inventory, hidden=False, pre_add_func=None):
    if recipient_inventory is not None and recipient_inventory.can_add(obj, hidden=hidden):
        if pre_add_func is not None:
            pre_add_func(obj)
        recipient_inventory.system_add_object(obj)
    else:
        obj.set_household_owner_id(services.active_household_id())
        build_buy.move_object_to_household_inventory(obj, object_location_type=ObjectOriginLocation.SIM_INVENTORY)

class TunableInventoryOwner(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'inventory_owner': TunableVariant(lot_inventory_type=TunableEnumEntry(description='\n                The inventory of the tuned inventory type that\n                belongs to the lot.\n                ', tunable_type=InventoryType, default=InventoryType.UNDEFINED, invalid_enums=(InventoryType.UNDEFINED,)), participant=TunableEnumEntry(description='\n                The inventory belonging to the interaction participant.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object, invalid_enums=(ParticipantType.Invalid,)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_lot_inventory = None

    @property
    def is_lot_inventory(self):
        if self._is_lot_inventory is None:
            self._is_lot_inventory = isinstance(self.inventory_owner, InventoryType)
        return self._is_lot_inventory

    def get_owner(self, resolver=None):
        if not self.is_lot_inventory:
            if resolver is None:
                raise ValueError('Attempting to get an inventory owned by an participant without specifying a resolver')
                return
            return resolver.get_participant(self.inventory_owner)
        return self.inventory_owner

    def get_owner_inventory(self, resolver=None):
        owner = self.get_owner(resolver=resolver)
        if owner is None:
            logger.error('Cannot get the inventory from a None object.')
            return
        return get_object_or_lot_inventory(owner)

def get_object_or_lot_inventory(owner, household_id=None):
    if not isinstance(owner, InventoryType):
        if isinstance(owner, sims.sim_info.SimInfo):
            owner = owner.get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE)
            if owner is None:
                return
        return owner.inventory_component
    lot = services.active_lot()
    owner_inventories = lot.get_object_inventories(owner)
    if len(owner_inventories) > 1:
        from objects.components.inventory_type_tuning import InventoryTypeTuning
        if InventoryTypeTuning.is_shared_between_objects(owner):
            raise ValueError('Attempt to transfer into inventory type with multiple nonshared inventories: {}'.format(owner))
        if household_id is not None:
            owner_inventories = [inventory for inventory in owner_inventories if inventory.owner.get_household_owner_id() == household_id]
    if len(owner_inventories) != 1:
        raise ValueError('Attempt to transfer into inventory type with multiple nonshared inventories: {}'.format(owner))
    return owner_inventories[0]
