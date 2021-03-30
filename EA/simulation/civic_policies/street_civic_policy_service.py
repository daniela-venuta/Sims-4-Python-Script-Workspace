from protocolbuffers import GameplaySaveData_pb2, FileSerialization_pb2from sims4.callback_utils import CallableListfrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyimport sims4from civic_policies.base_civic_policy_provider import BaseCivicPolicyProvider, BaseCivicPolicyProviderServiceMixinfrom distributor.rollback import ProtocolBufferRollbackfrom eco_footprint.eco_footprint_tuning import EcoFootprintTunablesfrom event_testing.test_events import TestEventimport game_servicesfrom world.street import get_street_instance_from_zone_id, Street, get_zone_ids_from_streetimport persistence_error_typesimport servicesimport worldimport zone_typeslogger = sims4.log.Logger('StreetService', default_owner='shouse')
class StreetService(Service, BaseCivicPolicyProviderServiceMixin):

    def __init__(self):
        super().__init__()
        self._provider_instances = {}
        self._street_by_provider = {}
        self._street_sim_info_home_zone_change_callbacks = {}
        self._street_household_home_zone_change_callbacks = {}
        self._current_household_key = None
        self._street_sim_added_callbacks = {}
        self._street_sim_removed_callbacks = {}
        self._enable_eco_footprint = True
        self._first_time_setup_needed = False

    @property
    def enable_eco_footprint(self):
        return self._enable_eco_footprint

    @enable_eco_footprint.setter
    def enable_eco_footprint(self, value):
        if self._enable_eco_footprint is not value:
            self._enable_eco_footprint = value
            street = services.current_street()
            provider = self.get_provider(street)
            provider.update_simulation_if_stale(self._enable_eco_footprint)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_STREET_CIVIC_POLICY_SERVICE

    @classproperty
    def required_packs(cls):
        return (Pack.EP09,)

    def on_client_connect(self, client):
        current_zone = services.current_zone()
        current_zone.register_callback(zone_types.ZoneState.SHUTDOWN_STARTED, self._on_zone_shutdown)
        services.get_event_manager().register_single_event(self, TestEvent.SimHomeZoneChanged)

    def on_client_disconnect(self, client):
        if not game_services.service_manager.is_traveling:
            Street.clear_caches()

    def _on_zone_shutdown(self):
        street_provider = self.get_provider(services.current_street())
        if street_provider is not None:
            street_provider.on_zone_shutdown()
        current_zone = services.current_zone()
        current_zone.unregister_callback(zone_types.ZoneState.SHUTDOWN_STARTED, self._on_zone_shutdown)
        services.get_event_manager().unregister_single_event(self, TestEvent.SimHomeZoneChanged)

    def save(self, object_list=None, zone_data=None, open_street_data=None, save_slot_data=None):
        service_data = GameplaySaveData_pb2.PersistableStreetService()
        for (street, provider) in self._provider_instances.items():
            with ProtocolBufferRollback(service_data.street_data) as street_data:
                street_data.street_id = street.guid64
                provider.save(street_data.civic_provider_data)
                provider.save_street_eco_footprint_data(street_data.street_eco_footprint_data)
        save_slot_data.gameplay_data.street_service = service_data

    def load(self, zone_data=None):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        service_data = save_slot_data_msg.gameplay_data.street_service
        self._first_time_setup_needed = len(service_data.street_data) == 0
        guid64_to_provider = {}
        manager = services.get_instance_manager(sims4.resources.Types.STREET)
        for street in manager.types.values():
            if not street.civic_policy.civic_policies:
                pass
            else:
                provider = street.civic_policy()
                self._provider_instances[street] = provider
                self._street_by_provider[provider] = street
                guid64_to_provider[street.guid64] = provider
        for street_data in service_data.street_data:
            provider = guid64_to_provider.get(street_data.street_id)
            if provider is not None:
                provider.load(street_data.civic_provider_data)
                provider.load_street_eco_footprint_data(street_data.street_eco_footprint_data)

    def save_options(self, options_proto):
        BaseCivicPolicyProviderServiceMixin.save_options(self, options_proto)
        options_proto.eco_footprint_gameplay_enabled = self._enable_eco_footprint

    def load_options(self, options_proto):
        BaseCivicPolicyProviderServiceMixin.load_options(self, options_proto)
        self._enable_eco_footprint = options_proto.eco_footprint_gameplay_enabled

    def on_all_households_and_sim_infos_loaded(self, client):
        for provider in self._provider_instances.values():
            provider.on_all_households_and_sim_infos_loaded()
        self.update_community_board_tooltip()

    def on_cleanup_zone_objects(self, client):
        self._reset_alarms()
        for provider in self._provider_instances.values():
            provider.finalize_startup()
        self._start_call_to_actions()
        self._send_update_message()
        if self._first_time_setup_needed:
            if self.voting_open:
                self._open_voting(suppress_dialog=True)
            self._first_time_setup_needed = False

    def enact(self, street, policy):
        provider = self._provider_instances.get(street)
        if provider is not None:
            return provider.enact(policy)
        return False

    def repeal(self, street, policy):
        provider = self._provider_instances.get(street)
        if provider is not None:
            return provider.repeal(policy)
        return False

    def vote(self, street, policy, count=1, user_directed=False, lobby_interaction=False):
        provider = self._provider_instances.get(street)
        if provider is not None:
            return provider.vote(policy, count, user_directed=user_directed, lobby_interaction=lobby_interaction)
        return False

    def force_end_voting(self, street):
        if street is None:
            self._close_voting()
            return True
        else:
            provider = self._provider_instances.get(street)
            if provider is not None:
                provider.close_voting()
                return True
        return False

    def add_for_repeal(self, street, policy):
        provider = self._provider_instances.get(street)
        if provider is not None:
            return provider.add_for_repeal(policy)
        return False

    def remove_from_repeal(self, street, policy):
        provider = self._provider_instances.get(street)
        if provider is not None:
            return provider.remove_from_repeal(policy)
        return False

    def get_provider(self, street):
        return self._provider_instances.get(street)

    def get_street(self, provider):
        return self._street_by_provider.get(provider)

    def register_sim_added_callback(self, street, callback):
        if street is None or callback is None:
            logger.error('Attempted to register an incomplete callback: {} for street {}', callback, street)
            return
        if street not in self._street_sim_added_callbacks:
            self._street_sim_added_callbacks[street] = CallableList()
        callback_list = self._street_sim_added_callbacks[street]
        if callback not in callback_list:
            callback_list.register(callback)

    def register_sim_removed_callback(self, street, callback):
        if street is None or callback is None:
            logger.error('Attempted to register an incomplete callback: {} for street {}', callback, street)
            return
        if street not in self._street_sim_removed_callbacks:
            self._street_sim_removed_callbacks[street] = CallableList()
        callback_list = self._street_sim_removed_callbacks[street]
        if callback not in callback_list:
            callback_list.register(callback)

    @staticmethod
    def _unregister_callback(street, callback, callable_lists):
        if street is None:
            logger.error('Attempted to unregister a callback on a None street', owner='jmorrow')
            return
        if street not in callable_lists:
            return
        callable_lists[street].unregister(callback)

    def unregister_sim_added_callback(self, street, callback):
        self._unregister_callback(street, callback, self._street_sim_added_callbacks)

    def unregister_sim_removed_callback(self, street, callback):
        self._unregister_callback(street, callback, self._street_sim_removed_callbacks)

    @staticmethod
    def _register_home_street_change_callback(callbacks, street, callback):
        if street is None or callback is None:
            logger.error('Attempt to register an incomplete callback: {} for street {}', callback, street)
            return
        if street not in callbacks:
            callbacks[street] = CallableList()
        callbacks[street].append(callback)

    def register_sim_info_home_street_change_callback(self, street, callback):
        StreetService._register_home_street_change_callback(self._street_sim_info_home_zone_change_callbacks, street, callback)

    def on_sim_added(self, sim_info):
        street = services.current_street()
        if street in self._street_sim_added_callbacks:
            self._street_sim_added_callbacks[street](sim_info)

    def on_sim_removed(self, sim_info):
        street = services.current_street()
        if street in self._street_sim_removed_callbacks:
            self._street_sim_removed_callbacks[street](sim_info)

    def register_household_home_street_change_callback(self, street, callback):
        StreetService._register_home_street_change_callback(self._street_household_home_zone_change_callbacks, street, callback)

    @staticmethod
    def _notify_of_home_lot_change(callbacks, entity, old_zone_id, new_zone_id):
        if entity is None:
            return
        if old_zone_id == new_zone_id:
            return

        def get_street(zone_id):
            if zone_id is None or zone_id == 0:
                return
            return get_street_instance_from_zone_id(zone_id)

        old_street = get_street(old_zone_id)
        new_street = get_street(new_zone_id)
        if old_street == new_street:
            return
        for street in (old_street, new_street):
            if not street is None:
                if street not in callbacks:
                    pass
                else:
                    callbacks[street](entity, old_street, new_street)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SimHomeZoneChanged:
            old_zone_id = resolver.get_resolved_arg('old_zone_id')
            new_zone_id = resolver.get_resolved_arg('new_zone_id')
            new_household_key = (sim_info.household_id, old_zone_id, new_zone_id)
            if self._current_household_key != new_household_key:
                self._current_household_key = new_household_key
                household = services.household_manager().get(sim_info.household_id)
                StreetService._notify_of_home_lot_change(self._street_household_home_zone_change_callbacks, household, old_zone_id, new_zone_id)
            StreetService._notify_of_home_lot_change(self._street_sim_info_home_zone_change_callbacks, sim_info, old_zone_id, new_zone_id)

    def get_neighborhood_proto(self, street, add=True):
        zone_ids = get_zone_ids_from_street(street)
        if not zone_ids:
            return (None, None)
        persistence_service = services.get_persistence_service()
        zone_id = zone_ids[0]
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        neighborhood_proto = persistence_service.get_neighborhood_proto_buf_from_zone_id(zone_id)
        if not neighborhood_proto:
            return (None, None)
        for street_data in neighborhood_proto.street_data:
            if street_data.world_id == zone_data.world_id:
                return (neighborhood_proto, street_data)
        if not add:
            return (None, None)
        street_data = FileSerialization_pb2.StreetInfoData()
        street_data.world_id = zone_data.world_id
        neighborhood_proto.street_data.append(street_data)
        return (neighborhood_proto, neighborhood_proto.street_data[-1])

    def _open_voting(self, suppress_dialog=False):
        super()._open_voting(suppress_dialog=suppress_dialog)
        self._send_update_message()

    def _close_voting(self):
        super()._close_voting()
        self._send_update_message()

    def _send_update_message(self):
        household = services.active_household()
        if household is None:
            return
        street = world.street.get_street_instance_from_world_id(household.get_home_world_id())
        if street is None:
            return
        provider = self.get_provider(street)
        if provider is None:
            return
        provider.send_update_message()

    def _get_active_household_provider(self):
        active_sim = services.active_sim_info()
        if active_sim is None or active_sim.household is None or active_sim.household.home_zone_id == 0:
            return
        street = get_street_instance_from_zone_id(active_sim.household.home_zone_id)
        return self.get_provider(street)

    def _show_notification(self, notification):
        if self._get_active_household_provider() is None:
            return
        super()._show_notification(notification)

    def _get_open_notification(self):
        provider = self._get_active_household_provider()
        if provider is not None and provider.new_enact_max_count() <= 0:
            return BaseCivicPolicyProvider.VOTING_OPEN_MAX_ENABLED_NOTIFICATION
        return super()._get_open_notification()

    def _get_warn_notification(self):
        provider = self._get_active_household_provider()
        if provider is not None and provider.new_enact_max_count() <= 0:
            repeal_policies = provider.get_up_for_repeal_policies()
            if repeal_policies:
                return BaseCivicPolicyProvider.VOTING_CLOSE_WARNING_MAX_ENABLED_NOTIFICATION
            return
        return super()._get_warn_notification()

    def _get_close_notification(self):
        provider = self._get_active_household_provider()
        if provider is not None and provider.new_enact_max_count() <= 0:
            repeal_policies = provider.get_up_for_repeal_policies()
            for repeal_policy in repeal_policies:
                signatures = provider.get_stat_value(repeal_policy.vote_count_statistic)
                if signatures >= BaseCivicPolicyProvider.REPEAL_PETITION_THRESHOLD:
                    return BaseCivicPolicyProvider.VOTING_CLOSE_MAX_ENABLED_NOTIFICATION_SUCCESS
                return BaseCivicPolicyProvider.VOTING_CLOSE_MAX_ENABLED_NOTIFICATION_FAIL
            return
        return super()._get_close_notification()
