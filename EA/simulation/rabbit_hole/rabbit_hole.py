import alarmsimport date_and_timeimport id_generatorfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.utils.statistic_element import ConditionalInteractionActionfrom rabbit_hole.tunable_rabbit_hole_condition import TunableRabbitHoleConditionfrom sims4 import randomfrom sims4.callback_utils import CallableListfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunablePackSafeReference, TunableReference, TunableList, TunableTuple, Tunable, OptionalTunable, TunableEnumEntryfrom sims4.utils import flexmethodfrom statistics.statistic_conditions import TunableRabbitHoleExitConditionimport servicesimport sims4import enumlogger = sims4.log.Logger('Rabbit Hole Service', default_owner='rrodgers')
class RabbitHolePhase(enum.Int, export=False):
    STARTING = 0
    ACTIVE = 1
    TRANSITIONING = 2
    TRAVELING = 3
    QUEUED = 4
    ACTIVE_PERSISTED = 5

class RabbitHoleTimingPolicy(enum.Int):
    COUNT_ALL_TIME = 0
    COUNT_ACTIVE_TIME = 1
    NO_TIME_LIMIT = 2

class RabbitHole(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RABBIT_HOLE)):
    INSTANCE_TUNABLES = {'affordance': TunableReference(description=' \n            The rabbit hole affordance. This affordance must have a tuned rabbit\n            hole liability and must use a rabbit hole exit condition.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'away_action': OptionalTunable(description='\n            If tuned, an away action for the rabbit holed sim info to run. If\n            not tuned, no away actions will be started.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.AWAY_ACTION)), enabled_by_default=True), 'go_home_and_attend': OptionalTunable(description='"\n            If tuned, this affordance will run when a sim needs to go home to\n            attend a rabbit hole. If not tuned, the sim will use the generic\n            travel. This only needs to be tuned in cases where we need special\n            travel behavior (like different constraints).\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('GoHomeTravelInteraction',))), 'loot_list': TunableList(description="\n            Loots to apply to rabbit holed sim after they leave the \n            rabbit hole. Won't be applied if the rabbit hole is cancelled.\n            ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'exit_conditions': TunableList(description='\n            A list of exit conditions for this rabbit hole. When exit\n            conditions are met then the rabbit hole ends.\n            ', tunable=TunableTuple(conditions=TunableList(description='\n                    A list of conditions that all must be satisfied for the\n                    group to be considered satisfied.\n                    ', tunable=TunableRabbitHoleCondition(description='\n                        A condition that must be satisfied.\n                        ')), tests=TunableTestSet(description='\n                    A set of tests. If these tests do not pass, this condition\n                    will not be attached.\n                    '))), 'time_tracking_policy': TunableEnumEntry(description="\n            This option determines how a rabbit hole will keep track of \n            duration:\n            COUNT_ALL_TIME - This rabbit hole's duration will begin when this\n            rabbit hole is first pushed. This should be used if the rabbit\n            hole's duration is supposed to point to a specific time. For\n            instance, if I know a sim has an audition between 1pm-2pm, I will\n            push them into a rabbit hole at 1pm with a duration of 1 hour. Now\n            imagine my sim is busy at class till 1:45pm. When they are done \n            with class, they should go to the audition. At this point, there\n            should be 15 minutes left in the audition and not 1 hour left. This\n            is because we decided to COUNT_ALL_TIME for the audition rabbit \n            hole.\n            COUNT_ACTIVE_TIME - This rabbit hole's duration will begin when the\n            sim enters it. Continuing from the above example, the audition\n            rabbit hole would end at 2:45pm and not 2:00pm if it had been tuned\n            to COUNT_ACTIVE_TIME since it only became active at 1:45pm.\n            ", tunable_type=RabbitHoleTimingPolicy, default=RabbitHoleTimingPolicy.COUNT_ACTIVE_TIME), 'tested_affordances': TunableList(description="\n            A list of test sets to run to choose the affordance to do for this\n            rabbit hole. If an affordance is found from this list, the sim will be\n            instantiated into this zone if not already and pushed to do the found\n            affordance, so tests should fail out if you do not want a sim to move\n            zones.\n            \n            If no affordance is found from this list that pass the\n            tests, normal rabbit hole affordance behavior will take over, running\n            either 'affordance' if at home or 'go_home_and_attend' if not at home.\n            \n            These tests are run when Sim is being added to a rabbit hole and also\n            on zone spin-up to check if we need to bring this Sim into the new zone to\n            put them into the rabbit hole in the new zone.\n            ", tunable=TunableTuple(tests=TunableTestSet(description='\n                    A set of tests that if passed will make this the affordance that is\n                    run for the rabbit hole.\n                    '), affordance=TunableReference(description='\n                    The rabbit hole affordance for this test set. This affordance must have a tuned rabbit\n                    hole liability and must use a rabbit hole exit condition. \n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))))}

    def __init__(self, sim_id, rabbit_hole_id=None, starting_phase=RabbitHolePhase.STARTING, picked_skill=None):
        self.rabbit_hole_id = rabbit_hole_id or id_generator.generate_object_id()
        self.sim_id = sim_id
        self.alarm_handle = None
        self.callbacks = CallableList()
        self.linked_rabbit_holes = []
        self.picked_skill = picked_skill
        self.ignore_travel_cancel_callbacks = False
        self.current_phase = starting_phase
        self._selected_affordance = None
        self.time_remaining_on_load = None

    @property
    def sim(self):
        return services.sim_info_manager().get(self.sim_id)

    @property
    def target(self):
        pass

    @flexmethod
    def get_participant(cls, inst, participant_type=ParticipantType.Actor, **kwargs):
        inst_or_cl = inst if inst is not None else cls
        participants = inst_or_cl.get_participants(participant_type=participant_type, **kwargs)
        if not participants:
            return
        if len(participants) > 1:
            raise ValueError('Too many participants returned for {}!'.format(participant_type))
        return next(iter(participants))

    @flexmethod
    def get_participants(cls, inst, participant_type, *args, **kwargs):
        if inst:
            sim_info = inst.sim
            if participant_type is ParticipantType.Actor:
                return (sim_info,)
            else:
                if participant_type is ParticipantType.Lot:
                    (services.get_zone(sim_info.zone_id, allow_uninstantiated_zones=True),)
                if participant_type is ParticipantType.PickedStatistic:
                    return (inst.picked_skill,)

    def is_valid_to_restore(self, sim_info):
        if self.is_active() and self.time_tracking_policy != RabbitHoleTimingPolicy.NO_TIME_LIMIT and self.time_remaining_on_load is None:
            return False
        return True

    def save(self, rabbit_hole_data):
        if self.alarm_handle is not None:
            rabbit_hole_data.time_remaining = self.alarm_handle.get_remaining_time().in_ticks()
        picked_stat = self.get_participant(ParticipantType.PickedStatistic)
        if picked_stat is not None:
            rabbit_hole_data.picked_stat_id = picked_stat.guid64
        rabbit_hole_data.phase = self.current_phase

    def load(self, rabbit_hole_data):
        if rabbit_hole_data.HasField('time_remaining'):
            self.time_remaining_on_load = date_and_time.TimeSpan(rabbit_hole_data.time_remaining)
        if rabbit_hole_data.HasField('picked_stat_id'):
            self.picked_skill = services.get_instance_manager(sims4.resources.Types.STATISTIC).get(rabbit_hole_data.picked_stat_id)
        if rabbit_hole_data.HasField('phase'):
            self.current_phase = RabbitHolePhase(rabbit_hole_data.phase)
        else:
            self.current_phase = RabbitHolePhase.ACTIVE
        if self.current_phase == RabbitHolePhase.ACTIVE:
            self.current_phase = RabbitHolePhase.ACTIVE_PERSISTED

    def on_restore(self):
        self._selected_affordance = None
        self.ignore_travel_cancel_callbacks = False

    def on_activate(self):
        pass

    def is_active(self):
        return self.current_phase == RabbitHolePhase.ACTIVE or self.current_phase == RabbitHolePhase.ACTIVE_PERSISTED

    def on_remove(self, canceled=False):
        self.callbacks(canceled=canceled)

    def select_affordance(self):
        if self._selected_affordance is not None:
            return self._selected_affordance
        sim_info = services.sim_info_manager().get(self.sim_id)
        resolver = SingleSimResolver(sim_info)
        for tested_affordance_tuning in self.tested_affordances:
            if tested_affordance_tuning.tests.run_tests(resolver):
                self._selected_affordance = tested_affordance_tuning.affordance
                return tested_affordance_tuning.affordance
        if sim_info.is_at_home:
            self._selected_affordance = self.affordance
            return self.affordance

    def select_travel_affordance(self):
        return self.go_home_and_attend

    def set_expiration_alarm(self, callback):
        if self.time_tracking_policy is RabbitHoleTimingPolicy.NO_TIME_LIMIT:
            logger.error("Expiration timer is trying to be set for a rabbit hole {} that doesn't support it.", self)
            return
        if self.alarm_handle is not None:
            time_remaining = self.alarm_handle.get_remaining_time()
            self.alarm_handle = alarms.add_alarm(self, time_remaining, callback, cross_zone=True)
            return
        if self.time_remaining_on_load is not None:
            self.alarm_handle = alarms.add_alarm(self, self.time_remaining_on_load, callback, cross_zone=True)
            return
        else:
            duration = self._get_duration()
            if duration is not None:
                self.alarm_handle = alarms.add_alarm(self, duration, callback, cross_zone=True)
                return

    def _get_duration(self):
        affordance = self.select_affordance()
        if affordance is not None:
            for conditional_action in affordance.basic_content.conditional_actions:
                for condition in conditional_action.conditions:
                    if hasattr(condition._tuned_values, 'min_time') and hasattr(condition._tuned_values, 'max_time'):
                        min_time = condition._tuned_values.min_time
                        max_time = condition._tuned_values.max_time
                        tuned_minutes = random.uniform(min_time, max_time)
                        return date_and_time.create_time_span(minutes=tuned_minutes)
