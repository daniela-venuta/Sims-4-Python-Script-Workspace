from sims4.commands import CommandTypefrom sims.sim_info_types import Genderimport servicesimport sims4.commands
@sims4.commands.Command('style.clear_style', command_type=CommandType.Live)
def clear_style(gender:Gender, _connection=None):
    style_service = services.get_style_service()
    if style_service is None:
        return
    style_service.clear_style_outfit_data(gender)
