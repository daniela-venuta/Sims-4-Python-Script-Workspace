from event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom interactions.utils.sim_focus import get_next_focus_idfrom interactions.utils.success_chance import SuccessChancefrom routing.route_events.route_event import RouteEventfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, TunableTuple, Tunablefrom sims4.tuning.tunable_hash import TunableStringHash32import interactions.utils.sim_focusimport sims4.loglogger = sims4.log.Logger('RouteEventPaired', default_owner='nabaker')
class RouteEventPaired(RouteEvent):
    INSTANCE_TUNABLES = {'focus': OptionalTunable(description='\n            Optional tuning for controlling sims focus\n            ', tunable=TunableTuple(layer=Tunable(description='\n                    Layer override: Ambient=0, SuperInteraction=3, Interaction=5.\n                    ', tunable_type=int, default=None), score=Tunable(description='\n                    Focus score.  This orders focus elements in the same layer.\n                    ', tunable_type=int, default=1), focus_bone_override=TunableStringHash32(description='\n                    The bone Sims direct their attention towards when focusing on an object.\n                    ')))}

    def __init__(self, actor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._provider_required = True
        self.actor = actor
        self._focus_id = None
        self.paired_event = None
        self.executed = False

    def on_executed(self, sim, path=None):
        if sim is not self.actor:
            logger.error('Changed sim for route event {} on_executed, new sim: {} existing sim: {}', self, sim, self.actor)
            return
        if self.paired_event is None:
            logger.error("Paired event didn't have pair for {}", self.actor)
            return
        if self.paired_event.executed:
            self._execute_internal(path)
            self.paired_event._execute_internal(path)
        else:
            self.executed = True

    def _execute_internal(self, path):
        if self.focus is not None:
            self._start_focus()
        super().on_executed(self.actor, path, force_alarm=self.focus is not None)

    def prepare_route_event(self, sim):
        if sim is not self.actor:
            logger.error('Changed sim for route event {} prepare_route_event, new sim: {} existing sim: {}', self, sim, self.actor)
            return
        super().prepare_route_event(sim, defer_process_until_execute=True)
        if self.paired_event is not None:
            self.event_data.target_loot_sim = self.paired_event.actor.ref()

    def get_resolver(self, actor):
        target_sim = self.paired_event.actor if self.paired_event is not None else None
        if target_sim is not None:
            return DoubleSimResolver(self.actor.sim_info, target_sim.sim_info)
        return SingleSimResolver(self.actor.sim_info)

    def _start_focus(self):
        if self._end_alarm is not None:
            return
        target_sim = self.paired_event.actor if self.paired_event is not None else None
        if target_sim is None:
            return
        self._focus_id = get_next_focus_id()
        if self.focus.focus_bone_override is not None:
            target_bone = self.focus.focus_bone_override
        elif not hasattr(target_sim, 'get_focus_bone'):
            logger.error('SimFocus target provided does not have get_focus_bone(): {}', target_sim)
            target_bone = 0
        else:
            target_bone = target_sim.get_focus_bone()
        interactions.utils.sim_focus.FocusAdd(self.actor, self._focus_id, self.focus.layer, self.focus.score, self.actor.id, target_sim.id, target_bone, sims4.math.Vector3(0, 0, 0), blocking=False)

    def _on_end(self, *args):
        super()._on_end(*args)
        if self._focus_id is not None:
            interactions.utils.sim_focus.FocusDelete(self.actor, self.actor.id, self._focus_id)
lock_instance_tunables(RouteEventPaired, scheduling_override=None, chance=SuccessChance.ONE)