from server_commands.argument_helpers import SimInfoParam, VectorParamimport cameraimport servicesimport sims4.commandsimport sims4.math
@sims4.commands.Command('update.camera.information', command_type=sims4.commands.CommandType.Live)
def update_camera_information(sim_id:int=None, target_x:float=None, target_y:float=None, target_z:float=None, camera_x:float=None, camera_y:float=None, camera_z:float=None, follow_mode:bool=None, _connection=None):
    camera.update(sim_id=sim_id, target_position=sims4.math.Vector3(target_x, target_y, target_z), camera_position=sims4.math.Vector3(camera_x, camera_y, camera_z), follow_mode=follow_mode)

@sims4.commands.Command('camera.focus_on_position')
def focus_on_position(pos:VectorParam, *_, _connection=None, **__):
    client = services.client_manager().get(_connection)
    camera.focus_on_position(pos, client)
    (x, y, z) = pos
    sims4.commands.output('focus on position: {}, {}, {}'.format(x, y, z), _connection)

@sims4.commands.Command('camera.shake')
def shake_camera(duration:float, frequency:float=None, amplitude:float=None, octaves:int=None, fade_multiplier:float=None, _connection=None):
    camera.shake_camera(duration, frequency=frequency, amplitude=amplitude, octaves=octaves, fade_multiplier=fade_multiplier)

@sims4.commands.Command('camera.focus_on_sim')
def focus_on_sim(sim_info:SimInfoParam, *_, _connection=None, **__):
    if sim_info is None:
        sims4.commands.output('Could not find Sim to focus on.', _connection)
        return
    sim = sim_info.get_sim_instance()
    if sim is None:
        sims4.commands.output('Could not find Sim to focus on.', _connection)
        return
    pos = sim.position
    client = services.client_manager().get(_connection)
    camera.focus_on_position(pos, client)
    sims4.commands.output('focus on sim: {}'.format(sim_info), _connection)

@sims4.commands.Command('camera.focus_on_locator')
def focus_on_locator(locator_id:int, *_, _connection=None, **__):
    locators = services.locator_manager().get(locator_id)
    if not locators:
        sims4.commands.output('Locator id {} has no associated locator in the current zone.'.format(locator_id), _connection)
        return
    if len(locators) > 1:
        sims4.commands.output('Locator id {} has more than one associated locator in the current zone. Choosing the first one that was found.'.format(locator_id), _connection)
    locator = locators[0]
    client = services.client_manager().get(_connection)
    (x, y, z) = locator.transform.translation
    sims4.commands.output('Focusing on locator {} at {} {} {}'.format(locator_id, x, y, z), _connection)
    camera.focus_on_position(locator.transform.translation, client)
