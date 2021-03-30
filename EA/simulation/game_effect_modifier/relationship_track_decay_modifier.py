from game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom relationships.relationship_enums import RelationshipTrackTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableReference, Tunable, OptionalTunable, TunableListimport servicesimport sims4.resourcesimport zone_types
class RelationshipTrackDecayModifier(HasTunableSingletonFactory, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'relationship_track': TunableReference(description='\n            The relationship track to modify the decay of.\n            ', manager=services.statistic_manager(), class_restrictions=('RelationshipTrack',)), 'modifier': Tunable(description='\n            How much relationship decay will be modified.\n            ', tunable_type=float, default=1.0), 'bit_based_modifier': OptionalTunable(description='\n            If enabled this will be a bit based modifier and only apply when a specific relationship\n            bit is active in the relationship.\n            ', tunable=TunableList(description='\n                A list of relationship bits that the modifier will only apply to when they are\n                active within the relationship.\n                ', tunable=TunableReference(description='\n                    A relationship bit that while the Sim has it, the modifier on the track will\n                    apply.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT))))}

    def __init__(self, relationship_track, modifier, bit_based_modifier, **kwargs):
        super().__init__(GameEffectType.RELATIONSHIP_TRACK_DECAY_MODIFIER)
        self._track_type = relationship_track
        self._modifier = modifier
        self._bit_based_modifier = bit_based_modifier

    def apply_modifier(self, sim_info):

        def _all_sim_infos_loaded_callback(*arg, **kwargs):
            zone = services.current_zone()
            zone.unregister_callback(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, _all_sim_infos_loaded_callback)
            self._modify_all_relationships(sim_info.sim_id)

        zone = services.current_zone()
        if zone.is_households_and_sim_infos_loaded or not zone.is_zone_running:
            zone.register_callback(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, _all_sim_infos_loaded_callback)
            return
        self._modify_all_relationships(sim_info.sim_id)

    def _add_decay_modifier(self, sim_id, relationship):
        if self._bit_based_modifier:
            tracker = relationship.get_track_tracker(sim_id, self._track_type)
            for bit in self._bit_based_modifier:
                tracker.add_bit_based_decay_modifier(self._track_type, bit, sim_id, self._modifier)
        else:
            track = relationship.get_track(sim_id, self._track_type)
            if track is None:
                return
            track.add_decay_rate_modifier(self._modifier)

    def _remove_decay_modifier(self, sim_id, relationship):
        if self._bit_based_modifier:
            tracker = relationship.get_track_tracker(sim_id, self._track_type)
            for bit in self._bit_based_modifier:
                tracker.remove_relationship_bit_decay_modifier(self._track_type, bit, sim_id, self._modifier)
        else:
            track = relationship.get_track(sim_id, self._track_type)
            if track is None:
                return
            track.remove_decay_rate_modifier(self._modifier)

    def _modify_all_relationships(self, sim_id):
        relationship_service = services.relationship_service()
        relationship_service.add_create_relationship_listener(sim_id, self._relationship_added_callback)
        relationships = relationship_service.get_all_sim_relationships(sim_id)
        for relationship in relationships:
            self._add_decay_modifier(sim_id, relationship)

    def _relationship_added_callback(self, sim_id, relationship):
        if relationship.is_object_rel():
            return
        self._add_decay_modifier(sim_id, relationship)

    def remove_modifier(self, sim_info, handle):
        relationship_service = services.relationship_service()
        sim_id = sim_info.sim_id
        relationship_service.remove_create_relationship_listener(sim_id, self._relationship_added_callback)
        relationship_service = services.relationship_service()
        relationships = relationship_service.get_all_sim_relationships(sim_id)
        for relationship in relationships:
            self._remove_decay_modifier(sim_id, relationship)
