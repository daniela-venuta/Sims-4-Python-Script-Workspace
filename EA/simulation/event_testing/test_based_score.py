import operatorfrom event_testing.results import TestResultNumericfrom event_testing.test_variants import TunableTestBasedScoreTestVariantfrom event_testing.tests import TunableTestVariantfrom sims4.math import Operatorfrom sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableList, TunableTuple, Tunableimport servicesimport sims4.loglogger = sims4.log.Logger('Test Based Score')
class TestBasedScore(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.test_based_score_manager()):

    @classmethod
    def _verify_tuning_callback(cls):
        for score in cls._scores:
            if score.test is None:
                logger.error('Invalid tuning. Test in test based score ({}) is tuned to None. Please set a valid test!', cls, owner='rfleig')

    INSTANCE_TUNABLES = {'_scores': TunableList(description='\n            A list of tuned tests and accompanied scores. All successful tests\n            add the scores to an effective score. The effective score is used by\n            threshold tests.\n            ', tunable=TunableTuple(description='\n                A test and score.\n                ', test=TunableTestVariant(description='\n                    Pass this test to get the accompanied score.\n                    '), score=Tunable(description='\n                    Score you get for passing the test.\n                    ', tunable_type=float, default=1))), '_batch_test_scores': TunableList(description='\n            A list of tuned tests that are able to return a numeric test result, we will add\n            result values of all passed tests to the total score.\n            \n            Supported tests: Social Context, Relationship Test Based Score\n            ', tunable=TunableTuple(test=TunableTestBasedScoreTestVariant(description='\n                    If this test passes and returns a numeric test result, we will add its result\n                    value to the score.\n                    ')))}

    @classmethod
    def _tuning_loaded_callback(cls):
        cls._positive_scores = list(score for score in cls._scores if score.score > 0)
        cls._negative_scores = list(score for score in cls._scores if score.score < 0)
        cls._negative_scores.sort(key=operator.attrgetter('score'))
        cls._positive_scores.sort(key=operator.attrgetter('score'), reverse=True)
        cls._total_positive_score = sum(score.score for score in cls._positive_scores)
        cls._total_negative_score = sum(score.score for score in cls._negative_scores)

    @classmethod
    def get_score(cls, resolver):
        yield_to_irq()
        scores = sum(test_pair.score for test_pair in cls._scores if resolver(test_pair.test))
        batch_test_scores = 0
        for batch_score_test in cls._batch_test_scores:
            result = resolver(batch_score_test.test)
            if result and isinstance(result, TestResultNumeric):
                batch_test_scores += result.current_value
        return scores + batch_test_scores

    @classmethod
    def passes_threshold(cls, resolver, threshold):
        direction = sims4.math.Operator.from_function(threshold.comparison).category
        if direction is Operator.LESS:
            current_score = sum(test_pair.score for test_pair in cls._positive_scores if resolver(test_pair.test))
            available_score = cls._total_negative_score
            remaining_scores = cls._negative_scores
        elif direction is Operator.GREATER:
            current_score = sum(test_pair.score for test_pair in cls._negative_scores if resolver(test_pair.test))
            available_score = cls._total_positive_score
            remaining_scores = cls._positive_scores
        else:
            return threshold.compare(cls.get_score(resolver))
        for batch_score_test in cls._batch_test_scores:
            result = resolver(batch_score_test.test)
            if result and isinstance(result, TestResultNumeric):
                current_score += result.current_value
        if threshold.compare(current_score):
            return True
        for test_pair in remaining_scores:
            available_score -= test_pair.score
            if resolver(test_pair.test):
                current_score += test_pair.score
                if threshold.compare(current_score):
                    return True
            elif not threshold.compare(current_score + available_score):
                return False
        return False

    @classmethod
    def debug_dump(cls, resolver, dump=logger.warn):
        dump('Generating scores for {}'.format(cls.__name__))
        for test_pair in cls._scores:
            dump('    Testing {}'.format(type(test_pair.test).__name__))
            result = resolver(test_pair.test)
            if result:
                dump('        PASS: +{}'.format(test_pair.score))
            else:
                dump('        FAILED: {}'.format(result))
        dump('  Score: {}'.format(cls.get_score(resolver)))
