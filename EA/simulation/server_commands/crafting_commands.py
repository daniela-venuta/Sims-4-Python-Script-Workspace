from carry.carry_postures import CarryingObjectfrom crafting import recipefrom crafting.crafting_interactions import create_craftablefrom crafting.crafting_process import CRAFTING_QUALITY_LIABILITYfrom crafting.recipe import Recipefrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParamimport crafting.crafting_processimport servicesimport sims4.commandsfrom sims4.resources import Typesfrom tag import Tag
@sims4.commands.Command('crafting.shorten_phases', command_type=sims4.commands.CommandType.Automation)
def shorten_phases(enabled:bool=None, _connection=None):
    output = sims4.commands.Output(_connection)
    if enabled is None:
        do_enabled = not crafting.crafting_process.shorten_all_phases
    else:
        do_enabled = enabled
    crafting.crafting_process.shorten_all_phases = do_enabled
    if enabled is None:
        if do_enabled:
            output('Crafting phases are shortened.')
        else:
            output('Crafting phases are normal length.')
    return True

@sims4.commands.Command('crafting.get_recipes_with_tag', command_type=sims4.commands.CommandType.Automation)
def get_recipes_with_tag(tag:Tag, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    recipes = services.get_instance_manager(sims4.resources.Types.RECIPE).get_ordered_types(only_subclasses_of=Recipe)
    automation_output('CraftingGetRecipesWithTag; Status:Begin')
    for (i, recipe) in enumerate(recipes):
        if tag not in recipe.recipe_tags:
            pass
        elif recipe.final_product.definition is None:
            pass
        else:
            automation_output('CraftingGetRecipesWithTag; Status:Data, RecipeId:{}, Recipe:{}, ProductId:{}'.format(recipe.guid64, recipe.__name__, recipe.final_product_definition_id))
            output('{}:{}'.format(recipe.guid64, recipe.__name__))
    automation_output('CraftingGetRecipesWithTag; Status:End')
    return True

@sims4.commands.Command('crafting.create_recipe', command_type=sims4.commands.CommandType.Automation)
def create_recipe(recipe:TunableInstanceParam(Types.RECIPE), opt_sim:OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        output('No sim for recipe creation')
        automation_output('CraftingCreateRecipe; Status:No Sim')
        return False
    craftable = create_craftable(recipe, sim)
    if craftable is None:
        output('Failed To Create Craftable')
        automation_output('CraftingCreateRecipe; Status:Failed To Create Craftable')
        return False
    CarryingObject.snap_to_good_location_on_floor(craftable, starting_transform=sim.transform, starting_routing_surface=sim.routing_surface)
    automation_output('CraftingCreateRecipe; Status:Success, ObjectId:{}'.format(craftable.id))
    return True

@sims4.commands.Command('crafting.show_quality')
def show_quality(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No sim for crafting.show_quality', _connection)
        return False
    crafting_liability = None
    for si in sim.si_state:
        crafting_liability = si.get_liability(CRAFTING_QUALITY_LIABILITY)
        if crafting_liability is not None:
            break
    if crafting_liability is None:
        sims4.commands.output('Sim {} is not doing any crafting interaction'.format(sim), _connection)
        return False
    (quality_state, quality_stats_value) = crafting_liability.get_quality_state_and_value()
    quality_state_strings = ['None', 'Poor', 'Normal', 'Outstanding']
    quality_state = quality_state or 0
    sims4.commands.output('Sim {} current crafting quality is {}({})'.format(sim, quality_state_strings[quality_state], quality_stats_value), _connection)
    return True

@sims4.commands.Command('crafting.ingredients_required_toggle', command_type=sims4.commands.CommandType.Cheat)
def toggle_ingredients_required(_connection=None):
    recipe.debug_ingredient_requirements = not recipe.debug_ingredient_requirements
    if recipe.debug_ingredient_requirements:
        message = 'Ingredient requirements have been enabled.'
    else:
        message = 'Ingredient requirements disabled. Craft at will.'
    sims4.commands.output(message, _connection)
