from interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableVariantimport servicesimport sims4logger = sims4.log.Logger('Organization Loot', default_owner='shipark')
class _JoinOrganizationOp(HasTunableSingletonFactory, AutoFactoryInit):

    def apply(self, subject, org_id):
        organization_service = services.organization_service()
        if organization_service is None:
            return False
        return organization_service.add_organization_member(subject, org_id)

class _LeaveOrganizationOp(HasTunableSingletonFactory, AutoFactoryInit):

    def apply(self, subject, org_id):
        organization_tracker = subject.organization_tracker
        if organization_tracker is None:
            return False
        organization_tracker.leave_organization(org_id)
        return True

class OrganizationMembershipLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'organization': TunableReference(description='\n            The organization to join or leave.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='Organization'), 'membership_action': TunableVariant(description='\n            Specify joining or leaving the tuned organization.\n            ', join=_JoinOrganizationOp.TunableFactory(), leave=_LeaveOrganizationOp.TunableFactory(), default='join')}

    def __init__(self, organization, membership_action, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.membership_action = membership_action

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('Attempting to run membership action on {} which is not a Sim.', subject)
        if not self.membership_action.apply(subject, self.organization.guid64):
            logger.error('Membership Loot Action failed on {}, org tracker or service were not available.', subject)
