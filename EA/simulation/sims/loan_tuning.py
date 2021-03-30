from protocolbuffers import Sims_pb2, Consts_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom sims4.tuning.tunable import TunableReference, TunableMapping, TunableEnumEntry, TunablePercent, TunablePackSafeReferencefrom sims4.tuning.tunable_base import ExportModesfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport enumimport servicesimport sims4.resources
class LoanType(enum.Int):
    INVALID = 0
    UNIVERSITY = 1

class LoanTunables:
    DEBT_STATISTIC = TunableReference(description='\n        The statistic used to track the amount of debt this Sim has incurred.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Statistic',))
    DEATH_DEBT_COLLECTION_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        The notification shown when a Sim that has unpaid debt dies.\n        ')
    POVERTY_LOOT = TunablePackSafeReference(description='\n        A loot action applied to all other members of the household if a Sim\n        with unpaid dies, and the debt amount is greater than or equal to\n        the household funds.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))
    INTEREST_MAP = TunableMapping(description='\n        Mapping between loan type and the interest rate for that type.\n        ', key_type=TunableEnumEntry(description='\n            The type of loan taken.\n            ', tunable_type=LoanType, default=LoanType.INVALID, invalid_enums=(LoanType.INVALID,)), value_type=TunablePercent(description='\n            The interest rate for the corresponding loan type.\n            ', default=10), tuple_name='InterestMappingTuple', export_modes=ExportModes.All)

    @staticmethod
    def get_loan_amount(amount, loan_type):
        interest_rate = LoanTunables.INTEREST_MAP.get(loan_type, 0)
        amount += amount*interest_rate
        return int(amount)

    @staticmethod
    def add_debt(sim_info, amount):
        if amount == 0:
            return
        sim_info_debt_stat = sim_info.statistic_tracker.get_statistic(LoanTunables.DEBT_STATISTIC, add=True)
        sim_info_debt_stat.add_value(amount)
        LoanTunables.send_loan_op(sim_info, -amount)

    @staticmethod
    def send_loan_op(sim_info, amount):
        msg = Sims_pb2.SetLoan()
        msg.amount = amount
        op = GenericProtocolBufferOp(Operation.SET_LOAN, msg)
        Distributor.instance().add_op(sim_info, op)

    @staticmethod
    def on_death(sim_info):
        debt_stat = sim_info.statistic_tracker.get_statistic(LoanTunables.DEBT_STATISTIC)
        if debt_stat is None:
            return
        debt_amount = debt_stat.get_value()
        if debt_amount == 0:
            return
        resolver = SingleSimResolver(sim_info)
        dialog = LoanTunables.DEATH_DEBT_COLLECTION_NOTIFICATION(sim_info, resolver=resolver)
        dialog.show_dialog()
        household_funds = sim_info.household.funds.money
        if debt_amount >= household_funds:
            for hh_sim_info in sim_info.household.sim_info_gen():
                if sim_info is hh_sim_info:
                    pass
                else:
                    resolver = DoubleSimResolver(hh_sim_info, sim_info)
                    LoanTunables.POVERTY_LOOT.apply_to_resolver(resolver)
        amount_to_remove = min(debt_amount, household_funds)
        sim_info.household.funds.try_remove_amount(amount_to_remove, Consts_pb2.TELEMETRY_LOANS_SIM_DEATH)
