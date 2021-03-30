from event_testing.resolver import SingleSimResolverfrom sims.genealogy_tracker import FamilyRelationshipIndexfrom sims.sim_info_types import Genderfrom sims.university.university_commands import create_kick_out_situationfrom sims.university.university_enums import UniversityHousingRoommateRequirementCriteria, EnrollmentStatus, UniversityHousingKickOutReasonfrom sims.university.university_housing_tuning import UniversityHousingTuningimport servicesimport sims4logger = sims4.log.Logger('UniversityUtils', default_owner='bnguyen')
class KickoutPayload:

    def __init__(self, kick_out_reason, sim_id, additional_sim_ids=None, destination_zone_id=0):
        self.kick_out_reason = kick_out_reason
        self.sim_id = sim_id
        self.additional_sim_ids = additional_sim_ids
        self.destination_zone_id = destination_zone_id

class UniversityUtils:

    @staticmethod
    def _get_university_id_from_configuration(config_data):
        if config_data is None or not config_data.HasField('university_id'):
            return
        return config_data.university_id

    @staticmethod
    def _get_gender_from_configuration(config_data):
        if config_data is None or not config_data.HasField('gender'):
            return
        return config_data.gender

    @staticmethod
    def _get_university_organization_id_from_configuration(config_data):
        if config_data is None or not config_data.HasField('organization_id'):
            return
        return config_data.organization_id

    @staticmethod
    def _get_club_id_from_configuration(config_data):
        if config_data is None or not config_data.HasField('club_id'):
            return
        return config_data.club_id

    @staticmethod
    def _get_university_requirement_filter_terms(config_data, filter_terms=[]):
        university_id = UniversityUtils._get_university_id_from_configuration(config_data)
        if university_id is None:
            return
        university_manager = services.get_instance_manager(sims4.resources.Types.UNIVERSITY)
        university = university_manager.get(university_id)
        if university is None:
            logger.error('No university found for id: {}', university_id, owner='bnguyen')
            return
        criteria = UniversityHousingRoommateRequirementCriteria.UNIVERSITY
        university_filter_term = UniversityHousingTuning.UNIVERSITY_HOUSING_ROOMMATE_FILTER_TERM_TEMPLATES[criteria]
        university_filter_term.set_university(university)
        filter_terms.append(university_filter_term)

    @staticmethod
    def _get_gender_requirement_filter_terms(config_data, filter_terms=[]):
        gender = UniversityUtils._get_gender_from_configuration(config_data)
        if gender is None or gender != Gender.MALE and gender != Gender.FEMALE:
            return
        criteria = UniversityHousingRoommateRequirementCriteria.GENDER
        gender_filter_term = UniversityHousingTuning.UNIVERSITY_HOUSING_ROOMMATE_FILTER_TERM_TEMPLATES[criteria]
        gender_filter_term.set_gender(Gender(gender))
        filter_terms.append(gender_filter_term)

    @staticmethod
    def _get_university_organization_requirement_filter_terms(config_data, filter_terms=[]):
        organization_id = UniversityUtils._get_university_organization_id_from_configuration(config_data)
        if organization_id is None:
            return
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        organization = snippet_manager.get(organization_id)
        if organization is None:
            return
        criteria = UniversityHousingRoommateRequirementCriteria.ORGANIZATION
        ranked_statistic_filter_term = UniversityHousingTuning.UNIVERSITY_HOUSING_ROOMMATE_FILTER_TERM_TEMPLATES[criteria]
        ranked_statistic_filter_term.set_ranked_statistic(organization.progress_statistic)
        filter_terms.append(ranked_statistic_filter_term)

    @staticmethod
    def _get_club_requirement_filter_terms(config_data, filter_terms=[]):
        club_service = services.get_club_service()
        if club_service is None:
            return
        club_id = UniversityUtils._get_club_id_from_configuration(config_data)
        if club_id is None or club_service.get_club_by_id(club_id) is None:
            return
        criteria = UniversityHousingRoommateRequirementCriteria.CLUB
        club_filter_term = UniversityHousingTuning.UNIVERSITY_HOUSING_ROOMMATE_FILTER_TERM_TEMPLATES[criteria]
        club_filter_term.set_specific_club_id(club_id)
        filter_terms.append(club_filter_term)

    @staticmethod
    def _get_university_housing_configuration(zone_id):
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is None or not zone_data.HasField('university_housing_configuration'):
            logger.error('No university housing configuration found for zone {}', zone_id, owner='bnguyen')
            return
        return zone_data.university_housing_configuration

    @staticmethod
    def get_university_housing_roommate_filter_terms(zone_id):
        config_data = UniversityUtils._get_university_housing_configuration(zone_id)
        filter_terms = []
        UniversityUtils._get_university_requirement_filter_terms(config_data, filter_terms)
        UniversityUtils._get_gender_requirement_filter_terms(config_data, filter_terms)
        UniversityUtils._get_university_organization_requirement_filter_terms(config_data, filter_terms)
        UniversityUtils._get_club_requirement_filter_terms(config_data, filter_terms)
        return tuple(filter_terms)

    @staticmethod
    def get_university_organization_requirement(zone_id):
        config_data = UniversityUtils._get_university_housing_configuration(zone_id)
        org_id = UniversityUtils._get_university_organization_id_from_configuration(config_data)
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        return snippet_manager.get(org_id)

    @staticmethod
    def _get_babies_and_parents_to_kickout(household, kickout_payloads):
        sim_info_manager = services.sim_info_manager()
        for baby_sim_info in household.baby_info_gen():
            if not baby_sim_info:
                pass
            else:
                mother_sim_id = baby_sim_info.get_relation(FamilyRelationshipIndex.MOTHER)
                mother_sim_info = sim_info_manager.get(mother_sim_id)
                father_sim_id = baby_sim_info.get_relation(FamilyRelationshipIndex.FATHER)
                father_sim_info = sim_info_manager.get(father_sim_id)
                if mother_sim_info and mother_sim_info.household is household:
                    parent_sim_id = mother_sim_info.id
                elif father_sim_info and father_sim_info.household is household:
                    parent_sim_id = father_sim_info.id
                else:
                    logger.error('No valid parents found for baby in university housing household', owner='bnguyen')
                    return
                additional_sim_ids = [baby_sim_info.id]
                payload = KickoutPayload(UniversityHousingKickOutReason.BABY, parent_sim_id, additional_sim_ids)
                kickout_payloads.append(payload)
                return

    @staticmethod
    def _get_common_kick_out_reason(sim_info):
        kick_out_reason = UniversityHousingKickOutReason.NONE
        if sim_info is None or sim_info.degree_tracker is None or sim_info.degree_tracker.is_immune_to_kickout:
            return kick_out_reason
        single_sim_resolver = SingleSimResolver(sim_info)
        tests = UniversityHousingTuning.UNIVERSITY_HOUSING_PREGNANCY_TEST
        if tests.run_tests(single_sim_resolver):
            kick_out_reason = UniversityHousingKickOutReason.PREGNANT
        else:
            degree_tracker = sim_info.degree_tracker
            enrollment_status = degree_tracker.get_enrollment_status()
            if enrollment_status == EnrollmentStatus.NONE or enrollment_status == EnrollmentStatus.NOT_ENROLLED:
                kick_out_reason = UniversityHousingKickOutReason.NOT_ENROLLED
            elif enrollment_status == EnrollmentStatus.SUSPENDED:
                kick_out_reason = UniversityHousingKickOutReason.SUSPENDED
            elif enrollment_status == EnrollmentStatus.DROPOUT:
                kick_out_reason = UniversityHousingKickOutReason.DROPOUT
        return kick_out_reason

    @staticmethod
    def _is_immediate_kickout_reason(kickout_reason):
        if kickout_reason == UniversityHousingKickOutReason.NONE or kickout_reason == UniversityHousingKickOutReason.GRADUATED:
            return False
        return True

    @staticmethod
    def _get_household_sims_to_kickout(household, kickout_payloads):
        for sim_info in household.sim_info_gen():
            if not sim_info is None:
                if sim_info.degree_tracker is None:
                    pass
                else:
                    destination_zone_id = 0
                    kick_out_reason = sim_info.degree_tracker.kickout_reason
                    if UniversityUtils._is_immediate_kickout_reason(kick_out_reason):
                        destination_zone_id = sim_info.degree_tracker.kickout_destination_zone
                    else:
                        common_kick_out_reason = UniversityUtils._get_common_kick_out_reason(sim_info)
                        if common_kick_out_reason != UniversityHousingKickOutReason.NOT_ENROLLED or kick_out_reason == UniversityHousingKickOutReason.NONE:
                            kick_out_reason = common_kick_out_reason
                    if kick_out_reason != UniversityHousingKickOutReason.NONE:
                        payload = KickoutPayload(kick_out_reason, sim_info.id, None, destination_zone_id)
                        kickout_payloads.append(payload)
                        return

    @staticmethod
    def validate_household_sims():
        if services.venue_service().get_university_housing_kick_out_completed():
            return
        zone = services.current_zone()
        owner_household = zone.lot.get_household()
        if owner_household and owner_household is not services.active_household():
            return
        situation_manager = services.get_zone_situation_manager()
        tags = (UniversityHousingTuning.UNIVERSITY_HOUSING_KICKOUT_SITUATION_BLOCKER_TAG,)
        if situation_manager.is_situation_with_tags_running(frozenset(tags)):
            return
        kickout_payloads = []
        UniversityUtils._get_babies_and_parents_to_kickout(owner_household, kickout_payloads)
        if len(kickout_payloads) == 0:
            UniversityUtils._get_household_sims_to_kickout(owner_household, kickout_payloads)
        if len(kickout_payloads) > 0:
            payload = kickout_payloads[0]
            create_kick_out_situation(kick_out_reason=payload.kick_out_reason, sim_id=payload.sim_id, additional_sim_ids=payload.additional_sim_ids, university_housing_destination_zone_id=payload.destination_zone_id)

    @staticmethod
    def validate_household_roommate(sim_id, zone_id):
        sim_info_manager = services.sim_info_manager()
        sim_info = sim_info_manager.get(sim_id)
        if not sim_info:
            return False
        if UniversityUtils._get_common_kick_out_reason(sim_info) != UniversityHousingKickOutReason.NONE:
            return False
        else:
            filter_terms = UniversityUtils.get_university_housing_roommate_filter_terms(zone_id)
            if not services.sim_filter_service().does_sim_match_filter(sim_id, additional_filter_terms=filter_terms, gsi_source_fn=lambda : 'UniversityUtils: Valid roommate based on {}'.format(str(zone_id))):
                return False
        return True
