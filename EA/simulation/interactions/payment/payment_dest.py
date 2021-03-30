from protocolbuffers import Consts_pb2from interactions import ParticipantTypefrom interactions.payment.payment_info import PaymentBusinessRevenueType, BusinessPaymentInfofrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableReference, OptionalTunable, TunablePercentimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('Payment', default_owner='rmccord')
class PaymentDestTuningFlags(enum.IntFlags):
    NO_DEST = 0
    ACTIVE_HOUSEHOLD = 1
    PARTICIPANT_HOUSEHOLD = 2
    BUSINESS = 4
    STATISTIC = 8
    ALL = NO_DEST | ACTIVE_HOUSEHOLD | PARTICIPANT_HOUSEHOLD | BUSINESS | STATISTIC

class _PaymentDest(HasTunableSingletonFactory, AutoFactoryInit):

    def give_payment(self, cost_info):
        raise NotImplementedError
        return False

    def get_funds_info(self, resolver):
        return (None, 0, None)

class PaymentDestNone(_PaymentDest):

    def give_payment(self, cost_info):
        return True

class PaymentDestActiveHousehold(_PaymentDest):

    def give_payment(self, cost_info):
        household = services.active_household()
        if household is not None:
            amount = cost_info.amount
            if amount > 0:
                household.funds.add(amount, Consts_pb2.FUNDS_INTERACTION_REWARD)
            return True
        return False

    def get_funds_info(self, resolver):
        household = services.active_household()
        if household is not None:
            money = household.funds.money
            return (household.funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

class PaymentDestParticipantHousehold(_PaymentDest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description="\n            The participant whose household will accept the payment. If the\n            participant is not a Sim, we will use the participant's owning\n            household.\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def give_payment(self, cost_info):
        household = self._get_household(cost_info.resolver)
        if household is not None:
            amount = cost_info.amount
            if amount > 0:
                household.funds.add(amount, Consts_pb2.FUNDS_INTERACTION_REWARD)
            return True
        return False

    def get_funds_info(self, resolver):
        household = self._get_household(resolver)
        if household is not None:
            money = household.funds.money
            return (household.funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

    def _get_household(self, resolver):
        participant = resolver.get_participant(self.participant)
        household = None
        if participant is not None:
            if participant.is_sim:
                household = participant.household
            else:
                household_owner_id = participant.get_household_owner_id()
                household = services.household_manager().get(household_owner_id)
        return household

class PaymentDestBusiness(_PaymentDest):

    def give_payment(self, cost_info):
        if not isinstance(cost_info, BusinessPaymentInfo):
            revenue_type = None
        else:
            revenue_type = cost_info.revenue_type
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.modify_funds(cost_info.amount, from_item_sold=revenue_type == PaymentBusinessRevenueType.ITEM_SOLD)
            return True
        return False

    def get_funds_info(self, resolver):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            money = business_manager.funds.money
            return (business_manager.funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

class PaymentDestStatistic(_PaymentDest):
    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            The statistic that should accept the payment.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'participant': TunableEnumEntry(description='\n            The participant whose statistic will accept the payment.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'is_debt': OptionalTunable(description='\n            True if the statistics is a debt, otherwise False.\n            ', tunable=TunablePercent(description='\n                Percent of debt that is minimum payment.\n                ', default=5), disabled_name='False', enabled_name='True')}

    def give_payment(self, cost_info):
        participant = cost_info.resolver.get_participant(self.participant)
        stat = None
        if participant is not None:
            tracker = participant.get_tracker(self.statistic)
            if tracker is not None:
                stat = tracker.get_statistic(self.statistic)
        if stat is not None:
            amount = cost_info.amount
            if self.is_debt:
                amount = -amount
            stat.add_value(amount)
            return True
        return False

    def get_funds_info(self, resolver):
        participant = resolver.get_participant(self.participant)
        stat = None
        if participant is not None:
            tracker = participant.get_tracker(self.statistic)
            if tracker is not None:
                stat = tracker.get_statistic(self.statistic)
        if stat is not None:
            value = stat.get_value()
            if self.is_debt is not None:
                return (value, value, int(self.is_debt*value))
            else:
                return (stat.max_value - value, value, None)
        return (None, 0, None)
