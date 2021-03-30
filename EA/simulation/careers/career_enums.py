import enum
class CareerCategory(enum.Int):
    Invalid = 0
    Work = 1
    School = 2
    TeenPartTime = 3
    Volunteer = 4
    AdultPartTime = 5
    UniversityCourse = 6

def get_selector_type_from_career_category(career_ref):
    career_category = career_ref.career_category
    if career_category == CareerCategory.Work:
        if career_ref.is_active:
            return CareerSelectorTypes.ACTIVE
        return CareerSelectorTypes.WORK
    if career_category == CareerCategory.Volunteer:
        return CareerSelectorTypes.VOLUNTEER
    if career_category == CareerCategory.AdultPartTime:
        return CareerSelectorTypes.ADULT_PARTTIME
    return CareerSelectorTypes.WORK

class CareerSelectorTypes(enum.Int):
    ALL = 0
    ACTIVE = 1
    WORK = 2
    VOLUNTEER = 3
    ADULT_PARTTIME = 4

class CareerPanelType(enum.Int):
    NORMAL_CAREER = 0
    AGENT_BASED_CAREER = 1
    FREELANCE_CAREER = 2
    ODD_JOB_CAREER = 3
    UNIVERSITY_COURSE = 4
    MISSIONS_CAREER = 5
    PARANORMAL_INVESTIGATOR_CAREER = 6
WORK_CAREER_CATEGORIES = (CareerCategory.Work, CareerCategory.TeenPartTime, CareerCategory.AdultPartTime)WORK_PART_TIME_CAREER_CATEGORIES = (CareerCategory.AdultPartTime, CareerCategory.TeenPartTime, CareerCategory.Volunteer)
class GigResult(enum.Int):
    GREAT_SUCCESS = 0
    SUCCESS = 1
    FAILURE = 2
    CRITICAL_FAILURE = 3
    CANCELED = 4

class CareerOutfitGenerationType(enum.Int):
    CAREER_TUNING = 0
    ZONE_DIRECTOR = 1

class CareerShiftType(enum.Int):
    ALL_DAY = 0
    MORNING = 1
    EVENING = 2

class ReceiveDailyHomeworkHelp(enum.Int):
    UNCHECKED = 0
    CHECKED_RECEIVE_HELP = 1
    CHECKED_NO_HELP = 2

class CareerEventDeclineOptions(enum.Int):
    CAREER_RABBITHOLE = 0
    CANCEL_CURRENT_GIG = 1
