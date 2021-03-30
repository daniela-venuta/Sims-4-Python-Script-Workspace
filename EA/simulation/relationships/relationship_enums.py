import enum
class RelationshipBitCullingPrevention(enum.Int):
    ALLOW_ALL = ...
    PLAYED_ONLY = ...
    PLAYED_AND_UNPLAYED = ...

class RelationshipDecayMetricKeys(enum.Int, export=False):
    RELS = ...
    RELS_WITH_DECAY = ...
    LONG_TERM_TRACKS = ...
    LONG_TERM_TRACKS_DECAYING = ...
    LONG_TERM_TRACKS_AT_CONVERGENCE = ...
    SHORT_TERM_TRACKS = ...
    SHORT_TERM_TRACKS_DECAYING = ...
    SHORT_TERM_TRACKS_AT_CONVERGENCE = ...

class RelationshipDirection(enum.Int):
    BIDIRECTIONAL = 0
    UNIDIRECTIONAL = 1

class SentimentSignType(enum.Int):
    INVALID = 0
    POSITIVE = 1
    NEGATIVE = 2

class SentimentDurationType(enum.Int):
    INVALID = 0
    LONG = 1
    SHORT = 2

class RelationshipTrackType(enum.Int, export=False):
    RELATIONSHIP = 0
    SENTIMENT = 1
