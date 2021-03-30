from interactions.utils.loot import LootActionsfrom sims4.tuning.tunable import TunableTuple, TunableVariant, TunableReference, AutoFactoryInit, TunablePercent, TunableList, TunableMapping, TunableRange, HasTunableSingletonFactory, TunablePackSafeReference, Tunablefrom tunable_multiplier import TunableMultiplierimport enumimport servicesimport sims4.resourceslogger = sims4.log.Logger('Scholarship Tuning', default_owner='shipark')
class ScholarshipTuning:
    APPLICATION_RESPONSE_TUNING = TunableTuple(description='\n        Loot actions to be run on scholarship acceptance or rejection.\n        \n        Reward object(s) given through the loot actions must have the\n        Scholarship Letter Component enabled in order to store information about\n        the resolved scholarship and sim applicant on the object.\n        ', value_threshold=Tunable(description="\n            A value threshold that when exceeds runs the 'accepted_beyond_value_\n            threshold' loot action.\n            ", tunable_type=int, default=1), accepted_beyond_value_threshold=LootActions.TunablePackSafeReference(description='\n            Loot action to be called when a Sim is accepted to\n            a scholarship and the value earned exceeds the tuned value threshold.\n            '), accepted_below_value_threshold=LootActions.TunablePackSafeReference(description='\n            Loot action to be called when a Sim is accepted to a scholarship and\n            the value does not exceed the tuned value threshold.\n            '), rejected=LootActions.TunablePackSafeReference(description='\n            Loot action to be called when a Sim is rejected from a scholarship.\n            '))
    FULL_RIDE_LOOT = LootActions.TunablePackSafeReference(description='\n        Loot to run if a sim has applied for scholarships and successfully\n        earned a full ride to attend university.\n        ')
    MERIT_SCHOLARSHIP = TunablePackSafeReference(description='\n        The merit scholarship to evaluate on enrollment. One Merit Scholarship\n        is earned at enrollment if any prestige degrees are earned.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='Scholarship')

class EvaluationBase(HasTunableSingletonFactory, AutoFactoryInit):

    def get_value(self, sim_info):
        raise NotImplementedError

    def get_score(self, sim_info, resolver, **kwargs):
        raise NotImplementedError

class MeritEvaluation(EvaluationBase):
    DEGREES_EARNED_TO_VALUE_OF_MERIT_SCHOLARSHIP = TunableMapping(key_type=TunableRange(description='\n            The threshold of prestige degrees earned.\n            ', tunable_type=int, minimum=0, default=1), value_type=TunableRange(description='\n            The value to award for a merit scholarship.\n            ', tunable_type=int, minimum=0, default=50))
    FACTORY_TUNABLES = {'prestige_majors': TunableList(description='\n            All prestige majors considered towards the merit scholarship.\n            ', tunable=TunableReference(description='\n                The Major a student Sim must have qualified for at enrollment in order\n                to qualify for this scholarship.\n                ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY_MAJOR)))}
    PERCENT_SUCCESS_CHANCE_PRESTIGE_MAJOR_EARNED = 100
    PERCENT_SUCCESS_CHANCE_PRESTIGE_MAJOR_UNEARNED = 0
    VALUE_NO_THRESHOLD_ACHIEVED = 0

    @classmethod
    def _verify_tuning_callback(cls):
        prev_key = 0
        for key in cls.DEGREES_EARNED_TO_VALUE_OF_MERIT_SCHOLARSHIP.keys():
            if key < prev_key:
                logger.error('Keys for ({}) must be in order by value. Entry with key {} is invalid', cls, key)
            prev_key = key

    def get_value(self, sim_info):
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            return logger.error('Attempting to get scholarship value from sim ({}), but degree tracker has None value.', sim_info)
        prestige_degrees_earned = []
        for university_prestige_degree_list in degree_tracker.get_accepted_prestige_degrees().values():
            prestige_degrees_earned.extend(university_prestige_degree_list)
        prev_threshold = 0
        for key_threshold in self.DEGREES_EARNED_TO_VALUE_OF_MERIT_SCHOLARSHIP.keys():
            if len(prestige_degrees_earned) > key_threshold:
                prev_threshold = key_threshold
            else:
                if prev_threshold != 0:
                    return self.DEGREES_EARNED_TO_VALUE_OF_MERIT_SCHOLARSHIP.get(prev_threshold)
                return self.VALUE_NO_THRESHOLD_ACHIEVED
        return self.VALUE_NO_THRESHOLD_ACHIEVED

    def get_score(self, sim_info, resolver, from_get_scholarship_chances=False):
        if sim_info.degree_tracker.accepted_degrees is None or from_get_scholarship_chances:
            return
        accepted_prestige_degrees_mapping = sim_info.degree_tracker.get_accepted_prestige_degrees()
        for (_, accepted_prestige_degrees) in accepted_prestige_degrees_mapping.items():
            for valid_prestige_major in self.prestige_majors:
                if valid_prestige_major.guid64 in accepted_prestige_degrees:
                    return self.PERCENT_SUCCESS_CHANCE_PRESTIGE_MAJOR_EARNED
        return self.PERCENT_SUCCESS_CHANCE_PRESTIGE_MAJOR_UNEARNED

class NeedEvaluation(EvaluationBase):
    FACTORY_TUNABLES = {'success_chance': TunableMultiplier.TunableFactory(description='\n            Base success percentage and tested multipliers that evaluate to the\n            sum chance of earning the scholarship.\n            ')}

    def get_value(self, sim_info):
        pass

    def get_score(self, _, resolver, **kwargs):
        return self.success_chance.get_multiplier(resolver)

class OtherEvaluation(EvaluationBase):
    FACTORY_TUNABLES = {'base_chance': TunablePercent(description='\n            The base chance a scholarship is earned.\n            ', default=20), 'additive_chance_scores': TunableReference(description='\n            For each passing score, the sum is added onto the base\n            scholarship acceptance chance.\n            ', manager=services.test_based_score_manager())}

    def get_value(self, sim_info):
        pass

    def get_score(self, _, resolver, **kwargs):
        return self.base_chance*100 + self.additive_chance_scores.get_score(resolver)

class ScholarshipEvaluationType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'evaluation_type': TunableVariant(description='\n            The evaluation type that determines whether or not a Sim will earn\n            a scholarship.            \n            ', merit=MeritEvaluation.TunableFactory(), need=NeedEvaluation.TunableFactory(), other=OtherEvaluation.TunableFactory())}

    def get_value(self, sim_info):
        return self.evaluation_type.get_value(sim_info)

class ScholarshipMaintenanceEnum(enum.Int):
    ACADEMIC = 1
    ACTIVITY = 2

class ScholarshipMaintenaceType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'maintenance_type': TunableVariant(description='\n            The type of requirement needed for a student to retain scholarship\n            benefits throughout the university term.\n            ', academic=TunableTuple(description='\n                The scholarship is dependent on staying enrolled in school.\n                \n                Dropping out, getting suspended or graduating all will cause the\n                Sim to lose the active scholarship status.\n                ', locked_args={'maintenance_enum': ScholarshipMaintenanceEnum.ACADEMIC}), activity=TunableTuple(description='\n                The scholarship is dependent on staying enrolled in an after-school\n                activity.\n                \n                If the sim is accepted to this scholarship on enrollment, they\n                will automatically be enrolled in this activity at the beginning\n                of the term. Dropping out of the activity will cause them to lose\n                this scholarship.\n                ', activity=TunableReference(description='\n                    The activity that this scholarship is dependent on.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), locked_args={'maintenance_enum': ScholarshipMaintenanceEnum.ACTIVITY}))}
