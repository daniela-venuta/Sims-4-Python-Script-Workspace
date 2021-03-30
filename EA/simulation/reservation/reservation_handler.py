from element_utils import build_critical_section_with_finallyfrom reservation.reservation_result import ReservationResultfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactoryfrom singletons import DEFAULTimport sims4logger = sims4.log.Logger('ReservationHandler', default_owner='miking')
class _ReservationHandler(HasTunableFactory, AutoFactoryInit):

    def __init__(self, sim, target, *args, reservation_interaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = sim
        self._target = target
        self._reservation_interaction = reservation_interaction

    def __str__(self):
        return '{}: {} on {} ({})'.format(type(self).__name__, self.sim, self.target, self.reservation_interaction)

    @property
    def sim(self):
        return self._sim

    @property
    def target(self):
        return self._target

    @property
    def reservation_interaction(self):
        return self._reservation_interaction

    def get_targets(self):
        return (self._target,)

    def allows_reservation(self, other_reservation_handler):
        raise NotImplementedError

    def begin_reservation(self, *_, _may_reserve_already_run=False, **__):
        if self._target.is_sim:
            return ReservationResult.TRUE
        if not _may_reserve_already_run:
            result = self.may_reserve(_from_reservation_call=True)
            if not result:
                logger.warn('begin_reservation() called on target {} but may_reserve() failed. {} ', self._target, result)
                return result
        self._target.add_reservation_handler(self)
        return ReservationResult.TRUE

    def do_reserve(self, sequence=()):
        return build_critical_section_with_finally(self.begin_reservation, sequence, self.end_reservation)

    def end_reservation(self, *_, **__):
        if self._target.is_sim:
            return ReservationResult.TRUE
        return self._target.remove_reservation_handler(self)

    def may_reserve(self, **kwargs):
        if self._target.is_sim:
            return ReservationResult.TRUE
        return self._target.may_reserve(self._sim, reservation_handler=self, **kwargs)

    def may_reserve_internal(self, context=DEFAULT):
        if self._reservation_interaction is not None:
            result = self._reservation_interaction.can_reserve_target(target=self._target, context=context)
            if not result:
                return result
        active_reservation_handlers = self._target.get_reservation_handlers()
        for active_reservation_handler in active_reservation_handlers:
            reserve_result = active_reservation_handler.allows_reservation(self)
            if not reserve_result:
                return reserve_result
            reserve_result = self.allows_reservation(active_reservation_handler)
            if not reserve_result:
                return reserve_result
        return ReservationResult.TRUE

    def _is_sim_allowed_to_clobber(self, other_reservation_handler):
        if self.sim is other_reservation_handler.sim:
            return True
        if other_reservation_handler.sim.is_sim:
            if self.sim.parent is other_reservation_handler.sim:
                return True
            if other_reservation_handler.sim.parent is self.sim:
                return True
            elif self.target.is_reservation_clobberer(self.sim, other_reservation_handler.sim) or self.target.is_reservation_clobberer(other_reservation_handler.sim, self.sim):
                return True
        if self.sim.is_sim and self.target.is_reservation_clobberer(self.sim, other_reservation_handler.sim) or self.target.is_reservation_clobberer(other_reservation_handler.sim, self.sim):
            return True
        return False
