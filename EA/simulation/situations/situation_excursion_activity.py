import servicesimport sims4from sims4.random import pop_weightedfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableVariant, TunableReference, TunableList, TunableTuple, Tunable, TunableEnumEntry, TunableLotDescription, TunableMapping, OptionalTunable, HasTunableFactory, AutoFactoryInit, HasTunableSingletonFactory, TunableSimMinute, TunableIntervalfrom sims4.tuning.tunable_base import GroupNamesfrom situations.custom_states.custom_states_common_tuning import RandomWeightedSituationStateKey, TimeBasedSituationStateKeyfrom situations.custom_states.custom_states_situation_state_excursion import TunableExcursionSituationStateSnippetfrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom situations.situation_goal_set import SituationGoalSetfrom situations.situation_goal_tuning_mixin import SituationGoalTuningMixinfrom situations.situation_job import SituationJobRewardfrom situations.situation_level_data_tuning_mixin import SituationLevelDataTuningMixinfrom situations.situation_scoring_mixin import SituationScoringMixinfrom situations.situation_types import SituationMedalfrom snippets import define_snippet, EXCURSION_ACTIVITYfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog import UiDialogOkCancelfrom world.lot import get_lot_id_from_instance_idlogger = sims4.log.Logger('Excursions', default_owner='miking')
class ActivitySetup(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'conditional_layers': TunableList(description='\n            Layers to apply when this setup is active.\n            ', tunable=TunableReference(description='\n                The Conditional Layer that will be loaded.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)), unique_entries=True), 'item_modifications': ModifyAllLotItems.TunableFactory(description='\n            State changes to apply to objects on the lot when this setup is active.\n            '), 'additional_goal_chains': TunableList(description='\n            Goal sets to include when this setup is active. These are used in addition to the minor_goal_chains\n            defined on the situation.\n            ', tunable=SituationGoalSet.TunableReference(), tuning_group=GroupNames.GOALS)}

class ActivitySetupCluster(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'num_setups': TunableInterval(description='\n            How many setups to apply.\n            ', tunable_type=int, default_lower=1, default_upper=1, minimum=0), 'setups': TunableMapping(description='\n            List of setups to choose from.\n            ', key_name='Setup Key', key_type=Tunable(description='\n                The key of this activity setup. Do not change once the setup is in use.\n                ', tunable_type=str, default=None), value_name='Activity Setup', value_type=TunableTuple(setup=ActivitySetup.TunableFactory(description='\n                    Tuned activity setup.\n                    '), weight=TunableMultiplier.TunableFactory(description='\n                    A weight with testable multipliers that is used to \n                    determine how likely this setup is to be picked when \n                    selecting randomly.\n                    '))), 'startup_actions': ModifyAllLotItems.TunableFactory(description='\n            State changes to apply to objects to reset them to their initial states before any ActivitySetup is\n            applied.\n            ')}

class ExcursionActivity(SituationGoalTuningMixin, SituationLevelDataTuningMixin, SituationScoringMixin, HasTunableFactory, AutoFactoryInit):

    class ExcursionLocationLot(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'lot': TunableLotDescription(description='\n                Lot where this activity takes place.\n                ')}

        def __call__(self):
            possible_zones = []
            lot_id = get_lot_id_from_instance_id(self.lot)
            if lot_id:
                zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
                if zone_id:
                    possible_zones.append(zone_id)
            return possible_zones

    class ExcursionLocationVenue(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'venue_type': TunableReference(description='\n                Venue type where this activity takes place.\n                ', manager=services.venue_manager())}

        def __call__(self):
            possible_zones = []
            venue_service = services.current_zone().venue_service
            possible_zones.extend(venue_service.get_zones_for_venue_type_gen(self.venue_type))
            return possible_zones

    FACTORY_TUNABLES = {'excursion_location': OptionalTunable(description='\n            Where this excursion activity takes place (lot or venue type).\n            If not specified, the player will remain in their current location.\n            ', tunable=TunableVariant(description='\n                Where this excursion activity takes place (lot or venue type).\n                ', lot=ExcursionLocationLot.TunableFactory(), venue_type=ExcursionLocationVenue.TunableFactory(), default='lot')), 'next_activity': TunableList(description='\n            Which activity(ies) to advance to next (if the required level is met).\n            ', tunable=TunableTuple(description='\n                Pair of next activity keys and tunable weights.\n                ', activity_key=Tunable(description='\n                    The key of the activity.\n                    ', tunable_type=str, default=None), weight=TunableMultiplier.TunableFactory(description='\n                    A weight with testable multipliers that is used to \n                    determine how likely this entry is to be picked when \n                    selecting randomly.\n                    '))), 'next_activity_required_level': TunableEnumEntry(description='\n            Minimum level the excursion must reach in order to advance to the next activity.\n            ', tunable_type=SituationMedal, default=SituationMedal.BRONZE), '_situation_states': TunableMapping(description='\n            A tunable mapping between situation state keys and situation states.\n            ', key_name='Situation State Key', key_type=Tunable(description='\n                The key of this situation state.  This key will be used when attempting to transition between different\n                situation states.\n                ', tunable_type=str, default=None), value_name='Situation State', value_type=TunableExcursionSituationStateSnippet(description='\n                The situation state that is tied to this key.\n                ')), '_starting_state': TunableVariant(description='\n            The starting state of this situation.\n            ', random_starting_state=RandomWeightedSituationStateKey.TunableFactory(), time_based=TimeBasedSituationStateKey.TunableFactory(), default='random_starting_state'), 'activity_job_rewards': TunableMapping(description='\n            Rewards given to the sim in this job when situation reaches specific medals.\n            ', key_type=TunableEnumEntry(SituationMedal, SituationMedal.TIN, description='\n                Medal to achieve to get the corresponding rewards.\n                '), value_type=TunableMapping(description='\n                Mapping of job role type to rewards.\n                ', key_type=TunableReference(description='\n                    A reference to a Situation Job.\n                    ', manager=services.get_instance_manager(Types.SITUATION_JOB)), value_type=TunableList(description='\n                    List of rewards to give.\n                    ', tunable=SituationJobReward.TunableFactory(description='\n                        Reward and LootAction benefits for accomplishing the medal.\n                        ')), key_name='Situation Job', value_name='Rewards'), key_name='Medal', value_name='Rewards'), 'duration': TunableSimMinute(description='\n            How long the activity will last in sim minutes. 0 means forever.\n            ', default=600), 'duration_randomizer': TunableSimMinute(description="\n            A random time between 0 and this tuned time will be added to the\n            activity's duration.\n            ", default=0, minimum=0), 'timer_expired_dialog': UiDialogOkCancel.TunableFactory(description='\n            Dialog to show on the dialog that appears when the activity timer expires.\n            '), 'move_on_dialog': UiDialogOkCancel.TunableFactory(description="\n            Dialog to show on the dialog that appears when the player presses the 'move on' button in the HUD.\n            "), 'activity_setups': TunableMapping(description='\n            Defines a list of ActivitySetupClusters (lists of conditional layers, states, goals) that can be applied\n            when the activity is active.\n            ', key_name='Cluster Key', key_type=Tunable(description='\n                The key of this activity setup cluster. Do not change once the setup is in use.\n                ', tunable_type=str, default=None), value_name='Activity Setup', value_type=ActivitySetupCluster.TunableFactory()), 'cancellation_rewards': TunableMapping(description="\n            A list of 'Rewards' (usually debuffs actually) to apply, based on job, if the situation is cancelled by\n            the player.\n            ", key_type=TunableReference(description='\n                A reference to a Situation Job.\n                ', manager=services.get_instance_manager(Types.SITUATION_JOB)), value_type=TunableList(description='\n                List of rewards to give.\n                ', tunable=SituationJobReward.TunableFactory(description='\n                    Reward and LootAction given for cancellation.\n                    ')), key_name='Situation Job', value_name='Rewards')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = None
        self.active_setups = []
        self.additional_goal_chains = []
        self.pending_conditional_layers = set()

    @property
    def situation_states(self):
        return self._situation_states

    def get_starting_situation_state(self):
        return self._starting_state()

    def set_score(self, score):
        self._score = score

    def _get_effective_score_for_levels(self, score):
        return score

    def get_possible_zone_ids_for_situation_activity(self):
        if self.excursion_location:
            possible_zones = self.excursion_location()
        else:
            possible_zones = []
        return possible_zones

    @property
    def zone_id(self):
        possible_zones = self.get_possible_zone_ids_for_situation_activity()
        if len(possible_zones) > 0:
            return possible_zones[0]
        else:
            return

    def get_minor_goal_chains(self):
        chains = []
        chains.extend(self.minor_goal_chains)
        chains.extend(self.additional_goal_chains)
        return chains

    def _undo_activity_setups(self):
        self.active_setups.clear()
        self.additional_goal_chains.clear()
        self.pending_conditional_layers.clear()
        for cluster in self.activity_setups.values():
            actions = cluster.startup_actions()
            actions.modify_objects()

    def _choose_activity_setups(self, resolver):
        chosen_setups = []
        for (cluster_key, cluster) in self.activity_setups.items():
            num_setups = cluster.num_setups.random_int()
            weighted_setups = [(entry.weight.get_multiplier(resolver), (setup_key, entry.setup)) for (setup_key, entry) in cluster.setups.items() if entry.weight.get_multiplier(resolver) > 0]
            while num_setups > 0 and weighted_setups:
                (setup_key, setup) = pop_weighted(weighted_setups)
                self._apply_activity_setup(setup)
                key_pair = (cluster_key, setup_key)
                chosen_setups.append(key_pair)
                num_setups -= 1
        return chosen_setups

    def _apply_activity_setup(self, setup):
        self.active_setups.append(setup)
        if setup.conditional_layers:
            situation_manager = services.get_zone_situation_manager()
            situation_id = self.owner.id
            for conditional_layer in setup.conditional_layers:
                self.pending_conditional_layers.add(conditional_layer.guid64)
                situation_manager.request_conditional_layer(situation_id, conditional_layer)
        elif setup.item_modifications is not None:
            modifications = setup.item_modifications()
            modifications.modify_objects()
        if setup.additional_goal_chains:
            self.additional_goal_chains.extend(setup.additional_goal_chains)

    def apply_activity_setups(self, resolver):
        self._undo_activity_setups()
        return self._choose_activity_setups(resolver)

    def get_activity_setup_by_key(self, cluster_key, setup_key):
        if cluster_key in self.activity_setups:
            cluster = self.activity_setups[cluster_key]
            if cluster is not None:
                if setup_key in cluster.setups:
                    entry = cluster.setups[setup_key]
                    return entry.setup
                logger.warn('Excursion situation {} activity {} cluster {} failed to find setup key {}.', self.owner, self, cluster_key, setup_key)
            else:
                logger.warn('Excursion situation {} activity {} failed to find cluster key {}.', self.owner, self, cluster_key)

    def request_activity_setup(self, cluster_key, setup_key):
        setup = self.get_activity_setup_by_key(cluster_key, setup_key)
        if setup is None:
            return False
        situation_manager = services.get_zone_situation_manager()
        situation_id = self.owner.id
        for conditional_layer in setup.conditional_layers:
            situation_manager.request_conditional_layer(situation_id, conditional_layer)
        return True

    def on_conditional_layer_loaded(self, conditional_layer):
        layer_guid = conditional_layer.guid64
        if layer_guid in self.pending_conditional_layers:
            self.pending_conditional_layers.remove(layer_guid)
            if not self.pending_conditional_layers:
                self._on_all_conditional_layers_loaded()

    def _on_all_conditional_layers_loaded(self):
        for setup in self.active_setups:
            if setup.item_modifications is not None:
                modifications = setup.item_modifications()
                modifications.modify_objects()
(TunableExcursionActivityReference, TunableExcursionActivitySnippet) = define_snippet(EXCURSION_ACTIVITY, ExcursionActivity.TunableFactory())