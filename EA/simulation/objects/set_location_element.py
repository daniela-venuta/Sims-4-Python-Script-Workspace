import sims4from event_testing.tests import TunableTestSetfrom interactions import ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableTuple, Tunable, TunableEnumEntry, TunableList, TunableSingletonFactorylogger = sims4.log.Logger('SetLocationElement', default_owner='skorman')
class TunableTransform(TunableSingletonFactory):

    @staticmethod
    def _factory(offset, quaternion):
        offset = sims4.math.Vector3(offset.x, offset.y, offset.z)
        quaternion = sims4.math.Quaternion(quaternion.x, quaternion.y, quaternion.z, quaternion.w)
        return sims4.math.Transform(offset, quaternion)

    FACTORY_TYPE = _factory

    def __init__(self, description='A tunable transform', **kwargs):
        super().__init__(offset=TunableTuple(x=Tunable(tunable_type=float, default=0.0), y=Tunable(tunable_type=float, default=0.0), z=Tunable(tunable_type=float, default=0.0)), quaternion=TunableTuple(x=Tunable(tunable_type=float, default=0.0), y=Tunable(tunable_type=float, default=0.0), z=Tunable(tunable_type=float, default=0.0), w=Tunable(tunable_type=float, default=1.0)), description=description, **kwargs)
MIRROR_TRANSLATION = sims4.math.Vector3(-1, 1, 1)MIRROR_QUATERNION = sims4.math.Quaternion(-1, 1, 1, -1)
class SetLocationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'tested_transforms': TunableList(description='\n            A tested list of transforms relative to the target to snap the \n            actor to on the server. The first in the list to pass tests\n            will be used.\n            ', tunable=TunableTuple(transform=TunableTransform(), tests=TunableTestSet())), 'actor': TunableEnumEntry(description='\n            The participant to snap.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'relative_target': TunableEnumEntry(description='\n            The participant to move the actor relative to.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'mirror_tests': TunableTestSet(description='\n            If these tests pass, The chosen transform will be mirrored.\n            ')}

    def _do_behavior(self):
        actor = self.interaction.get_participant(self.actor)
        relative_target = self.interaction.get_participant(self.relative_target)
        if actor is None or relative_target is None:
            logger.error('Failed to resolve participants for SetLocationElement for interaction {}.', self.interaction)
            return
        resolver = self.interaction.get_resolver()
        should_mirror = self.mirror_tests and self.mirror_tests.run_tests(resolver=resolver)
        base_transform = relative_target.transform
        for tested_transform in self.tested_transforms:
            if not tested_transform.tests.run_tests(resolver=resolver):
                pass
            else:
                transform = tested_transform.transform
                if should_mirror:
                    t = transform.translation
                    t = sims4.math.Vector3(MIRROR_TRANSLATION.x*t.x, MIRROR_TRANSLATION.y*t.y, MIRROR_TRANSLATION.z*t.z)
                    q = transform.orientation
                    q = sims4.math.Quaternion(MIRROR_QUATERNION.x*q.x, MIRROR_QUATERNION.y*q.y, MIRROR_QUATERNION.z*q.z, MIRROR_QUATERNION.w*q.w)
                    transform = sims4.math.Transform(t, q)
                transform = sims4.math.Transform.concatenate(transform, base_transform)
                actor.transform = transform
                return
