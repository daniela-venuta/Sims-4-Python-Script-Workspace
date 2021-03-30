import sims4from event_testing.resolver import GlobalResolverfrom event_testing.tests import TunableTestSetfrom scheduler import WeeklySchedule, ScheduleEntryfrom sims4.tuning.tunable import TunableFactory, TunableList, TunableTuple, TunableReferencefrom situations.complex.bowling_venue import BowlingVenueMixinfrom situations.situation_guest_list import SituationGuestListfrom venues.scheduling_zone_director import SchedulingZoneDirectorimport services
class TestedSituationWeeklySchedule(WeeklySchedule):

    @TunableFactory.factory_option
    def schedule_entry_data(pack_safe=False):
        return {'schedule_entries': TunableList(description='\n                A list of event schedules. Each event is a mapping of days of the\n                week to a start_time and duration.\n                ', tunable=ScheduleEntry.TunableFactory(schedule_entry_data={'tuning_name': 'situation', 'tuning_type': TunableTuple(situation=TunableReference(description='\n                                The situation to start according to the tuned schedule.\n                                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=pack_safe), tests=TunableTestSet(description='\n                                A set of tests to run before attempting to start the\n                                scheduled situation. If any test fails, the situation\n                                will not start.\n                                '))}))}

class BarZoneDirector(BowlingVenueMixin, SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'special_bar_schedule': TestedSituationWeeklySchedule.TunableFactory(description='\n            The schedule to trigger the different special scheduled events.\n            ', schedule_entry_data={'pack_safe': True})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._special_bar_schedule = None

    def on_loading_screen_animation_finished(self):
        super().on_loading_screen_animation_finished()
        self._special_bar_schedule = self.special_bar_schedule(start_callback=self._start_special_bar_event)

    def _start_special_bar_event(self, scheduler, alarm_data, extra_data):
        tested_situation = alarm_data.entry.situation
        situation = tested_situation.situation
        if not situation.situation_meets_starting_requirements():
            return
        situation_manager = services.get_zone_situation_manager()
        if any(situation is type(running_situation) for running_situation in situation_manager.running_situations()):
            return
        tests = tested_situation.tests
        if tests:
            resolver = GlobalResolver()
            if not tests.run_tests(resolver):
                return
        guest_list = SituationGuestList(invite_only=True)
        situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False, scoring_enabled=False, creation_source=self.instance_name)
