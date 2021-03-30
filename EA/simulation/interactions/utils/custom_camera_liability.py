from distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom gsi_handlers.gsi_utils import format_enum_namefrom interactions import ParticipantTypefrom interactions.liability import Liabilityfrom protocolbuffers import DistributorOps_pb2from sims4.hash_util import hash32from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry
class CustomCameraMode(DynamicEnum):
    INVALID = 0
    _hashed_modes = {}

    @classmethod
    def get_hashed_mode(cls, camera_mode):
        hashed_mode = cls._hashed_modes.get(camera_mode, None)
        if hashed_mode is None:
            hashed_mode = hash32(format_enum_name(camera_mode))
            cls._hashed_modes[camera_mode] = hashed_mode
        return hashed_mode

class CustomCameraLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'CustomCameraLiability'
    FACTORY_TUNABLES = {'camera_mode': TunableEnumEntry(description='\n            Desired custom camera mode.\n            ', tunable_type=CustomCameraMode, default=CustomCameraMode.INVALID, invalid_enums=(CustomCameraMode.INVALID,))}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._subject = interaction.get_participant(ParticipantType.Actor)
        self._on = False

    def on_run(self):
        if self._on:
            return
        self.send_camera_event(True)
        self._on = True

    def release(self):
        if not self._on:
            return
        self.send_camera_event(False)
        self._on = False

    def send_camera_event(self, camera_on):
        cam_proto = DistributorOps_pb2.ToggleCustomCamera()
        cam_proto.camera_mode = CustomCameraMode.get_hashed_mode(self.camera_mode)
        cam_proto.sim_id = self._subject.sim_id
        cam_proto.camera_on = camera_on
        cam_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.TOGGLE_CUSTOM_CAMERA, cam_proto)
        Distributor.instance().add_op(self._subject, cam_op)
