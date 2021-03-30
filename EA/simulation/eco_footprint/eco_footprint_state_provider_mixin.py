from distributor.system import Distributorfrom protocolbuffers import Consts_pb2, S4Common_pb2import alarmsimport worldimport servicesimport sims4from eco_footprint.eco_footprint_enums import EcoFootprintStateType, EcoFootprintDirectionfrom eco_footprint.eco_footprint_telemetry import send_eco_footprint_state_change_telemetryfrom eco_footprint.eco_footprint_tuning import EcoFootprintTunablesfrom event_testing.resolver import ZoneResolverfrom objects.components import ComponentContainerfrom objects.components.statistic_component import HasStatisticComponent
class EcoFootprintStateProviderMixin(ComponentContainer, HasStatisticComponent):
    UPDATE_ECO_FOOTPRINT_EFFECTS = 'Update Eco Footprint Effects'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_statistic_component()
        self._curr_state_type = EcoFootprintStateType.NEUTRAL
        self._simulating_eco_footprint_on_street = False
        self.active_lot_weight = 0
        self.inactive_lots_total = 0
        self._update_convergence_handle = None
        self._eco_footprint_states = {}
        for (state_type, state) in EcoFootprintTunables.ECO_FOOTPRINT_STATE_DATA.eco_footprint_states.items():
            self._eco_footprint_states[state_type] = state(self)
        self._eco_footprint_decay_modifiers = {EcoFootprintDirection.AT_CONVERGENCE: 1}
        self._is_eco_footprint_compatible = False
        self._persisted_convergence = None
        self._street_convergence_fully_computed = False

    def change_state(self, new_state_type, skip_nudge=False):
        if self._curr_state_type is not new_state_type:
            old_state_type = self._curr_state_type
            self._eco_footprint_states[old_state_type].exit()
            self._eco_footprint_states[new_state_type].enter()
            self._curr_state_type = new_state_type
            if not skip_nudge:
                moving_toward_green = new_state_type < old_state_type
                nudge_amt = EcoFootprintTunables.ECO_FOOTPRINT_STATE_DATA.additional_footprint_change_on_state_change
                footprint = self.get_street_footprint()
                if moving_toward_green:
                    footprint.add_value(-nudge_amt)
                else:
                    footprint.add_value(nudge_amt)
            send_eco_footprint_state_change_telemetry(services.get_world_description_id(services.current_zone().world_id), old_state_type, new_state_type, self.get_street_footprint_convergence_value())

    def on_zone_shutdown(self):
        if self._update_convergence_handle is not None:
            self._update_convergence_handle.cancel()
            self._update_convergence_handle = None

    def update_simulation_if_stale(self, enable_simulation):
        if not self._is_eco_footprint_compatible:
            return
        if enable_simulation:
            new_state_type = EcoFootprintTunables.eco_footprint_value_to_state(self.get_street_footprint_value())
            if self._simulating_eco_footprint_on_street and self._curr_state_type != new_state_type:
                self.change_state(new_state_type)
            if not self._simulating_eco_footprint_on_street:
                self._eco_footprint_states[new_state_type].enter()
                self._curr_state_type = new_state_type
                self._simulating_eco_footprint_on_street = True
            if self._update_convergence_handle is None:
                self._update_convergence_handle = alarms.add_alarm(self, EcoFootprintTunables.STREET_CONVERGENCE_UPDATE_TUNING.update_interval(), self._recompute_street_convergence, use_sleep_time=False, repeating=True)
            self._update_eco_footprint_effects(skip_nudge=True)
        else:
            if self._simulating_eco_footprint_on_street:
                self._eco_footprint_states[self._curr_state_type].exit()
                self._simulating_eco_footprint_on_street = False
            if self._update_convergence_handle is not None:
                self._update_convergence_handle.cancel()
                self._update_convergence_handle = None

    def on_all_households_and_sim_infos_loaded(self):
        street = services.street_service().get_street(self)
        world_desc_id = world.street.get_world_description_id_from_street(street)
        self._is_eco_footprint_compatible = world_desc_id is not None and services.get_is_eco_footprint_compatible_for_world_description(world_desc_id)

    def finalize_startup(self):
        street_service = services.street_service()
        street = street_service.get_street(self)
        for (state_type, state) in self._eco_footprint_states.items():
            is_active = state_type == self._curr_state_type
            state.finalize_startup(is_active)
        if not self._is_eco_footprint_compatible:
            return
        if street is services.current_street():
            self._fully_compute_street_convergence()
            self.update_simulation_if_stale(street_service.enable_eco_footprint)
        elif self._persisted_convergence is not None:
            footprint_stat = self.get_street_footprint()
            footprint_stat.convergence_value = self._persisted_convergence

    def force_set_eco_footprint_state(self, state, update_lot_values=True):
        if not self._is_eco_footprint_compatible:
            return
        street_footprint_tuning = EcoFootprintTunables.STREET_FOOTPRINT
        if state == EcoFootprintStateType.GREEN:
            new_footprint_value = street_footprint_tuning.min_value
        elif state == EcoFootprintStateType.NEUTRAL:
            new_footprint_value = 0.5*(street_footprint_tuning.min_value + street_footprint_tuning.max_value)
        else:
            new_footprint_value = street_footprint_tuning.max_value
        self.force_set_eco_footprint_value(new_footprint_value, update_lot_values=update_lot_values)

    def force_set_eco_footprint_value(self, new_value, update_lot_values=True):
        if not self._is_eco_footprint_compatible:
            return
        street = services.street_service().get_street(self)
        street_footprint = self.get_street_footprint()
        street_footprint.set_value(new_value)
        if update_lot_values:
            zone_manager = services.get_zone_manager()
            for (lot_id, zone_ids) in world.street.get_lot_id_to_zone_ids_dict(street).items():
                zone = zone_manager.get(zone_ids[0], allow_uninstantiated_zones=True)
                if zone is not None:
                    zone.lot.commodity_tracker.set_value(EcoFootprintTunables.LOT_FOOTPRINT, new_value)
            self._fully_compute_street_convergence()
        self._update_eco_footprint_effects(skip_nudge=True)

    def _recompute_street_convergence(self, *args):
        street_footprint_stat = self.get_street_footprint()
        street_service = services.street_service()
        lot = services.active_lot()
        lot_footprint_value = lot.commodity_tracker.get_value(EcoFootprintTunables.LOT_FOOTPRINT)
        aggregate = self.inactive_lots_total + self.active_lot_weight*lot_footprint_value
        aggregate = EcoFootprintTunables.get_modified_convergence_value(street_footprint_stat, aggregate, street_service.get_street(self))
        street_footprint_stat.convergence_value = aggregate
        self._update_street_decay_rate()
        self._update_eco_footprint_effects()

    def _update_eco_footprint_effects(self, skip_nudge=False):
        street_service = services.street_service()
        street = street_service.get_street(self) if street_service is not None else None
        if street is None:
            return
        (neighborhood_proto, street_info_data) = street_service.get_neighborhood_proto(street)
        if neighborhood_proto is None or street_info_data is None:
            return
        street_service.start_bulk_policy_update(EcoFootprintStateProviderMixin.UPDATE_ECO_FOOTPRINT_EFFECTS)
        street_footprint_value = self.get_street_footprint_value()
        self.change_state(EcoFootprintTunables.eco_footprint_value_to_state(street_footprint_value), skip_nudge=skip_nudge)
        street_service.end_bulk_policy_update(EcoFootprintStateProviderMixin.UPDATE_ECO_FOOTPRINT_EFFECTS)
        self.distribute_neighborhood_update()

    def distribute_neighborhood_update(self):
        street_service = services.street_service()
        street = street_service.get_street(self) if street_service is not None else None
        if street is None:
            return
        (neighborhood_proto, street_info_data) = street_service.get_neighborhood_proto(street)
        if neighborhood_proto is None or street_info_data is None:
            return
        current_zone = services.current_zone()
        if current_zone is None:
            return
        persistence_service = services.get_persistence_service()
        lot_data = persistence_service.get_lot_proto_buff(current_zone.lot.lot_id)
        lot = services.active_lot()
        lot_footprint_value = lot.commodity_tracker.get_value(EcoFootprintTunables.LOT_FOOTPRINT)
        lot_data.eco_footprint_state = EcoFootprintTunables.eco_footprint_value_to_state(lot_footprint_value)
        street_footprint_stat = self.get_street_footprint()
        street_footprint_value = street_footprint_stat.get_value()
        street_info_data.eco_footprint_delta = street_footprint_stat.convergence_value - street_footprint_value
        street_info_data.eco_footprint_state = self._curr_state_type
        if self._curr_state_type == EcoFootprintStateType.GREEN:
            min = street_footprint_stat.min_value
            max = EcoFootprintTunables.ECO_FOOTPRINT_STATE_DATA.green_threshold
        elif self._curr_state_type == EcoFootprintStateType.NEUTRAL:
            min = EcoFootprintTunables.ECO_FOOTPRINT_STATE_DATA.green_threshold
            max = EcoFootprintTunables.ECO_FOOTPRINT_STATE_DATA.industrial_threshold
        else:
            min = EcoFootprintTunables.ECO_FOOTPRINT_STATE_DATA.industrial_threshold
            max = street_footprint_stat.max_value
        if max - min is not 0:
            street_info_data.normalized_eco_footprint_state_progress = (street_footprint_value - min)/(max - min)
        distributor = Distributor.instance()
        distributor.add_event(Consts_pb2.MSG_NS_NEIGHBORHOOD_UPDATE, neighborhood_proto)

    def _fully_compute_street_convergence(self):
        street_service = services.street_service()
        street = street_service.get_street(self)
        if street is None:
            return
        is_first_time_initialization = not self.commodity_tracker.has_statistic(EcoFootprintTunables.STREET_FOOTPRINT)
        if is_first_time_initialization:
            self.commodity_tracker.add_statistic(EcoFootprintTunables.STREET_FOOTPRINT)
        played_lot_count = 0
        total_lot_count = 0
        played_lot_total = 0
        unplayed_lot_total = 0
        lot_id_to_zone_id_dict = world.street.get_lot_id_to_zone_ids_dict(street)
        statistics_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        persistence_service = services.get_persistence_service()
        household_manager = services.household_manager()
        active_lot = services.active_lot()
        active_lot_is_played = False
        for (lot_id, zone_ids) in lot_id_to_zone_id_dict.items():
            is_played_lot = False
            for zone_id in zone_ids:
                household_id = persistence_service.get_household_id_from_zone_id(zone_id)
                if household_id:
                    household = household_manager.get(household_id)
                    if household is not None and household.is_played_household:
                        is_played_lot = True
                        break
            stat_value = EcoFootprintTunables.LOT_FOOTPRINT.default_value
            if active_lot.lot_id == lot_id:
                lot = services.active_lot()
                stat_value = lot.commodity_tracker.get_value(EcoFootprintTunables.LOT_FOOTPRINT)
                active_lot_is_played = is_played_lot
            else:
                zone_data = persistence_service.get_zone_proto_buff(zone_ids[0])
                if zone_data is not None:
                    commodity_tracker_data = zone_data.gameplay_zone_data.commodity_tracker
                    for stat_data in commodity_tracker_data.commodities:
                        stat_cls = statistics_manager.get(stat_data.name_hash)
                        if stat_cls is EcoFootprintTunables.LOT_FOOTPRINT:
                            stat_value = stat_data.value
                            break
                    house_desc_id = services.get_house_description_id(zone_data.lot_template_id, zone_data.lot_description_id, zone_data.active_plex)
                    stat_value = services.get_eco_footprint_value(house_desc_id)
            if is_played_lot:
                played_lot_total += stat_value
                played_lot_count += 1
            else:
                unplayed_lot_total += stat_value
            total_lot_count += 1
        percentage_of_lots_played = 0 if total_lot_count is 0 else played_lot_count/total_lot_count
        curve = EcoFootprintTunables.STREET_CONVERGENCE_UPDATE_TUNING.played_lot_weight
        weight_of_played_lots = curve.get(percentage_of_lots_played)
        unplayed_lot_count = total_lot_count - played_lot_count
        if played_lot_count > 0:
            played_lot_factor = weight_of_played_lots*played_lot_total*(1/played_lot_count)
        else:
            played_lot_factor = 0
        if unplayed_lot_count > 0:
            unplayed_lot_factor = (1 - weight_of_played_lots)*unplayed_lot_total*(1/unplayed_lot_count)
        else:
            unplayed_lot_factor = 0
        aggregate = played_lot_factor + unplayed_lot_factor
        if active_lot_is_played:
            if played_lot_count == 0:
                self.active_lot_weight = 0
            else:
                self.active_lot_weight = weight_of_played_lots/played_lot_count
        elif unplayed_lot_count == 0:
            self.active_lot_weight = 0
        else:
            self.active_lot_weight = (1 - weight_of_played_lots)/unplayed_lot_count
        active_lot_total = self.active_lot_weight*active_lot.commodity_tracker.get_value(EcoFootprintTunables.LOT_FOOTPRINT)
        self.inactive_lots_total = aggregate - active_lot_total
        street_footprint_stat = self.get_street_footprint()
        street_footprint_stat.convergence_value = EcoFootprintTunables.get_modified_convergence_value(street_footprint_stat, aggregate, street)
        if is_first_time_initialization:
            if street.initial_street_eco_footprint_override is not None:
                street_footprint_stat.set_value(street.initial_street_eco_footprint_override)
            else:
                street_footprint_stat.set_value(street_footprint_stat.convergence_value)
        self._compute_street_decay_modifiers()
        self._street_convergence_fully_computed = True

    def _compute_street_decay_modifiers(self):
        street_service = services.street_service()
        street = street_service.get_street(self)
        if street is None:
            return
        if not self._is_eco_footprint_compatible:
            return
        zone_ids = world.street.get_zone_ids_from_street(street)
        for (direction, modifier_tuple) in EcoFootprintTunables.STREET_CONVERGENCE_UPDATE_TUNING.convergence_rate_tuning.items():
            decay_modifier = 1
            if zone_ids is not None:
                for zone_id in zone_ids:
                    resolver = ZoneResolver(zone_id)
                    decay_modifier *= modifier_tuple.per_lot_modifiers.get_multiplier(resolver)
            self._eco_footprint_decay_modifiers[direction] = decay_modifier
        self._update_street_decay_rate()

    def _update_street_decay_rate(self):
        street_footprint_stat = self.get_street_footprint()
        street_footprint_stat.clear_decay_rate_modifiers()
        if self.current_eco_footprint_direction in self._eco_footprint_decay_modifiers:
            street_footprint_stat.add_decay_rate_modifier(self._eco_footprint_decay_modifiers[self.current_eco_footprint_direction])

    def on_build_buy_exit(self):
        if self._street_convergence_fully_computed:
            self._compute_street_decay_modifiers()
            self._recompute_street_convergence()
        else:
            self._fully_compute_street_convergence()

    @property
    def is_eco_footprint_compatible(self):
        return self._is_eco_footprint_compatible

    @property
    def current_eco_footprint_direction(self):
        street_footprint = self.get_street_footprint()
        if street_footprint is None:
            return EcoFootprintDirection.AT_CONVERGENCE
        footprint_current_value = street_footprint.get_value()
        convergence_value = street_footprint.convergence_value
        if footprint_current_value > convergence_value:
            return EcoFootprintDirection.TOWARD_GREEN
        if footprint_current_value < convergence_value:
            return EcoFootprintDirection.TOWARD_INDUSTRIAL
        return EcoFootprintDirection.AT_CONVERGENCE

    def get_street_footprint(self, add=True):
        return self.commodity_tracker.get_statistic(EcoFootprintTunables.STREET_FOOTPRINT, add=add)

    def get_street_footprint_convergence_value(self):
        if self.commodity_tracker.has_statistic(EcoFootprintTunables.STREET_FOOTPRINT):
            return self.get_street_footprint().convergence_value
        else:
            return 0

    def get_street_footprint_value(self):
        return self.commodity_tracker.get_value(EcoFootprintTunables.STREET_FOOTPRINT)

    @property
    def current_eco_footprint_state(self):
        return self._curr_state_type

    def _save_street_eco_footprint_data(self, eco_footprint_data):
        eco_footprint_data.current_eco_footprint_state = self._curr_state_type
        eco_footprint_data.effects_are_simulated = self._simulating_eco_footprint_on_street
        street = services.street_service().get_street(self)
        if street is services.current_street() and not self._street_convergence_fully_computed:
            self._fully_compute_street_convergence()
        eco_footprint_data.convergence = self.get_street_footprint_convergence_value()

    def _load_street_eco_footprint_data(self, eco_footprint_data):
        current_state_type = eco_footprint_data.current_eco_footprint_state
        if current_state_type == EcoFootprintStateType.NEUTRAL:
            self._curr_state_type = EcoFootprintStateType.NEUTRAL
        elif current_state_type == EcoFootprintStateType.GREEN:
            self._curr_state_type = EcoFootprintStateType.GREEN
        else:
            self._curr_state_type = EcoFootprintStateType.INDUSTRIAL
        self._simulating_eco_footprint_on_street = eco_footprint_data.effects_are_simulated
        self._persisted_convergence = eco_footprint_data.convergence
