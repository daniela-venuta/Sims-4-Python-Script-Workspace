import servicesimport sims4.logfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4 import randomfrom sims4.tuning.tunable import OptionalTunable, TunableReferencelogger = sims4.log.Logger('CareerGigOps', default_owner='trevor')
class AddCareerGigOp(BaseLootOperation):
    FACTORY_TUNABLES = {'career_gig': TunableReference(description="\n            Career gig to add. If the Sim already has a Gig for this career, this\n            one will overwrite it. The career for this gig will also be added to\n            the Sim if they don't already have it.\n            ", manager=services.get_instance_manager(sims4.resources.Types.CAREER_GIG)), 'gig_customer_filter': OptionalTunable(description="\n            If enabled, will generate a customer sim for the Gig. If no Sim can be\n            created, the gig won't be added.\n            ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)))}

    def __init__(self, *args, career_gig, gig_customer_filter, **kwargs):
        super().__init__(*args, **kwargs)
        self.career_gig = career_gig
        self.gig_customer_filter = gig_customer_filter

    def _apply_to_subject_and_target(self, subject, target, resolver):
        customer = None
        if self.gig_customer_filter is not None:
            results = services.sim_filter_service().submit_filter(self.gig_customer_filter, callback=None, allow_yielding=False, gsi_source_fn=lambda : f'AddCareerGigOp{str(self)}')
            if not results:
                logger.error('AddCareerGigOP {} is tuned to have an associated sim but the filter returned no results.', self)
                return
            customer = random.pop_weighted([(r.score, r) for r in results]).sim_info
        career_tracker = subject.career_tracker
        career = career_tracker.get_career_by_uid(self.career_gig.career.guid64)
        if career is None:
            career_tracker.add_career(self.career_gig.career(subject.sim_info))
        now = services.time_service().sim_now
        time_till_gig = self.career_gig.get_time_until_next_possible_gig(now)
        if time_till_gig is None:
            logger.error('AddCareerGigOp {} with gig {} failed to find a valid time.', self, self.career_gig)
            return
        career_tracker.set_gig(self.career_gig, now + time_till_gig, gig_customer=customer)
