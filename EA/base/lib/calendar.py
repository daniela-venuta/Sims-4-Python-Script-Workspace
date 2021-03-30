import sysimport datetimeimport locale as _localefrom itertools import repeat__all__ = ['IllegalMonthError', 'IllegalWeekdayError', 'setfirstweekday', 'firstweekday', 'isleap', 'leapdays', 'weekday', 'monthrange', 'monthcalendar', 'prmonth', 'month', 'prcal', 'calendar', 'timegm', 'month_name', 'month_abbr', 'day_name', 'day_abbr', 'Calendar', 'TextCalendar', 'HTMLCalendar', 'LocaleTextCalendar', 'LocaleHTMLCalendar', 'weekheader']error = ValueError
class IllegalMonthError(ValueError):

    def __init__(self, month):
        self.month = month

    def __str__(self):
        return 'bad month number %r; must be 1-12' % self.month

class IllegalWeekdayError(ValueError):

    def __init__(self, weekday):
        self.weekday = weekday

    def __str__(self):
        return 'bad weekday number %r; must be 0 (Monday) to 6 (Sunday)' % self.weekday
January = 1February = 2mdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
class _localized_month:
    _months = [datetime.date(2001, i + 1, 1).strftime for i in range(12)]
    _months.insert(0, lambda x: '')

    def __init__(self, format):
        self.format = format

    def __getitem__(self, i):
        funcs = self._months[i]
        if isinstance(i, slice):
            return [f(self.format) for f in funcs]
        else:
            return funcs(self.format)

    def __len__(self):
        return 13

class _localized_day:
    _days = [datetime.date(2001, 1, i + 1).strftime for i in range(7)]

    def __init__(self, format):
        self.format = format

    def __getitem__(self, i):
        funcs = self._days[i]
        if isinstance(i, slice):
            return [f(self.format) for f in funcs]
        else:
            return funcs(self.format)

    def __len__(self):
        return 7
day_name = _localized_day('%A')day_abbr = _localized_day('%a')month_name = _localized_month('%B')month_abbr = _localized_month('%b')(MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY) = range(7)
def isleap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def leapdays(y1, y2):
    y1 -= 1
    y2 -= 1
    return y2//4 - y1//4 - (y2//100 - y1//100) + (y2//400 - y1//400)
