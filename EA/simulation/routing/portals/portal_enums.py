import enumfrom animation import animation_constants
class PathSplitType(enum.Int, export=False):
    PathSplitType_DontSplit = 0
    PathSplitType_Split = 1
    PathSplitType_LadderSplit = 2

class PortalAlignment(enum.Int):
    PA_FRONT = 0
    PA_LEFT = 1
    PA_RIGHT = 2

    @staticmethod
    def get_asm_parameter_string(alignment):
        if alignment is PortalAlignment.PA_FRONT:
            return animation_constants.ASM_LADDER_PORTAL_ALIGNMENT_FRONT
        if alignment is PortalAlignment.PA_LEFT:
            return animation_constants.ASM_LADDER_PORTAL_ALIGNMENT_LEFT
        elif alignment is PortalAlignment.PA_RIGHT:
            return animation_constants.ASM_LADDER_PORTAL_ALIGNMENT_RIGHT
        else:
            return
        return

    @staticmethod
    def get_bit_flag(alignment):
        return 1 << alignment

class LadderType(enum.Int, export=False):
    LADDER_OCEAN = 0
    LADDER_BUILD = 1
