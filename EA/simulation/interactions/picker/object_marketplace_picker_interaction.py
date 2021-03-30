import randomimport servicesimport sims4import tagfrom crafting.crafting_interactions import create_craftablefrom crafting.recipe import get_recipes_matching_tagfrom date_and_time import TimeSpanfrom interactions.base.picker_interaction import PurchasePickerInteractionfrom interactions.utils.tunable_icon import TunableIconfrom objects.components.object_marketplace_component import ObjectMarketplaceComponentfrom objects.components.state import ObjectStateValuefrom protocolbuffers import Consts_pb2from sims.sim_info_types import Genderfrom sims.sim_spawner import SimSpawnerfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.random import weighted_random_itemfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableRange, TunableList, TunableTuple, Tunable, TunableSet, TunableEnumWithFilterfrom sims4.tuning.tunable_base import GroupNamesfrom tag import TunableTagfrom tunable_time import TunableTimeSpanlogger = sims4.log.Logger('ObjectMarketplacePickerInteraction', default_owner='rrodgers')
class ObjectMarketplacePickerInteraction(PurchasePickerInteraction):
    OBJECT_MARKETPLACE_PURCHASED_STATE_VALUE = ObjectStateValue.TunablePackSafeReference(description='\n        The state value that will be applied to objects after they have\n        been purchased to indicate they have been purchased.\n        ')
    REFRESH_TIME_TEXT = TunableLocalizedStringFactory(description='\n        Text indicating how much time is left until the picker refreshes. Shown\n        in picker. Receives a single time token.\n        ')
    INSTANCE_TUNABLES = {'recipe_tags': TunableSet(description='\n            Tags that determine what recipes will provide objects that appear\n            in this picker.\n            ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, filter_prefixes=['recipe'], default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,)), minlength=1, tuning_group=GroupNames.PICKERTUNING), 'refresh_period': TunableTimeSpan(description="\n            This picker's items will refresh every refresh_period time. They\n            will also refresh if the game is reloaded.\n            ", default_hours=1, tuning_group=GroupNames.PICKERTUNING), 'items_available': TunableRange(description='\n            The number of items available in the picker.\n            ', tunable_type=int, minimum=1, default=1, tuning_group=GroupNames.PICKERTUNING), 'quality_weights': TunableList(description='\n            Weights and qualities for determining the quality of objects in\n            the picker.\n            ', tunable=TunableTuple(state_value=ObjectStateValue.TunableReference(description='\n                    The quality state value.\n                    '), weight=Tunable(description='\n                    A weight that will make this quality more likely to appear.\n                    ', tunable_type=float, default=1)), tuning_group=GroupNames.PICKERTUNING), 'purchased_tag': TunableTag(filter_prefixes=['inventory_plopsy']), 'sold_icon': TunableIcon(description='\n            An icon override for picker rows that display sold items.\n            ', tuning_group=GroupNames.PICKERTUNING), 'sold_description_text': TunableLocalizedStringFactory(description='\n            Description text for picker rows that display sold items.\n            ', tuning_group=GroupNames.PICKERTUNING), 'default_description_text': TunableLocalizedStringFactory(description='\n            Description text for picker rows that are available. Tokens:\n            0: String, the username of the fictional seller.\n            ', tuning_group=GroupNames.PICKERTUNING)}
    purchased_recipes = []
    last_items_period_id = -1
    current_item_data = {}

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        return True

    def _populate_items(self, purchase_picker_data):
        period_id = int(services.time_service().sim_now.absolute_ticks()/self.refresh_period().in_ticks())
        if period_id != ObjectMarketplacePickerInteraction.last_items_period_id:
            ObjectMarketplacePickerInteraction.last_items_period_id = period_id
            ObjectMarketplacePickerInteraction.purchased_recipes = []
            ObjectMarketplacePickerInteraction.current_item_data = {}
            tagged_recipes = set()
            for tag in self.recipe_tags:
                tagged_recipes.update(get_recipes_matching_tag(tag))
            rand = random.Random()
            selected_recipes = rand.sample(tagged_recipes, self.items_available)
            for recipe in selected_recipes:
                definition = recipe.final_product.definition
                if definition is None:
                    logger.error('Recipe {} with no definition cannot be used in PurchaseRecipePickerInteraction', recipe)
                else:
                    quality_weight_pairs = [(quality_weight.weight, quality_weight.state_value) for quality_weight in self.quality_weights]
                    quality_state_value = weighted_random_item(quality_weight_pairs)
                    obj = create_craftable(recipe, None, quality=quality_state_value)
                    price = ObjectMarketplaceComponent.calculate_sale_price(obj)
                    obj.destroy(cause='Destroy temporary object in PurchaseRecipePickerInteraction')
                    ObjectMarketplacePickerInteraction.current_item_data[definition] = (recipe, quality_state_value, price)
        for (definition, (recipe, quality, price)) in ObjectMarketplacePickerInteraction.current_item_data.items():
            purchase_picker_data.add_definition_to_purchase(definition, custom_price=price)

    def _supports_pick_response(self):
        return True

    def _on_picker_selected(self, dialog):
        super()._on_picker_selected(dialog)
        (definition_ids, _) = dialog.get_result_definitions_and_counts()
        for definition_id in definition_ids:
            definition = services.definition_manager().get(definition_id)
            ObjectMarketplacePickerInteraction.purchased_recipes.append(definition)
            (recipe, quality, price) = ObjectMarketplacePickerInteraction.current_item_data[definition]
            if not services.active_household().funds.try_remove(price, Consts_pb2.TELEMETRY_OBJECT_BUY):
                logger.error('Could not complete object marketplace purchase of {} due to insufficient funds', recipe)
            else:
                obj = create_craftable(recipe, None, inventory_owner=self.sim, quality=quality, owning_household_id_override=self.sim.household_id, place_in_inventory=True)
                obj.append_tags(frozenset([self.purchased_tag]), persist=True)
                if self.OBJECT_MARKETPLACE_PURCHASED_STATE_VALUE is not None:
                    obj.set_state(self.OBJECT_MARKETPLACE_PURCHASED_STATE_VALUE.state, self.OBJECT_MARKETPLACE_PURCHASED_STATE_VALUE)

    def _get_enabled_option(self, item):
        if item in ObjectMarketplacePickerInteraction.purchased_recipes:
            return False
        return True

    def _get_right_custom_text(self):
        refresh_period = self.refresh_period().in_ticks()
        now = services.time_service().sim_now.absolute_ticks()
        next_period_id = int(now/refresh_period) + 1
        next_period_time = next_period_id*refresh_period
        refresh_time = next_period_time - now
        return self.REFRESH_TIME_TEXT(TimeSpan(refresh_time))

    def _get_availability_option(self, item):
        if item in ObjectMarketplacePickerInteraction.purchased_recipes:
            return 0
        return 1

    def _get_icon_override_option(self, item):
        if item in ObjectMarketplacePickerInteraction.purchased_recipes:
            return self.sold_icon

    def _get_description_override_option(self, item):
        if item in ObjectMarketplacePickerInteraction.purchased_recipes:
            return self.sold_description_text()
        else:
            buyer_name = SimSpawner.get_random_first_name(Gender.MALE, sim_name_type_override=ObjectMarketplaceComponent.BUYER_NAME_TYPE)
            return self.default_description_text(buyer_name)
lock_instance_tunables(ObjectMarketplacePickerInteraction, purchase_list_option=None)