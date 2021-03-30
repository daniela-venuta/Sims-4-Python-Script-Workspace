from interactions.utils import adventurefrom event_testing.resolver import SingleSimResolverfrom server_commands.argument_helpers import get_optional_target, OptionalTargetParam, TunableMultiTypeInstanceParamfrom snippets import get_defined_snippets_genimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Adventure')
@sims4.commands.Command('adventure.toggle_show_all_adventure_moments')
def toggle_show_all_adventure_moments(enable:bool=None, _connection=None):
    adventure._show_all_adventure_moments
    if enable is None:
        enable = not adventure._show_all_adventure_moments
    adventure.set_show_all_adventure_momentss = enable

def _display_adventure_enums(adventures_dict, display_moment_data, resolver, _connection=None):
    output = sims4.commands.Output(_connection)
    for (title, adventures) in adventures_dict.items():
        index = 1
        output('  Location: ' + title)
        for adventure in adventures:
            output('    Adventure {}'.format(index))
            adventure.factory.display_adventure_enums(adventure._tuned_values, display_moment_data, resolver, _connection)
            index += 1

@sims4.commands.Command('adventure.show_adventure_enums', command_type=sims4.commands.CommandType.DebugOnly)
def show_adventure_enums(source:TunableMultiTypeInstanceParam((sims4.resources.Types.INTERACTION, sims4.resources.Types.CAREER_LEVEL)), display_moment_data:bool=False, opt_sim:OptionalTargetParam=None, _connection=None):
    sims4.commands.output('Source: {}'.format(source), _connection)
    adventures_dict = source.get_adventures()
    if adventures_dict:
        sim = get_optional_target(opt_sim, _connection)
        _display_adventure_enums(adventures_dict, display_moment_data, SingleSimResolver(sim.sim_info), _connection)
        return True
    sims4.commands.output('Failed to find adventures in specified source', _connection)
    return False

def _display_adventure_moment_data(adventures_dict, moment_key, resolver, _connection=None):
    found = False
    for (title, adventures) in adventures_dict.items():
        index = 1
        for adventure in adventures:
            found |= adventure.factory.display_adventure_moment_data(adventure._tuned_values, moment_key, title, index, resolver, _connection)
            index += 1
    return found

def _display_initial_moment_data(adventures_dict, resolver, _connection):
    output = sims4.commands.Output(_connection)
    for (title, adventures) in adventures_dict.items():
        index = 1
        output('  Location: ' + title)
        for adventure in adventures:
            output('    Adventure {}'.format(index))
            adventure.factory.display_initial_moment_data(adventure._tuned_values, resolver, _connection)
            index += 1

@sims4.commands.Command('adventure.show_adventure_moment_data', command_type=sims4.commands.CommandType.DebugOnly)
def show_adventure_moment_data(source:TunableMultiTypeInstanceParam((sims4.resources.Types.INTERACTION, sims4.resources.Types.CAREER_LEVEL)), moment_key:adventure.AdventureMomentKey=None, opt_sim:OptionalTargetParam=None, _connection=None):
    sims4.commands.output('Source: {}'.format(source), _connection)
    adventures_dict = source.get_adventures()
    if adventures_dict:
        sim = get_optional_target(opt_sim, _connection)
        if moment_key is None:
            _display_initial_moment_data(adventures_dict, SingleSimResolver(sim.sim_info), _connection)
            return True
        if _display_adventure_moment_data(adventures_dict, moment_key, SingleSimResolver(sim.sim_info), _connection):
            return True
        sims4.commands.output('Failed to find specified adventure key in sources adventures', _connection)
        return False
    sims4.commands.output('Failed to find adventures in specified source', _connection)
    return False

def _find_and_display_adventure_moment(source, tuning_name, resolver, verbose, display_all, _connection):
    adventures_dict = source.get_adventures()
    displayed_source = False
    output = sims4.commands.Output(_connection)
    for (title, adventures) in adventures_dict.items():
        displayed_title = False
        for adventure in adventures:
            for (moment_key, name, path) in adventure.factory.find_moment_gen(adventure._tuned_values, tuning_name):
                if not displayed_source:
                    output('Source: {}'.format(source))
                    displayed_source = True
                if not displayed_title:
                    output('  Location: ' + title)
                    displayed_title = True
                output('    Key: {}'.format(moment_key))
                output('      Matched Name: {}'.format(name))
                output('      Path: {}'.format(path))
                if verbose:
                    output('    Detailed Path')
                    for path_moment_key in path:
                        output('    Key: {}'.format(path_moment_key))
                        adventure.factory.display_adventure_moment_data(adventure._tuned_values, path_moment_key, title, -1, resolver, _connection)
                output(' '.format(path))
                return True
    return False

@sims4.commands.Command('adventure.find_adventure_moment', command_type=sims4.commands.CommandType.DebugOnly)
def find_adventure_moment(tuning_name:str, verbose:bool=False, display_all:bool=False, opt_sim:OptionalTargetParam=None, _connection=None):
    tuning_name = tuning_name.lower()
    tuning_types = (sims4.resources.Types.INTERACTION, sims4.resources.Types.CAREER_LEVEL)
    found = False
    sim = get_optional_target(opt_sim, _connection)
    resolver = SingleSimResolver(sim.sim_info)
    for tuning_type in tuning_types:
        manager = services.get_instance_manager(tuning_type)
        for source in manager.types.values():
            if _find_and_display_adventure_moment(source, tuning_name, resolver, verbose, display_all, _connection):
                found = True
                if not display_all:
                    return True
    if found:
        return True
    sims4.commands.output('Failed to find any usage of specified adventure moment', _connection)
    return False

@sims4.commands.Command('adventure.reset_adventures', command_type=sims4.commands.CommandType.DebugOnly)
def reset_adventures(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    adventure_tracker = sim.sim_info.adventure_tracker
    if adventure_tracker is not None:
        adventure_tracker.clear_adventure_tracker()
        sims4.commands.output('Cleared', _connection)
        return True
    sims4.commands.output('Failed to find adventure tracker for specified sim', _connection)
    return False

@sims4.commands.Command('adventure.report_last_shown')
def report_last_shown(_connection=None):
    sims4.commands.output('{}'.format(adventure.get_last_adventure_shown()), _connection)
    return True

@sims4.commands.Command('adventure.dump_adventure_moment_tuning')
def dump_adventure_moment_tuning(_connection=None):
    snippets = list(get_defined_snippets_gen('Adventure_Moment'))
    snippets.sort(key=lambda s: str(s))
    for snippet in snippets:
        sims4.commands.output('{}'.format(snippet), _connection)
    return True
