import objectsfrom objects.components.statistic_component import HasStatisticComponentfrom objects.components import ComponentContainer, forward_to_componentsfrom sims4.utils import constproperty
class LotLevel(ComponentContainer, HasStatisticComponent):

    def __init__(self, level_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.level_index = level_index

    def save(self, lot_level_data):
        lot_level_data.level_index = self.level_index
        lot_level_data.ClearField('commodity_tracker')
        (commodities, _, _) = self.commodity_tracker.save()
        self.update_all_commodities()
        lot_level_data.commodity_tracker.commodities.extend(commodities)

    def load(self, lot_level_data):
        self.commodity_tracker.load(lot_level_data.commodity_tracker.commodities)

    @constproperty
    def is_sim():
        return False

    @constproperty
    def is_lot_level():
        return True

    @property
    def is_downloaded(self):
        return False

    def on_teardown(self):
        statistic_component = self.get_component(objects.components.types.STATISTIC_COMPONENT)
        if statistic_component is not None:
            statistic_component.on_remove()

    @forward_to_components
    def on_finalize_load(self):
        pass
