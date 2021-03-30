from interactions import ParticipantTypefrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableEnumEntry, TunableReference, HasTunableSingletonFactory, TunableSet, AutoFactoryInit, TunableEnumWithFilter, TunableMappingfrom singletons import EMPTY_SETfrom tag import Tagimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('UniversityConstraints', default_owner='nabaker')
class UniversityCourseReferenceSpawnPointTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'_course_slot': TunableReference(description='\n            Course slot from which to pull the spawn point tags.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions=('UniversityCourseCareerSlot',))}

    def get_tags(self, sim_info, interaction):
        return self._course_slot.get_spawn_point_tags(sim_info)

class UniversitySpecificSpawnPointTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'spawn_point_tags': TunableMapping(description='\n            University specific classroom tags.\n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY)), value_type=TunableSet(tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=('Spawn',)), minlength=1))}

    def get_tags(self, sim_info, interaction):
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            logger.error('Trying to get University Specific spawn point from sim {} with no degree tracker', sim_info)
            return EMPTY_SET
        university = degree_tracker.get_university()
        if university not in self.spawn_point_tags:
            return EMPTY_SET
        return self.spawn_point_tags[university]

class UniversityCourseCareerSISpawnPointTags(HasTunableSingletonFactory, AutoFactoryInit):

    def get_tags(self, sim_info, interaction):
        if interaction is None:
            return EMPTY_SET
        career_uid = interaction.interaction_parameters.get('career_uid')
        if career_uid is None:
            logger.error('Trying to get University Specific spawn point via career SI from invalid interaction: {}', interaction)
            return EMPTY_SET
        career = services.get_instance_manager(sims4.resources.Types.CAREER).get(career_uid)
        if career is None or not hasattr(career, 'get_spawn_point_tags'):
            return EMPTY_SET
        return career.get_spawn_point_tags(sim_info)

class UniversityCourseParticipantSpawnPointTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant from which the career ID will be obtained. \n            Typically should be PickedItemId if this interaction comes via a \n            CareerPickerSuperInteraction.\n            ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId)}

    def get_tags(self, sim_info, interaction):
        if interaction is None:
            return EMPTY_SET
        career_uid = interaction.get_participant(self.participant)
        if career_uid is None:
            logger.error('Trying to get University Specific spawn point via invalid participant {}: {}', self.participant)
            return EMPTY_SET
        career = services.get_instance_manager(sims4.resources.Types.CAREER).get(career_uid)
        if career is None or not hasattr(career, 'get_spawn_point_tags'):
            return EMPTY_SET
        return career.get_spawn_point_tags(sim_info)
