from lot_decoration.lot_decoration_enums import LOT_DECORATION_DEFAULT_ID
class DefaultDecorationProvider:

    @property
    def decoration_preset(self):
        pass

    @property
    def decoration_type_id(self):
        return LOT_DECORATION_DEFAULT_ID

class HolidayDecorationProvider:

    def __init__(self, holiday_id):
        self._holiday_id = holiday_id

    @property
    def decoration_preset(self):
        return services.holiday_service().get_decoration_preset(self._holiday_id)

    @property
    def decoration_type_id(self):
        return self._holiday_id
