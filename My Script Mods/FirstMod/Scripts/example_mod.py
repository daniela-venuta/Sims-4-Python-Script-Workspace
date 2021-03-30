import sims4.commands #required to use cheat code command


@sims4.commands.Command('myfirstscript', command_type=sims4.commands.CommandType.Live)
def myfirstscript(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output("testing example scripts. plz work.")
