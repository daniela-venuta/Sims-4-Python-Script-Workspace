import event_testing.test_baseimport sims4.logfrom event_testing.results import TestResultfrom interactions import ParticipantTypeSim, ParticipantTypeObject, ParticipantTypeSingleSimfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, Tunable, TunableTuple, TunableVariantfrom tag import TunableTaglogger = sims4.log.Logger('FavoritesTests', default_owner='trevor')
class FavoritesTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The subject who's favorite we're testing against.\n            ", tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target': TunableEnumEntry(description='\n            The potential favorite object to test against.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), 'favorite_type': TunableVariant(description="\n            The type of favorite that we are testing.\n            \n            Preferred Object: Test whether the object is a sim's preferred object\n            to use for a specific func tag.\n            Favorite Stack: Test whether the object is in one of the sim's favorite stacks\n            in their inventory.\n            ", preferred_object=TunableTuple(description="\n                Test whether the object is a sim's preferred object for\n                a specified tag.\n                ", tag=TunableTag(description='\n                    The tag that represents this type of favorite.\n                    ', filter_prefixes=('Func',)), instance_must_match=Tunable(description='\n                    If checked, the object instance must match the instance\n                    of the favorite object for this test to pass (barring the\n                    case where this test is negated). If unchecked, either the\n                    instance or definition may match for this test to pass.\n                    ', tunable_type=bool, default=True)), locked_args={'favorite_stack': None}, default='preferred_object'), 'negate': Tunable(description='\n            If checked, the result of this test will be negated. Error cases,\n            like subject or target not being found or the subject not having a\n            favorites tracker, will always fail.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.target}

    def __call__(self, subject=None, target=None):
        if not (subject and target):
            logger.error('Subject or Target not found while running a Favorites Test')
            return TestResult(False, 'Subject or Target was not found.', tooltip=self.tooltip)
        if len(subject) > 1:
            logger.error('FavoritesTest is being called with more than one participant for subject. Only the first participant will be used.')
        if len(target) > 1:
            logger.error('FavoritesTest is being called with more than one participant for target. Only the first participant will be used.')
        sim = subject[0]
        obj = target[0]
        favorites_tracker = sim.sim_info.favorites_tracker
        if favorites_tracker is None:
            return TestResult(False, 'Sim {} has no favorites tracker.', sim, tooltip=self.tooltip)
        if self.favorite_type is not None:
            if favorites_tracker.is_favorite(self.favorite_type.tag, obj, self.favorite_type.instance_must_match):
                if self.negate:
                    return TestResult(False, 'Found favorite for Sim. Test is negated.', tooltip=self.tooltip)
                return TestResult.TRUE
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Object {} is not the favorite for Sim {}', obj, sim, tooltip=self.tooltip)
        if favorites_tracker.is_favorite_stack(obj):
            if self.negate:
                return TestResult(False, 'Obj is part of a favorite stack for Sim. Test is negated.', tooltip=self.tooltip)
            return TestResult.TRUE
        if self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, 'Object {} is not part of a favorite stack for Sim {}', obj, sim, tooltip=self.tooltip)

class HasAnyFavoriteOfTypeTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The subject whose preference we're testing\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'favorite_tag': TunableTag(description='\n            The tag to check whether the subject has a preference for\n            ', filter_prefixes=('Func',)), 'negate': Tunable(description='\n            If checked, the result of the test will be negated\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subject': self.subject}

    def __call__(self, subject=None):
        if not subject:
            logger.error('Subject not found while running a Has Any Preference Test')
            return TestResult(False, 'Subject not found', tooltip=self.tooltip)
        if len(subject) > 1:
            logger.error('FavoritesTest is being called with more than one participant for subject. Only the first participant will be used.')
        sim = subject[0]
        favorites_tracker = sim.sim_info.favorites_tracker
        if favorites_tracker is None:
            return TestResult(False, 'Sim {} has no favorites tracker.', sim, tooltip=self.tooltip)
        if self.favorite_tag is not None:
            if favorites_tracker.has_favorite(self.favorite_tag):
                if self.negate:
                    return TestResult(False, 'Sim has a favorite for {}. Test is negated', self.favorite_tag, tooltip=self.tooltip)
                return TestResult.TRUE
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Sim has no favorite for tag {}', self.favorite_tag, tooltip=self.tooltip)
        elif self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, 'No favorite tag set', tooltip=self.tooltip)
