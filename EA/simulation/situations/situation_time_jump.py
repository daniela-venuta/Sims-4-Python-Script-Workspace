import servicesimport sims4.resourcesfrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableVariant, TunableReference, Tunable, AutoFactoryInit
class _SituationTimeJump(HasTunableSingletonFactory):

    def should_load(self, seed):
        raise NotImplementedError

    def require_guest_list_regeneration(self, situation):
        return False

class SituationTimeJumpDisallow(_SituationTimeJump):

    def should_load(self, seed):
        if services.current_zone().time_has_passed_in_world_since_zone_save():
            return False
        return True

class SituationTimeJumpAllow(_SituationTimeJump):

    def should_load(self, seed):
        return True

    def require_guest_list_regeneration(self, situation):
        if services.current_zone().time_has_passed_in_world_since_zone_save():
            return True
        return False

class SituationTimeJumpSimulate(SituationTimeJumpAllow):

    def should_load(self, seed):
        if not services.current_zone().time_has_passed_in_world_since_zone_save():
            return True
        else:
            situation_type = seed.situation_type
            if situation_type is not None and situation_type.should_load_after_time_jump(seed):
                seed.allow_time_jump = True
                return True
        return False

class SituationTimeJumpGigBased(_SituationTimeJump, AutoFactoryInit):
    FACTORY_TUNABLES = {'gig': TunableReference(description='\n            The gig house Sims must have in order for this situation to\n            time jump.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_GIG)), 'time_jump_allowed': Tunable(description='\n            If checked, time jump is allowed if any household Sim has the tuned \n            Gig and disallowed if no Sims are on the tuned Gig.\n            If unchecked, time jump is disallowed if any household Sim has the \n            tuned Gig and allowed if no Sims are on the tuned Gig.\n            ', tunable_type=bool, default=True)}

    def should_load(self, seed):
        gig_guid = self.gig.guid64
        career_guid = self.gig.career.guid64
        sim_has_gig = False
        for sim_info in services.active_household():
            gig_career = sim_info.career_tracker.get_career_by_uid(career_guid)
            if gig_career is None:
                pass
            else:
                current_gig = gig_career.get_current_gig()
                if current_gig is not None and current_gig.guid64 == gig_guid:
                    return self.time_jump_allowed
        return not self.time_jump_allowed
SITUATION_TIME_JUMP_DISALLOW = SituationTimeJumpDisallow()
class TunableSituationTimeJumpVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, disallow=SituationTimeJumpDisallow.TunableFactory(), allow=SituationTimeJumpAllow.TunableFactory(), simulate=SituationTimeJumpSimulate.TunableFactory(), gig_based=SituationTimeJumpGigBased.TunableFactory(), default='disallow', **kwargs)
