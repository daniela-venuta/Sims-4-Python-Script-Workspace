import servicesimport sims4from event_testing.game_option_tests import TestableGameOptionsfrom event_testing.test_events import TestEventfrom sims4.common import Pack
@sims4.commands.Command('dust.set_dust_enabled', pack=Pack.SP22, command_type=sims4.commands.CommandType.Live)
def set_dust_enabled(enabled:bool=True, _connection=None):
    services.get_event_manager().process_event(TestEvent.TestedGameOptionChanged, custom_keys=(TestableGameOptions.DUST_SYSTEM_ENABLED,))
    dust_service = services.dust_service()
    if dust_service is not None:
        dust_service.set_enabled(enabled)
    return True
