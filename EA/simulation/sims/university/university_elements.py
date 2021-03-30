from interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunableimport sims4.loglogger = sims4.log.Logger('UniversityElements', default_owner='mkartika')
class UniversityEnrollmentElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'is_reenrollment': Tunable(description='\n            If checked, the enrollment UI will be considered re-enrollment\n            where the dialog has preselected university and major.\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self):
        sim = self.interaction.sim
        degree_tracker = sim.sim_info.degree_tracker
        if degree_tracker is None:
            logger.error("Trying to display University Enrollment on {} but that Sim doesn't have a degree tracker.", sim)
            return False
        degree_tracker.generate_enrollment_information(is_reenrollment=self.is_reenrollment)
        return True
