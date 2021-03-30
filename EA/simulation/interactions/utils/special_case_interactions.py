from interactions.base.super_interaction import SuperInteraction
class MultiSimPostureSpecialExitSuperInteraction(SuperInteraction):

    def should_push_posture_primitive_for_multi_exit(self):
        return False
