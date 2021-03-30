import servicesfrom event_testing.resolver import SingleSimResolverfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableFactory, TunableMapping, TunableReference, TunableTuple, TunableList, TunableVariant, Tunable, AutoFactoryInit, HasTunableSingletonFactoryfrom situations.custom_states.custom_states_common_tuning import RandomWeightedSituationStateKey, CustomStatesSituationTriggerDataTestVariantfrom situations.situation_complex import SituationStatefrom situations.situation_guest_list import SituationGuestListfrom snippets import CUSTOM_STATES_SITUATION_STATE, define_snippetfrom tunable_time import TunableTimeSpan, TunableTimeOfDay
class CustomStatesSituationStateChange(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'possible_states': RandomWeightedSituationStateKey.TunableFactory()}

    def __call__(self, situation_state):
        situation_state.owner.change_state_by_key(self.possible_states())

class CustomStatesSituationEndSituation(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, situation_state):
        situation_state.owner._self_destruct()

class CustomStatesSituationGiveLoot(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'loot_actions': TunableList(description='\n            A list of loot actions to apply.\n            ', tunable=TunableReference(description='\n                The loot to apply.\n                ', manager=services.get_instance_manager(Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True))}

    def __call__(self, situation_state):
        for sim in situation_state.owner.all_sims_in_situation_gen():
            resolver = SingleSimResolver(sim.sim_info)
            for loot_action in self.loot_actions:
                loot_action.apply_to_resolver(resolver)

class CustomStatesSituationReplaceSituation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'new_situation': TunableReference(description='\n            The new situation to be created.\n            \n            This situation will be created using the default guest list (predefined if the situation has one else an\n            empty one) and non-user facing.  If we want either Sims transferred between this situation and the next one\n            or the following situation to be user facing GPE would just need to add new tuning within this factory to\n            add the logic.\n            ', manager=services.get_instance_manager(Types.SITUATION))}

    def __call__(self, situation_state):
        situation_state.owner._self_destruct()
        guest_list = self.new_situation.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        services.get_zone_situation_manager().create_situation(self.new_situation, guest_list=guest_list, user_facing=False)
HAS_TRIGGERED_KEY = 'has_triggered_{}'
class BaseSituationTrigger(HasTunableFactory, AutoFactoryInit):

    def __init__(self, owner, index, effect, **kwargs):
        super().__init__(**kwargs)
        self._owner = owner
        self._index = index
        self._effect = effect
        self._has_triggered = False

    def _setup(self, reader):
        raise NotImplementedError

    def on_activate(self, reader):
        if reader is not None:
            self._has_triggered = reader.read_bool(HAS_TRIGGERED_KEY.format(self._index), False)
            if self._has_triggered:
                return
        self._setup(reader)

    def save(self, writer):
        writer.write_bool(HAS_TRIGGERED_KEY.format(self._index), self._has_triggered)

    def destroy(self):
        self._owner = None
        self._index = None
        self._effect = None
        self._has_triggered = None
DURATION_ALARM_KEY = 'duration_alarm_{}'
class DurationTrigger(BaseSituationTrigger):
    FACTORY_TUNABLES = {'duration': TunableTimeSpan(description='\n            The amount of time that will expire before this duration effect is triggered.\n            ')}

    def _duration_complete(self, _):
        self._has_triggered = True
        self._effect(self._owner)

    def _setup(self, reader):
        self._owner._create_or_load_alarm_with_timespan(DURATION_ALARM_KEY.format(self._index), self.duration(), self._duration_complete, reader=reader, should_persist=True)
DAY_TIME_ALARM_KEY = 'day_time_alarm_{}'
class TimeOfDayTrigger(BaseSituationTrigger):
    FACTORY_TUNABLES = {'time': TunableTimeOfDay(description='\n            The time of day that this trigger will occur at.\n            ')}

    def _duration_complete(self, _):
        self._has_triggered = True
        self._effect(self._owner)

    def _setup(self, reader):
        now = services.game_clock_service().now()
        self._owner._create_or_load_alarm_with_timespan(DURATION_ALARM_KEY.format(self._index), now.time_till_next_day_time(self.time), self._duration_complete, reader=reader, should_persist=False)

class TestEventTrigger(BaseSituationTrigger):
    FACTORY_TUNABLES = {'test': CustomStatesSituationTriggerDataTestVariant(description='\n            A test that will be listened to in order to act as a trigger.  These tests will not be checked\n            when entering the state to see if they are already complete.\n            '), 'only_trigger_for_situation_sims': Tunable(description='\n            If checked then we will only perform this trigger if the Sim linked to the even is in the\n            situation.\n            ', tunable_type=bool, default=True)}

    def _setup(self, reader):
        services.get_event_manager().register_tests(self, (self.test,))

    def destroy(self):
        if not self._has_triggered:
            services.get_event_manager().unregister_tests(self, (self.test,))
        super().destroy()

    def handle_event(self, sim_info, event, resolver):
        if self._has_triggered:
            return
        if self.only_trigger_for_situation_sims and not self._owner.owner.is_sim_info_in_situation(sim_info):
            return
        if not resolver(self.test):
            return
        self._has_triggered = True
        self._effect(self._owner)
        services.get_event_manager().unregister_tests(self, (self.test,))

class CustomStatesSituationState(SituationState, HasTunableFactory):
    FACTORY_TUNABLES = {'job_and_role_changes': TunableMapping(description='\n            A mapping between situation jobs and role states that defines\n            what role states we want to switch to for sims on which jobs\n            when this situation state is entered.\n            \n            If a situation role does not need to change it does not need to\n            be specified.\n            ', key_type=TunableReference(description="\n                A reference to a SituationJob that we will use to change\n                sim's role state.\n                ", manager=services.get_instance_manager(Types.SITUATION_JOB)), key_name='Situation Job', value_type=TunableReference(description='\n                The role state that we will switch sims of the linked job\n                into.\n                ', manager=services.get_instance_manager(Types.ROLE_STATE)), value_name='Role State'), 'triggers': TunableList(description='\n            A link between effects and triggers for those effects.\n            ', tunable=TunableTuple(description='\n                A grouping of an effect and triggers for that effect.\n                ', effect=TunableVariant(description='\n                    The effect that will occur when one of the triggers is met.\n                    ', change_state=CustomStatesSituationStateChange.TunableFactory(), end_situation=CustomStatesSituationEndSituation.TunableFactory(), loot=CustomStatesSituationGiveLoot.TunableFactory(), replace_situation=CustomStatesSituationReplaceSituation.TunableFactory(), default='change_state'), triggers=TunableList(description='\n                    The different triggers that are linked to this effect.\n                    ', tunable=TunableVariant(description='\n                        A trigger to perform an effect within the situation.\n                        ', duration=DurationTrigger.TunableFactory(), time_of_day=TimeOfDayTrigger.TunableFactory(), test_event=TestEventTrigger.TunableFactory(), default='duration'))))}

    def __init__(self, job_and_role_changes, triggers):
        super().__init__()
        self._job_and_role_changes = job_and_role_changes
        self._triggers = []
        index = 0
        for effect_trigger in triggers:
            for trigger in effect_trigger.triggers:
                self._triggers.append(trigger(self, index, effect_trigger.effect))
                index += 1

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for (job, role_state) in self._job_and_role_changes.items():
            self.owner._set_job_role_state(job, role_state)
        for trigger_data in self._triggers:
            trigger_data.on_activate(reader)

    def on_deactivate(self):
        super().on_deactivate()
        for trigger_data in self._triggers:
            trigger_data.destroy()
        self._triggers.clear()

    def save_state(self, writer):
        super().save_state(writer)
        for trigger_data in self._triggers:
            trigger_data.save(writer)
(TunableCustomStatesSituationStateReference, TunableCustomStatesSituationStateSnippet) = define_snippet(CUSTOM_STATES_SITUATION_STATE, CustomStatesSituationState.TunableFactory())