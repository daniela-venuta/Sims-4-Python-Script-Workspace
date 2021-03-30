import servicesfrom sims.bills_enums import UtilityEndOfBillActionfrom sims.household_utilities.utility_types import Utilitiesfrom sims4.commands import CommandType, Command, output
@Command('bills.sell_excess_utility', command_type=CommandType.Live)
def sell_excess_utility(utility:Utilities, _connection=None):
    active_household = services.active_household()
    if active_household is None:
        output('Attempting to sell excess utilities when there is no active household.', _connection)
        return
    active_household.bills_manager.sell_excess_utility(utility)

@Command('bills.set_utility_end_bill_action', command_type=CommandType.Live)
def set_utility_end_bill_action(utility:Utilities, utility_action:UtilityEndOfBillAction, _connection=None):
    active_household = services.active_household()
    if active_household is None:
        output('Attempting to sell excess utilities when there is no active household.', _connection)
        return
    active_household.bills_manager.set_utility_end_bill_action(utility, utility_action)

@Command('bills.show_bills_dialog', command_type=CommandType.Live)
def show_bills_dialog(_connection=None):
    active_household = services.active_household()
    if active_household is None:
        output('Attempting to show bills dialog when there is no active household.', _connection)
        return
    active_household.bills_manager.show_bills_dialog()
