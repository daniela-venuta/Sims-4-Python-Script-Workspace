from sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableRange, TunableTuplefrom bucks.bucks_enums import BucksType
class BucksRecycling:
    RECYCLING_VALUE = TunableMapping(description='\n        Maps a buck type the parameters controlling object recycling value.\n        Recycling Formula:\n        Total = Base Value * Price Response Curve (Object Current Simoleon Value) * \n            Object Recycle Value (Buck Type)\n        ', key_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=BucksType.INVALID, pack_safe=True), key_name='Bucks Type', value_type=TunableTuple(description='\n            Recycling parameters for this buck type.\n            ', base_value=TunableRange(description='\n                Base multiplier for this buck type\n                ', tunable_type=float, default=1.0, minimum=0.0), price_response_curve=TunableCurve(description='\n                Modulate the base value by the objects Simoleon value.\n                ', x_axis_name='Object Price', y_axis_name='Base Multiplier')), value_name='Recycled Value')

    @classmethod
    def get_recycling_value_for_object(cls, bucks, obj):
        if obj is None or (obj.is_sim or bucks not in obj.recycling_data.recycling_values) or bucks not in BucksRecycling.RECYCLING_VALUE:
            return 0
        object_recycle_value = obj.recycling_data.recycling_values[bucks]
        object_value = obj.current_value
        params = BucksRecycling.RECYCLING_VALUE[bucks]
        recycle_curve_value = params.price_response_curve.get(object_value)
        return int(params.base_value*recycle_curve_value*object_recycle_value*object_value)
