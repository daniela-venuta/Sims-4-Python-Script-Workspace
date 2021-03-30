import randomfrom event_testing.resolver import SingleSimResolverfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable_icon import TunableIconfrom sims.university.university_enums import FinalCourseRequirementfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, OptionalTunable, TunableTuple, TunableMapping, TunableEnumEntry, TunableInterval, TunableList, TunablePackSafeReference, TunableReference, TunableSet, TunableEnumWithFilter, TunableThreshold, TunableRange, Tunablefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import classpropertyfrom tag import Tag, TunableTagsfrom tunable_multiplier import TunableMultiplierimport servicesimport sims4.loglogger = sims4.log.Logger('UniversityTuning', default_owner='nabaker')_UniversityDisplayMixin = get_display_mixin(has_description=True, has_icon=True, has_tooltip=True, enabled_by_default=True, export_modes=ExportModes.All)
class University(HasTunableReference, _UniversityDisplayMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.UNIVERSITY)):
    COURSE_ELECTIVES = TunableTuple(description='\n        Tuning structure holding all electives data.\n        ', electives=TunableList(description='\n            A list of weighted elective courses that will be available in \n            all university.\n            ', tunable=TunableTuple(description='\n                Weighted elective course data.\n                ', elective=TunableReference(description='\n                    Elective course data.\n                    ', manager=services.get_instance_manager(Types.UNIVERSITY_COURSE_DATA), pack_safe=True), weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this elective relative to other electives \n                    in this list.\n                    '))), elective_count=TunableInterval(description='\n            The number of elective courses to choose for enrollment from the \n            elective list. Random number will be chosen from the interval.\n            ', tunable_type=int, default_lower=8, default_upper=10, minimum=1, maximum=100), elective_change_frequency=TunableRange(description='\n            The frequency, in Sim days, at which the electives option will\n            regenerate.\n            ', tunable_type=int, default=1, minimum=1, maximum=50))
    ALL_UNIVERSITIES = TunableList(description='\n        A list of all available universities in the game.\n        ', tunable=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY), pack_safe=True), unique_entries=True)
    ALL_DEGREES = TunableList(description='\n        A list of all available degrees that will be available in all \n        university.\n        ', tunable=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY_MAJOR), pack_safe=True), unique_entries=True)
    SKILL_TO_MAJOR_TUNING = TunableMapping(description='\n        A mapping of Skill -> Majors that we can use to determine what the \n        appropriate major is for an existing Sim. Each Skill can be mapped to \n        a list of Majors. If more than one is specified then a random major \n        will be chosen if the Sim is being assigned a major based on that skill.\n        ', key_type=TunableReference(description='\n            The skill being used to assign the major.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Skill',)), value_type=TunableList(description='\n            The set of majors to choose from when assigning a major based on \n            the associated skill type. If this has more than one entry then\n            one of the majors will be chosen at random.\n            ', tunable=TunableReference(description='\n                The university major to enroll the Sim in.\n                ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY_MAJOR), pack_safe=True), minlength=1, unique_entries=True))
    PROFESSOR_ARCHETYPES = TunableMapping(description='\n        A mapping of school to professor archetypes so that we can get\n        professors with the correct skill set for the college they will be\n        teaching at.\n        ', key_type=TunableReference(description='\n            The university that the professor archetype will belong to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY), pack_safe=True), value_type=TunableList(description='\n            A list of Sim Filters used to find sims that match a certain archetype\n            and make them a professor by giving them the correct trait.\n            ', tunable=TunableReference(description='\n                A single Sim filter defining a professor archetype to search for.\n                \n                A search will be run using this filter as the archetype when\n                creating a professor and if no Sims match or can be conformed to\n                this filter then a new Sim will be created using the tuned Sim \n                Template.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), pack_safe=True)))
    INSTANCE_TUNABLES = {'prestige_degrees': TunableList(description='\n            List of prestige degrees.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY_MAJOR)), unique_entries=True, export_modes=ExportModes.All), 'organizations': TunableList(description='\n            List of organizations which are available in this university.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.SNIPPET), class_restrictions=('Organization',)), unique_entries=True, export_modes=ExportModes.All), 'brochure_loot': TunableReference(description='\n            The loot to show university brochure.\n            ', manager=services.get_instance_manager(Types.ACTION), class_restrictions=('LootActions',)), 'mascot_label': Tunable(description='\n            Mascot label name to be used by enrollment wizard UI. \n            ', tunable_type=str, default='', export_modes=ExportModes.All, tuning_group=GroupNames.UI)}
    _all_degree_ids = None
    _prestige_degree_ids = None
    _non_prestige_degree_ids = None
    _non_prestige_degrees = None

    @classmethod
    def _verify_tuning_callback(cls):
        all_degrees = set(University.ALL_DEGREES)
        prestige_degrees = set(cls.prestige_degrees)
        if not prestige_degrees.issubset(all_degrees):
            logger.error('Prestige Degrees {} in University {} is not tuned as All Degrees in sims.university.university_tuning.', prestige_degrees - all_degrees, cls.__name__, owner='mkartika')

    @classproperty
    def all_degree_ids(cls):
        if cls._all_degree_ids is None:
            cls._all_degree_ids = [d.guid64 for d in cls.ALL_DEGREES]
        return cls._all_degree_ids

    @classproperty
    def prestige_degree_ids(cls):
        if cls._prestige_degree_ids is None:
            cls._prestige_degree_ids = [d.guid64 for d in cls.prestige_degrees]
        return cls._prestige_degree_ids

    @classproperty
    def non_prestige_degree_ids(cls):
        if cls._non_prestige_degree_ids is None:
            cls._non_prestige_degree_ids = [d.guid64 for d in cls.non_prestige_degrees]
        return cls._non_prestige_degree_ids

    @classproperty
    def non_prestige_degrees(cls):
        if cls._non_prestige_degrees is None:
            cls._non_prestige_degrees = [d for d in University.ALL_DEGREES if d not in cls.prestige_degrees]
        return cls._non_prestige_degrees

    @staticmethod
    def generate_elective_courses(resolver):
        elective_courses = []
        elective_count = random.randint(University.COURSE_ELECTIVES.elective_count.lower_bound, University.COURSE_ELECTIVES.elective_count.upper_bound)
        weighted_electives = []
        for e in University.COURSE_ELECTIVES.electives:
            if e.elective.course_skill_data.related_skill is None:
                pass
            else:
                weighted_electives.append((e.weight.get_multiplier(resolver), e.elective))
        for _ in range(elective_count):
            if not weighted_electives:
                break
            index = sims4.random.weighted_random_index(weighted_electives)
            if index is not None:
                weighted_elective = weighted_electives.pop(index)
                elective_courses.append(weighted_elective[1])
        return elective_courses

    @staticmethod
    def choose_random_university():
        if not University.ALL_UNIVERSITIES:
            return
        return random.choice(University.ALL_UNIVERSITIES)

    @staticmethod
    def choose_random_major():
        if not University.ALL_DEGREES:
            return
        return random.choice(University.ALL_DEGREES)

class UniversityCourseData(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.UNIVERSITY_COURSE_DATA)):
    INSTANCE_TUNABLES = {'spawn_point_tag': TunableMapping(description='\n            University specific spawn point tags.\n            Used by course related interactions to determine which spawn\n            point to use for the constraint. (i.e. the one in front of the\n            appropriate building)\n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY)), value_type=TunableSet(tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=('Spawn',)), minlength=1)), 'classroom_tag': TunableMapping(description='\n            University specific classroom tags.\n            Used by university interactions on shells to determine which building\n            shell should have the interaction(s) available.\n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY)), value_type=TunableSet(tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID), minlength=1)), 'university_course_mapping': TunableMapping(description='\n            University specific course name and description.\n            Each university can have its own course name and description\n            defined.\n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY)), value_type=TunableTuple(course_name=TunableLocalizedStringFactory(description='\n                    The name of this course.\n                    '), course_description=TunableLocalizedString(description='\n                    A description for this course.\n                    ', allow_none=True), export_class_name='UniversityCourseDisplayData'), tuple_name='UniversityCourseDataMapping', export_modes=ExportModes.All), 'course_skill_data': TunableTuple(description='\n            The related skill data for this specific course.  Whenever a Sim \n            does something that increases their course grade performance (like\n            attending lecture or studying), this skill will also increase by\n            the tunable amount.  Likewise, whenever this related skill \n            increases, the course grade will also increase.\n            ', related_skill=OptionalTunable(description='\n                The related skill associated with this course.\n                ', tunable=TunablePackSafeReference(manager=services.get_instance_manager(Types.STATISTIC), class_restrictions=('Skill',)))), 'icon': TunableIcon(description='\n            Icon for this university course.\n            ', export_modes=ExportModes.All, allow_none=True), 'cost': TunableRange(description='\n            The cost of this course.\n            ', tunable_type=int, default=200, minimum=0, export_modes=ExportModes.All), 'course_tags': TunableTags(description='\n            The tag for this course.  Used for objects that may be shared \n            between courses.\n            ', filter_prefixes=['course']), 'final_requirement_type': TunableEnumEntry(description='\n            The final requirement for this course.  This requirement must be \n            completed before the course can be considered complete.\n            ', tunable_type=FinalCourseRequirement, default=FinalCourseRequirement.NONE), 'final_requirement_aspiration': TunableReference(description='\n            An aspiration to use for tracking the final course requirement. \n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationAssignment', allow_none=True), 'professor_assignment_trait': TunableMapping(description='\n            A mapping of University -> professor assignment trait.\n            \n            This is needed because each of the universities shipped with EP08\n            use the exact same classes but we want different teachers for each\n            university.\n            ', key_type=TunableReference(description='\n                A reference to the University that the professor will belong to.\n                ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY)), value_type=TunableReference(description='\n                The trait used to identify the professor for this course.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)))}

    @classproperty
    def is_elective(cls):
        return any(cls is e.elective for e in University.COURSE_ELECTIVES.electives)

class UniversityMajor(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.UNIVERSITY_MAJOR)):
    INSTANCE_TUNABLES = {'courses': TunableList(description='\n            List of courses, in order, for this major\n            ', tunable=UniversityCourseData.TunableReference(), minlength=1), 'acceptance_score': TunableTuple(description='\n            Score requirement to be accepted in this major as prestige degree.\n            ', score=TunableMultiplier.TunableFactory(description='\n                Define the base score and multiplier to calculate acceptance\n                score of a Sim.\n                '), score_threshold=TunableThreshold(description='\n                The threshold to perform against the score to see if a Sim \n                can be accepted in this major.\n                ')), 'display_name': TunableLocalizedString(description="\n            The major's name.\n            ", tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'display_description': TunableLocalizedString(description="\n            The major's description.\n            ", tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'icons': TunableTuple(description='\n            Display icons for this major.\n            ', icon=TunableIcon(description="\n                The major's icon.\n                "), icon_prestige=TunableIcon(description="\n                The major's prestige icon.\n                "), icon_high_res=TunableIcon(description="\n                The major's high resolution icon.\n                "), icon_prestige_high_res=TunableIcon(description="\n                The major's prestige high resolution icon.\n                "), export_class_name='UniversityMajorIconTuple', tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'major_benefit_map': TunableMapping(description='\n            University specific major benefit description. Each university can \n            have its own description defined for this University Major.\n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY)), value_type=TunableLocalizedString(description='\n                Major benefit description.\n                '), tuple_name='UniversityMajorBenefitMapping', tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'graduation_reward': TunableMapping(description='\n            Loot on graduation at each university for each GPA threshold\n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.UNIVERSITY)), value_type=TunableList(description='\n                Loot for each GPA range (lower bound inclusive, upper bound\n                exclusive.\n                ', tunable=TunableTuple(gpa_range=TunableInterval(description='\n                        GPA range to receive this loot.\n                        Lower bound inclusive, upper bound exclusive.\n                        ', tunable_type=float, default_lower=0, default_upper=10), loot=TunableList(tunable=LootActions.TunableReference(description='\n                            The loot action applied.\n                            ', pack_safe=True))))), 'career_tracks': TunableList(description='\n            List of career tracks for which the UI will indicate this major\n            will provide benefit.  Is not used to actually provide said benefit.\n            ', tunable=TunableReference(description='\n                These are the career tracks that will benefit from this major.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_TRACK), pack_safe=True), tuning_group=GroupNames.UI, export_modes=ExportModes.ClientBinary, unique_entries=True)}

    @classmethod
    def graduate(cls, sim_info, university, gpa):
        resolver = SingleSimResolver(sim_info)
        if university in cls.graduation_reward:
            for grad_reward in cls.graduation_reward[university]:
                if grad_reward.gpa_range.lower_bound <= gpa and gpa < grad_reward.gpa_range.upper_bound:
                    for loot_action in grad_reward.loot:
                        loot_action.apply_to_resolver(resolver)

    @classmethod
    def get_sim_acceptance_score(cls, sim_info):
        resolver = SingleSimResolver(sim_info)
        return cls.acceptance_score.score.get_multiplier(resolver)

    @classmethod
    def can_sim_be_accepted(cls, sim_info):
        sim_score = cls.get_sim_acceptance_score(sim_info)
        return cls.acceptance_score.score_threshold.compare(sim_score)
