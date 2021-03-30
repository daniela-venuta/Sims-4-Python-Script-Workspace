from collections import defaultdictimport randomfrom protocolbuffers import GameplaySaveData_pb2from autonomy.autonomy_preference import ObjectPreferenceTag, AutonomyPreferenceTypefrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom households.household_tracker import HouseholdTrackerfrom sims4.tuning.tunable import TunableEnumSet, TunableMapping, TunableEnumEntry, TunableList, TunableReferencefrom singletons import DEFAULTimport servicesimport sims4logger = sims4.log.Logger('ObjectPreference', default_owner='nabaker')
class _ZoneSpecificObjectPreferenceData:

    def __init__(self):
        self.object_to_sim = defaultdict(dict)
        self._sim_to_object = {}

    def __contains__(self, key):
        return key in self._sim_to_object

    def __getitem__(self, key):
        return self._sim_to_object[key]

    def __iter__(self):
        return iter(self._sim_to_object)

    def __len__(self):
        return len(self._sim_to_object)

    def __bool__(self):
        if self._sim_to_object:
            return True
        return False

    def keys(self):
        return self._sim_to_object.keys()

    def values(self):
        return self._sim_to_object.values()

    def items(self):
        return self._sim_to_object.items()

    def get_restricted_object(self, sim_id):
        if sim_id in self._sim_to_object:
            return self._sim_to_object[sim_id]
        return (None, None)

    def get_restricted_sim(self, object_id, subroot_index):
        if object_id in self.object_to_sim and subroot_index in self.object_to_sim[object_id]:
            return self.object_to_sim[object_id][subroot_index]

    def get_restricted_sims(self, object_id):
        if object_id in self.object_to_sim:
            return self.object_to_sim[object_id].values()

    def set_restriction(self, object_id, subroot_index, sim_id):
        if sim_id in self._sim_to_object:
            (old_object_id, old_subroot_index) = self._sim_to_object[sim_id]
            self.clear_restriction(old_object_id, old_subroot_index)
        return_sim_id = self.get_restricted_sim(object_id, subroot_index)
        self.object_to_sim[object_id][subroot_index] = sim_id
        self._sim_to_object[sim_id] = (object_id, subroot_index)
        if return_sim_id is not None and return_sim_id != sim_id:
            del self._sim_to_object[return_sim_id]
            return return_sim_id

    def clear_restriction(self, object_id, subroot_index):
        if object_id not in self.object_to_sim:
            return
        if subroot_index is None:
            sims_to_clear = self.object_to_sim[object_id].values()
            del self.object_to_sim[object_id]
        elif subroot_index in self.object_to_sim[object_id]:
            sims_to_clear = (self.object_to_sim[object_id][subroot_index],)
            del self.object_to_sim[object_id][subroot_index]
            if not self.object_to_sim[object_id]:
                del self.object_to_sim[object_id]
        else:
            sims_to_clear = tuple()
        for sim_id in sims_to_clear:
            del self._sim_to_object[sim_id]
        game_object = services.object_manager().get(object_id)
        if game_object is not None:
            game_object.update_object_tooltip()

    def get_invalid_object_ids(self):
        object_manager = services.object_manager()
        invalid_object_ids = []
        for object_id in self.object_to_sim:
            if object_manager.get(object_id) is None:
                invalid_object_ids.append(object_id)
        return invalid_object_ids

class HouseholdObjectPreferenceTracker(HouseholdTracker):
    TAGS_TO_CONVERT = TunableEnumSet(description='\n        The tags that should automatically be converted from "use preference"\n        functionality to "use only" functionality on load.\n        ', enum_type=ObjectPreferenceTag, enum_default=ObjectPreferenceTag.INVALID, invalid_enums=(ObjectPreferenceTag.INVALID,))
    IGNORE_TESTS = TunableMapping(description='\n        Mapping of tag to tests used to bypass the use only status.\n        SingelSimResolver on the sim is used.\n        ', key_type=TunableEnumEntry(description='\n            The visual style of the balloon background.\n            ', tunable_type=ObjectPreferenceTag, default=ObjectPreferenceTag.INVALID, invalid_enums=(ObjectPreferenceTag.INVALID,)), value_type=TunableTestSet(description='\n            Set of tests that must be passed for sim to ignore "use only" status.\n            '))

    def __init__(self, household):
        self._owner = household
        self._zone_object_preference_datas = defaultdict(_ZoneSpecificObjectPreferenceData)

    @property
    def owner(self):
        return self._owner

    def reset(self):
        self._zone_object_preference_datas = defaultdict(_ZoneSpecificObjectPreferenceData)

    def household_lod_cleanup(self):
        self.reset()

    def _is_ignore_disallowed(self, sim_info, preference_tag):
        return sim_info.is_selectable and (preference_tag in self.IGNORE_TESTS and self.IGNORE_TESTS[preference_tag].run_tests(SingleSimResolver(sim_info)))

    def get_restricted_object(self, sim_id, preference_tag):
        zone_preference_tuple = (services.current_zone_id(), preference_tag)
        if zone_preference_tuple not in self._zone_object_preference_datas:
            return (None, None)
        return self._zone_object_preference_datas[zone_preference_tuple].get_restricted_object(sim_id)

    def get_restricted_sims(self, object_id, preference_tag):
        zone_preference_tuple = (services.current_zone_id(), preference_tag)
        if zone_preference_tuple not in self._zone_object_preference_datas:
            return
        return self._zone_object_preference_datas[zone_preference_tuple].get_restricted_sims(object_id)

    def get_restricted_sim(self, object_id, subroot_index, preference_tag):
        zone_preference_tuple = (services.current_zone_id(), preference_tag)
        if zone_preference_tuple not in self._zone_object_preference_datas:
            return
        return self._zone_object_preference_datas[zone_preference_tuple].get_restricted_sim(object_id, subroot_index)

    def get_preferable_subroot_index(self, game_object):
        if game_object.is_sim or not (game_object.is_part and game_object.restrict_autonomy_preference):
            return
        return game_object.subroot_index

    def get_restriction(self, sim_info, game_object, preference_tag, full_object=False, allow_test=True):
        sim_id = sim_info.sim_id
        zone_preference_tuple = (services.current_zone_id(), preference_tag)
        if zone_preference_tuple not in self._zone_object_preference_datas:
            return AutonomyPreferenceType.ALLOWED
        object_id = game_object.id
        subroot_index = self.get_preferable_subroot_index(game_object)
        zone_preference_data = self._zone_object_preference_datas[zone_preference_tuple]
        if sim_id in zone_preference_data:
            (owned_object_id, owned_subroot_index) = zone_preference_data[sim_id]
            if owned_object_id not in services.object_manager():
                zone_preference_data.clear_restriction(owned_object_id, None)
            else:
                if owned_object_id == object_id and (full_object or subroot_index == owned_subroot_index):
                    return AutonomyPreferenceType.USE_ONLY
                if allow_test and self._is_ignore_disallowed(sim_info, preference_tag):
                    return AutonomyPreferenceType.ALLOWED
                return AutonomyPreferenceType.DISALLOWED
        if object_id in zone_preference_data.object_to_sim:
            if full_object:
                if None not in zone_preference_data.object_to_sim[object_id]:
                    return AutonomyPreferenceType.ALLOWED
                    if subroot_index not in zone_preference_data.object_to_sim[object_id]:
                        return AutonomyPreferenceType.ALLOWED
            elif subroot_index not in zone_preference_data.object_to_sim[object_id]:
                return AutonomyPreferenceType.ALLOWED
        else:
            return AutonomyPreferenceType.ALLOWED
        if allow_test and self._is_ignore_disallowed(sim_info, preference_tag):
            return AutonomyPreferenceType.ALLOWED
        return AutonomyPreferenceType.DISALLOWED

    def set_restriction(self, sim_info, game_objects, preference_tag, should_force):
        zone_preference_data = self._zone_object_preference_datas[(services.current_zone_id(), preference_tag)]
        if should_force or sim_info.sim_id in zone_preference_data:
            return
        object_id = None
        subroot_index = None
        for game_object in game_objects:
            object_id = game_object.id
            if game_object.is_part and game_object.restrict_autonomy_preference:
                subroot_index = game_object.subroot_index
            else:
                subroot_index = None
            if zone_preference_data.get_restricted_sim(object_id, subroot_index) is not None:
                pass
            else:
                break
        if not should_force:
            return
        if object_id is not None:
            old_sim_id = zone_preference_data.set_restriction(object_id, subroot_index, sim_info.sim_id)
            if old_sim_id is not None:
                roommate_service = services.get_roommate_service()
                if roommate_service is not None:
                    roommate_service.assign_bed(old_sim_id)
            game_object.update_object_tooltip()

    def set_object_restriction(self, sim_id, obj, preference_tag):
        zone_preference_data = self._zone_object_preference_datas[(services.current_zone_id(), preference_tag)]
        for part in obj.parts:
            if part.restrict_autonomy_preference:
                zone_preference_data.set_restriction(obj.id, part.subroot_index, sim_id)
                return
        zone_preference_data.set_restriction(obj.id, None, sim_id)
        obj.update_object_tooltip()

    def clear_restriction(self, game_objects, preference_tag):
        zone_preference_data = self._zone_object_preference_datas[(services.current_zone_id(), preference_tag)]
        object_id = None
        subroot_index = None
        for game_object in game_objects:
            object_id = game_object.id
            subroot_index = self.get_preferable_subroot_index(game_object)
            sim_id = zone_preference_data.get_restricted_sim(object_id, subroot_index)
            if sim_id is not None:
                zone_preference_data.clear_restriction(object_id, subroot_index)
                roommate_service = services.get_roommate_service()
                if roommate_service is not None:
                    roommate_service.assign_bed(sim_id, avoid_id=object_id)

    def clear_sim_restriction(self, sim_id):
        current_zone_id = services.current_zone_id()
        for (zone_preference_tuple, zone_preference_data) in self._zone_object_preference_datas.items():
            if zone_preference_tuple[0] == current_zone_id:
                (object_id, subroot_index) = zone_preference_data.get_restricted_object(sim_id)
                if object_id is not None:
                    zone_preference_data.clear_restriction(object_id, subroot_index)

    def update_preference_if_possible(self, sim_info):
        object_manager = services.object_manager()
        use_preferences = sim_info.autonomy_use_preferences
        sim_id = sim_info.sim_id
        for preference_tag in self.TAGS_TO_CONVERT:
            if preference_tag in use_preferences:
                old_object_id = use_preferences[preference_tag]
                old_object = object_manager.get(old_object_id)
                if old_object is not None:
                    del use_preferences[preference_tag]
                    subroot_index = None
                    zone_preference_data = self._zone_object_preference_datas[(services.current_zone_id(), preference_tag)]
                    if sim_id in zone_preference_data:
                        pass
                    else:
                        for old_object_part in old_object.parts:
                            if old_object_part.restrict_autonomy_preference:
                                subroot_index = old_object_part.subroot_index
                                existing_sim_id = zone_preference_data.get_restricted_sim(old_object_id, subroot_index)
                                if existing_sim_id is None:
                                    break
                        if subroot_index is not None:
                            pass
                        else:
                            zone_preference_data.set_restriction(old_object_id, subroot_index, sim_id)

    def convert_existing_preferences(self):
        for sim_info in self._owner:
            self.update_preference_if_possible(sim_info)

    def save_data(self, household_msg):
        household_msg.object_preference_tracker = GameplaySaveData_pb2.ObjectPreferenceTracker()
        for (zone_preference_tuple, zone_preference_data) in self._zone_object_preference_datas.items():
            with ProtocolBufferRollback(household_msg.object_preference_tracker.zone_preference_datas) as save_zone_data:
                save_zone_data.zone_id = zone_preference_tuple[0]
                save_zone_data.preference_tag = zone_preference_tuple[1]
                for (sim_id, object_tuple) in zone_preference_data.items():
                    with ProtocolBufferRollback(save_zone_data.sim_preferences) as save_sim_preference:
                        (object_id, subroot_index) = object_tuple
                        save_sim_preference.sim_id = sim_id
                        save_sim_preference.object_id = object_id
                        if subroot_index is None:
                            save_sim_preference.subroot_index = -1
                        else:
                            save_sim_preference.subroot_index = subroot_index

    def load_data(self, object_preference_msg, is_household=True):
        for zone_data in object_preference_msg.zone_preference_datas:
            if is_household:
                zone_data_proto = services.get_persistence_service().get_zone_proto_buff(zone_data.zone_id)
                if not zone_data_proto is None:
                    if zone_data_proto.household_id != self._owner.id:
                        pass
                    else:
                        zone_specific_data = self._zone_object_preference_datas[(zone_data.zone_id, zone_data.preference_tag)]
                        for sim_preference in zone_data.sim_preferences:
                            subroot_index = None if sim_preference.subroot_index == -1 else sim_preference.subroot_index
                            zone_specific_data.set_restriction(sim_preference.object_id, subroot_index, sim_preference.sim_id)
            else:
                zone_specific_data = self._zone_object_preference_datas[(zone_data.zone_id, zone_data.preference_tag)]
                for sim_preference in zone_data.sim_preferences:
                    subroot_index = None if sim_preference.subroot_index == -1 else sim_preference.subroot_index
                    zone_specific_data.set_restriction(sim_preference.object_id, subroot_index, sim_preference.sim_id)

    def validate_objects(self, zone_id):
        roommate_service = services.get_roommate_service()
        for (zone_preference_tuple, zone_preference_data) in self._zone_object_preference_datas.items():
            if zone_preference_tuple[0] != zone_id:
                pass
            else:
                for bad_object_id in zone_preference_data.get_invalid_object_ids():
                    sim_ids = zone_preference_data.get_restricted_sims(bad_object_id)
                    if not sim_ids:
                        pass
                    else:
                        zone_preference_data.clear_restriction(bad_object_id, None)
                        if roommate_service is not None:
                            for sim_id in sim_ids:
                                roommate_service.assign_bed(sim_id, avoid_id=bad_object_id)
