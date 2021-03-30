import build_buyfrom bucks.bucks_enums import BucksTypefrom bucks.bucks_recycling import BucksRecyclingfrom bucks.bucks_utils import BucksUtilsfrom event_testing.resolver import SingleSimResolver, SingleActorAndObjectResolverfrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperation, BaseTargetedLootOperationfrom objects.gallery_tuning import ContentSourcefrom tunable_multiplier import TunableMultiplier, TunableStatisticModifierCurvefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesfrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableReference, Tunable, OptionalTunable, TunableList, TunableTupleimport sims4logger = sims4.log.Logger('Bucks', default_owner='tastle')
class BucksLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'bucks_type': TunableEnumEntry(description='\n            The type of Bucks to grant.\n            ', tunable_type=BucksType, default=BucksType.INVALID, pack_safe=True), 'amount': Tunable(description='\n            The amount of Bucks to award.\n            ', tunable_type=int, default=10), 'statistic_multipliers': TunableList(description='\n            Tunables for adding statistic based multipliers to the payout in the\n            format:\n            \n            amount *= statistic.value\n            ', tunable=TunableStatisticModifierCurve.TunableFactory()), 'force_refund': Tunable(description='\n            If enabled then if the total amount of bucks would be reduced to\n            a negative value, the bucks tracker will try to get back to zero\n            by refunding perks to make up the difference.\n            ', tunable_type=bool, default=False), 'notification': OptionalTunable(description='\n            If enabled and an amount is awarded, displays a dialog to the user.\n            \n            The notification will have access to the amount awarded as a \n            localization token. e.g. {0.GalacticCredits} \n            ', tunable=TunableUiDialogNotificationSnippet())}

    def __init__(self, bucks_type, amount, statistic_multipliers, force_refund=False, notification=None, **kwargs):
        super().__init__(**kwargs)
        self._bucks_type = bucks_type
        self._amount = amount
        self._statistic_multipliers = statistic_multipliers
        self._force_refund = force_refund
        self._notification = notification

    def _get_multiplier(self, resolver):
        amount_multiplier = 1
        if self._statistic_multipliers:
            for statistic_multiplier in self._statistic_multipliers:
                amount_multiplier *= statistic_multiplier.get_multiplier(resolver)
        return amount_multiplier

    def _apply_to_subject_and_target(self, subject, target, resolver):
        amount = int(round(self._amount*self._get_multiplier(resolver)))
        tracker = BucksUtils.get_tracker_for_bucks_type(self._bucks_type, owner_id=subject.id, add_if_none=amount > 0)
        if tracker is None:
            logger.error('Attempting to apply a BucksLoot op to the subject {} of amount {} but they have no tracker for that bucks type {}.', subject, amount, self._bucks_type)
            return
        result = tracker.try_modify_bucks(self._bucks_type, amount, force_refund=self._force_refund)
        if not result:
            logger.error("Failed to modify the Sim {}'s bucks of type {} by amount {}.", subject, self._bucks_type, amount)
        elif amount and self._notification:
            dialog = self._notification(subject, resolver=resolver)
            dialog.show_dialog(additional_tokens=(amount,))

class _UnlockPerkStrategy(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'unlock_for_free': Tunable(description='\n            When checked the perk can be awarded even if the Sim you are\n            awarding it to cannot afford the perk.\n            \n            When unchecked this loot will attempt to charge the Sim for perk\n            and if the Sim cannot afford the perk will fail to award the perk.\n            This failure will happen silently as it is a totally normal flow\n            for this loot.\n            ', tunable_type=bool, default=True)}

    def try_unlock_perk(self, subject, bucks_tracker, perk):
        if not self.unlock_for_free:
            curr_bucks = bucks_tracker.get_bucks_amount_for_type(perk.associated_bucks_type)
            if curr_bucks >= perk.unlock_cost:
                bucks_tracker.pay_for_and_unlock_perk(perk)
            else:
                return False
        else:
            bucks_tracker.unlock_perk(perk)
        return True

class _PerkProgressStrategy(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'progress': Tunable(description='\n            This is the amount of progress to give towards awarding the perk', tunable_type=float, default=0)}

    def try_unlock_perk(self, subject, bucks_tracker, perk):
        if perk.progression_statistic is None:
            logger.error('Attempting to gain progress for a perk that has no progression statistic.', owner='jdimailig')
            return False
        if bucks_tracker.is_perk_unlocked(perk):
            return False
        curr_bucks = bucks_tracker.get_bucks_amount_for_type(perk.associated_bucks_type)
        if curr_bucks < perk.unlock_cost:
            return False
        progress_stat_inst = subject.get_statistic(perk.progression_statistic)
        progress_stat_inst.add_value(self.progress)
        perk_unlocked = bucks_tracker.is_perk_unlocked(perk)
        if perk_unlocked:
            subject.sim_info.remove_statistic(perk.progression_statistic)
        return perk_unlocked

class AwardPerkLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'description': '\n            This loot will give the specified perk to the sim.\n            ', 'perk': TunableReference(description='\n            The perk to give the Sim. \n            ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)), 'award_strategy': TunableVariant(unlock=_UnlockPerkStrategy.TunableFactory(), progress=_PerkProgressStrategy.TunableFactory(), default='unlock'), 'notification_on_successful_unlock': OptionalTunable(description='\n            If enabled, a notification that displays when the perk is\n            successfully awarded.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                This is the notification that shows when the perk is successfully\n                unlocked.\n                '))}

    def __init__(self, perk, award_strategy=None, notification_on_successful_unlock=None, **kwargs):
        super().__init__(**kwargs)
        self._perk = perk
        self._award_strategy = award_strategy
        self._notification_on_successful_unlock = notification_on_successful_unlock

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Subject {} is None for the loot {}.', self.subject, self)
            return False
        bucks_tracker = BucksUtils.get_tracker_for_bucks_type(self._perk.associated_bucks_type, subject.sim_id, add_if_none=True)
        if bucks_tracker is None:
            logger.error("Subject {} doesn't have a perk bucks tracker of type {} for the loot {}.", self.subject, self._bucks_type, self)
            return False
        show_dialog = self._award_strategy.try_unlock_perk(subject, bucks_tracker, self._perk)
        if show_dialog and self._notification_on_successful_unlock is not None:
            notification = self._notification_on_successful_unlock(subject, resolver=SingleSimResolver(subject))
            notification.show_dialog()

class RecyclingBucksLoot(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'bucks_types': TunableList(description='\n            The type of Bucks to grant.\n            ', tunable=TunableTuple(buck_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID), buck_multiplier=TunableMultiplier.TunableFactory(description='\n                    Multipliers to apply only to this buck type when recycling an object.\n                    '))), 'bucks_multipliers': TunableMultiplier.TunableFactory(description='\n            Multipliers to apply to all bucks amounts granted by recycling an object.\n            ')}

    def __init__(self, bucks_types, bucks_multipliers, **kwargs):
        super().__init__(**kwargs)
        self._bucks_types = bucks_types
        self._bucks_multipliers = bucks_multipliers

    def _apply_to_subject_and_target(self, subject, target, resolver):
        bucks_multiplier = self._bucks_multipliers.get_multiplier(resolver)
        for buck_type_tuning in self._bucks_types:
            amount = BucksRecycling.get_recycling_value_for_object(buck_type_tuning.buck_type, target)
            if amount == 0:
                pass
            else:
                final_multiplier = bucks_multiplier*buck_type_tuning.buck_multiplier.get_multiplier(resolver)
                amount *= final_multiplier
                tracker = BucksUtils.get_tracker_for_bucks_type(buck_type_tuning.buck_type, owner_id=subject.id, add_if_none=True)
                if tracker is None:
                    logger.error('Attempting to apply a BucksLoot op to the subject {} of amount {} but they have no tracker for that bucks type {}.', subject, amount, buck_type_tuning.buck_type)
                else:
                    result = tracker.try_modify_bucks(buck_type_tuning.buck_type, int(amount))
                    if not result:
                        logger.error("Failed to modify the Sim {}'s bucks of type {} by amount {}.", subject, buck_type_tuning.buck_type, self._amount)
        resolver = SingleActorAndObjectResolver(subject, target, self)
        for loot_action in target.recycling_data.recycling_loot:
            loot_action.apply_to_resolver(resolver)

    def _get_subject_household(self, subject):
        if subject.is_sim:
            return subject.household
        elif subject.household_owner_id is not None:
            return services.household_manager().get(subject.household_owner_id)

    def _get_object_inventory(self, obj):
        if obj.is_sim:
            return
        inventoryitem_component = getattr(obj, 'inventoryitem_component', None)
        if inventoryitem_component.inventory_owner is not None:
            inventory = getattr(inventoryitem_component.inventory_owner, 'inventory_component', None)
        return inventory
