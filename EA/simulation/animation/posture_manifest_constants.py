from animation.posture_manifest import MATCH_ANY, MATCH_NONE, PostureManifestEntry, PostureManifest
class PostureConstants:
    SIT_POSTURE_TYPE = TunableReference(description='\n        A reference to the sit posture type.\n        ', manager=services.get_instance_manager(sims4.resources.Types.POSTURE))
