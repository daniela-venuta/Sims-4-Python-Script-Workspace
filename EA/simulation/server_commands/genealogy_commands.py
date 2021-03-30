from collections import namedtuplefrom protocolbuffers import DistributorOps_pb2from distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom interactions.utils.death import DeathTypefrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, RequiredTargetParamfrom sims.genealogy_tracker import FamilyRelationshipIndex, genealogy_caching, FamilyRelationshipTuningfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_types import Age, Genderfrom sims.sim_spawner import SimCreator, SimSpawnerimport servicesimport sims4.commands
@sims4.commands.Command('genealogy.print')
def genalogy_print(sim_id:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        return False
    genealogy = sim.sim_info.genealogy
    genealogy.log_contents()
    return True

@sims4.commands.Command('genealogy.generate_dynasty', command_type=sims4.commands.CommandType.Automation)
def genealogy_random_generate(sim_id:OptionalTargetParam=None, generations:int=4, set_to_min_lod=False, _connection=None):
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        return False

    def add_parents(child, generation=0):
        if generation >= generations:
            return
        sim_creators = (SimCreator(gender=Gender.MALE, age=Age.ADULT, last_name=child.last_name), SimCreator(gender=Gender.FEMALE, age=Age.ADULT))
        (sim_info_list, _) = SimSpawner.create_sim_infos(sim_creators, account=sim.account, zone_id=sim.zone_id, creation_source='cheat: genealogy.generate_dynasty')
        sim_info_list[0].death_tracker.set_death_type(DeathType.get_random_death_type())
        sim_info_list[1].death_tracker.set_death_type(DeathType.get_random_death_type())
        if set_to_min_lod:
            sim_info_list[0].request_lod(SimInfoLODLevel.MINIMUM)
            sim_info_list[1].request_lod(SimInfoLODLevel.MINIMUM)
        child.set_and_propagate_family_relation(FamilyRelationshipIndex.FATHER, sim_info_list[0])
        child.set_and_propagate_family_relation(FamilyRelationshipIndex.MOTHER, sim_info_list[1])
        add_parents(sim_info_list[0], generation=generation + 1)
        add_parents(sim_info_list[1], generation=generation + 1)

    add_parents(sim.sim_info)
    sims4.commands.output('Dynasty created for {}'.format(sim), _connection)
    return True

@sims4.commands.Command('genealogy.find_relation')
def genalogy_relation(x_sim:RequiredTargetParam, y_sim:RequiredTargetParam, _connection=None):
    output = sims4.commands.Output(_connection)
    sim_x = x_sim.get_target()
    bit = None
    if sim_x is not None:
        bit = sim_x.sim_info.genealogy.get_family_relationship_bit(y_sim.target_id, output)
    return bit is not None
FamilyTreeNode = namedtuple('FamilyTreeNode', ('sim_id', 'proto_node', 'antecedent_depth', 'descendant_depth', 'extended_info_depth', 'include_spouse', 'step_depth'))
@sims4.commands.Command('genealogy.show_family_tree', command_type=sims4.commands.CommandType.Live)
def genealogy_show_family_tree(sim_info_id:int, antecedent_depth:int=8, descendant_depth:int=2, _connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim_info_manager = services.sim_info_manager()
    family_tree_msg = DistributorOps_pb2.ShowFamilyTree()
    sims_to_look_at = []
    additional_sims_to_look_at = []
    sims_looked_at = set()
    sims_to_look_at.append(FamilyTreeNode(sim_id=sim_info_id, proto_node=family_tree_msg.root, antecedent_depth=antecedent_depth, descendant_depth=descendant_depth, extended_info_depth=2, include_spouse=True, step_depth=2))
    with genealogy_caching():
        automation_output('FamilyTreeInfo; Status:Begin')
        while True:
            if sims_to_look_at or additional_sims_to_look_at:
                if sims_to_look_at:
                    family_tree_node = sims_to_look_at.pop(0)
                else:
                    family_tree_node = additional_sims_to_look_at.pop(0)
                family_tree_node.proto_node.sim_id = family_tree_node.sim_id
                if family_tree_node.sim_id in sims_looked_at:
                    pass
                else:
                    sims_looked_at.add(family_tree_node.sim_id)
                    sim_info = sim_info_manager.get(family_tree_node.sim_id)
                    if sim_info is None:
                        pass
                    else:
                        automation_output('FamilyTreeInfo; Status:Data, Sim:{}, AntDepth:{}, DesDepth:{}, Gender:{}'.format(family_tree_node.sim_id, family_tree_node.antecedent_depth, family_tree_node.descendant_depth, sim_info.gender))
                        if family_tree_node.include_spouse:
                            spouse_id = sim_info.spouse_sim_id
                            if spouse_id:
                                additional_sims_to_look_at.append(FamilyTreeNode(sim_id=spouse_id, proto_node=family_tree_node.proto_node.spouse, antecedent_depth=0, descendant_depth=1 if family_tree_node.step_depth else 0, extended_info_depth=0, include_spouse=False, step_depth=0))
                        if family_tree_node.antecedent_depth:
                            for parent_id in sim_info.genealogy.get_parent_sim_ids_gen():
                                with ProtocolBufferRollback(family_tree_node.proto_node.parents) as parent_family_tree_node:
                                    sims_to_look_at.append(FamilyTreeNode(sim_id=parent_id, proto_node=parent_family_tree_node, antecedent_depth=family_tree_node.antecedent_depth - 1, descendant_depth=1 if family_tree_node.extended_info_depth else 0, extended_info_depth=family_tree_node.extended_info_depth - 1 if family_tree_node.extended_info_depth else 0, include_spouse=True, step_depth=family_tree_node.step_depth - 1 if family_tree_node.step_depth else 0))
                        if family_tree_node.descendant_depth:
                            for child_id in sim_info.genealogy.get_children_sim_ids_gen():
                                with ProtocolBufferRollback(family_tree_node.proto_node.children) as child_family_tree_node:
                                    sims_to_look_at.append(FamilyTreeNode(sim_id=child_id, proto_node=child_family_tree_node, antecedent_depth=1 if family_tree_node.extended_info_depth else 0, descendant_depth=descendant_depth - 1, extended_info_depth=0, include_spouse=True, step_depth=0))
                        if not family_tree_node.extended_info_depth:
                            if family_tree_node.include_spouse:
                                for relationship in sim_info.relationship_tracker:
                                    if family_tree_node.extended_info_depth:
                                        if relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.SIBLING_RELATIONSHIP_BIT):
                                            with ProtocolBufferRollback(family_tree_node.proto_node.siblings) as sibling_family_tree_node:
                                                additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=sibling_family_tree_node, antecedent_depth=1, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                                        elif sim_info_id == family_tree_node.sim_id and relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.GRANDPARENT_RELATIONSHIP_BIT):
                                            with ProtocolBufferRollback(family_tree_node.proto_node.grandparents) as grandparent_family_tree_node:
                                                additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=grandparent_family_tree_node, antecedent_depth=0, descendant_depth=1, extended_info_depth=0, include_spouse=True, step_depth=0))
                                        elif relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.GRANDCHILD_RELATIONSHIP_BIT):
                                            with ProtocolBufferRollback(family_tree_node.proto_node.grandchildren) as grandchild_family_tree_node:
                                                additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=grandchild_family_tree_node, antecedent_depth=1, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                                    if family_tree_node.include_spouse:
                                        if relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.DIVORCED_SPOUSE_RELATIONSHIP_BIT):
                                            with ProtocolBufferRollback(family_tree_node.proto_node.divorced_spouses) as divorced_spouse_family_tree_node:
                                                additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=divorced_spouse_family_tree_node, antecedent_depth=0, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                                        if relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.DEAD_SPOUSE_RELATIONSHIP_BIT):
                                            with ProtocolBufferRollback(family_tree_node.proto_node.dead_spouses) as dead_spouse_family_tree_node:
                                                additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=dead_spouse_family_tree_node, antecedent_depth=0, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                        for relationship in sim_info.relationship_tracker:
                            if family_tree_node.extended_info_depth:
                                if relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.SIBLING_RELATIONSHIP_BIT):
                                    with ProtocolBufferRollback(family_tree_node.proto_node.siblings) as sibling_family_tree_node:
                                        additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=sibling_family_tree_node, antecedent_depth=1, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                                elif sim_info_id == family_tree_node.sim_id and relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.GRANDPARENT_RELATIONSHIP_BIT):
                                    with ProtocolBufferRollback(family_tree_node.proto_node.grandparents) as grandparent_family_tree_node:
                                        additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=grandparent_family_tree_node, antecedent_depth=0, descendant_depth=1, extended_info_depth=0, include_spouse=True, step_depth=0))
                                elif relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.GRANDCHILD_RELATIONSHIP_BIT):
                                    with ProtocolBufferRollback(family_tree_node.proto_node.grandchildren) as grandchild_family_tree_node:
                                        additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=grandchild_family_tree_node, antecedent_depth=1, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                            if family_tree_node.include_spouse:
                                if relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.DIVORCED_SPOUSE_RELATIONSHIP_BIT):
                                    with ProtocolBufferRollback(family_tree_node.proto_node.divorced_spouses) as divorced_spouse_family_tree_node:
                                        additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=divorced_spouse_family_tree_node, antecedent_depth=0, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
                                if relationship.has_bit(sim_info.sim_id, FamilyRelationshipTuning.DEAD_SPOUSE_RELATIONSHIP_BIT):
                                    with ProtocolBufferRollback(family_tree_node.proto_node.dead_spouses) as dead_spouse_family_tree_node:
                                        additional_sims_to_look_at.append(FamilyTreeNode(sim_id=relationship.get_other_sim_id(sim_info_id), proto_node=dead_spouse_family_tree_node, antecedent_depth=0, descendant_depth=0, extended_info_depth=0, include_spouse=False, step_depth=0))
        automation_output('FamilyTreeInfo; Status:End')
    distributor = Distributor.instance()
    family_tree_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SHOW_FAMILY_TREE, family_tree_msg)
    distributor.add_op_with_no_owner(family_tree_op)
