from routing import SurfaceTypefrom sims4.tuning.tunable import TunableEnumEntry, TunableMappingfrom tag import TunableTag
class VehicleTuning:
    SURFACE_FAVORITES = TunableMapping(description='\n        Tuning that specifies which favorite tag to search for when a Sim\n        attempts to deploy a vehicle on a given surface.\n        \n        Example: Sim is in the water and wants to deploy a water vehicle. They\n        have both an Aqua Zip and an Island Canoe, but only the Aqua Zip is the\n        favorite. We want to ask the favorites tracker if a given favorite\n        water vehicle has been set, which is based on the tag tuned here.\n        ', key_name='Surface', value_name='Favorite Tag', key_type=TunableEnumEntry(description='\n            The Surface we want to apply a favorite tag to. If the Sim is on\n            this surface and has an opportunity to deploy a vehicle, then we\n            use the corresponding tag to choose it.\n            ', tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_WORLD, invalid_enums=(SurfaceType.SURFACETYPE_UNKNOWN,)), value_type=TunableTag(description='\n            The favorite tag we search the inventory for when deploying vehicles.\n            ', filter_prefixes=('Func',)))

def get_favorite_tag_for_surface(surface_type):
    return VehicleTuning.SURFACE_FAVORITES.get(surface_type, None)

def get_favorite_tags_for_vehicle(vehicle):
    favorite_tags = []
    vehicle_component = vehicle.vehicle_component
    for surface_type in vehicle_component.allowed_surfaces:
        tag = get_favorite_tag_for_surface(surface_type)
        if tag is not None:
            favorite_tags.append(tag)
    return favorite_tags
