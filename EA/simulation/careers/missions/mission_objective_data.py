import servicesimport sims4.logfrom collections import defaultdictfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom event_testing.weighted_objectives import WeightedObjectivesfrom objects.object_state_utils import ObjectStateHelperfrom sims4 import randomfrom sims4.tuning.tunable import AutoFactoryInit, Tunable, HasTunableSingletonFactory, TunableMapping, TunableList, OptionalTunable, TunableLotDescriptionfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestListfrom world.lot import get_lot_id_from_instance_idlogger = sims4.log.Logger('MissionObjectiveData', default_owner='trevor')
class MissionObjectiveData(HasTunableSingletonFactory, AutoFactoryInit):
    MISSION_OBJECTIVE_INVALID = 0
    MISSION_OBJECTIVE_NOT_ACTIVE = 1
    MISSION_OBJECTIVE_ACTIVE = 2
    MISSION_OBJECTIVE_COMPLETE = 3
    FACTORY_TUNABLES = {'weighted_objectives': WeightedObjectives(description='\n            A list of tested, weighted objectives. A set of tests are run against \n            the active Sim. If the tests pass, this objective and the weight are \n            added to a list for randomization. Only one Objective is selected.\n            '), 'completes_mission': Tunable(description='\n            If checked, completion of this Objective will also complete the\n            Mission.\n            ', tunable_type=bool, default=False), 'requires_previous_objective_complete': Tunable(description='\n            If checked, this objective can only be completed if the previous\n            objective in the Mission has been completed.\n            ', tunable_type=bool, default=False), 'object_state_changes_on_active': OptionalTunable(description='\n            If enabled, allows setting the tuned state on all matching objects\n            when this objective is active and able to be completed.\n            ', tunable=ObjectStateHelper.TunableFactory(description='\n                The objects and states to set on them.\n                ')), 'object_state_changes_on_complete': OptionalTunable(description='\n            If enabled, allows setting the tuned state on all matching objects\n            when this objective is complete.\n            ', tunable=ObjectStateHelper.TunableFactory(description='\n                The objects and states to set on them.\n                ')), 'lot_specific_situations': TunableMapping(description='\n            A mapping of Lots to Situations that should start when this \n            Objective is active and the Sim has loaded into the Zone for the\n            tuned Lot.\n            ', key_name='Lot Description', value_name='Situations', key_type=TunableLotDescription(description='\n                The lot this situation should start in.\n                '), value_type=TunableList(description='\n                The list of Situations to start when the Sim has loaded into the\n                Zone for the tuned Lot Description.\n                ', tunable=Situation.TunableReference(description='\n                    A Situation to start.\n                    ')))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_objective = None
        self._state = self.MISSION_OBJECTIVE_INVALID
        self._created_situations = defaultdict(list)

    @property
    def selected_objective(self):
        return self._selected_objective

    @property
    def is_active(self):
        return self._state == self.MISSION_OBJECTIVE_ACTIVE

    @property
    def is_complete(self):
        return self._state == self.MISSION_OBJECTIVE_COMPLETE

    @property
    def is_valid(self):
        return not self.is_invalid

    @property
    def is_invalid(self):
        return self._state == self.MISSION_OBJECTIVE_INVALID

    def initialize_mission_objective(self, sim_info, objectives_to_ignore=()):
        potential_objectives = []
        self._created_situations = defaultdict(list)
        resolver = SingleSimResolver(sim_info)
        for weighted_objective in self.weighted_objectives:
            if weighted_objective.objective in objectives_to_ignore:
                pass
            elif weighted_objective.tests.run_tests(resolver):
                potential_objectives.append((weighted_objective.weight, weighted_objective.objective))
        if not potential_objectives:
            self._state = self.MISSION_OBJECTIVE_INVALID
            return
        self._state = self.MISSION_OBJECTIVE_NOT_ACTIVE
        self._selected_objective = random.weighted_random_item(potential_objectives)
        if not self.requires_previous_objective_complete:
            self.activate_mission_objective(sim_info)

    def activate_mission_objective(self, sim_info):
        self._state = self.MISSION_OBJECTIVE_ACTIVE
        self._activate_object_states(sim_info)
        self._start_situations()

    def _activate_object_states(self, sim_info):
        if self._state != self.MISSION_OBJECTIVE_ACTIVE:
            return
        if self.object_state_changes_on_active:
            self.object_state_changes_on_active.execute_helper(sim_info)

    def _start_situations(self):
        if self._state != self.MISSION_OBJECTIVE_ACTIVE:
            return
        situation_manager = services.get_zone_situation_manager()
        for (lot_desc, situations) in self.lot_specific_situations.items():
            lot_id = get_lot_id_from_instance_id(lot_desc)
            zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
            if zone_id == services.current_zone_id() and zone_id not in self._created_situations:
                for situation in situations:
                    situation_id = situation_manager.create_situation(situation, creation_source=str(self._selected_objective), guest_list=SituationGuestList(invite_only=True), user_facing=False)
                    if situation_id is not None:
                        self._created_situations[zone_id].append(situation_id)

    def complete_mission_objective(self, sim_info):
        if self.object_state_changes_on_complete:
            self.object_state_changes_on_complete.execute_helper(sim_info)
        self._state = self.MISSION_OBJECTIVE_COMPLETE

    def on_zone_load(self, sim_info):
        self._start_situations()
        self._activate_object_states(sim_info)

    def save(self, proto_data):
        proto_data.state = self._state
        proto_data.objective_id = 0 if self.is_invalid else self.selected_objective.guid64
        proto_data.ClearField('created_situations')
        if self._created_situations:
            for (zone_id, situation_ids) in self._created_situations.items():
                with ProtocolBufferRollback(proto_data.created_situations) as created_situation_data:
                    created_situation_data.zone_id = zone_id
                    created_situation_data.situation_ids.extend(situation_ids)

    def load(self, proto_data):
        objective = services.objective_manager().get(proto_data.objective_id)
        if objective is None:
            logger.error('Trying to load an objective for Mission {} but the Objective can not be found. The Objective will be ignored for this Mission.', self)
            self._state = self.MISSION_OBJECTIVE_INVALID
            return
        self._selected_objective = objective
        self._state = proto_data.state
        self._created_situations = defaultdict(list)
        for created_situation_data in proto_data.created_situations:
            self._created_situations[created_situation_data.zone_id].extend(created_situation_data.situation_ids)
