from protocolbuffers import SimObjectAttributes_pb2import enumimport operatorimport servicesfrom distributor.ops import TraitAtRiskUpdatefrom distributor.system import Distributorfrom buffs.tunable import TunableBuffReferencefrom event_testing.resolver import SingleSimResolverfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_types import Agefrom sims4.log import Loggerfrom sims4.math import Threshold, clampfrom sims4.resources import Typesfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.instances import HashedTunedInstanceMetaclass, lock_instance_tunablesfrom sims4.tuning.tunable import HasTunableReference, TunableTuple, OptionalTunable, Tunable, TunableReference, TunableList, TunableRange, TunableMapping, TunableEnumEntry, TunableSetfrom statistics.continuous_statistic_tuning import TunedContinuousStatisticfrom traits.trait_type import TraitTypefrom tunable_multiplier import TestedSumfrom ui.ui_dialog_notification import UiDialogNotificationlogger = Logger('TraitStatistics', default_owner='jjacobson')
class TraitStatisticGroup(DynamicEnum):
    NO_GROUP = 0

class TraitStatisticStates(enum.Int, export=False):
    OPPOSING_AT_RISK = ...
    OPPOSING_UNLOCKED = ...
    OPPOSING_IN_PROGRESS = ...
    LOCKED = ...
    IN_PROGRESS = ...
    UNLOCKED = ...
    AT_RISK = ...

class TraitStatisticData(TunableTuple):

    def __init__(self, *args, set_in_progress_from_locked_default=50, set_locked_from_in_progress_default=25, set_unlocked_from_in_progress_default=75, set_at_risk_from_unlocked_default=50, set_at_locked_from_at_risk_default=25, set_unlocked_from_at_risk_default=75, **kwargs):
        super().__init__(*args, trait=TunableReference(description='\n                The trait that will be unlocked when this TraitStatistic hits\n                its unlocked point.\n                ', manager=services.get_instance_manager(Types.TRAIT)), set_in_progress_from_locked_value=Tunable(description='\n                The value at which this Trait Statistic will be set in progress\n                from being locked.  This is also the point that it will be\n                unhidden if it has been marked hidden.\n                ', tunable_type=float, default=set_in_progress_from_locked_default), set_locked_from_in_progress_value=Tunable(description='\n                The value at which this Trait Statistic will be set to locked\n                from being in progress.\n                ', tunable_type=float, default=set_locked_from_in_progress_default), set_unlocked_from_in_progress_value=Tunable(description='\n                The value at which this Trait Statistic will be set to unlocked\n                from being in progress.\n                ', tunable_type=float, default=set_unlocked_from_in_progress_default), set_at_risk_from_unlocked_value=Tunable(description='\n                The value at which this Trait Statistic will be set to at\n                risk from being unlocked.\n                ', tunable_type=float, default=set_at_risk_from_unlocked_default), set_at_locked_from_at_risk_value=Tunable(description='\n                The value at which this Trait Statistic will be set to at\n                locked from being at risk.\n                ', tunable_type=float, default=set_at_locked_from_at_risk_default), set_unlocked_from_at_risk_value=Tunable(description='\n                The value at which this Trait Statistic will be set to unlocked\n                from being at risk.\n                ', tunable_type=float, default=set_unlocked_from_at_risk_default), unlocked_notification=OptionalTunable(description='\n                If enabled then a notification will be played when this trait statistic is unlocked.\n                ', tunable=UiDialogNotification.TunableFactory(description='\n                    Notification that will play when a trait statistic becomes unlocked.\n                    ')), at_risk_notification=OptionalTunable(description='\n                If enabled then a notification will be played when this trait statistic is set at risk.\n                ', tunable=UiDialogNotification.TunableFactory(description='\n                    Notification that will play when a trait statistic becomes at risk.\n                    ')), unlocked_lost_notification=OptionalTunable(description='\n                If enabled then a notification will be played when this trait statistic is locked after\n                having the trait unlocked.\n                ', tunable=UiDialogNotification.TunableFactory(description='\n                    Notification that will play when a trait statistic becomes locked after having the trait\n                    unlocked.\n                    ')), neglect_buffs=TunableList(description='\n                A list of neglect buffs that can be applied if this trait statistic is in neglect.\n                With each day that the trait statistic is in neglect we will increment the buff to\n                the next one.\n                ', tunable=TunableBuffReference(description='\n                    A buff that will be added when this trait statistic is in neglect.\n                    ')), daily_pushback=Tunable(description='\n                The value that this statistic will be pushed back daily.  This value will be subtracted\n                from the current value daily.\n                ', tunable_type=float, default=0), **kwargs)

class TraitStatistic(HasTunableReference, TunedContinuousStatistic, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.STATISTIC)):
    GROUPS = TunableMapping(description='\n        A mapping between Groups for trait statistics and the maximum number\n        of traits that are allowed to be unlocked for that group.\n        ', key_type=TunableEnumEntry(description='\n            The trait statistic group to limit.\n            ', tunable_type=TraitStatisticGroup, default=TraitStatisticGroup.NO_GROUP, invalid_enums=(TraitStatisticGroup.NO_GROUP,)), value_type=TunableRange(description='\n            The maximum number of trait statistics in this group that can be\n            in either the unlocked or at risk states.  When this cap is reached\n            all other trait statistics in the group will only be allowed to have\n            their value change towards the default value of the statistic.\n            ', tunable_type=int, default=1, minimum=1))
    INSTANCE_TUNABLES = {'trait_data': TraitStatisticData(), 'opposing_trait_data': OptionalTunable(description='\n            If enabled then this trait statistic will have a separate trait\n            data representing an opposing trait along the trait tracker.\n            ', tunable=TraitStatisticData(set_in_progress_from_locked_default=-50, set_locked_from_in_progress_default=-25, set_unlocked_from_in_progress_default=-75, set_at_risk_from_unlocked_default=-50, set_at_locked_from_at_risk_default=-25, set_unlocked_from_at_risk_default=-75)), 'periodic_tests': TestedSum.TunableFactory(description='\n            A Tested Sum of values that will be added to the statistic on\n            an interval determined in the Trait Statistic Tracker.\n            '), 'max_daily_progress': OptionalTunable(description='\n            If enabled then this trait statistic will have a cap of how much progrees\n            it can make per day.\n            ', tunable=TunableRange(description='\n                The amount of progress that this statistic is allowed to be made daily.\n                ', tunable_type=float, default=10, minimum=0)), 'ages': TunableSet(description='\n            Allowed ages for this trait statistic.\n            ', tunable=TunableEnumEntry(description='\n                An allowed age for this trait statistic.\n                ', tunable_type=Age, default=Age.ADULT)), 'group': TunableEnumEntry(description='\n            The group that this trait statistic belongs to.\n            Each group can then limit the number of trait statistics\n            in the unlocked/at risk states.  When this limit is reached\n            then all trait statistics within this group that are not in\n            the aforementioned states will only be allowed to have their\n            value change towards the default value of this statistic.\n            \n            Tuning for these groups can be setup in the trait_statistc\n            module tuning.\n            ', tunable_type=TraitStatisticGroup, default=TraitStatisticGroup.NO_GROUP)}

    @classmethod
    def _verify_trait_data_in_bounds(cls, trait_data, prefix=''):
        if not (cls.min_value < trait_data.set_in_progress_from_locked_value and trait_data.set_in_progress_from_locked_value < cls.max_value):
            logger.error(prefix + 'Set In Progress From Locked Value is outside the min or max bounds of {}', cls)
        if not (cls.min_value < trait_data.set_locked_from_in_progress_value and trait_data.set_locked_from_in_progress_value < cls.max_value):
            logger.error(prefix + 'Set Locked From In Progress Value is outside the min or max bounds of {}', cls)
        if not (cls.min_value < trait_data.set_unlocked_from_in_progress_value and trait_data.set_unlocked_from_in_progress_value < cls.max_value):
            logger.error(prefix + 'Set Unlocked From In Progress Value is outside the min or max bounds of {}', cls)
        if not (cls.min_value < trait_data.set_at_risk_from_unlocked_value and trait_data.set_at_risk_from_unlocked_value < cls.max_value):
            logger.error(prefix + 'Set At Risk From Unlocked Value is outside the min or max bounds of {}', cls)
        if not (cls.min_value < trait_data.set_at_locked_from_at_risk_value and trait_data.set_at_locked_from_at_risk_value < cls.max_value):
            logger.error(prefix + 'Set Locked From At Risk Value is outside the min or max bounds of {}', cls)
        if not (cls.min_value < trait_data.set_unlocked_from_at_risk_value and trait_data.set_unlocked_from_at_risk_value < cls.max_value):
            logger.error(prefix + 'Set Unlocked From At Risk Value is outside the min or max bounds of {}', cls)

    @classmethod
    def _verify_tuning_callback(cls):
        cls._verify_trait_data_in_bounds(cls.trait_data)
        if cls.trait_data.set_in_progress_from_locked_value <= cls.trait_data.set_locked_from_in_progress_value:
            logger.error('Set In Progress From Locked Value is less than or equal to Set Locked From In Progress Value in {}', cls)
        if cls.trait_data.set_unlocked_from_in_progress_value <= cls.trait_data.set_in_progress_from_locked_value:
            logger.error('Set Unlocked From In Progress Value is less than or equal to Set In Progress From Locked Value in {}', cls)
        if cls.trait_data.set_unlocked_from_in_progress_value <= cls.trait_data.set_at_risk_from_unlocked_value:
            logger.error('Set Unlocked From In Progress Value is less than or equal to Set At Risk From Unlocked Value in {}', cls)
        if cls.trait_data.set_at_risk_from_unlocked_value <= cls.trait_data.set_at_locked_from_at_risk_value:
            logger.error('Set At Risk From Unlocked Value is less than or equal to Set Locked From At Risk Value in {}', cls)
        if cls.trait_data.set_in_progress_from_locked_value <= cls.trait_data.set_at_locked_from_at_risk_value:
            logger.error('Set In Progress From Locked Value is less than or equal to Set Locked From At Risk Value in {}', cls)
        if cls.trait_data.set_unlocked_from_at_risk_value <= cls.trait_data.set_at_risk_from_unlocked_value:
            logger.error('Set Unlocked From At Risk Value is less than or equal to Set At Risk From Unlocked Value in {}', cls)
        if cls.opposing_trait_data is not None:
            cls._verify_trait_data_in_bounds(cls.opposing_trait_data, prefix='Opposing ')
            if cls.opposing_trait_data.set_in_progress_from_locked_value >= cls.opposing_trait_data.set_locked_from_in_progress_value:
                logger.error('Opposing Set In Progress From Locked Value is greater than or equal to Set Locked From In Progress Value in {}', cls)
            if cls.opposing_trait_data.set_unlocked_from_in_progress_value >= cls.opposing_trait_data.set_in_progress_from_locked_value:
                logger.error('Opposing Set Unlocked From In Progress Value is greater than or equal to Set In Progress From Locked Value in {}', cls)
            if cls.opposing_trait_data.set_unlocked_from_in_progress_value >= cls.opposing_trait_data.set_at_risk_from_unlocked_value:
                logger.error('Opposing Set Unlocked From In Progress Value is greater than or equal to Set At Risk From Unlocked Value in {}', cls)
            if cls.opposing_trait_data.set_at_risk_from_unlocked_value >= cls.opposing_trait_data.set_at_locked_from_at_risk_value:
                logger.error('Opposing Set At Risk From Unlocked Value is greater than or equal to Set Locked From At Risk Value in {}', cls)
            if cls.opposing_trait_data.set_in_progress_from_locked_value >= cls.opposing_trait_data.set_at_locked_from_at_risk_value:
                logger.error('Opposing Set In Progress From Locked Value is greater than or equal to Set Locked From At Risk Value in {}', cls)
            if cls.opposing_trait_data.set_unlocked_from_at_risk_value >= cls.opposing_trait_data.set_at_risk_from_unlocked_value:
                logger.error('Opposing Set Unlocked From At Risk Value is greater than or equal to Set At Risk From Unlocked Value in {}', cls)

    @classmethod
    def _tuning_loaded_callback(cls):
        cls.trait_data.trait.trait_statistic = cls
        if cls.opposing_trait_data is not None:
            cls.opposing_trait_data.trait.trait_statistic = cls

    def __init__(self, tracker):
        super().__init__(tracker, self.initial_value)
        self._state = TraitStatisticStates.LOCKED
        self._next_positive_state_callback_data = None
        self._next_negative_state_callback_data = None
        self._neglect_buff_index = None
        self._neglect_buff_handle = None
        self._value_added = False
        self._max_daily_cap = None
        self._min_daily_cap = None
        self._group_limited = False
        self._on_daily_cap_reached_listeners = None
        self._suppress_at_risk_notification = False

    @property
    def state(self):
        return self._state

    @property
    def trait_unlocked(self):
        return self._state >= TraitStatisticStates.UNLOCKED or self._state <= TraitStatisticStates.OPPOSING_UNLOCKED

    @classmethod
    def can_add(cls, owner, force_add=False, **kwargs):
        if owner.age not in cls.ages:
            return False
        if cls.group != TraitStatisticGroup.NO_GROUP and not services.lifestyle_service().can_add_trait_statistic(cls):
            return False
        return super().can_add(owner, **kwargs)

    @property
    def group_limited(self):
        return self._group_limited

    def add_group_limiter(self):
        self._group_limited = True
        self._update_value()

    def remove_group_limiter(self):
        self._group_limited = False
        self._update_value()

    def _clear_state_callbacks(self):
        if self._next_positive_state_callback_data is not None:
            self.remove_callback_listener(self._next_positive_state_callback_data)
            self._next_positive_state_callback_data = None
        if self._next_negative_state_callback_data is not None:
            self.remove_callback_listener(self._next_negative_state_callback_data)
            self._next_negative_state_callback_data = None

    def _setup_callbacks(self, next_positive_callback=None, next_positive_callback_value=0, next_negative_callback=None, next_negative_callback_value=0):
        self._clear_state_callbacks()
        current_value = self.get_value()
        if next_positive_callback is not None:
            if current_value > next_positive_callback_value:
                next_positive_callback(self)
                return
            self._next_positive_state_callback_data = self.create_and_add_callback_listener(Threshold(next_positive_callback_value, operator.gt), next_positive_callback)
        if next_negative_callback is not None:
            if current_value < next_negative_callback_value:
                next_negative_callback(self)
                return
            self._next_negative_state_callback_data = self.create_and_add_callback_listener(Threshold(next_negative_callback_value, operator.lt), next_negative_callback)

    def _setup_locked_state_listeners(self):
        if self.opposing_trait_data is None:
            self._setup_callbacks(next_positive_callback=self._enter_in_progress_state, next_positive_callback_value=self.trait_data.set_in_progress_from_locked_value)
        else:
            self._setup_callbacks(next_positive_callback=self._enter_in_progress_state, next_positive_callback_value=self.trait_data.set_in_progress_from_locked_value, next_negative_callback=self._enter_opposing_in_progress_state, next_negative_callback_value=self.opposing_trait_data.set_in_progress_from_locked_value)

    def _enter_locked_state(self, _):
        if self._state == TraitStatisticStates.AT_RISK:
            self._state = TraitStatisticStates.LOCKED
            self.tracker.owner.remove_trait(self.trait_data.trait)
            self._remove_neglect()
            if self.trait_data.unlocked_lost_notification is not None:
                sim_info = self.tracker.owner
                notification = self.trait_data.unlocked_lost_notification(sim_info, SingleSimResolver(sim_info))
                notification.show_dialog()
        elif self._state == TraitStatisticStates.OPPOSING_AT_RISK:
            self._state = TraitStatisticStates.LOCKED
            self.tracker.owner.remove_trait(self.opposing_trait_data.trait)
            self._remove_neglect()
            if self.opposing_trait_data.unlocked_lost_notification is not None:
                sim_info = self.tracker.owner
                notification = self.opposing_trait_data.unlocked_lost_notification(sim_info, SingleSimResolver(sim_info))
                notification.show_dialog()
        else:
            self._state = TraitStatisticStates.LOCKED
        self.tracker._on_statistic_state_changed(self)
        self._setup_locked_state_listeners()
        self._send_at_risk_message()

    def _setup_in_progress_state_listeners(self):
        self._setup_callbacks(next_positive_callback=self._enter_unlocked_state, next_positive_callback_value=self.trait_data.set_unlocked_from_in_progress_value, next_negative_callback=self._enter_locked_state, next_negative_callback_value=self.trait_data.set_locked_from_in_progress_value)

    def _enter_in_progress_state(self, _):
        self._state = TraitStatisticStates.IN_PROGRESS
        self.tracker._on_statistic_state_changed(self)
        self._setup_in_progress_state_listeners()
        if self.trait_data.trait.trait_type == TraitType.LIFESTYLE:
            services.lifestyle_service().on_lifestyle_set_in_progress(self.tracker.owner, self)

    def _setup_unlocked_state_listeners(self):
        self._setup_callbacks(next_negative_callback=self._enter_at_risk_state, next_negative_callback_value=self.trait_data.set_at_risk_from_unlocked_value)

    def _enter_unlocked_state(self, _):
        if self._state == TraitStatisticStates.IN_PROGRESS:
            self._state = TraitStatisticStates.UNLOCKED
            self.tracker.owner.add_trait(self.trait_data.trait)
            if self.trait_data.unlocked_notification is not None:
                sim_info = self.tracker.owner
                notification = self.trait_data.unlocked_notification(sim_info, SingleSimResolver(sim_info))
                notification.show_dialog()
        else:
            self._state = TraitStatisticStates.UNLOCKED
        self.tracker._on_statistic_state_changed(self)
        self._setup_unlocked_state_listeners()
        self._send_at_risk_message()

    def _setup_at_risk_state_listeners(self):
        self._setup_callbacks(next_positive_callback=self._enter_unlocked_state, next_positive_callback_value=self.trait_data.set_unlocked_from_at_risk_value, next_negative_callback=self._enter_locked_state, next_negative_callback_value=self.trait_data.set_at_locked_from_at_risk_value)

    def _enter_at_risk_state(self, _):
        self._state = TraitStatisticStates.AT_RISK
        self.tracker._on_statistic_state_changed(self)
        self._setup_at_risk_state_listeners()
        self._send_at_risk_message()
        if self.trait_data.at_risk_notification is not None and not self._suppress_at_risk_notification:
            sim_info = self.tracker.owner
            notification = self.trait_data.at_risk_notification(sim_info, SingleSimResolver(sim_info))
            notification.show_dialog()

    def _setup_opposing_in_progress_state_listeners(self):
        self._setup_callbacks(next_positive_callback=self._enter_locked_state, next_positive_callback_value=self.opposing_trait_data.set_locked_from_in_progress_value, next_negative_callback=self._enter_opposing_unlocked_state, next_negative_callback_value=self.opposing_trait_data.set_unlocked_from_in_progress_value)

    def _enter_opposing_in_progress_state(self, _):
        self._state = TraitStatisticStates.OPPOSING_IN_PROGRESS
        self.tracker._on_statistic_state_changed(self)
        self._setup_opposing_in_progress_state_listeners()
        if self.opposing_trait_data.trait.trait_type == TraitType.LIFESTYLE:
            services.lifestyle_service().on_lifestyle_set_in_progress(self.tracker.owner, self)

    def _setup_opposing_unlocked_state_listeners(self):
        self._setup_callbacks(next_positive_callback=self._enter_opposing_at_risk_state, next_positive_callback_value=self.opposing_trait_data.set_at_risk_from_unlocked_value)

    def _enter_opposing_unlocked_state(self, _):
        if self._state == TraitStatisticStates.OPPOSING_IN_PROGRESS:
            self._state = TraitStatisticStates.OPPOSING_UNLOCKED
            self.tracker.owner.add_trait(self.opposing_trait_data.trait)
            if self.opposing_trait_data.unlocked_notification is not None:
                sim_info = self.tracker.owner
                notification = self.opposing_trait_data.unlocked_notification(sim_info, SingleSimResolver(sim_info))
                notification.show_dialog()
        else:
            self._state = TraitStatisticStates.OPPOSING_UNLOCKED
        self.tracker._on_statistic_state_changed(self)
        self._setup_opposing_unlocked_state_listeners()
        self._send_at_risk_message()

    def _setup_opposing_at_risk_state_listeners(self):
        self._setup_callbacks(next_positive_callback=self._enter_locked_state, next_positive_callback_value=self.opposing_trait_data.set_at_locked_from_at_risk_value, next_negative_callback=self._enter_opposing_unlocked_state, next_negative_callback_value=self.opposing_trait_data.set_unlocked_from_at_risk_value)

    def _enter_opposing_at_risk_state(self, _):
        self._state = TraitStatisticStates.OPPOSING_AT_RISK
        self.tracker._on_statistic_state_changed(self)
        self._setup_opposing_at_risk_state_listeners()
        self._send_at_risk_message()
        if self.opposing_trait_data.at_risk_notification is not None and not self._suppress_at_risk_notification:
            sim_info = self.tracker.owner
            notification = self.opposing_trait_data.at_risk_notification(sim_info, SingleSimResolver(sim_info))
            notification.show_dialog()

    @classmethod
    def on_trait_added(cls, sim_info, trait):
        trait_statistic = sim_info.trait_statistic_tracker.get_statistic(cls, add=True)
        if trait is cls.trait_data.trait:
            if trait_statistic.state == TraitStatisticStates.UNLOCKED or trait_statistic.state == TraitStatisticStates.AT_RISK:
                return
            trait_statistic.set_value(cls.max_value, ignore_caps=True)
            trait_statistic.reset_daily_caps()
        elif trait is cls.opposing_trait_data.trait:
            if trait_statistic.state == TraitStatisticStates.OPPOSING_UNLOCKED or trait_statistic.state == TraitStatisticStates.OPPOSING_AT_RISK:
                return
            trait_statistic.set_value(cls.min_value, ignore_caps=True)
            trait_statistic.reset_daily_caps()
        else:
            logger.error('Trait statistic {} was notified that a trait was being added for a {} which is a trait that it is not managing.', cls, trait)

    @classmethod
    def on_trait_removed(cls, sim_info, trait):
        trait_statistic = sim_info.trait_statistic_tracker.get_statistic(cls, add=False)
        if trait_statistic is None:
            return
        try:
            trait_statistic._suppress_at_risk_notification = True
            if trait is cls.trait_data.trait:
                if trait_statistic.state < TraitStatisticStates.UNLOCKED:
                    return
                trait_statistic.set_value(cls.default_value, ignore_caps=True)
                trait_statistic.reset_daily_caps()
            elif trait is cls.opposing_trait_data.trait:
                if trait_statistic.state > TraitStatisticStates.OPPOSING_UNLOCKED:
                    return
                trait_statistic.set_value(cls.default_value, ignore_caps=True)
                trait_statistic.reset_daily_caps()
            else:
                logger.error('Trait statistic {} was notified that a trait was being added for a {} which is a trait that it is not managing.', cls, trait)
        finally:
            trait_statistic._suppress_at_risk_notification = False

    def startup_statistic(self, from_load=False):
        if not from_load:
            self.reset_daily_caps()
        if self._state == TraitStatisticStates.LOCKED:
            self._setup_locked_state_listeners()
        elif self._state == TraitStatisticStates.IN_PROGRESS:
            self._setup_in_progress_state_listeners()
        elif self._state == TraitStatisticStates.UNLOCKED:
            self._setup_unlocked_state_listeners()
        elif self._state == TraitStatisticStates.AT_RISK:
            self._setup_at_risk_state_listeners()
        elif self._state == TraitStatisticStates.OPPOSING_IN_PROGRESS:
            self._setup_opposing_in_progress_state_listeners()
        elif self._state == TraitStatisticStates.OPPOSING_UNLOCKED:
            self._setup_opposing_unlocked_state_listeners()
        elif self._state == TraitStatisticStates.OPPOSING_AT_RISK:
            self._setup_opposing_at_risk_state_listeners()
        else:
            logger.error('Attempting to setup alarms for state {} that is not valid.', self._state)

    def _send_at_risk_message(self):
        distributor = Distributor.instance()
        trait = self.trait_data.trait
        at_risk = self._state == TraitStatisticStates.AT_RISK
        op = TraitAtRiskUpdate(trait, at_risk)
        distributor.add_op(self.tracker.owner, op)
        if self.opposing_trait_data is not None:
            opposing_trait = self.opposing_trait_data.trait
            opposing_at_risk = self._state == TraitStatisticStates.OPPOSING_AT_RISK
            opposing_op = TraitAtRiskUpdate(opposing_trait, opposing_at_risk)
            distributor.add_op(self.tracker.owner, opposing_op)

    def _remove_neglect(self):
        if self._neglect_buff_handle is not None:
            self.tracker.owner.remove_buff(self._neglect_buff_handle)
            self._neglect_buff_handle = None
            self._neglect_buff_index = None

    def _handle_neglect(self, trait_data):
        if TraitStatisticStates.OPPOSING_UNLOCKED < self._state and self._state < TraitStatisticStates.UNLOCKED:
            return
        if self._value_added:
            return
        if self._neglect_buff_index is None:
            self._neglect_buff_index = 0
        else:
            if self._neglect_buff_index + 1 == len(trait_data.neglect_buffs):
                return
            self.tracker.owner.remove_buff(self._neglect_buff_handle)
            self._neglect_buff_index += 1
        neglect_buff_data = trait_data.neglect_buffs[self._neglect_buff_index]
        self._neglect_buff_handle = self.tracker.owner.add_buff(neglect_buff_data.buff_type, buff_reason=neglect_buff_data.buff_reason)

    def _on_daily_cap_reached(self, _):
        services.lifestyle_service().on_daily_cap_reached(self.tracker.owner)

    def reset_daily_caps(self, current_value=None):
        if self.max_daily_progress is None:
            return
        if current_value is None:
            current_value = self.get_value()
        self._max_daily_cap = min(current_value + self.max_daily_progress, self.max_value)
        self._min_daily_cap = max(current_value - self.max_daily_progress, self.min_value)
        if self.trait_data.trait.trait_type != TraitType.LIFESTYLE:
            return
        if self._on_daily_cap_reached_listeners is not None:
            for listener in self._on_daily_cap_reached_listeners:
                self.remove_callback_listener(listener)
            self._on_daily_cap_reached_listeners.clear()
        else:
            self._on_daily_cap_reached_listeners = list()
        self._on_daily_cap_reached_listeners.append(self.create_and_add_callback_listener(Threshold(self._max_daily_cap, operator.ge), self._on_daily_cap_reached))
        if self.opposing_trait_data is None:
            return
        self._on_daily_cap_reached_listeners.append(self.create_and_add_callback_listener(Threshold(self._min_daily_cap, operator.le), self._on_daily_cap_reached))

    def perform_end_of_day_actions(self):
        value = self.get_value()
        if value >= self.default_value:
            trait_data = self.trait_data
            new_value = max(self.default_value, value - trait_data.daily_pushback)
        else:
            trait_data = self.opposing_trait_data
            new_value = min(self.default_value, value - trait_data.daily_pushback)
        self.set_value(new_value, ignore_caps=True)
        self._handle_neglect(trait_data)
        self.reset_daily_caps(current_value=new_value)
        self._value_added = False

    def _get_minimum_decay_level(self):
        if self._group_limited:
            if self._value > self.default_value:
                group_limited_cap = self.default_value
            else:
                group_limited_cap = self._value
            if self._min_daily_cap is None:
                return max(group_limited_cap, self.min_value)
            return max(group_limited_cap, self._min_daily_cap)
        if self._min_daily_cap is None:
            return self.min_value
        return self._min_daily_cap

    def _get_maximum_decay_level(self):
        if self._group_limited:
            if self._value > self.default_value:
                group_limited_cap = self.default_value
            else:
                group_limited_cap = self._value
            if self._max_daily_cap is None:
                return min(group_limited_cap, self.max_value)
            return min(group_limited_cap, self._max_daily_cap)
        if self._max_daily_cap is None:
            return self.max_value
        return self._max_daily_cap

    def _check_for_value_gain(self, old_value, new_value):
        if not (self.default_value <= old_value and old_value < new_value):
            if self.default_value >= old_value and old_value > new_value:
                self._value_added = True
                self._remove_neglect()
        else:
            self._value_added = True
            self._remove_neglect()

    def _update_value(self):
        old_value = self._value
        minimum_decay = self._get_minimum_decay_level()
        maximum_decay = self._get_maximum_decay_level()
        super()._update_value(minimum_decay_value=minimum_decay, maximum_decay_value=maximum_decay)
        self._check_for_value_gain(old_value, self._value)

    def set_value(self, value, ignore_caps=False, **kwargs):
        old_value = self._value
        if not ignore_caps:
            value = clamp(self._get_minimum_decay_level(), value, self._get_maximum_decay_level())
        super().set_value(value, **kwargs)
        self._check_for_value_gain(old_value, self._value)

    def get_save_message(self, tracker):
        msg = SimObjectAttributes_pb2.TraitStatistic()
        self.save(msg)
        return msg

    def save(self, msg):
        msg.trait_statistic_id = self.guid64
        msg.value = self.get_value()
        msg.state = self._state
        if self._neglect_buff_index is not None:
            msg.neglect_buff_index = self._neglect_buff_index
        msg.value_added = self._value_added
        if self._max_daily_cap is not None:
            msg.max_daily_cap = self._max_daily_cap
        if self._min_daily_cap is not None:
            msg.min_daily_cap = self._min_daily_cap

    def load(self, msg):
        self.set_value(msg.value, ignore_caps=True)
        self._state = TraitStatisticStates(msg.state)
        if msg.HasField('neglect_buff_index'):
            self._neglect_buff_index = msg.neglect_buff_index
            if self._state >= TraitStatisticStates.UNLOCKED:
                trait_data = self.trait_data
            else:
                trait_data = self.opposing_trait_data
            try:
                neglect_buff_data = trait_data.neglect_buffs[self._neglect_buff_index]
                self._neglect_buff_handle = self.tracker.owner.add_buff(neglect_buff_data.buff_type, buff_reason=neglect_buff_data.buff_reason)
            except:
                logger.exception("Stat: {} Current State: {} shouldn't have neglect buff index set: {}", self, self._state, self._neglect_buff_index)
                self._neglect_buff_index = None
        self._value_added = msg.value_added
        if msg.HasField('max_daily_cap'):
            self._max_daily_cap = msg.max_daily_cap
        if msg.HasField('min_daily_cap'):
            self._min_daily_cap = msg.min_daily_cap
        self.startup_statistic(from_load=True)
lock_instance_tunables(TraitStatistic, min_lod_value=SimInfoLODLevel.ACTIVE, respect_lod_on_add=True)