from distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom protocolbuffers import Animation_pb2, DistributorOps_pb2from sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunable, TunableAnglefrom sims4.tuning.tunable_hash import TunableStringHash32import sims4.loglogger = sims4.log.Logger('ProceduralAnimationHelpers', default_owner='yozhang')
class ProceduralAnimationRotationMixin(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'procedural_animation_control_name': TunableStringHash32(description='\n            Name of the procedural animation control we want to manipulate.\n            '), 'target_joint': TunableStringHash32(description='\n            The target joint we want the procedural animation to face to.\n            '), 'duration': Tunable(description='\n            How long the rotation animation should play.\n            ', tunable_type=float, default=1), 'rotation_around_facing': TunableAngle(description="\n            By default we use Y-Axis as up reference when we do rotation. If we set a non-zero \n            angle here, it will also rotate clock-wise about the facing direction.\n            \n            e.g. If we set this as 90 for BB droid's body rotation animation, sphere body will\n            rotate 90 degrees about its facing direction.\n            ", default=0.0)}

def control_rotation_lookat(obj, control_id, target, target_joint, duration=1.0, rotation_around_facing=0.0):
    if obj is None:
        logger.callstack('Attempting to set control rotation for a None object.', level=sims4.log.LEVEL_ERROR)
        return
    if target is None:
        logger.error('Attempting to rotate to look at a None target. subject: {}', obj)
        return
    msg = Animation_pb2.ProceduralControlRotation()
    msg.control_id = control_id
    msg.duration = duration
    msg.target_id = target.id
    msg.target_joint_hash = target_joint
    msg.rotation_around_facing = rotation_around_facing
    distributor = Distributor.instance()
    op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.PROCEDURAL_CONTROL_ROTATE, msg)
    distributor.add_op(obj, op)
