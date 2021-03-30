from distributor.ops import AskAboutClubsDialogfrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom organizations.organization_enums import OrganizationStatusEnumfrom server_commands.argument_helpers import TunableInstanceParam, RequiredTargetParamfrom sims4.commands import CommandTypeimport servicesimport sims4logger = sims4.log.Logger('OrganizationCommands', default_owner='shipark')
@sims4.commands.Command('ui.leave_organization', command_type=sims4.commands.CommandType.Live)
def ui_leave_organization(org_id:int, _connection=None):
    active_sim = services.get_active_sim()
    if active_sim is None:
        logger.error('Active Sim is None and cannot be.')
        return False
    org_tracker = active_sim.sim_info.organization_tracker
    if org_tracker is None:
        logger.error("({})'s organization tracker is None and cannot be.", active_sim.full_name)
        return False
    org_tracker.leave_organization(org_id)
    return org_tracker.get_organization_status(org_id) != OrganizationStatusEnum.ACTIVE

@sims4.commands.Command('drama.travel_to_event_zone', command_type=sims4.commands.CommandType.Live)
def travel_to_event_zone(drama_node:TunableInstanceParam(sims4.resources.Types.DRAMA_NODE), _connection=None):
    if drama_node.drama_node_type == DramaNodeType.FESTIVAL:
        drama_node.travel_to_festival()
        return
    if drama_node.drama_node_type == DramaNodeType.VENUE_EVENT:
        drama_scheduler = services.drama_scheduler_service()
        if drama_scheduler is None:
            logger.error("Failed to run 'travel_to_event_zone' for ({}) because drama scheduler is not initiated.", str(drama_node))
        active_drama_nodes = [node for node in drama_scheduler.active_nodes_gen() if node.guid64 == drama_node.guid64]
        if not active_drama_nodes:
            logger.error("Failed to run 'travel_to_event_zone' for ({}), there is no event of that type active.")
            return
        active_drama_nodes[0].travel_to_venue()
        return
    logger.error("Unsupported drama node type({}) for 'travel to event zone. Travel cancelled for ({})", str(drama_node.drama_node_type), str(drama_node))

@sims4.commands.Command('orgs.show_orgs_events_dialog', command_type=CommandType.Live)
def show_orgs_events_dialog(sim:RequiredTargetParam, _connection=None):
    sim_info = sim.get_target(manager=services.sim_info_manager())
    if sim_info is None:
        sims4.commands.output('Sim with id {} is not found to show organizations events dialog.'.format(sim.target_id), _connection)
        return False
    op = AskAboutClubsDialog(sim_info.id, show_orgs=True)
    Distributor.instance().add_op_with_no_owner(op)
