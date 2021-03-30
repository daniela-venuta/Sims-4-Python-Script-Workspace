from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom objects.components import Component, types, componentmethod_with_fallbackfrom sims4.localization import LocalizationHelperTuningfrom sims4.repr_utils import standard_reprfrom sims4.tuning.tunable import HasTunableFactoryimport servicesimport sims4logger = sims4.log.Logger('Scholarship Letter Component', default_owner='shipark')
class ScholarshipLetterComponent(Component, HasTunableFactory, component_name=types.SCHOLARSHIP_LETTER_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.ScholarshipLetterComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scholarship_id = None
        self._applicant_sim_id = None

    def set_applicant_sim_id(self, sim_id):
        self._applicant_sim_id = sim_id

    def set_scholarship_id(self, evaluated_scholarship_id):
        self._scholarship_id = evaluated_scholarship_id

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_info(self):
        return services.sim_info_manager().get(self._applicant_sim_id)

    def get_applicant_name(self):
        if self._applicant_sim_id is None:
            logger.error("Applicant Sim ID is None and cannot be in order to get                            the applicant's name for object with scholarship letter component ({}).", self.owner)
            return
        applicant = services.sim_info_manager().get(self._applicant_sim_id)
        if applicant is None:
            logger.error("Applicant Sim is None and cannot be in order to get                the applicant's name for object with scholarship letter component ({}).", self.owner)
            return
        return LocalizationHelperTuning.get_sim_full_name(applicant)

    def get_scholarship_amount(self):
        if self._scholarship_id is None:
            logger.error("Scholarship ID is None and cannot be in order to get                the scholarships's amount for object with scholarship letter component ({}).", self.owner)
            return
        if self._applicant_sim_id is None:
            logger.error("Applicant Sim ID is None and cannot be in order to get                the scholarships's amount for object with scholarship letter component ({}).", self.owner)
            return
        sim = services.sim_info_manager().get(self._applicant_sim_id)
        if sim is None:
            logger.error("Applicant Sim is None and cannot be in order to get                the scholarships's amount for object with scholarship letter component ({}).", self.owner)
            return
        scholarship = services.snippet_manager().get(self._scholarship_id)
        return scholarship.get_value(sim.sim_info)

    def get_scholarship_name(self):
        if self._scholarship_id is None:
            logger.error("Scholarship ID is None and cannot be in order to get                the scholarships's name for object with scholarship letter component ({}).", self.owner)
            return
        scholarship = services.snippet_manager().get(self._scholarship_id)
        return scholarship.display_name()

    def get_scholarship_description(self):
        if self._scholarship_id is None:
            logger.error("Scholarship ID is None and cannot be in order to get                the scholarships's description for object with scholarship letter component ({}).", self.owner)
            return
        scholarship = services.snippet_manager().get(self._scholarship_id)
        return scholarship.display_description()

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.ScholarshipLetterComponent
        scholarship_letter_component_save = persistable_data.Extensions[protocols.PersistableScholarshipLetterComponent.persistable_data]
        if self._scholarship_id is not None:
            scholarship_letter_component_save.scholarship_id = self._scholarship_id
        if self._applicant_sim_id is not None:
            scholarship_letter_component_save.applicant_sim_id = self._applicant_sim_id
        persistence_master_message.data.extend([persistable_data])

    def load(self, game_component_message):
        scholarship_letter_component = game_component_message.Extensions[protocols.PersistableScholarshipLetterComponent.persistable_data]
        if scholarship_letter_component.scholarship_id is not None:
            self._scholarship_id = scholarship_letter_component.scholarship_id
        if scholarship_letter_component.applicant_sim_id is not None:
            self._applicant_sim_id = scholarship_letter_component.applicant_sim_id

    def __repr__(self):
        return standard_repr(self, self.owner)
