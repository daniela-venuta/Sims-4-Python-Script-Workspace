import server_commands.argument_helpersimport servicesimport sims4.commandsfrom server_commands.argument_helpers import TunableInstanceParamlogger = sims4.log.Logger('Rewards')
@sims4.commands.Command('rewards.give_reward')
def give_reward(reward_type:TunableInstanceParam(sims4.resources.Types.REWARD), opt_sim:server_commands.argument_helpers.OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    sim = server_commands.argument_helpers.get_optional_target(opt_sim, _connection)
    reward_type.give_reward(sim.sim_info)
    output('Successfully gave the reward.')

@sims4.commands.Command('rewards.give_cas_part')
def give_cas_part(cas_part_definition_id:int, sim:server_commands.argument_helpers.OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    sim = server_commands.argument_helpers.get_optional_target(sim, _connection)
    if sim is None:
        household = services.active_household()
    else:
        household = sim.household
    household.add_cas_part_to_reward_inventory(cas_part_definition_id)
    output('Successfully rewarded cas part.')
