from persistence_error_types import ErrorCodesfrom protocolbuffers import GameplaySaveData_pb2import servicesfrom event_testing.resolver import SingleSimResolverfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableList, TunableReference, Tunable, TunableEnumEntryfrom sims4.utils import classpropertyfrom statistics.trait_statistic import TraitStatisticStates, TraitStatisticGroupfrom traits.trait_type import TraitTypefrom ui.ui_lifestyles_dialog import UiDialogLifestyles, LifestyleUiStatefrom ui.ui_dialog_notification import UiDialogNotification
class LifestyleService(Service):
    LIFESTYLES = TunableList(description='\n        A list of all of the lifestyles as they will be displayed in the UI.\n        ', tunable=TunableReference(description='\n            A reference to a lifestyle.\n            ', manager=services.get_instance_manager(Types.TRAIT), pack_safe=True))
    HIDDEN_LIFESTYLES = TunableList(description='\n        A list of the lifestyles that begin hidden.  When a lifestyle is\n        first set in progress it and all opposing lifestyles will be unhidden\n        globally.\n        ', tunable=TunableReference(description='\n            A reference to a lifestyle.\n            ', manager=services.get_instance_manager(Types.TRAIT), pack_safe=True))
    DAILY_CAP_REACHED_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        Notification that will play when a lifestyle hits the daily cap on progress\n        first time.\n        ')
    IN_PROGRESS_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        Notification that will play when a lifestyle becomes set in progress for the\n        first time.\n        ')
    UNHIDDEN_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        Notification that will play when a lifestyle becomes unhidden for the first\n        time.\n        ')
    MAX_ACTIVE_LIFESTYLES = Tunable(description='\n        Maximum number of active lifestyles a sim can have.\n        ', tunable_type=int, default=3)
    LIFESTYLES_DIALOG = UiDialogLifestyles.TunableFactory(description='\n        Dialog that will show all the lifestyles and their states for the current Sim.\n        ')
    TRAIT_STATISTIC_GROUP = TunableEnumEntry(description='\n        The trait statistic group for lifestyles\n        ', tunable_type=TraitStatisticGroup, default=TraitStatisticGroup.NO_GROUP)

    def __init__(self):
        self._lifestyles_enabled = True
        self._has_seen_daily_cap_notification = False
        self._has_seen_in_progress_notification = False
        self._has_seen_hidden_notification = False
        self._hidden_lifestyles = None
        self.trait_stat_to_ui_state_switcher = {TraitStatisticStates.OPPOSING_IN_PROGRESS: LifestyleUiState.LOCKED, TraitStatisticStates.OPPOSING_UNLOCKED: LifestyleUiState.LOCKED, TraitStatisticStates.OPPOSING_AT_RISK: LifestyleUiState.LOCKED, TraitStatisticStates.AT_RISK: LifestyleUiState.AT_RISK, TraitStatisticStates.UNLOCKED: LifestyleUiState.ACTIVE, TraitStatisticStates.IN_PROGRESS: LifestyleUiState.IN_PROGRESS, TraitStatisticStates.LOCKED: LifestyleUiState.LOCKED}

    @classproperty
    def save_error_code(cls):
        return ErrorCodes.SERVICE_SAVE_FAILED_LIFESTYLE_SERVICE

    @property
    def lifestyles_enabled(self):
        return self._lifestyles_enabled

    def _cleanup_lifestyles(self):
        sim_info_manager = services.sim_info_manager()
        for sim_info in sim_info_manager.get_all():
            if sim_info.has_trait_statistic_tracker:
                sim_info.trait_statistic_tracker.remove_all_statistics_by_group(self.TRAIT_STATISTIC_GROUP)
            sim_info.trait_tracker.remove_traits_of_type(TraitType.LIFESTYLE)

    def set_lifestyles_enabled(self, enabled):
        if self._lifestyles_enabled == enabled:
            return
        self._lifestyles_enabled = enabled
        if self._lifestyles_enabled:
            return
        self._cleanup_lifestyles()

    def can_add_trait_statistic(self, trait_statistic):
        if trait_statistic.group != self.TRAIT_STATISTIC_GROUP:
            return True
        return self._lifestyles_enabled

    def on_all_households_and_sim_infos_loaded(self, client):
        if not self._lifestyles_enabled:
            self._cleanup_lifestyles()

    def on_daily_cap_reached(self, sim_info):
        if self._has_seen_daily_cap_notification:
            return
        notification = LifestyleService.DAILY_CAP_REACHED_NOTIFICATION(sim_info, resolver=SingleSimResolver(sim_info))
        notification.show_dialog()
        self._has_seen_daily_cap_notification = True

    def on_lifestyle_set_in_progress(self, sim_info, lifestyle_statistic):
        if self._hidden_lifestyles is None:
            self._hidden_lifestyles = set(LifestyleService.HIDDEN_LIFESTYLES)
        if lifestyle_statistic.trait_data.trait in self._hidden_lifestyles:
            self._hidden_lifestyles.remove(lifestyle_statistic.trait_data.trait)
            if lifestyle_statistic.opposing_trait_data is not None:
                self._hidden_lifestyles.remove(lifestyle_statistic.opposing_trait_data.trait)
            hidden_notification = LifestyleService.UNHIDDEN_NOTIFICATION(sim_info, resolver=SingleSimResolver(sim_info))
            hidden_notification.show_dialog()
            return
        if self._has_seen_in_progress_notification:
            return
        notification = LifestyleService.IN_PROGRESS_NOTIFICATION(sim_info, resolver=SingleSimResolver(sim_info))
        notification.show_dialog()
        self._has_seen_in_progress_notification = True

    def get_lifestyle_ui_state_from_trait(self, sim_info, lifestyle_trait):
        if self._hidden_lifestyles is None:
            self._hidden_lifestyles = set(LifestyleService.HIDDEN_LIFESTYLES)
        if lifestyle_trait in self._hidden_lifestyles:
            return LifestyleUiState.HIDDEN
        trait_statistic_state = sim_info.trait_statistic_tracker.get_trait_state(lifestyle_trait)
        return self.trait_stat_to_ui_state_switcher.get(trait_statistic_state, None)

    def save(self, object_list=None, zone_data=None, open_street_data=None, save_slot_data=None):
        service_data = GameplaySaveData_pb2.PersistableLifestyleService()
        service_data.has_seen_daily_cap_notification = self._has_seen_daily_cap_notification
        service_data.has_seen_in_progress_notification = self._has_seen_in_progress_notification
        service_data.has_seen_hidden_notification = self._has_seen_hidden_notification
        if self._hidden_lifestyles is None:
            self._hidden_lifestyles = set(LifestyleService.HIDDEN_LIFESTYLES)
        for hidden_lifestyle in self._hidden_lifestyles:
            service_data.hidden_lifestyles.append(hidden_lifestyle.guid64)
        save_slot_data.gameplay_data.lifestyle_service = service_data

    def load(self, zone_data=None):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if not save_slot_data_msg.gameplay_data.HasField('lifestyle_service'):
            return
        service_data = save_slot_data_msg.gameplay_data.lifestyle_service
        if service_data.HasField('has_seen_daily_cap_notification'):
            self.has_seen_daily_cap_notification = service_data.has_seen_daily_cap_notification
        if service_data.HasField('has_seen_in_progress_notification'):
            self._has_seen_in_progress_notification = service_data.has_seen_in_progress_notification
        if service_data.HasField('has_seen_hidden_notification'):
            self._has_seen_hidden_notification = service_data.has_seen_hidden_notification
        trait_manager = services.get_instance_manager(Types.TRAIT)
        self._hidden_lifestyles = set()
        for trait_id in service_data.hidden_lifestyles:
            trait = trait_manager.get(trait_id)
            if trait is None:
                pass
            else:
                self._hidden_lifestyles.add(trait)

    def load_options(self, options_proto):
        self._lifestyles_enabled = options_proto.lifestyles_effects_enabled

    def save_options(self, options_proto):
        options_proto.lifestyles_effects_enabled = self._lifestyles_enabled
