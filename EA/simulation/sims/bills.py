import telemetry_helperfrom collections import namedtuplefrom distributor.ops import ShowBillsPanelfrom distributor.system import Distributorfrom event_testing.test_events import TestEventfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning, TunableLocalizedStringfrom sims4.telemetry import TelemetryWriterfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuple, TunablePercent, TunableInterval, TunableMapping, TunableReference, TunableEnumEntry, TunableRange, TunableVariant, OptionalTunablefrom sims4.utils import flexmethodfrom singletons import DEFAULTimport sims4.logimport sims4.mathfrom audio.primitive import TunablePlayAudio, play_tunable_audiofrom clock import interval_in_sim_weeksfrom date_and_time import TimeSpan, create_date_and_time, DateAndTime, MINUTES_PER_HOUR, HOURS_PER_DAYfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom event_testing.tests import TunableTestSetfrom protocolbuffers import Consts_pb2from sims.funds import get_funds_for_source, FundsSourcefrom sims.household_utilities.utility_types import Utilities, UtilityShutoffReasonPriorityfrom tunable_multiplier import TunableMultiplierfrom tunable_time import TunableTimeOfWeek, Days, TunableTimeSpanfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport alarmsimport build_buyimport clockimport objects.componentsimport servicesfrom sims.bills_enums import AdditionalBillSource, UtilityEndOfBillActionlogger = sims4.log.Logger('Bills', default_owner='jjacobson')TELEMETRY_GROUP_BILLS = 'BILL'TELEMETRY_HOOK_BILL_GIVEN = 'BIGI'TELEMETRY_RENT = 'rent'TELEMETRY_PROPERTY_TAX = 'prot'TELEMETRY_OTHER_BILLS = 'otbi'TELEMETRY_POWER = 'powr'TELEMETRY_WATER = 'watr'bills_telemetry_writer = TelemetryWriter(TELEMETRY_GROUP_BILLS)UtilityInfo = namedtuple('UtilityInfo', ('utility', 'cost', 'max_value', 'current_value', 'utility_name', 'utility_symbol', 'rate_of_change', 'selling'))SummaryLineItem = namedtuple('SummaryLineItem', ('amount', 'label', 'tooltip'))
class BillReductionEnum(DynamicEnumLocked):
    GlobalPolicy_ControlInvasiveSpecies = 0
    GlobalPolicy_ControlOverfishing = 1
    GlobalPolicy_CoconutRebate = 2
    GlobalPolicy_SupportOrganicProduce = 3
    GlobalPolicy_ExperimentalPollutionCleaner = 4
    GlobalPolicy_LitteringFines = 5

class UnpaidBillSourceInfo:
    __slots__ = ('billable_amount', 'net_consumption', 'statistic_deltas')

    def __init__(self):
        self.billable_amount = 0
        self.net_consumption = 0
        self.statistic_deltas = None

    def add_delta(self, statistic, delta):
        if not sims4.math.almost_equal(delta, 0):
            if self.statistic_deltas is None:
                self.statistic_deltas = []
            self.statistic_deltas.append((statistic, delta))

    def __add__(self, o):
        ret = UnpaidBillSourceInfo()
        ret.billable_amount = self.billable_amount + o.billable_amount
        ret.net_consumption = self.net_consumption + o.net_consumption
        stat_set = set()
        if self.statistic_deltas:
            stat_set.update([d[0] for d in self.statistic_deltas])
        if o.statistic_deltas:
            stat_set.update([d[0] for d in o.statistic_deltas])
        if stat_set:
            ret.statistic_deltas = []
            for stat in stat_set:
                delta = sum([d[1] if d[0] == stat else 0 for d in self.statistic_deltas])
                delta += sum([d[1] if d[0] == stat else 0 for d in o.statistic_deltas])
                ret.statistic_deltas.append((stat, delta))
        return ret

    def __sub__(self, o):
        ret = UnpaidBillSourceInfo()
        ret.billable_amount = self.billable_amount - o.billable_amount
        ret.net_consumption = self.net_consumption - o.net_consumption
        stat_set = set()
        if self.statistic_deltas:
            stat_set.update([d[0] for d in self.statistic_deltas])
        if o.statistic_deltas:
            stat_set.update([d[0] for d in o.statistic_deltas])
        if stat_set:
            ret.statistic_deltas = []
            for stat in stat_set:
                delta = sum([d[1] if d[0] == stat else 0 for d in self.statistic_deltas])
                delta -= sum([d[1] if d[0] == stat else 0 for d in o.statistic_deltas])
                ret.statistic_deltas.append((stat, delta))
        return ret

    def is_zero(self):
        return sims4.math.almost_equal(self.billable_amount, 0.0) and (sims4.math.almost_equal(self.net_consumption, 0.0) and (self.statistic_deltas is None or sum([1 if d[1] != 0 else 0 for d in self.statistic_deltas]) == 0))
ALL_BILLS_SOURCE = -1PROPERTY_TAX_SOURCE = -2
class BillsSourceVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, all_bills=TunableTuple(description='\n                Apply this reduction to all bills.\n                ', locked_args={'utility': ALL_BILLS_SOURCE}), property_taxes=TunableTuple(description='\n                Apply this reduction to property taxes\n                ', locked_args={'utility': PROPERTY_TAX_SOURCE}), utility=TunableTuple(description='\n                Apply this reduction to property taxes\n                ', utility=TunableEnumEntry(description='\n                    The utility to modify.\n                    ', tunable_type=Utilities, default=Utilities.POWER)), default='all_bills', **kwargs)

class BillsItemizedEntryDisplay(TunableTuple):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_label=TunableLocalizedString(description='\n                Label text to use for the line item.\n                '), generic_tooltip=TunableLocalizedString(description='\n                Text to show as the default tooltip for the line item when an additional\n                breakdown is not available.\n                '), detailed_tooltip=OptionalTunable(TunableLocalizedStringFactory(description='\n                If additional information is available, this tooltip is shown\n                instead of the generic one and provided a formatted list of reasons\n                as a 0.String token.\n                If this string is not provided, the generic tooltip is used instead.\n                ')), **kwargs)

class Bills:
    BILL_ARRIVAL_NOTIFICATION = TunableList(description='\n        A list of notifications that show up if bills are delivered. We run\n        through the notifications and tests in order to see which one passes\n        first.\n        ', tunable=TunableTuple(description='\n            Tests and Notification for when bills are delivered. We run the\n            tests first before popping the notification.\n            ', notification=UiDialogNotification.TunableFactory(description='\n                A notification which pops up when bills are delivered.\n                '), tests=TunableTestSet(description='\n                Tests to determine if we should show this notification.\n                ')))
    BILL_ARRIVAL_NOTIFICATION_LOOT = TunableList(description='\n        A list of loot actions that show up if bills are delivered and a notification is shown.\n        We run through the loot actions and tests in order to see which ones pass.\n        ', tunable=TunableReference(description='\n                The bill notification loot action applied.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))
    REDUCTION_REASON_TEXT_MAP = TunableMapping(description='\n        A mapping of reduction reason to text that will appear as a bullet\n        in a bulleted list in the bill arrival notification.\n        ', key_type=TunableEnumEntry(description='\n            Reason for bill reduction.\n            ', tunable_type=BillReductionEnum, default=BillReductionEnum.GlobalPolicy_ControlInvasiveSpecies), value_type=TunableLocalizedString(description='\n            A string representing the bill reduction in the bills panel.\n            '))
    REDUCTION_REASON_SOURCE = TunableMapping(description="\n        A mapping of reduction reason to what part of the bill it'll modify.\n        ", key_type=TunableEnumEntry(description='\n            Reason for bill reduction.\n            ', tunable_type=BillReductionEnum, default=BillReductionEnum.GlobalPolicy_ControlInvasiveSpecies), value_type=BillsSourceVariant(description='\n            The source of bills to apply this reduction to.\n            '))
    UTILITY_INFO = TunableMapping(key_type=Utilities, value_type=TunableList(description='\n            Utility specific controls.  Tuning for tested UI when a utility will\n            soon become delinquent or is shut off as well as tuning for the computation\n            of the usage and bill.\n            ', tunable=TunableTuple(description='\n                Notifications and tooltips related to shutting off utilities,\n                accompanied by tests which must pass before we show the\n                notification or tooltip.\n                ', warning_notification=UiDialogNotification.TunableFactory(description='\n                    A notification which appears when the player will be losing this\n                    utility soon due to delinquency.\n                    '), shutoff_notification=UiDialogNotification.TunableFactory(description='\n                    A notification which appears when the player loses this utility\n                    due to delinquency.\n                    '), shutoff_tooltip=TunableLocalizedStringFactory(description='\n                    A tooltip to show when an interaction cannot be run due to this\n                    utility being shutoff.\n                    '), tests=TunableTestSet(description='\n                    Test set which determines if we show the notification and\n                    tooltip or not.\n                    '), statistic=TunableReference(description='\n                    The statistic keeping how much of the net consumption of this utility.  Positive values indicate\n                    production while negative values indicate usage.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), statistic_sell_value=Tunable(description="\n                    The value that the statistic will be set to when selling the excess value either through\n                    a cheat or at the end of the bills period.  This is to make it so that if your utilities would\n                    normally be shutoff for not having a positive value we have fudged it up just slightly so that\n                    they won't flicker off and on.\n                    ", tunable_type=float, default=1.0), unit_cost=Tunable(description='\n                    The Simoleon unit cost for this utility.\n                    ', tunable_type=float, default=1), unit_cost_sell_price_multiplier=TunableMultiplier.TunableFactory(description='\n                    A price multiplier that will be applied when selling this utility.\n                    '), name=TunableLocalizedString(description='\n                    The name of this utility for the bills panel ui.\n                    '), font_symbol=Tunable(description='\n                    The decimal value for the unicode code point that represents the font symbol used for this utility.\n                    Ask your UX partner or see the Special Characters list on confluence for this value.\n                    Note that unicode values are usually represented as hexadecimal (i.e. U+2B20) but this value needs to be\n                    inputted as a decimal (i.e. 11040)\n                    ', tunable_type=int, default=0))))
    BILLS_UI = TunableTuple(description='\n        Tunables related to the display of the bills UI.\n        ', rent_item_display=BillsItemizedEntryDisplay(description='\n            Configures how rent is displayed.\n            '), property_tax_item_display=BillsItemizedEntryDisplay(description='\n            Configures how property/lot tax is displayed.\n            '), tax_modifiers_item_display=BillsItemizedEntryDisplay(description='\n            Configures how tax modifiers are displayed.\n            '), additional_bills_item_display=BillsItemizedEntryDisplay(description='\n            Configures how additional bills or taxes are displayed.\n            '), utility_item_display=TunableMapping(description='\n            Configures how each utility is displayed in an itemized billing list.\n            ', key_type=Utilities, value_type=TunableTuple(description='\n                Configure how a utility is displayed in an itemized billing list.\n                ', tooltip=TunableLocalizedString(description='\n                    Tooltip to display for the utility line item.\n                    '))), unpaid_bills_display=BillsItemizedEntryDisplay(description='\n            Configures how unpaid bills are displayed.\n            '), unpaid_rent_display=BillsItemizedEntryDisplay(description='\n            Configures how unpaid rent is displayed.\n            '))
    BILL_COST_MODIFIERS_SIM_WITH_REASON = TunableList(description='\n        A tunable list of test sets and associated multipliers to apply to the\n        total bill cost per payment on a per Sim basis.\n        ', tunable=TunableTuple(description='\n            A multiplier that could be applied to the total bill.\n            ', test=TunableTestSet(description='\n                If this test set passes then the bills will be multiplied by this amount.\n                '), multiplier=TunableRange(description='\n                The multiplier to apply to to the bill when the tests pass.\n                ', tunable_type=float, default=1, minimum=0), multiplier_description=TunableLocalizedString(description='\n                The description of the multiplier that will appear in the tooltip\n                of the tax breaks tooltip.\n                '), source=BillsSourceVariant(description='\n                The source of bills to apply this reduction to.\n                ')))
    BILL_COST_MODIFIERS_HOUSEHOLD_WITH_REASON = TunableList(description='\n        A tunable list of test sets and associated multipliers to apply to the\n        total bill cost per payment on a per household basis.\n        ', tunable=TunableTuple(description='\n            A multiplier that could be applied to the total bill.\n            ', test=TunableTestSet(description='\n                If this test set passes then the bills will be multiplied by this amount.\n                '), multiplier=TunableRange(description='\n                The multiplier to apply to to the bill when the tests pass.\n                ', tunable_type=float, default=1, minimum=0), multiplier_description=TunableLocalizedString(description='\n                The description of the multiplier that will appear in the tooltip\n                of the tax breaks tooltip.\n                '), source=BillsSourceVariant(description='\n                The source of bills to apply this reduction to.\n                ')))
    BILL_OBJECT = TunableReference(description="\n        The object that will be delivered to the lot's mailbox once bills have\n        been scheduled.\n        ", manager=services.definition_manager())
    DELINQUENCY_FREQUENCY = Tunable(description='\n        Tunable representing the number of Sim hours between utility shut offs.\n        ', tunable_type=int, default=24)
    DELINQUENCY_WARNING_OFFSET_TIME = Tunable(description='\n        Tunable representing the number of Sim hours before a delinquency state\n        kicks in that a warning notification pops up.\n        ', tunable_type=int, default=2)
    BILL_BRACKETS = TunableList(description="\n        A list of brackets that determine the percentages that each portion of\n        a household's value is taxed at.\n        \n        ex: The first $2000 of a household's value is taxed at 10%, and\n        everything after that is taxed at 15%.\n        ", tunable=TunableTuple(description='\n            A value range and tax percentage that define a bill bracket.\n            ', value_range=TunableInterval(description="\n                A tunable range of integers that specifies a portion of a\n                household's total value.\n                ", tunable_type=int, default_lower=0, default_upper=None), tax_percentage=TunablePercent(description="\n                A tunable percentage value that defines what percent of a\n                household's value within this value_range the player is billed\n                for.\n                ", default=10)))
    TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY = TunableTimeOfWeek(description="\n        The time of the week that we will attempt to place a bill in this\n        household's hidden inventory so it can be delivered.  This time should\n        be before the mailman shows up for that day or the bill will not be\n        delivered until the following day.\n        ", default_day=Days.MONDAY, default_hour=8, default_minute=0)
    AUDIO = TunableTuple(description='\n        Tuning for all the audio stings that will play as a part of bills.\n        ', delinquency_warning_sfx=TunablePlayAudio(description='\n            The sound to play when a delinquency warning is displayed.\n            '), delinquency_activation_sfx=TunablePlayAudio(description='\n            The sound to play when delinquency is activated.\n            '), delinquency_removed_sfx=TunablePlayAudio(description='\n            The sound to play when delinquency is removed.\n            '), bills_paid_sfx=TunablePlayAudio(description='\n            The sound to play when bills are paid.  If there are any delinquent\n            utilities, the delinquency_removed_sfx will play in place of this.\n            '))
    BILLS_UTILITY_SHUTOFF_REASON = TunableEnumEntry(description='\n        The utility shutoff reason for bills. This determines how important the\n        bills tooltip is when we shutoff the utility for delinquent bills\n        relative to other shutoff reasons.\n        ', tunable_type=UtilityShutoffReasonPriority, default=UtilityShutoffReasonPriority.NO_REASON)
    LOT_OWED_PAYMENT_SUCCEED = TunableUiDialogNotificationSnippet(description='\n        A notification which pops up when payment owed from previous lot is deducted.\n        ')
    LOT_OWED_PAYMENT_FAIL = TunableUiDialogNotificationSnippet(description='\n        A notification which pops up when payment owed from previous lot fails to be deducted.\n        ')
    REPO_MAN_TIMER = TunableTimeSpan(description='\n        The amount of time after the last utility is turned off that the repo man will become valid to start\n        showing up.\n        ')
    BILL_COLOR_STRING_POSITIVE = TunableLocalizedStringFactory(description='\n        The localized string factory to add a color to a money value if it is positive.\n        ')
    BILL_COLOR_STRING_NEGATIVE = TunableLocalizedStringFactory(description='\n        The localized string factory to add a color to a money value if it is negative.\n        ')
    BILL_TUTORIAL = TunableReference(description='\n        Tutorial instance for the bills notification lesson.\n        ', manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL), allow_none=True, class_restrictions=('Tutorial',))
    ADDITIONAL_BILL_SOURCE_KEY_START = 256
    UNKNOWN_SOURCE_KEY_START = 2147483648

    @staticmethod
    def get_bill_source_key_from_enum(value):
        if isinstance(value, Utilities):
            return int(value)
        if isinstance(value, AdditionalBillSource):
            return Bills.ADDITIONAL_BILL_SOURCE_KEY_START + int(value)
        logger.error('Unexpected bill source ', value, owner='shouse')
        return Bills.UNKNOWN_SOURCE_KEY_START + int(value)

    @staticmethod
    def get_bill_source_enum_from_key(key):
        if key < Bills.ADDITIONAL_BILL_SOURCE_KEY_START:
            return Utilities(key)
        if key < Bills.UNKNOWN_SOURCE_KEY_START:
            return AdditionalBillSource(key - 256)
        return key & ~Bills.UNKNOWN_SOURCE_KEY_START

    def __init__(self, household):
        self._household = household
        self._utility_delinquency = {utility: False for utility in Utilities}
        self._can_deliver_bill = False
        self._current_payment_owed = None
        self._current_bill_details = {}
        self._bill_timer_handle = None
        self._shutoff_handle = None
        self._warning_handle = None
        self._additional_bill_costs = {}
        self.bill_notifications_enabled = True
        self.autopay_bills = False
        self._stored_bill_timer_ticks = 0
        self._stored_shutoff_timer_ticks = 0
        self._stored_warning_timer_ticks = 0
        self._put_bill_in_hidden_inventory = False
        self._lot_unpaid_bill = {}
        self._utility_bill_action = {}
        self._repo_man_due_time = None

    @property
    def can_deliver_bill(self):
        return self._can_deliver_bill

    @property
    def is_repo_man_due(self):
        if self._repo_man_due_time is None:
            return False
        now = services.time_service().sim_now
        return now > self._repo_man_due_time

    @property
    def current_payment_owed(self):
        return self._current_payment_owed

    def reduce_amount_owed(self, amount):
        if self._current_payment_owed is None:
            return
        self._current_payment_owed -= amount
        if self._current_payment_owed <= 0:
            self.pay_bill(clear_bill=True)

    def current_source_owed(self, source):
        return self._current_bill_details.get(Bills.get_bill_source_key_from_enum(source))

    def get_end_of_bill_action(self, utility):
        return self._utility_bill_action.get(utility, UtilityEndOfBillAction.SELL)

    def set_utility_end_bill_action(self, utility, utility_action):
        self._utility_bill_action[utility] = utility_action

    @flexmethod
    def get_utility_info(cls, inst, utility):
        utility_infos = cls.UTILITY_INFO[utility]
        sim_info = services.active_sim_info()
        if sim_info is None or sim_info.household is not inst._household:
            sim_infos = inst._household.sim_infos
            if sim_infos:
                sim_info = sim_infos[0]
        if inst is not None and sim_info is None:
            resolver = GlobalResolver()
        else:
            resolver = SingleSimResolver(sim_info)
        for utility_info in utility_infos:
            if utility_info.tests.run_tests(resolver):
                return utility_info
        logger.error('Utility Info could not pass tests for {}. Please check tuning in bills', utility, owner='rmccord')

    def _get_lot(self):
        home_zone = services.get_zone(self._household.home_zone_id)
        if home_zone is not None:
            return home_zone.lot

    def _set_up_alarm(self, timer_data, handle, callback):
        if timer_data <= 0:
            return
        if handle is not None:
            alarms.cancel_alarm(handle)
        return alarms.add_alarm(self._household, clock.TimeSpan(timer_data), callback, use_sleep_time=False, cross_zone=True)

    def _set_up_bill_timer(self, from_negative_payout=False):
        if self._current_payment_owed is not None:
            return
        if self._stored_bill_timer_ticks > 0:
            self._bill_timer_handle = self._set_up_alarm(self._stored_bill_timer_ticks, self._bill_timer_handle, lambda _: self.allow_bill_delivery())
            self._stored_bill_timer_ticks = 0
            return
        day = self.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY.day
        hour = self.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY.hour
        minute = self.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY.minute
        time = create_date_and_time(days=day, hours=hour, minutes=minute)
        time_until_bill_delivery = services.time_service().sim_now.time_to_week_time(time)
        bill_delivery_time = services.time_service().sim_now + time_until_bill_delivery
        end_of_first_week = DateAndTime(0) + interval_in_sim_weeks(1)
        if from_negative_payout or bill_delivery_time < end_of_first_week:
            time_until_bill_delivery += interval_in_sim_weeks(1)
        if time_until_bill_delivery.in_ticks() <= 0:
            time_until_bill_delivery = TimeSpan(1)
        self._bill_timer_handle = alarms.add_alarm(self._household, time_until_bill_delivery, lambda _: self.allow_bill_delivery(), cross_zone=True)

    def _set_up_timers(self):
        self._set_up_bill_timer()
        if self._stored_shutoff_timer_ticks == 0 and self._stored_warning_timer_ticks == 0:
            return
        next_delinquent_utility = None
        for utility in self._utility_delinquency:
            if self._utility_delinquency[utility]:
                pass
            else:
                next_delinquent_utility = utility
                break
        logger.error('Household {} has stored shutoff {} or warning {} ticks but all utilities are already delinquent.', self._household, self._stored_shutoff_timer_ticks, self._stored_warning_timer_ticks)
        self._stored_shutoff_timer_ticks = 0
        self._stored_warning_timer_ticks = 0
        return
        utility_info = self.get_utility_info(next_delinquent_utility)
        if utility_info is not None:
            warning_notification = utility_info.warning_notification
            self._warning_handle = self._set_up_alarm(self._stored_warning_timer_ticks, self._warning_handle, lambda _: self._send_notification(warning_notification))
        self._shutoff_handle = self._set_up_alarm(self._stored_shutoff_timer_ticks, self._shutoff_handle, lambda _: self._shut_off_utility(next_delinquent_utility))
        self._stored_shutoff_timer_ticks = 0
        self._stored_warning_timer_ticks = 0

    def get_bills_arrival_notification(self):
        resolver = SingleSimResolver(services.active_sim_info())
        for notification_tests in self.BILL_ARRIVAL_NOTIFICATION:
            if notification_tests.tests.run_tests(resolver):
                return notification_tests.notification
        logger.error('No tests passed for bills arrival notifications. Please check tuning in bills.', owner='rmccord')

    def give_bills_arrival_notification_loots(self):
        resolver = SingleSimResolver(services.active_sim_info())
        for notification_loot in self.BILL_ARRIVAL_NOTIFICATION_LOOT:
            notification_loot.apply_to_resolver(resolver)

    def sanitize_household_inventory(self):
        if build_buy.is_household_inventory_available(self._household.id):
            bill_ids = build_buy.find_objects_in_household_inventory((self.BILL_OBJECT.id,), self._household.id)
            for bill_id in bill_ids:
                build_buy.remove_object_from_household_inventory(bill_id, self._household)

    def on_all_households_and_sim_infos_loaded(self):
        if self._household.id != services.active_household_id():
            return
        if services.venue_service().get_venue_tuning(self._household.home_zone_id).is_university_housing:
            self.autopay_bills = True
        if self._household and self._household.home_zone_id != 0 and self._current_payment_owed is not None and self._stored_shutoff_timer_ticks == 0 and not (self._can_deliver_bill or self.is_any_utility_delinquent()):
            logger.error('Household {} loaded in a state where bills will never advance. Kickstarting the system.', self._household)
            self.trigger_bill_notifications_from_delivery()
            return
        if self._can_deliver_bill and self._get_lot() is None:
            self.trigger_bill_notifications_from_delivery()
        else:
            self._set_up_timers()
        if self.current_payment_owed is None:
            self._destroy_all_bills_objects()

    def on_active_sim_set(self):
        if self._household.id != services.active_household_id():
            return
        current_zone_id = services.current_zone_id()
        bills_paid_key_tuple = []
        money_to_pay = 0
        sim_ids_at_current_zone = [sim_info.id for sim_info in self._household.sim_info_gen() if sim_info.zone_id == current_zone_id]
        previous_zone_id = 0
        for (key_tuple, money_info) in self._lot_unpaid_bill.items():
            (zone_id, _) = key_tuple
            if zone_id == current_zone_id:
                pass
            else:
                (money_amount, sim_ids) = money_info
                if not any(sim_id in sim_ids for sim_id in sim_ids_at_current_zone):
                    pass
                else:
                    money_to_pay += money_amount
                    bills_paid_key_tuple.append(key_tuple)
                    previous_zone_id = zone_id
        if money_to_pay > 0:
            active_sim = services.get_active_sim()
            funds = get_funds_for_source(FundsSource.HOUSEHOLD, sim=active_sim)
            payment_succeed_notification = self.LOT_OWED_PAYMENT_SUCCEED
            payment_fail_notification = self.LOT_OWED_PAYMENT_FAIL
            venue_tuning = services.venue_service().get_venue_tuning(previous_zone_id)
            if venue_tuning is not None:
                zone_director_tuning = venue_tuning.zone_director
                if zone_director_tuning.venue_owed_payment_data.payment_succeed_notification is not None:
                    payment_succeed_notification = zone_director_tuning.venue_owed_payment_data.payment_succeed_notification
                if zone_director_tuning.venue_owed_payment_data.payment_fail_notification is not None:
                    payment_fail_notification = zone_director_tuning.venue_owed_payment_data.payment_fail_notification
            if funds.try_remove(money_to_pay, Consts_pb2.TELEMETRY_INTERACTION_COST, active_sim):
                dialog = payment_succeed_notification(active_sim.sim_info, None)
                dialog.show_dialog(additional_tokens=(money_to_pay,))
            else:
                dialog = payment_fail_notification(active_sim.sim_info, None)
                dialog.show_dialog(additional_tokens=(money_to_pay,))
        for key_tuple in bills_paid_key_tuple:
            del self._lot_unpaid_bill[key_tuple]

    def is_utility_delinquent(self, utility):
        if self._utility_delinquency[utility]:
            if self._current_payment_owed is None:
                self._clear_delinquency_status()
                logger.error('Household {} has delinquent utilities without actually owing any money. Resetting delinquency status.', self._household)
                return False
            else:
                return True
        return False

    def is_any_utility_delinquent(self):
        for delinquency_status in self._utility_delinquency.values():
            if delinquency_status:
                return True
        return False

    def mailman_has_delivered_bills(self):
        if self.current_payment_owed is not None and (self._shutoff_handle is not None or self.is_any_utility_delinquent()):
            return True
        return False

    def is_additional_bill_source_delinquent(self, additional_bill_source):
        cost = self._additional_bill_costs.get(additional_bill_source, 0)
        if cost > 0 and any(self._utility_delinquency.values()):
            return True
        return False

    def get_utility_bill_info(self, utility):
        bill_info = UnpaidBillSourceInfo()
        lot = self._get_lot()
        statistic_component = None if lot is None else lot.get_component(objects.components.types.STATISTIC_COMPONENT)
        utility_info = self.get_utility_info(utility)
        if statistic_component is not None and utility_info is not None:
            statistic_value = statistic_component.get_stat_value(utility_info.statistic)
            bill_info.net_consumption = statistic_value
            if bill_info.net_consumption > utility_info.statistic_sell_value:
                keep_excess_production = self._utility_bill_action.get(utility, UtilityEndOfBillAction.SELL) == UtilityEndOfBillAction.STORE
                bill_info.net_consumption -= utility_info.statistic_sell_value
            elif bill_info.net_consumption > 0:
                keep_excess_production = True
            else:
                keep_excess_production = False
            if keep_excess_production:
                bill_info.billable_amount = 0
                bill_info.add_delta(utility_info.statistic, 0)
            else:
                if bill_info.net_consumption > 0:
                    resolver = GlobalResolver()
                    multiplier = utility_info.unit_cost_sell_price_multiplier.get_multiplier(resolver)
                else:
                    multiplier = 1
                bill_info.billable_amount = -1*int(utility_info.unit_cost*bill_info.net_consumption*multiplier)
                bill_info.add_delta(utility_info.statistic, -statistic_value)
        return bill_info

    def get_utility_bill_total_net_production(self):
        total_net_units = 0
        for utility in Bills.UTILITY_INFO.keys():
            utility_info = self.get_utility_bill_info(utility)
            if utility_info.is_zero():
                pass
            else:
                total_net_units += utility_info.net_consumption
        return total_net_units

    def _get_bill_multiplier(self):
        multipliers = {utility: 1 for utility in Utilities}
        multipliers[ALL_BILLS_SOURCE] = 1
        multipliers[PROPERTY_TAX_SOURCE] = 1
        bill_multiplier_descriptions = []
        resolver = None
        for sim_info in self._household._sim_infos:
            resolver = SingleSimResolver(sim_info)
            for potential_bill_multiplier in Bills.BILL_COST_MODIFIERS_SIM_WITH_REASON:
                if potential_bill_multiplier.test.run_tests(resolver):
                    multipliers[potential_bill_multiplier.source.utility] *= potential_bill_multiplier.multiplier
                    bill_multiplier_descriptions.append(potential_bill_multiplier.multiplier_description)
        if resolver is None:
            resolver = GlobalResolver()
        for potential_bill_multiplier in Bills.BILL_COST_MODIFIERS_HOUSEHOLD_WITH_REASON:
            if potential_bill_multiplier.test.run_tests(resolver):
                multipliers[potential_bill_multiplier.source.utility] *= potential_bill_multiplier.multiplier
                bill_multiplier_descriptions.append(potential_bill_multiplier.multiplier_description)
        bill_reductions = services.global_policy_service().get_bill_reductions()
        if bill_reductions:
            for (reduction_reason, reduction) in bill_reductions.items():
                multipliers[self.REDUCTION_REASON_SOURCE.get(reduction_reason, ALL_BILLS_SOURCE)] *= reduction
                reduction_text = self.REDUCTION_REASON_TEXT_MAP.get(reduction_reason)
                if reduction_text:
                    bill_multiplier_descriptions.append(reduction_text)
                else:
                    logger.error('Attempting to get reduction reason ({}) without a tuned value in the Reduction Reason Text Map.', str(reduction_reason), owner='jjacobson')
        return (multipliers, bill_multiplier_descriptions)

    def _get_rent_cost(self):
        plex_service = services.get_plex_service()
        if not plex_service.is_zone_an_apartment(self._household.home_zone_id, consider_penthouse_an_apartment=False):
            return 0
        persistence_service = services.get_persistence_service()
        house_description_id = persistence_service.get_house_description_id(self._household.home_zone_id)
        return services.get_rent(house_description_id)

    def _get_property_taxes(self):
        plex_service = services.get_plex_service()
        if plex_service.is_zone_an_apartment(self._household.home_zone_id, consider_penthouse_an_apartment=False):
            return 0
        billable_household_value = self._household.household_net_worth(billable=True)
        tax_value = 0
        for bracket in Bills.BILL_BRACKETS:
            lower_bound = bracket.value_range.lower_bound
            if billable_household_value >= lower_bound:
                upper_bound = bracket.value_range.upper_bound
                if upper_bound is None:
                    upper_bound = billable_household_value
                bound_difference = upper_bound - lower_bound
                value_difference = billable_household_value - lower_bound
                if value_difference > bound_difference:
                    value_difference = bound_difference
                value_difference *= bracket.tax_percentage
                tax_value += value_difference
        return tax_value

    def _get_additional_bill_costs(self):
        total_bill_amount = 0
        bill_details = {}
        for (source, additional_cost) in self._additional_bill_costs.items():
            if sims4.math.almost_equal(additional_cost, 0.0):
                pass
            else:
                total_bill_amount += additional_cost
                source_info = UnpaidBillSourceInfo()
                source_info.billable_amount = additional_cost
                source_key = Bills.get_bill_source_key_from_enum(source)
                if source_key in bill_details:
                    bill_details[source_key] += source_info
                else:
                    bill_details[source_key] = source_info
        return (total_bill_amount, bill_details)

    def get_bill_amount(self):
        (multipliers, bill_multiplier_descriptions) = self._get_bill_multiplier()
        bill_amount = 0
        with telemetry_helper.begin_hook(bills_telemetry_writer, TELEMETRY_HOOK_BILL_GIVEN) as hook:
            rent = self._get_rent_cost()
            bill_amount += rent
            property_taxes = self._get_property_taxes()*multipliers[ALL_BILLS_SOURCE]*multipliers[PROPERTY_TAX_SOURCE]
            bill_amount += property_taxes
            (additional_bills, bill_details) = self._get_additional_bill_costs()
            for (source_key, bill_info) in bill_details.items():
                if source_key in self._current_bill_details:
                    self._current_bill_details[source_key] += bill_info
                else:
                    self._current_bill_details[source_key] = bill_info
            bill_amount += additional_bills
            power_amount = 0
            water_amount = 0
            for utility in Bills.UTILITY_INFO.keys():
                utility_info = self.get_utility_bill_info(utility)
                if utility_info.is_zero():
                    pass
                else:
                    if utility_info.billable_amount < 0:
                        utility_amount = utility_info.billable_amount
                    else:
                        utility_amount = utility_info.billable_amount*multipliers[ALL_BILLS_SOURCE]*multipliers[utility]
                    bill_amount += utility_amount
                    if utility == Utilities.POWER:
                        power_amount = utility_amount
                    elif utility == Utilities.WATER:
                        water_amount = utility_amount
                    source_key = Bills.get_bill_source_key_from_enum(utility)
                    if source_key in self._current_bill_details:
                        self._current_bill_details[source_key] += utility_info
                    else:
                        self._current_bill_details[source_key] = utility_info
        with telemetry_helper.begin_hook(bills_telemetry_writer, TELEMETRY_HOOK_BILL_GIVEN) as hook:
            hook.write_float(TELEMETRY_RENT, rent)
            hook.write_float(TELEMETRY_PROPERTY_TAX, rent)
            hook.write_float(TELEMETRY_OTHER_BILLS, additional_bills)
            hook.write_float(TELEMETRY_POWER, power_amount)
            hook.write_float(TELEMETRY_WATER, water_amount)
        return int(bill_amount)

    def allow_bill_delivery(self):
        if self._bill_timer_handle is not None:
            alarms.cancel_alarm(self._bill_timer_handle)
            self._bill_timer_handle = None
        self._place_bill_in_hidden_inventory()

    def _place_bill_in_hidden_inventory(self):
        self._current_payment_owed = self.get_bill_amount()
        if self._current_payment_owed <= 0:
            self.pay_bill(sound=False)
            return
        lot = self._get_lot()
        if lot is not None:
            lot.create_object_in_hidden_inventory(self.BILL_OBJECT, self._household.id)
            self._put_bill_in_hidden_inventory = False
            self._can_deliver_bill = True
            return
        self._put_bill_in_hidden_inventory = True
        self.trigger_bill_notifications_from_delivery()

    def _place_bill_in_mailbox(self):
        lot = self._get_lot()
        if lot is None:
            return
        lot.create_object_in_mailbox(self.BILL_OBJECT, self._household.id)
        self._put_bill_in_hidden_inventory = False

    def trigger_bill_notifications_from_delivery(self):
        if self.mailman_has_delivered_bills():
            return
        self._can_deliver_bill = False
        if self.autopay_bills or self._current_payment_owed == 0 or not self._household:
            self.pay_bill(sound=False)
            return
        self._set_next_delinquency_timers()
        bills_arrival_notification = self.get_bills_arrival_notification()
        if bills_arrival_notification is not None:
            notification_shown = self._send_notification(bills_arrival_notification)
            if notification_shown:
                self.give_bills_arrival_notification_loots()

    def _destroy_all_bills_objects(self):

        def is_current_households_bill(obj, household_id):
            return obj.definition is self.BILL_OBJECT and (obj.get_household_owner_id() is None or obj.get_household_owner_id() == household_id)

        def remove_from_inventory(inventory):
            for obj in [obj for obj in inventory if is_current_households_bill(obj, self._household.id)]:
                obj.destroy(source=inventory, cause='Paying bills.')

        lot = self._get_lot()
        if lot is not None:
            for (_, inventory) in lot.get_all_object_inventories_gen():
                remove_from_inventory(inventory)
        for sim_info in self._household:
            sim = sim_info.get_sim_instance()
            if sim is not None:
                remove_from_inventory(sim.inventory_component)
        self._put_bill_in_hidden_inventory = False

    def pay_bill(self, sound=True, clear_bill=False):
        if clear_bill or self._current_payment_owed < 0:
            bills_arrival_notification = self.get_bills_arrival_notification()
            if bills_arrival_notification is not None:
                self.bill_notifications_enabled = True
                notification_shown = self._send_notification(bills_arrival_notification)
                if notification_shown:
                    self.give_bills_arrival_notification_loots()
            self._household.funds.add(-self._current_payment_owed, Consts_pb2.TELEMETRY_INTERACTION_REWARD, count_as_earnings=False)
            from_negative_payout = True
        else:
            from_negative_payout = False
        if self._current_payment_owed:
            lot = self._get_lot()
            statistic_component = None if lot is None else lot.get_component(objects.components.types.STATISTIC_COMPONENT)
            if statistic_component is not None:
                for (source, detail) in self._current_bill_details.items():
                    self.pay_source_bill(self.get_bill_source_enum_from_key(source), detail, statistic_component)
            for status in self._utility_delinquency.values():
                if status:
                    play_tunable_audio(self.AUDIO.delinquency_removed_sfx)
                    break
            if sound:
                play_tunable_audio(self.AUDIO.bills_paid_sfx)
        self._current_payment_owed = None
        self._current_bill_details.clear()
        self._clear_delinquency_status()
        self._repo_man_due_time = None
        self._set_up_bill_timer(from_negative_payout=from_negative_payout)
        self._destroy_all_bills_objects()

    def pay_source_bill(self, source, source_bill_info, lot_statistic_component=None):
        if source_bill_info is None or not source_bill_info.statistic_deltas:
            return
        if lot_statistic_component is None:
            lot = self._get_lot()
            lot_statistic_component = None if lot is None else lot.get_component(objects.components.types.STATISTIC_COMPONENT)
        if lot_statistic_component is None:
            return
        utility_production_stat = None
        if isinstance(source, Utilities):
            utility_info = self.get_utility_info(source)
            if utility_info is not None:
                utility_production_stat = utility_info.statistic
        for (statistic, delta) in source_bill_info.statistic_deltas:
            new_value = lot_statistic_component.get_stat_value(statistic) + delta
            lot_statistic_component.set_stat_value(statistic, value=new_value)
            if not utility_production_stat is None:
                if statistic is not utility_production_stat:
                    pass
                elif delta < 0:
                    for sim_info in self._household.sim_infos:
                        services.get_event_manager().process_event(TestEvent.SoldUtilityOnBill, sim_info=sim_info)

    def sell_excess_utility(self, utility):
        lot = self._get_lot()
        if lot is None:
            logger.error('Attempting to sell excess utility with no lot available.', owner='jjacobson')
            return
        lot_statistic_component = lot.get_component(objects.components.types.STATISTIC_COMPONENT)
        if lot_statistic_component is None:
            logger.error('Attempting to sell excess utility with no lot statistic component available.', owner='jjacobson')
        utility_info = self.get_utility_info(utility)
        if utility_info is None:
            logger.error('Attempting to sell excess utility with no utility info available.', owner='jjacobson')
            return
        current_value = lot_statistic_component.get_stat_value(utility_info.statistic)
        if current_value <= utility_info.statistic_sell_value:
            return
        resolver = GlobalResolver()
        multiplier = utility_info.unit_cost_sell_price_multiplier.get_multiplier(resolver)
        self._household.funds.add(int(utility_info.unit_cost*(current_value - utility_info.statistic_sell_value)*multiplier), Consts_pb2.TELEMETRY_INTERACTION_REWARD, count_as_earnings=False)
        lot_statistic_component.set_stat_value(utility_info.statistic, utility_info.statistic_sell_value)
        for sim_info in self._household.sim_infos:
            services.get_event_manager().process_event(TestEvent.SoldUtilityOnBill, sim_info=sim_info)

    def _clear_delinquency_status(self):
        for utility in self._utility_delinquency:
            services.utilities_manager(self._household.id).restore_utility(utility, self.BILLS_UTILITY_SHUTOFF_REASON)
            self._utility_delinquency[utility] = False
        self._additional_bill_costs = {}
        if self._shutoff_handle is not None:
            alarms.cancel_alarm(self._shutoff_handle)
            self._shutoff_handle = None
        if self._warning_handle is not None:
            alarms.cancel_alarm(self._warning_handle)
            self._warning_handle = None

    def _set_next_delinquency_timers(self):
        for utility in self._utility_delinquency:
            if self._utility_delinquency[utility]:
                pass
            else:
                utility_info = self.get_utility_info(utility)
                if utility_info is not None:
                    warning_notification = utility_info.warning_notification
                    self._warning_handle = alarms.add_alarm(self, clock.interval_in_sim_hours(self.DELINQUENCY_FREQUENCY - self.DELINQUENCY_WARNING_OFFSET_TIME), lambda _: self._send_notification(warning_notification), cross_zone=True)
                self._shutoff_handle = alarms.add_alarm(self, clock.interval_in_sim_hours(self.DELINQUENCY_FREQUENCY), lambda _: self._shut_off_utility(utility), cross_zone=True)
                break
        now = services.time_service().sim_now
        self._repo_man_due_time = now + Bills.REPO_MAN_TIMER()

    def _shut_off_utility(self, utility):
        if self._current_payment_owed == None:
            self._clear_delinquency_status()
            logger.error('Household {} is getting a utility shut off without actually owing any money. Resetting delinquency status.', self._household)
            return
        utility_info = self.get_utility_info(utility)
        shutoff_tooltip = None
        if utility_info is not None:
            shutoff_notification = utility_info.shutoff_notification
            self._send_notification(shutoff_notification)
            shutoff_tooltip = utility_info.shutoff_tooltip
        if self._shutoff_handle is not None:
            alarms.cancel_alarm(self._shutoff_handle)
            self._shutoff_handle = None
        self._utility_delinquency[utility] = True
        self._set_next_delinquency_timers()
        lot = self._get_lot()
        if lot is None:
            return
        statistic_component = lot.get_component(objects.components.types.STATISTIC_COMPONENT)
        if statistic_component is None:
            return
        statistic = statistic_component.get_stat_instance(utility_info.statistic)
        current_value = statistic.get_value()
        if current_value <= 0:
            services.utilities_manager(self._household.id).shut_off_utility(utility, self.BILLS_UTILITY_SHUTOFF_REASON, shutoff_tooltip)

    def _get_colored_text(self, value):
        if value > 0:
            return Bills.BILL_COLOR_STRING_NEGATIVE(value)
        return Bills.BILL_COLOR_STRING_POSITIVE(abs(value))

    def _send_notification(self, notification):
        current_time = services.time_service().sim_now
        if self._warning_handle is not None and self._warning_handle.finishing_time <= current_time:
            alarms.cancel_alarm(self._warning_handle)
            self._warning_handle = None
            play_tunable_audio(self.AUDIO.delinquency_warning_sfx)
        if not self.bill_notifications_enabled:
            return False
        client = services.client_manager().get_client_by_household(self._household)
        if client is None:
            return False
        active_sim_info = client.active_sim_info
        if active_sim_info is None:
            return False
        reduction_reasons_string = ''
        bill_reductions = services.global_policy_service().get_bill_reductions()
        if bill_reductions:
            reduction_reasons = []
            for (reduction_reason, reduction) in bill_reductions.items():
                reduction_text = self.REDUCTION_REASON_TEXT_MAP.get(reduction_reason)
                if reduction_text:
                    reduction_reasons.append(reduction_text)
                else:
                    logger.error('Attempting to get reduction reason ({}) bullet point without a tuned value in the Reduction Reason Text Map.', str(reduction_reason), owner='shipark')
                    return False
            reduction_reasons_string = LocalizationHelperTuning.get_bulleted_list((None,), reduction_reasons)
        (multipliers, multiplier_reasons) = self._get_bill_multiplier()
        detail_tokens = []
        rent = self._get_rent_cost()
        property_tax = self._get_property_taxes()*multipliers[ALL_BILLS_SOURCE]*multipliers[PROPERTY_TAX_SOURCE]
        if rent != 0:
            detail_tokens.append(Bills.BILL_COLOR_STRING_NEGATIVE(rent))
        else:
            detail_tokens.append(Bills.BILL_COLOR_STRING_NEGATIVE(property_tax))
        for utility in Utilities:
            source_info = self.current_source_owed(utility)
            if source_info is None:
                detail_tokens.append(Bills.BILL_COLOR_STRING_POSITIVE(0))
            else:
                detail_tokens.append(self._get_colored_text(source_info.billable_amount*multipliers[ALL_BILLS_SOURCE]*multipliers[utility]))
        other_fees = 0
        for (source_key, details) in self._current_bill_details.items():
            if source_key < Bills.ADDITIONAL_BILL_SOURCE_KEY_START:
                pass
            else:
                other_fees += details.billable_amount
        detail_tokens.append(self._get_colored_text(other_fees))
        remaining_time = max(int(self._shutoff_handle.get_remaining_time().in_hours()), 0) if self._shutoff_handle is not None else 0
        dialog = notification(active_sim_info, None)
        icon_override = DEFAULT
        plex_service = services.get_plex_service()
        if plex_service.is_zone_a_plex(self._household.home_zone_id):
            landlord_service = services.get_landlord_service()
            if landlord_service is not None:
                icon_override = IconInfoData(obj_instance=landlord_service.get_landlord_sim_info())
        additional_tokens = [remaining_time, self._get_colored_text(self._current_payment_owed), reduction_reasons_string]
        additional_tokens.extend(detail_tokens)
        dialog.show_dialog(icon_override=icon_override, additional_tokens=tuple(additional_tokens), tutorial_id=Bills.BILL_TUTORIAL.guid64)
        return True

    def add_additional_bill_cost(self, additional_bill_source, cost):
        current_cost = self._additional_bill_costs.get(additional_bill_source, 0)
        self._additional_bill_costs[additional_bill_source] = current_cost + cost

    def add_lot_unpaid_bill(self, zone_id, situation_id, money_amount, sims_on_lot):
        key_tuple = (zone_id, situation_id)
        self._lot_unpaid_bill[key_tuple] = (money_amount, list(sims_on_lot))

    def remove_lot_unpaid_bill(self, zone_id, situation_id):
        key_tuple = (zone_id, situation_id)
        if key_tuple in self._lot_unpaid_bill:
            del self._lot_unpaid_bill[key_tuple]

    def load_data(self, householdProto):
        for additional_bill_cost in householdProto.gameplay_data.additional_bill_costs:
            self.add_additional_bill_cost(additional_bill_cost.bill_source, additional_bill_cost.cost)
        for lot_unpaid_bill_item in householdProto.gameplay_data.lot_unpaid_bill_data:
            key_tuple = (lot_unpaid_bill_item.zone_id, lot_unpaid_bill_item.situation_id)
            sims_on_lot = []
            for sim_id in lot_unpaid_bill_item.sim_ids_on_lot:
                sims_on_lot.append(sim_id)
            self._lot_unpaid_bill[key_tuple] = (lot_unpaid_bill_item.money_amount, sims_on_lot)
        self._can_deliver_bill = householdProto.gameplay_data.can_deliver_bill
        self._put_bill_in_hidden_inventory = householdProto.gameplay_data.put_bill_in_hidden_inventory
        if self._put_bill_in_hidden_inventory:
            self._place_bill_in_mailbox()
        self._current_payment_owed = householdProto.gameplay_data.current_payment_owed
        if self._current_payment_owed == 0:
            self._current_payment_owed = None
        elif hasattr(householdProto.gameplay_data, 'current_bill_details'):
            statistics_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            for current_bill_detail_msg in householdProto.gameplay_data.current_bill_details:
                source_key = current_bill_detail_msg.utility
                current_bill_detail = UnpaidBillSourceInfo()
                current_bill_detail.billable_amount = current_bill_detail_msg.billable_amount
                current_bill_detail.net_consumption = current_bill_detail_msg.net_consumption
                for delta_msg in current_bill_detail_msg.statistic_deltas:
                    statistics = statistics_manager.get(delta_msg.stat_id)
                    if statistics is None:
                        pass
                    else:
                        if current_bill_detail.statistic_deltas is None:
                            current_bill_detail.statistic_deltas = []
                        current_bill_detail.statistic_deltas.append((statistics, delta_msg.delta))
                if not current_bill_detail.is_zero():
                    self._current_bill_details[source_key] = current_bill_detail
        self._stored_bill_timer_ticks = householdProto.gameplay_data.bill_timer
        self._stored_shutoff_timer_ticks = householdProto.gameplay_data.shutoff_timer
        self._stored_warning_timer_ticks = householdProto.gameplay_data.warning_timer
        if self._stored_shutoff_timer_ticks > 0 or self._stored_warning_timer_ticks > 0:
            logger.error('Household {} loaded with utility shutoff or warning timers but no owed payment. Clearing utility shutoff and warning timers.', self._household)
            self._stored_shutoff_timer_ticks = 0
            self._stored_warning_timer_ticks = 0
        if self._stored_bill_timer_ticks > 0:
            logger.error('Household {} loaded with both a bill delivery timer and an owed payment. Clearing bill delivery timer.', self._household)
            self._stored_bill_timer_ticks = 0
        for utility in householdProto.gameplay_data.delinquent_utilities:
            self._utility_delinquency[utility] = True
            utility_info = self.get_utility_info(utility)
            shutoff_tooltip = None
            if utility_info is not None:
                shutoff_tooltip = utility_info.shutoff_tooltip
            utility_manager = services.get_utilities_manager_by_zone_id(self._household.home_zone_id)
            if utility_manager is not None:
                utility_manager.shut_off_utility(utility, self.BILLS_UTILITY_SHUTOFF_REASON, shutoff_tooltip, from_load=True)
        for bill_utility_setting in householdProto.gameplay_data.bill_utility_settings:
            self._utility_bill_action[bill_utility_setting.utility] = bill_utility_setting.end_of_bill_action
        if self._current_payment_owed is None and self._current_payment_owed is not None and householdProto.gameplay_data.HasField('repo_man_due_time'):
            self._repo_man_due_time = DateAndTime(householdProto.gameplay_data.repo_man_due_time)

    def save_data(self, household_msg):
        for utility in Utilities:
            if self.is_utility_delinquent(utility):
                household_msg.gameplay_data.delinquent_utilities.append(utility)
        for (bill_source, cost) in self._additional_bill_costs.items():
            with ProtocolBufferRollback(household_msg.gameplay_data.additional_bill_costs) as additional_bill_cost:
                additional_bill_cost.bill_source = bill_source
                additional_bill_cost.cost = cost
        for (key_tuple, money_sim_info) in self._lot_unpaid_bill.items():
            (zone_id, situation_id) = key_tuple
            with ProtocolBufferRollback(household_msg.gameplay_data.lot_unpaid_bill_data) as lot_unpaid_bill:
                lot_unpaid_bill.zone_id = zone_id
                lot_unpaid_bill.situation_id = situation_id
                (money_amount, sim_ids) = money_sim_info
                lot_unpaid_bill.money_amount = money_amount
                for sim_id in sim_ids:
                    lot_unpaid_bill.sim_ids_on_lot.append(sim_id)
        household_msg.gameplay_data.can_deliver_bill = self._can_deliver_bill
        household_msg.gameplay_data.put_bill_in_hidden_inventory = self._put_bill_in_hidden_inventory
        if self.current_payment_owed is not None:
            household_msg.gameplay_data.current_payment_owed = int(self.current_payment_owed)
            for (source_key, details) in self._current_bill_details.items():
                with ProtocolBufferRollback(household_msg.gameplay_data.current_bill_details) as current_bill_detail:
                    current_bill_detail.utility = source_key
                    current_bill_detail.billable_amount = int(details.billable_amount)
                    current_bill_detail.net_consumption = details.net_consumption
                    if details.statistic_deltas:
                        for (statistic, delta) in details.statistic_deltas:
                            with ProtocolBufferRollback(current_bill_detail.statistic_deltas) as statistic_delta:
                                statistic_delta.stat_id = statistic.guid64
                                statistic_delta.delta = delta
        current_time = services.time_service().sim_now
        if self._bill_timer_handle is not None:
            time = max((self._bill_timer_handle.finishing_time - current_time).in_ticks(), 0)
            household_msg.gameplay_data.bill_timer = time
        else:
            household_msg.gameplay_data.bill_timer = self._stored_bill_timer_ticks
        if self._shutoff_handle is not None:
            time = max((self._shutoff_handle.finishing_time - current_time).in_ticks(), 0)
            household_msg.gameplay_data.shutoff_timer = time
        else:
            household_msg.gameplay_data.shutoff_timer = self._stored_shutoff_timer_ticks
        if self._warning_handle is not None:
            time = max((self._warning_handle.finishing_time - current_time).in_ticks(), 0)
            household_msg.gameplay_data.warning_timer = time
        else:
            household_msg.gameplay_data.warning_timer = self._stored_warning_timer_ticks
        for (utility, action) in self._utility_bill_action.items():
            with ProtocolBufferRollback(household_msg.gameplay_data.bill_utility_settings) as bill_utility_settings:
                bill_utility_settings.utility = utility
                bill_utility_settings.end_of_bill_action = action
        if self._repo_man_due_time is not None:
            household_msg.gameplay_data.repo_man_due_time = self._repo_man_due_time.absolute_ticks()

    def show_bills_dialog(self):
        (multipliers, multiplier_reasons) = self._get_bill_multiplier()
        property_tax = self._get_property_taxes()
        tax_modifier = property_tax - property_tax*multipliers[ALL_BILLS_SOURCE]*multipliers[PROPERTY_TAX_SOURCE]
        utility_infos = []
        lot = self._get_lot()
        statistic_component = None if lot is None else lot.get_component(objects.components.types.STATISTIC_COMPONENT)
        if statistic_component is not None:
            for utility in Bills.UTILITY_INFO.keys():
                utility_info = self.get_utility_info(utility)
                if utility_info is None:
                    pass
                else:
                    statistic = statistic_component.get_stat_instance(utility_info.statistic, add=True)
                    current_value = statistic.get_value()
                    max_value = statistic.max_value
                    rate_of_change = statistic.get_change_rate()*MINUTES_PER_HOUR*HOURS_PER_DAY
                    selling = self._utility_bill_action.get(utility, UtilityEndOfBillAction.SELL) == UtilityEndOfBillAction.SELL
                    utility_name = utility_info.name
                    utility_symbol = utility_info.font_symbol
                    if current_value > utility_info.statistic_sell_value:
                        keep_excess_production = not selling
                        current_value -= utility_info.statistic_sell_value
                    elif current_value > 0:
                        keep_excess_production = True
                    else:
                        keep_excess_production = False
                    if keep_excess_production:
                        cost = 0
                    else:
                        if current_value > 0:
                            resolver = GlobalResolver()
                            multiplier = utility_info.unit_cost_sell_price_multiplier.get_multiplier(resolver)
                        else:
                            multiplier = 1
                        cost = int(utility_info.unit_cost*current_value*multiplier)
                    if cost < 0:
                        tax_modifier -= cost - cost*multipliers[ALL_BILLS_SOURCE]*multipliers[utility]
                    utility_infos.append(UtilityInfo(utility, cost, max_value, current_value, utility_name, utility_symbol, rate_of_change, selling))

        def build_item(amount, item_display_tuning, details=None):
            tooltip = item_display_tuning.generic_tooltip
            if details:
                tooltip = item_display_tuning.detailed_tooltip(LocalizationHelperTuning.get_bulleted_list((None,), details))
            return SummaryLineItem(amount, item_display_tuning.item_label, tooltip)

        line_items = []
        plex_service = services.get_plex_service()
        if plex_service.is_zone_an_apartment(self._household.home_zone_id, consider_penthouse_an_apartment=False):
            line_items.append(build_item(-1*self._get_rent_cost(), Bills.BILLS_UI.rent_item_display))
            is_apartment = True
        else:
            line_items.append(build_item(-1*self._get_property_taxes(), Bills.BILLS_UI.property_tax_item_display))
            is_apartment = False
        for utility_info in utility_infos:
            tooltip = None
            if utility_info.utility in Bills.BILLS_UI.utility_item_display:
                tooltip = Bills.BILLS_UI.utility_item_display[utility_info.utility].tooltip
            line_items.append(SummaryLineItem(utility_info.cost, utility_info.utility_name, tooltip))
        (additional_bill_cost, _) = self._get_additional_bill_costs()
        line_items.append(build_item(-1*additional_bill_cost, Bills.BILLS_UI.additional_bills_item_display))
        line_items.append(build_item(tax_modifier, Bills.BILLS_UI.tax_modifiers_item_display, details=multiplier_reasons))
        if self._current_payment_owed is not None:
            if is_apartment:
                line_items.append(build_item(-1*self._current_payment_owed, Bills.BILLS_UI.unpaid_rent_display))
            else:
                line_items.append(build_item(-1*self._current_payment_owed, Bills.BILLS_UI.unpaid_bills_display))
        op = ShowBillsPanel(utility_infos, line_items)
        Distributor.instance().add_op_with_no_owner(op)
