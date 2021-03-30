import randomimport servicesfrom event_testing.resolver import SingleActorAndObjectResolverfrom sims.favorites.favorites_tuning import FavoritesTuning
def get_favorite_in_sim_inventory(sim, favorite_data):
    favorites_tracker = sim.sim_info.favorites_tracker
    if favorites_tracker is None:
        return (None, None)
    sim_inventory = sim.inventory_component
    (favorite_obj_id, favorite_def_id) = favorites_tracker.get_favorite(favorite_data.favorite_tag)
    if favorite_obj_id is not None:
        favorite_object = services.current_zone().find_object(favorite_obj_id)
        if favorite_object is not None and favorite_object in sim_inventory:
            return (favorite_object.definition, favorite_object)
    elif favorite_def_id is not None:
        return (services.definition_manager().get(favorite_def_id), None)
    other_objects = sim_inventory.get_objects_by_tag(favorite_data.favorite_tag)
    if not other_objects:
        return (None, None)
    else:
        tested_other_objects = []
        for other_obj in other_objects:
            resolver = SingleActorAndObjectResolver(sim.sim_info, other_obj, 'get_favorite_in_sim_inventory')
            if favorite_data.random_choice_tests.run_tests(resolver):
                tested_other_objects.append(other_obj)
        if tested_other_objects:
            found_obj = random.choice(tested_other_objects)
            return (found_obj.definition, found_obj)
        else:
            return (None, None)
    return (None, None)

def get_favorite_by_definition(sim, favorite_data):
    favorites_tracker = sim.sim_info.favorites_tracker
    if favorites_tracker is None:
        return
    (favorite_obj_id, favorite_def_id) = favorites_tracker.get_favorite(favorite_data.favorite_tag)
    return services.definition_manager().get(favorite_def_id)

def get_animation_override_for_prop_def(definition):
    for overrides in FavoritesTuning.FAVORITES_ANIMATION_OVERRIDES:
        if definition in overrides.favorite_definitions:
            return overrides.animation_overrides
