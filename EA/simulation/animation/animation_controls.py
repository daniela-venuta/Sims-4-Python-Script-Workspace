from animation.animation_constants import ProceduralControlTypefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, Tunable, OptionalTunablefrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.tuning.geometric import TunableVector2import sims4.math
class ProceduralControlBase(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {}

    def build_control_msg(self, msg):
        pass

class TerrainAlignmentMixin(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'terrain_alignment': Tunable(description='\n            If enabled, we will attempt to use this control as a terrain\n            alignment support. Each control type implements terrain alignment\n            differently.\n            ', tunable_type=bool, default=False), 'bump_sound': OptionalTunable(description="\n            If enabled, this is the name of the sound to play when the control\n            hits a 'bump' in the terrain.\n            ", tunable=Tunable(description='\n                The name of the sound to play when the control hits a bump in\n                the terrain. We use a string here instead of a hash so that we\n                can modify the sound name based on the terrain and other\n                factors from locomotion.\n                ', tunable_type=str, default=''))}

    def build_terrain_alignment_msg(self, msg):
        msg.enable_terrain_alignment = self.terrain_alignment
        if self.bump_sound:
            msg.bump_sound_name = self.bump_sound

class ProceduralControlWheel(ProceduralControlBase, TerrainAlignmentMixin):
    FACTORY_TUNABLES = {'reference_joint': TunableStringHash32(description='\n            The joint we use to determine where the wheel is on the bike.\n            '), 'control_joint': TunableStringHash32(description="\n            The joint that is controlled and rotates with the actor's velocity.\n            ")}

    def build_control_msg(self, msg):
        super().build_control_msg(msg)
        self.build_terrain_alignment_msg(msg)
        msg.control_type = ProceduralControlType.WHEEL
        msg.joint_name_hash = self.control_joint
        msg.reference_joint_name_hash = self.reference_joint

class ProceduralControlSphereWheel(ProceduralControlWheel):
    FACTORY_TUNABLES = {}

    def build_control_msg(self, msg):
        super().build_control_msg(msg)
        msg.control_type = ProceduralControlType.SPHERE_WHEEL

class ProceduralControlSkate(ProceduralControlBase, TerrainAlignmentMixin):
    FACTORY_TUNABLES = {'control_joint': TunableStringHash32(description='\n            The joint that we use for terrain alignment.\n            '), 'half_dimensions': TunableVector2(description='\n            The half dimensions in the X-Z direction that we use to determine\n            the size of the skate for terrain alignment.\n            ', default=sims4.math.Vector2(0.1, 0.1), x_axis_name='X Half', y_axis_name='Z Half')}

    def build_control_msg(self, msg):
        super().build_control_msg(msg)
        self.build_terrain_alignment_msg(msg)
        msg.control_type = ProceduralControlType.SKATE
        msg.joint_name_hash = self.control_joint
        (msg.dimensions.x, msg.dimensions.y, msg.dimensions.z) = sims4.math.Vector3(self.half_dimensions.x, 0.0, self.half_dimensions.y)
