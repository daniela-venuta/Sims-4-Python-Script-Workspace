from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariantimport sims4.logfrom interactions.payment.payment_cost import PaymentAmount, PaymentAmountUpTo, PaymentBills, PaymentCatalogValue, PaymentCurrentValue, PaymentBaseRetailValue, PaymentBaseDiningBill, PaymentBusinessAmount, PaymentDialog, PaymentFromLiability, PaymentUtility, PaymentMarketplaceListingfrom interactions.payment.payment_source import get_tunable_payment_source_variantfrom snippets import define_snippetfrom tunable_multiplier import TunableMultiplierlogger = sims4.log.Logger('Payment', default_owner='rmccord')
class Payment(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'payment_cost': TunableVariant(description='\n            The type of payment, which defines the payment amount.\n            ', amount=PaymentAmount.TunableFactory(), amount_up_to=PaymentAmountUpTo.TunableFactory(), bills=PaymentBills.TunableFactory(), catalog_value=PaymentCatalogValue.TunableFactory(), current_value=PaymentCurrentValue.TunableFactory(), base_retail_value=PaymentBaseRetailValue.TunableFactory(), dining_meal_cost=PaymentBaseDiningBill.TunableFactory(), business_amount=PaymentBusinessAmount.TunableFactory(), input_dialog=PaymentDialog.TunableFactory(), liability=PaymentFromLiability.TunableFactory(), object_marketplace_listing=PaymentMarketplaceListing.TunableFactory(), utility=PaymentUtility.TunableFactory(), default='amount'), 'payment_source': get_tunable_payment_source_variant(description='\n            The source of the funds.\n            '), 'cost_modifiers': TunableMultiplier.TunableFactory(description='\n            A tunable list of test sets and associated multipliers to apply to\n            the total cost of this payment.\n            ')}

    def get_simoleon_delta(self, resolver, override_amount=None):
        (amount, fund_source) = self.payment_cost.get_simoleon_delta(resolver, self.payment_source, self.cost_modifiers)
        if self.payment_source.require_full_amount:
            return (amount, fund_source)
        else:
            return (0, fund_source)

    def try_deduct_payment(self, resolver, sim, fail_callback=None):
        success = self.payment_cost.try_deduct_payment(resolver, sim, fail_callback, self.payment_source, self.cost_modifiers)
        if success or fail_callback:
            fail_callback()
        return success

    def get_cost_string(self):
        return self.payment_source.get_cost_string()

    def get_gain_string(self):
        return self.payment_source.get_gain_string()
(TunablePaymentReference, TunablePaymentSnippet) = define_snippet('payment', Payment.TunableFactory())