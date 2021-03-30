from sims4.tuning.dynamic_enum import DynamicEnumLockedimport enum
class Grade(DynamicEnumLocked):
    UNKNOWN = 0

class FinalCourseRequirement(enum.Int):
    NONE = 0
    EXAM = 1
    PAPER = 2
    PRESENTATION = 3

class EnrollmentStatus(enum.Int):
    NONE = 0
    ENROLLED = 1
    NOT_ENROLLED = 2
    PROBATION = 3
    SUSPENDED = 4
    DROPOUT = 5
    GRADUATED = 6

class UniversityHousingKickOutReason(enum.Int):
    NONE = 0
    GRADUATED = 1
    SUSPENDED = 2
    DROPOUT = 3
    MOVED = 4
    NOT_ENROLLED = 5
    PREGNANT = 6
    BABY = 7

class UniversityHousingRoommateRequirementCriteria(enum.Int):
    NONE = 0
    UNIVERSITY = 1
    GENDER = 2
    ORGANIZATION = 3
    CLUB = 4

class UniversityInfoType(enum.Int):
    INVALID = 0
    PRESTIGE_DEGREES = 1
    NON_PRESTIGE_DEGREES = 2
    ORGANIZATIONS = 3

class HomeworkCheatingStatus(enum.Int, export=False):
    NONE = 0
    CHEATING_FAIL = 1
    CHEATING_SUCCESS = 2

class UniversityMajorStatus(enum.Int, export=False):
    NOT_ACCEPTED = 0
    ACCEPTED = 1
    GRADUATED = 2
