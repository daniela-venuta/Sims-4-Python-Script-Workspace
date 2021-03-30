from protocolbuffers import Consts_pb2, UI_pb2, InteractionOps_pb2, MoveInMoveOut_pb2from distributor import shared_messagesfrom distributor.ops import SplitHouseholdDialog, SendUIMessagefrom distributor.system import Distributorfrom google.protobuf import text_formatfrom objects import ALL_HIDDEN_REASONSfrom objects.object_enums import ResetReasonfrom server_commands.argument_helpers import OptionalTargetParamfrom sims.sim_spawner import SimSpawnerfrom sims4.commands import CommandTypefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport distributorimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Commands')
class HouseholdCommandTuning:
    HOUSEHOLD_NEIGHBOR_MOVED_IN_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        The notification that is displayed when a household is moved in next\n        door.\n        Passed in token is the household name of the household that ends up\n        living in the house.\n        ')

@sims4.commands.Command('households.list')
def list_households(household_id:int=None, _connection=None):
    household_manager = services.household_manager()
    output = sims4.commands.Output(_connection)
    output('Household report:')
    if household_id is not None:
        households = (household_manager.get(household_id),)
    else:
        households = household_manager.get_all()
    for household in households:
        output('{}, {} Sims'.format(str(household), len(household)))
        for sim_info in household.sim_info_gen():
            if sim_info.is_instanced(allow_hidden_flags=0):
                output(' Instanced: {}'.format(sim_info))
            elif sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                output(' Hidden: {}'.format(sim_info))
            else:
                output(' Off lot: {}'.format(sim_info))

@sims4.commands.Command('households.modify_funds', command_type=sims4.commands.CommandType.Automation)
def modify_household_funds(amount:int, household_id:int=0, reason=None, _connection=None):
    if reason is None:
        reason = Consts_pb2.TELEMETRY_MONEY_CHEAT
    if household_id == 0:
        tgt_client = services.client_manager().get(_connection)
        if tgt_client is not None:
            household = tgt_client.household
    else:
        household = services.household_manager().get(household_id)
    if household is not None:
        if amount > 0:
            household.funds.add(amount, reason)
        else:
            household.funds.try_remove(-amount, reason)
    else:
        sims4.commands.output('Invalid Household id: {}'.format(household_id), _connection)

@sims4.commands.Command('households.get_value', command_type=sims4.commands.CommandType.DebugOnly)
def get_value(household_id:int, billable:bool=False, _connection=None):
    household = services.household_manager().get(household_id)
    if household is not None:
        value = household.household_net_worth(billable=billable)
        sims4.commands.output('Simoleon value of household {} is {}.'.format(household, value), _connection)
    else:
        sims4.commands.output('Invalid Household id: {}'.format(household_id), _connection)

@sims4.commands.Command('households.get_household_display_info', command_type=sims4.commands.CommandType.Automation)
def get_household_display_info(lot_id:int, _connection=None):
    persistence_service = services.get_persistence_service()
    household_display_info = UI_pb2.HouseholdDisplayInfo()
    household_id = persistence_service.get_household_id_from_lot_id(lot_id)
    if household_id is None:
        household_id = 0
    household = services.household_manager().get(household_id)
    if household is None:
        household_id = 0
    else:
        household_display_info.at_home_sim_ids.extend(household.get_sims_at_home_not_instanced_not_busy())
    household_display_info.household_id = household_id
    household_display_info.lot_id = lot_id
    op = shared_messages.create_message_op(household_display_info, Consts_pb2.MSG_UI_HOUSEHOLD_DISPLAY_INFO)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('households.merge_with_active', command_type=sims4.commands.CommandType.Live)
def merge_with_active(household_id:int, _connection=None):
    client = services.client_manager().get(_connection)
    household = client.household
    household.merge(household_id)

@sims4.commands.Command('households.merge_with_neighbor', command_type=sims4.commands.CommandType.Live)
def merge_with_neighbor(zone_id:int, merge:bool, household_id:int, _connection=None):
    venue_tuning = services.venue_service().get_venue_tuning(zone_id)
    if venue_tuning is None:
        return
    if venue_tuning.is_residential or not venue_tuning.is_university_housing:
        return
    old_household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
    household_manager = services.household_manager()
    if old_household_id is not None:
        old_household = household_manager.get(old_household_id)
    else:
        old_household = None
    if merge:
        if old_household is None:
            logger.error('Trying to merge None old household with a new one of household id {}.', household_id, owner='jjacobson')
            return
        old_household.merge(household_id, should_spawn=zone_id == services.current_zone_id(), selectable=False)
        notification_household = old_household
    else:
        if old_household is not None:
            old_household.clear_household_lot_ownership()
        new_household = household_manager.load_household(household_id)
        new_household.move_into_zone(zone_id)
        notification_household = new_household
    zone_name = ''
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is not None:
            zone_name = zone_data.name
    dialog = HouseholdCommandTuning.HOUSEHOLD_NEIGHBOR_MOVED_IN_NOTIFICATION(None)
    dialog.show_dialog(additional_tokens=(notification_household.name, zone_name))

@sims4.commands.Command('households.fill_visible_commodities_world', command_type=sims4.commands.CommandType.Cheat)
def set_visible_commodities_to_best_value_for_world(opt_object:OptionalTargetParam=None, _connection=True):
    for sim_info in services.sim_info_manager().objects:
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=True)

@sims4.commands.Command('households.fill_visible_commodities_household', command_type=sims4.commands.CommandType.Cheat)
def set_visible_commodities_to_best_value_for_household(opt_object:OptionalTargetParam=None, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim
    household = active_sim_info.household
    for sim_info in household.sim_info_gen():
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=True)

def _set_motive_decay(sim_infos, enable=True):
    for sim_info in sim_infos:
        for commodity in sim_info.commodity_tracker.get_all_commodities():
            if commodity.is_visible:
                current_decay_modifier = commodity.get_decay_rate_modifier()
                if enable:
                    if current_decay_modifier == 0:
                        commodity.remove_decay_rate_modifier(0)
                        commodity.send_commodity_progress_msg()
                        if not current_decay_modifier == 0:
                            commodity.add_decay_rate_modifier(0)
                            commodity.send_commodity_progress_msg()
                elif not current_decay_modifier == 0:
                    commodity.add_decay_rate_modifier(0)
                    commodity.send_commodity_progress_msg()

@sims4.commands.Command('households.enable_household_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def enable_household_motive_decay(opt_object:OptionalTargetParam=None, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim
    household = active_sim_info.household
    _set_motive_decay(household.sim_info_gen(), True)

@sims4.commands.Command('households.disable_household_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def disable_household_motive_decay(opt_object:OptionalTargetParam=None, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim
    household = active_sim_info.household
    _set_motive_decay(household.sim_info_gen(), False)

@sims4.commands.Command('households.enable_world_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def enable_world_motive_decay(opt_object:OptionalTargetParam=None, _connection=True):
    _set_motive_decay(services.sim_info_manager().objects, True)

@sims4.commands.Command('households.disable_world_motive_decay', command_type=sims4.commands.CommandType.Cheat)
def disable_world_motive_decay(opt_object:OptionalTargetParam=None, _connection=True):
    _set_motive_decay(services.sim_info_manager().objects, False)

@sims4.commands.Command('households.collection_view_update', command_type=sims4.commands.CommandType.Live)
def collection_view_update(collection_id:int=0, _connection=None):
    active_sim_info = services.client_manager().get(_connection).active_sim_info
    active_sim_info.household.collection_tracker.mark_as_viewed(collection_id)

@sims4.commands.Command('household.split', command_type=CommandType.Live)
def household_split(sourceHouseholdId:int, targetHouseholdId:int=0, cancelable:bool=True, allow_sim_transfer:bool=True, selected_sim_ids=[], destination_zone_id:int=0, callback_command_name=None, lock_preselected_sims=True):
    if destination_zone_id and not targetHouseholdId:
        logger.error('HouseholdSplit: Target household required when specifying a destination zone.', owner='bnguyen')
    op = SplitHouseholdDialog(sourceHouseholdId, targetHouseholdId, cancelable=cancelable, allow_sim_transfer=allow_sim_transfer, selected_sim_ids=selected_sim_ids, destination_zone_id=destination_zone_id, callback_command_name=callback_command_name, lock_preselected_sims=lock_preselected_sims)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('household.split_do_command', command_type=CommandType.Live)
def household_split_do_command(sourceHouseholdId:int, selected_sim_id:int, lock_preselected_sims:bool=True):
    household_split(sourceHouseholdId, selected_sim_ids=(selected_sim_id,), lock_preselected_sims=lock_preselected_sims)

@sims4.commands.Command('household.transfer_sims', command_type=CommandType.Live)
def household_transfer_sims_live_mode(transfer_sims_data:str, _connection=None):
    proto = UI_pb2.SplitHousehold()
    text_format.Merge(transfer_sims_data, proto)
    household_manager = services.household_manager()
    if proto.source_household_id == 0:
        tgt_client = services.client_manager().get(_connection)
        if tgt_client is None:
            return False
        account = tgt_client.account
        source_household = household_manager.create_household(account, starting_funds=0)
        _name_new_family(source_household, proto.to_source_sims)
        source_household.save_data()
        proto.source_household_id = source_household.id
    else:
        source_household = household_manager.get(proto.source_household_id)
        if source_household.name == '':
            _name_new_family(source_household, proto.to_source_sims)
    if source_household is None:
        sims4.commands.output('Source Household is not found. ID = {}'.format(proto.source_household_id), _connection)
        return
    if proto.target_household_id == 0:
        tgt_client = services.client_manager().get(_connection)
        if tgt_client is None:
            return False
        account = tgt_client.account
        target_household = household_manager.create_household(account, starting_funds=0)
        _name_new_family(target_household, proto.to_target_sims)
        target_household.save_data()
        proto.target_household_id = target_household.id
    else:
        target_household = household_manager.get(proto.target_household_id)
        if target_household.name == '':
            _name_new_family(target_household, proto.to_target_sims)
    if target_household is None:
        sims4.commands.output('Target Household is not found. ID = {}'.format(proto.target_household_id), _connection)
    if _is_complete_transfer(source_household, proto.to_target_sims) and source_household.home_zone_id != 0:
        household_manager.add_pending_transfer(source_household.id, proto)
        save_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        services.current_zone().save_zone(save_data_msg)
        if services.current_zone_id() == source_household.home_zone_id:
            proto.target_funds_difference += _get_household_home_lot_furnishings_value(source_household)
        _move_household_out_of_lot(source_household, proto)
        return
    if _is_complete_transfer(target_household, proto.to_source_sims) and target_household.home_zone_id != 0:
        household_manager.add_pending_transfer(target_household.id, proto)
        save_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        services.current_zone().save_zone(save_data_msg)
        if services.current_zone_id() == target_household.home_zone_id:
            proto.source_funds_difference += _get_household_home_lot_furnishings_value(target_household)
        _move_household_out_of_lot(target_household, proto)
        return
    _transfer_sims_main(proto, source_household, target_household)

def _transfer_sims_main(proto, source_household, target_household):
    _switch_sims(source_household, target_household, proto.to_target_sims)
    _switch_sims(target_household, source_household, proto.to_source_sims)
    household_manager = services.household_manager()
    if not source_household:
        household_manager.transfer_household_inventory(source_household, target_household)
        _reset_active_lot_object_owner_ids(source_household)
    elif not target_household:
        household_manager.transfer_household_inventory(target_household, source_household)
    if source_household.is_player_household is not target_household.is_player_household:
        if source_household.is_player_household or proto.to_source_sims:
            source_household.set_played_household(True)
        elif target_household.is_player_household or proto.to_target_sims:
            target_household.set_played_household(True)
    modify_household_funds(proto.target_funds_difference, target_household.id, Consts_pb2.FUNDS_SPLIT_HOUSEHOLD)
    modify_household_funds(proto.source_funds_difference, source_household.id, Consts_pb2.FUNDS_SPLIT_HOUSEHOLD)
    if proto.funds > 0:
        if not source_household:
            modify_household_funds(proto.funds, target_household.id, Consts_pb2.FUNDS_LOT_SELL)
        elif not target_household:
            modify_household_funds(proto.funds, source_household.id, Consts_pb2.FUNDS_LOT_SELL)
    if not target_household.destroy_household_if_empty():
        sim_info_manager = services.sim_info_manager()
        for sim_id in proto.to_target_sims:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is not None and proto.destination_zone_id > 0:
                if sim_info.is_instanced():
                    sim_info.inject_into_inactive_zone(proto.destination_zone_id, start_away_actions=False, skip_instanced_check=True, skip_daycare=True)
                    sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                    sim.reset(ResetReason.RESET_EXPECTED, cause='Sim split into new family and injected into that zone.')
                else:
                    sim_info.inject_into_inactive_zone(proto.destination_zone_id)
        if target_household.home_zone_id == 0:
            if proto.destination_zone_id != 0:
                target_household.move_into_zone(proto.destination_zone_id)
                sim_id = proto.to_target_sims[0]
                _activate_sims_family(sim_id, target_household.id)
            else:
                _enter_move_out_mode(target_household.id, is_in_game_evict=True)
        elif proto.to_target_sims:
            sim_id = proto.to_target_sims[0]
            _activate_sims_family(sim_id, target_household.id)
    op = SendUIMessage('LiveModeSplitDone')
    Distributor.instance().add_op_with_no_owner(op)

def _switch_sims(source_household, target_household, sim_list):
    household_manager = services.household_manager()
    sim_info_manager = services.sim_info_manager()
    active_household = services.active_household()
    for sim_id in sim_list:
        sim_info = sim_info_manager.get(sim_id)
        if sim_info is None:
            pass
        else:
            household_manager.switch_sim_from_household_to_target_household(sim_info, source_household, target_household, destroy_if_empty_household=False)
            if target_household is active_household and not sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS):
                SimSpawner.spawn_sim(sim_info)

@sims4.commands.Command('household.move_in_move_out', command_type=CommandType.Live)
def trigger_move_in_move_out(_connection=None, is_in_game_evict=None):
    _enter_move_out_mode(is_in_game_evict=is_in_game_evict)

def _enter_move_out_mode(moving_household_id=None, is_in_game_evict=None):
    msg = InteractionOps_pb2.MoveInMoveOutInfo()
    if moving_household_id is not None:
        msg.moving_family_id = moving_household_id
    if is_in_game_evict is not None:
        msg.is_in_game_evict = is_in_game_evict
    distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_MOVE_IN_MOVE_OUT, msg)

def _activate_sims_family(sim_id, household_id):
    sim_info_manager = services.sim_info_manager()
    sim_info = sim_info_manager.get(sim_id)
    if sim_info is not None:
        sim_info.send_travel_live_to_nhd_to_live_op(household_id)

def _move_household_out_of_lot(household, transfer_sims_data):
    zone_id = household.home_zone_id
    msg = MoveInMoveOut_pb2.MoveInMoveOutData()
    msg.zone_src = zone_id
    msg.zone_dst = 0
    msg.move_out_data_src.sell_furniture = transfer_sims_data.bSellFurniture
    msg.move_out_data_src.delta_funds = transfer_sims_data.funds
    msg.notify_gameplay = True
    distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_MOVE_FAMILY_OUT, msg)

def _is_complete_transfer(household, transfer_sims):
    remaining_sims = [x for x in household if x.id not in transfer_sims]
    if household and remaining_sims:
        return False
    return True

@sims4.commands.Command('household.handle_updated_family', command_type=CommandType.Live)
def handle_family_updated(household_id:int):
    household_manager = services.household_manager()
    pending_removal_data = household_manager.get_pending_transfer(household_id)
    if pending_removal_data is None:
        return
    source_household = household_manager.get(pending_removal_data.source_household_id)
    if source_household is None:
        logger.error('Pending removal data is missing a valid source_household_id. Something went wrong and so we are aborting')
        return
    target_household = household_manager.get(pending_removal_data.target_household_id)
    if target_household is None:
        logger.error('Pending removal data is missing a valid target_household_id. Something went wrong and so we are aborting')
        return
    _transfer_sims_main(pending_removal_data, source_household, target_household)

def _name_new_family(household, sims_to_transfer):
    sim_info_manager = services.sim_info_manager()
    if len(sims_to_transfer) == 0:
        logger.error("Creating a new household during a split without any Sims to move into that household. This shouldn't happen.")
        return
    sim_info = sim_info_manager.get(sims_to_transfer[0])
    household.name = sim_info.last_name

def _reset_active_lot_object_owner_ids(household):
    object_manager = services.object_manager()
    for obj in object_manager.valid_objects():
        if obj.household_owner_id == household.id:
            obj.set_household_owner_id(0)

def _get_household_home_lot_furnishings_value(household):
    zone = services.get_zone(household.home_zone_id, allow_uninstantiated_zones=True)
    lot_data = zone.lot
    return lot_data.furnished_lot_value - lot_data.unfurnished_lot_value

def is_zone_occupied(zone_id):
    target_household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
    return target_household_id is not None and target_household_id != 0
