import time as _timeimport math as _math
def _cmp(x, y):
    if x == y:
        return 0
    elif x > y:
        return 1
    return -1
MINYEAR = 1MAXYEAR = 9999_MAXORDINAL = 3652059_DAYS_IN_MONTH = [-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]_DAYS_BEFORE_MONTH = [-1]dbm = 0for dim in _DAYS_IN_MONTH[1:]:
    _DAYS_BEFORE_MONTH.append(dbm)
    dbm += dimdel dbmdel dim
def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def _days_before_year(year):
    y = year - 1
    return y*365 + y//4 - y//100 + y//400

def _days_in_month(year, month):
    if month == 2 and _is_leap(year):
        return 29
    return _DAYS_IN_MONTH[month]

def _days_before_month(year, month):
    return _DAYS_BEFORE_MONTH[month] + (month > 2 and _is_leap(year))

def _ymd2ord(year, month, day):
    dim = _days_in_month(year, month)
    return _days_before_year(year) + _days_before_month(year, month) + day
_DI400Y = _days_before_year(401)_DI100Y = _days_before_year(101)_DI4Y = _days_before_year(5)
def _ord2ymd(n):
    n -= 1
    (n400, n) = divmod(n, _DI400Y)
    year = n400*400 + 1
    (n100, n) = divmod(n, _DI100Y)
    (n4, n) = divmod(n, _DI4Y)
    (n1, n) = divmod(n, 365)
    year += n100*100 + n4*4 + n1
    if n1 == 4 or n100 == 4:
        return (year - 1, 12, 31)
    leapyear = n1 == 3 and (n4 != 24 or n100 == 3)
    month = n + 50 >> 5
    preceding = _DAYS_BEFORE_MONTH[month] + (month > 2 and leapyear)
    if preceding > n:
        month -= 1
        preceding -= _DAYS_IN_MONTH[month] + (month == 2 and leapyear)
    n -= preceding
    return (year, month, n + 1)
_MONTHNAMES = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']_DAYNAMES = [None, 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
def _build_struct_time(y, m, d, hh, mm, ss, dstflag):
    wday = (_ymd2ord(y, m, d) + 6) % 7
    dnum = _days_before_month(y, m) + d
    return _time.struct_time((y, m, d, hh, mm, ss, wday, dnum, dstflag))

def _format_time(hh, mm, ss, us, timespec='auto'):
    specs = {'hours': '{:02d}', 'minutes': '{:02d}:{:02d}', 'seconds': '{:02d}:{:02d}:{:02d}', 'milliseconds': '{:02d}:{:02d}:{:02d}.{:03d}', 'microseconds': '{:02d}:{:02d}:{:02d}.{:06d}'}
    if timespec == 'auto':
        timespec = 'microseconds' if us else 'seconds'
    elif timespec == 'milliseconds':
        us //= 1000
    try:
        fmt = specs[timespec]
    except KeyError:
        raise ValueError('Unknown timespec value')
    return fmt.format(hh, mm, ss, us)

def _format_offset(off):
    s = ''
    if off is not None:
        if off.days < 0:
            sign = '-'
            off = -off
        else:
            sign = '+'
        (hh, mm) = divmod(off, timedelta(hours=1))
        (mm, ss) = divmod(mm, timedelta(minutes=1))
        s += '%s%02d:%02d' % (sign, hh, mm)
        if ss or ss.microseconds:
            s += ':%02d' % ss.seconds
            if ss.microseconds:
                s += '.%06d' % ss.microseconds
    return s

def _wrap_strftime(object, format, timetuple):
    freplace = None
    zreplace = None
    Zreplace = None
    newformat = []
    push = newformat.append
    i = 0
    n = len(format)
    while i < n:
        ch = format[i]
        i += 1
        if ch == '%':
            if i < n:
                ch = format[i]
                i += 1
                if ch == 'f':
                    if freplace is None:
                        freplace = '%06d' % getattr(object, 'microsecond', 0)
                    newformat.append(freplace)
                elif ch == 'z':
                    if zreplace is None:
                        zreplace = ''
                        if hasattr(object, 'utcoffset'):
                            offset = object.utcoffset()
                            if offset is not None:
                                sign = '+'
                                if offset.days < 0:
                                    offset = -offset
                                    sign = '-'
                                (h, rest) = divmod(offset, timedelta(hours=1))
                                (m, rest) = divmod(rest, timedelta(minutes=1))
                                s = rest.seconds
                                u = offset.microseconds
                                if u:
                                    zreplace = '%c%02d%02d%02d.%06d' % (sign, h, m, s, u)
                                elif s:
                                    zreplace = '%c%02d%02d%02d' % (sign, h, m, s)
                                else:
                                    zreplace = '%c%02d%02d' % (sign, h, m)
                    newformat.append(zreplace)
                elif ch == 'Z':
                    if Zreplace is None:
                        Zreplace = ''
                        if hasattr(object, 'tzname'):
                            s = object.tzname()
                            if s is not None:
                                Zreplace = s.replace('%', '%%')
                    newformat.append(Zreplace)
                else:
                    push('%')
                    push(ch)
            else:
                push('%')
        else:
            push(ch)
    newformat = ''.join(newformat)
    return _time.strftime(newformat, timetuple)

def _parse_isoformat_date(dtstr):
    year = int(dtstr[0:4])
    if dtstr[4] != '-':
        raise ValueError('Invalid date separator: %s' % dtstr[4])
    month = int(dtstr[5:7])
    if dtstr[7] != '-':
        raise ValueError('Invalid date separator')
    day = int(dtstr[8:10])
    return [year, month, day]

def _parse_hh_mm_ss_ff(tstr):
    len_str = len(tstr)
    time_comps = [0, 0, 0, 0]
    pos = 0
    for comp in range(0, 3):
        if len_str - pos < 2:
            raise ValueError('Incomplete time component')
        time_comps[comp] = int(tstr[pos:pos + 2])
        pos += 2
        next_char = tstr[pos:pos + 1]
        if next_char and comp >= 2:
            break
        if next_char != ':':
            raise ValueError('Invalid time separator: %c' % next_char)
        pos += 1
    if pos < len_str:
        if tstr[pos] != '.':
            raise ValueError('Invalid microsecond component')
        else:
            pos += 1
            len_remainder = len_str - pos
            if len_remainder not in (3, 6):
                raise ValueError('Invalid microsecond component')
            time_comps[3] = int(tstr[pos:])
            if len_remainder == 3:
                time_comps[3] *= 1000
    return time_comps

def _parse_isoformat_time(tstr):
    len_str = len(tstr)
    if len_str < 2:
        raise ValueError('Isoformat time too short')
    tz_pos = tstr.find('-') + 1 or tstr.find('+') + 1
    timestr = tstr[:tz_pos - 1] if tz_pos > 0 else tstr
    time_comps = _parse_hh_mm_ss_ff(timestr)
    tzi = None
    if tz_pos > 0:
        tzstr = tstr[tz_pos:]
        if len(tzstr) not in (5, 8, 15):
            raise ValueError('Malformed time zone string')
        tz_comps = _parse_hh_mm_ss_ff(tzstr)
        if all(x == 0 for x in tz_comps):
            tzi = timezone.utc
        else:
            tzsign = -1 if tstr[tz_pos - 1] == '-' else 1
            td = timedelta(hours=tz_comps[0], minutes=tz_comps[1], seconds=tz_comps[2], microseconds=tz_comps[3])
            tzi = timezone(tzsign*td)
    time_comps.append(tzi)
    return time_comps

def _check_tzname(name):
    if name is not None and not isinstance(name, str):
        raise TypeError("tzinfo.tzname() must return None or string, not '%s'" % type(name))

def _check_utc_offset(name, offset):
    if offset is None:
        return
    if not isinstance(offset, timedelta):
        raise TypeError("tzinfo.%s() must return None or timedelta, not '%s'" % (name, type(offset)))
    if not (-timedelta(1) < offset and offset < timedelta(1)):
        raise ValueError('%s()=%s, must be strictly between -timedelta(hours=24) and timedelta(hours=24)' % (name, offset))

def _check_int_field(value):
    if isinstance(value, int):
        return value
    if not isinstance(value, float):
        try:
            value = value.__int__()
        except AttributeError:
            pass
        if isinstance(value, int):
            return value
        raise TypeError('__int__ returned non-int (type %s)' % type(value).__name__)
        raise TypeError('an integer is required (got type %s)' % type(value).__name__)
    raise TypeError('integer argument expected, got float')

def _check_date_fields(year, month, day):
    year = _check_int_field(year)
    month = _check_int_field(month)
    day = _check_int_field(day)
    if not (MINYEAR <= year and year <= MAXYEAR):
        raise ValueError('year must be in %d..%d' % (MINYEAR, MAXYEAR), year)
    if not (1 <= month and month <= 12):
        raise ValueError('month must be in 1..12', month)
    dim = _days_in_month(year, month)
    if not (1 <= day and day <= dim):
        raise ValueError('day must be in 1..%d' % dim, day)
    return (year, month, day)

def _check_time_fields(hour, minute, second, microsecond, fold):
    hour = _check_int_field(hour)
    minute = _check_int_field(minute)
    second = _check_int_field(second)
    microsecond = _check_int_field(microsecond)
    if not (0 <= hour and hour <= 23):
        raise ValueError('hour must be in 0..23', hour)
    if not (0 <= minute and minute <= 59):
        raise ValueError('minute must be in 0..59', minute)
    if not (0 <= second and second <= 59):
        raise ValueError('second must be in 0..59', second)
    if not (0 <= microsecond and microsecond <= 999999):
        raise ValueError('microsecond must be in 0..999999', microsecond)
    if fold not in (0, 1):
        raise ValueError('fold must be either 0 or 1', fold)
    return (hour, minute, second, microsecond, fold)

def _check_tzinfo_arg(tz):
    if tz is not None and not isinstance(tz, tzinfo):
        raise TypeError('tzinfo argument must be None or of a tzinfo subclass')

def _cmperror(x, y):
    raise TypeError("can't compare '%s' to '%s'" % (type(x).__name__, type(y).__name__))

def _divide_and_round(a, b):
    (q, r) = divmod(a, b)
    r *= 2
    greater_than_half = r > b if b > 0 else r < b
    if q % 2 == 1:
        q += 1
    return q

class timedelta:
    __slots__ = ('_days', '_seconds', '_microseconds', '_hashcode')

    def __new__(cls, days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0):
        d = s = us = 0
        days += weeks*7
        seconds += minutes*60 + hours*3600
        microseconds += milliseconds*1000
        if isinstance(days, float):
            (dayfrac, days) = _math.modf(days)
            (daysecondsfrac, daysecondswhole) = _math.modf(dayfrac*86400.0)
            s = int(daysecondswhole)
            d = int(days)
        else:
            daysecondsfrac = 0.0
            d = days
        if isinstance(seconds, float):
            (secondsfrac, seconds) = _math.modf(seconds)
            seconds = int(seconds)
            secondsfrac += daysecondsfrac
        else:
            secondsfrac = daysecondsfrac
        (days, seconds) = divmod(seconds, 86400)
        d += days
        s += int(seconds)
        usdouble = secondsfrac*1000000.0
        if isinstance(microseconds, float):
            microseconds = round(microseconds + usdouble)
            (seconds, microseconds) = divmod(microseconds, 1000000)
            (days, seconds) = divmod(seconds, 86400)
            d += days
            s += seconds
        else:
            microseconds = int(microseconds)
            (seconds, microseconds) = divmod(microseconds, 1000000)
            (days, seconds) = divmod(seconds, 86400)
            d += days
            s += seconds
            microseconds = round(microseconds + usdouble)
        (seconds, us) = divmod(microseconds, 1000000)
        s += seconds
        (days, s) = divmod(s, 86400)
        d += days
        if abs(d) > 999999999:
            raise OverflowError('timedelta # of days is too large: %d' % d)
        self = object.__new__(cls)
        self._days = d
        self._seconds = s
        self._microseconds = us
        self._hashcode = -1
        return self

    def __repr__(self):
        args = []
        if self._days:
            args.append('days=%d' % self._days)
        if self._seconds:
            args.append('seconds=%d' % self._seconds)
        if self._microseconds:
            args.append('microseconds=%d' % self._microseconds)
        if not args:
            args.append('0')
        return '%s.%s(%s)' % (self.__class__.__module__, self.__class__.__qualname__, ', '.join(args))

    def __str__(self):
        (mm, ss) = divmod(self._seconds, 60)
        (hh, mm) = divmod(mm, 60)
        s = '%d:%02d:%02d' % (hh, mm, ss)
        if self._days:

            def plural(n):
                if abs(n) != 1:
                    pass
                return (n, '')

            s = '%d day%s, ' % plural(self._days) + s
        if self._microseconds:
            s = s + '.%06d' % self._microseconds
        return s

    def total_seconds(self):
        return ((self.days*86400 + self.seconds)*1000000 + self.microseconds)/1000000

    @property
    def days(self):
        return self._days

    @property
    def seconds(self):
        return self._seconds

    @property
    def microseconds(self):
        return self._microseconds

    def __add__(self, other):
        if isinstance(other, timedelta):
            return timedelta(self._days + other._days, self._seconds + other._seconds, self._microseconds + other._microseconds)
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, timedelta):
            return timedelta(self._days - other._days, self._seconds - other._seconds, self._microseconds - other._microseconds)
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, timedelta):
            return -self + other
        return NotImplemented

    def __neg__(self):
        return timedelta(-self._days, -self._seconds, -self._microseconds)

    def __pos__(self):
        return self

    def __abs__(self):
        if self._days < 0:
            return -self
        else:
            return self

    def __mul__(self, other):
        if isinstance(other, int):
            return timedelta(self._days*other, self._seconds*other, self._microseconds*other)
        elif isinstance(other, float):
            usec = self._to_microseconds()
            (a, b) = other.as_integer_ratio()
            return timedelta(0, 0, _divide_and_round(usec*a, b))
        return NotImplemented

    __rmul__ = __mul__

    def _to_microseconds(self):
        return (self._days*86400 + self._seconds)*1000000 + self._microseconds

    def __floordiv__(self, other):
        if not isinstance(other, (int, timedelta)):
            return NotImplemented
        usec = self._to_microseconds()
        if isinstance(other, timedelta):
            return usec//other._to_microseconds()
        elif isinstance(other, int):
            return timedelta(0, 0, usec//other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float, timedelta)):
            return NotImplemented
        usec = self._to_microseconds()
        if isinstance(other, timedelta):
            return usec/other._to_microseconds()
        if isinstance(other, int):
            return timedelta(0, 0, _divide_and_round(usec, other))
        elif isinstance(other, float):
            (a, b) = other.as_integer_ratio()
            return timedelta(0, 0, _divide_and_round(b*usec, a))

    def __mod__(self, other):
        if isinstance(other, timedelta):
            r = self._to_microseconds() % other._to_microseconds()
            return timedelta(0, 0, r)
        return NotImplemented

    def __divmod__(self, other):
        if isinstance(other, timedelta):
            (q, r) = divmod(self._to_microseconds(), other._to_microseconds())
            return (q, timedelta(0, 0, r))
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, timedelta):
            return self._cmp(other) == 0
        else:
            return False

    def __le__(self, other):
        if isinstance(other, timedelta):
            return self._cmp(other) <= 0
        _cmperror(self, other)

    def __lt__(self, other):
        if isinstance(other, timedelta):
            return self._cmp(other) < 0
        _cmperror(self, other)

    def __ge__(self, other):
        if isinstance(other, timedelta):
            return self._cmp(other) >= 0
        _cmperror(self, other)

    def __gt__(self, other):
        if isinstance(other, timedelta):
            return self._cmp(other) > 0
        _cmperror(self, other)

    def _cmp(self, other):
        return _cmp(self._getstate(), other._getstate())

    def __hash__(self):
        if self._hashcode == -1:
            self._hashcode = hash(self._getstate())
        return self._hashcode

    def __bool__(self):
        return self._days != 0 or (self._seconds != 0 or self._microseconds != 0)

    def _getstate(self):
        return (self._days, self._seconds, self._microseconds)

    def __reduce__(self):
        return (self.__class__, self._getstate())
timedelta.min = timedelta(-999999999)timedelta.max = timedelta(days=999999999, hours=23, minutes=59, seconds=59, microseconds=999999)timedelta.resolution = timedelta(microseconds=1)
class date:
    __slots__ = ('_year', '_month', '_day', '_hashcode')

    def __new__(cls, year, month=None, day=None):
        if month is None and (isinstance(year, bytes) and (len(year) == 4 and 1 <= year[2])) and year[2] <= 12:
            self = object.__new__(cls)
            self._date__setstate(year)
            self._hashcode = -1
            return self
        (year, month, day) = _check_date_fields(year, month, day)
        self = object.__new__(cls)
        self._year = year
        self._month = month
        self._day = day
        self._hashcode = -1
        return self

    @classmethod
    def fromtimestamp(cls, t):
        (y, m, d, hh, mm, ss, weekday, jday, dst) = _time.localtime(t)
        return cls(y, m, d)

    @classmethod
    def today(cls):
        t = _time.time()
        return cls.fromtimestamp(t)

    @classmethod
    def fromordinal(cls, n):
        (y, m, d) = _ord2ymd(n)
        return cls(y, m, d)

    @classmethod
    def fromisoformat(cls, date_string):
        if not isinstance(date_string, str):
            raise TypeError('fromisoformat: argument must be str')
        try:
            return cls(*_parse_isoformat_date(date_string))
        except Exception:
            raise ValueError('Invalid isoformat string: %s' % date_string)

    def __repr__(self):
        return '%s.%s(%d, %d, %d)' % (self.__class__.__module__, self.__class__.__qualname__, self._year, self._month, self._day)

    def ctime(self):
        weekday = self.toordinal() % 7 or 7
        return '%s %s %2d 00:00:00 %04d' % (_DAYNAMES[weekday], _MONTHNAMES[self._month], self._day, self._year)

    def strftime(self, fmt):
        return _wrap_strftime(self, fmt, self.timetuple())

    def __format__(self, fmt):
        if not isinstance(fmt, str):
            raise TypeError('must be str, not %s' % type(fmt).__name__)
        if len(fmt) != 0:
            return self.strftime(fmt)
        return str(self)

    def isoformat(self):
        return '%04d-%02d-%02d' % (self._year, self._month, self._day)

    __str__ = isoformat

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def day(self):
        return self._day

    def timetuple(self):
        return _build_struct_time(self._year, self._month, self._day, 0, 0, 0, -1)

    def toordinal(self):
        return _ymd2ord(self._year, self._month, self._day)

    def replace(self, year=None, month=None, day=None):
        if year is None:
            year = self._year
        if month is None:
            month = self._month
        if day is None:
            day = self._day
        return type(self)(year, month, day)

    def __eq__(self, other):
        if isinstance(other, date):
            return self._cmp(other) == 0
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, date):
            return self._cmp(other) <= 0
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, date):
            return self._cmp(other) < 0
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, date):
            return self._cmp(other) >= 0
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, date):
            return self._cmp(other) > 0
        return NotImplemented

    def _cmp(self, other):
        y = self._year
        m = self._month
        d = self._day
        y2 = other._year
        m2 = other._month
        d2 = other._day
        return _cmp((y, m, d), (y2, m2, d2))

    def __hash__(self):
        if self._hashcode == -1:
            self._hashcode = hash(self._getstate())
        return self._hashcode

    def __add__(self, other):
        if isinstance(other, timedelta):
            o = self.toordinal() + other.days
            if 0 < o and o <= _MAXORDINAL:
                return date.fromordinal(o)
            raise OverflowError('result out of range')
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, timedelta):
            return self + timedelta(-other.days)
        elif isinstance(other, date):
            days1 = self.toordinal()
            days2 = other.toordinal()
            return timedelta(days1 - days2)
        return NotImplemented

    def weekday(self):
        return (self.toordinal() + 6) % 7

    def isoweekday(self):
        return self.toordinal() % 7 or 7

    def isocalendar(self):
        year = self._year
        week1monday = _isoweek1monday(year)
        today = _ymd2ord(self._year, self._month, self._day)
        (week, day) = divmod(today - week1monday, 7)
        if week < 0:
            year -= 1
            week1monday = _isoweek1monday(year)
            (week, day) = divmod(today - week1monday, 7)
        elif today >= _isoweek1monday(year + 1):
            year += 1
            week = 0
        return (year, week + 1, day + 1)

    def _getstate(self):
        (yhi, ylo) = divmod(self._year, 256)
        return (bytes([yhi, ylo, self._month, self._day]),)

    def __setstate(self, string):
        (yhi, ylo, self._month, self._day) = string
        self._year = yhi*256 + ylo

    def __reduce__(self):
        return (self.__class__, self._getstate())
_date_class = datedate.min = date(1, 1, 1)date.max = date(9999, 12, 31)date.resolution = timedelta(days=1)
class tzinfo:
    __slots__ = ()

    def tzname(self, dt):
        raise NotImplementedError('tzinfo subclass must override tzname()')

    def utcoffset(self, dt):
        raise NotImplementedError('tzinfo subclass must override utcoffset()')

    def dst(self, dt):
        raise NotImplementedError('tzinfo subclass must override dst()')

    def fromutc(self, dt):
        if not isinstance(dt, datetime):
            raise TypeError('fromutc() requires a datetime argument')
        if dt.tzinfo is not self:
            raise ValueError('dt.tzinfo is not self')
        dtoff = dt.utcoffset()
        if dtoff is None:
            raise ValueError('fromutc() requires a non-None utcoffset() result')
        dtdst = dt.dst()
        if dtdst is None:
            raise ValueError('fromutc() requires a non-None dst() result')
        delta = dtoff - dtdst
        if delta:
            dt += delta
            dtdst = dt.dst()
            if dtdst is None:
                raise ValueError('fromutc(): dt.dst gave inconsistent results; cannot convert')
        return dt + dtdst

    def __reduce__(self):
        getinitargs = getattr(self, '__getinitargs__', None)
        if getinitargs:
            args = getinitargs()
        else:
            args = ()
        getstate = getattr(self, '__getstate__', None)
        if getstate:
            state = getstate()
        else:
            state = getattr(self, '__dict__', None) or None
        if state is None:
            return (self.__class__, args)
        else:
            return (self.__class__, args, state)
_tzinfo_class = tzinfo
class time:
    __slots__ = ('_hour', '_minute', '_second', '_microsecond', '_tzinfo', '_hashcode', '_fold')

    def __new__(cls, hour=0, minute=0, second=0, microsecond=0, tzinfo=None, *, fold=0):
        if isinstance(hour, bytes) and len(hour) == 6 and hour[0] & 127 < 24:
            self = object.__new__(cls)
            self._time__setstate(hour, minute or None)
            self._hashcode = -1
            return self
        (hour, minute, second, microsecond, fold) = _check_time_fields(hour, minute, second, microsecond, fold)
        _check_tzinfo_arg(tzinfo)
        self = object.__new__(cls)
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._tzinfo = tzinfo
        self._hashcode = -1
        self._fold = fold
        return self

    @property
    def hour(self):
        return self._hour

    @property
    def minute(self):
        return self._minute

    @property
    def second(self):
        return self._second

    @property
    def microsecond(self):
        return self._microsecond

    @property
    def tzinfo(self):
        return self._tzinfo

    @property
    def fold(self):
        return self._fold

    def __eq__(self, other):
        if isinstance(other, time):
            return self._cmp(other, allow_mixed=True) == 0
        else:
            return False

    def __le__(self, other):
        if isinstance(other, time):
            return self._cmp(other) <= 0
        _cmperror(self, other)

    def __lt__(self, other):
        if isinstance(other, time):
            return self._cmp(other) < 0
        _cmperror(self, other)

    def __ge__(self, other):
        if isinstance(other, time):
            return self._cmp(other) >= 0
        _cmperror(self, other)

    def __gt__(self, other):
        if isinstance(other, time):
            return self._cmp(other) > 0
        _cmperror(self, other)

    def _cmp(self, other, allow_mixed=False):
        mytz = self._tzinfo
        ottz = other._tzinfo
        myoff = otoff = None
        if mytz is ottz:
            base_compare = True
        else:
            myoff = self.utcoffset()
            otoff = other.utcoffset()
            base_compare = myoff == otoff
        if base_compare:
            return _cmp((self._hour, self._minute, self._second, self._microsecond), (other._hour, other._minute, other._second, other._microsecond))
        if myoff is None or otoff is None:
            if allow_mixed:
                return 2
            raise TypeError('cannot compare naive and aware times')
        myhhmm = self._hour*60 + self._minute - myoff//timedelta(minutes=1)
        othhmm = other._hour*60 + other._minute - otoff//timedelta(minutes=1)
        return _cmp((myhhmm, self._second, self._microsecond), (othhmm, other._second, other._microsecond))

    def __hash__(self):
        if self._hashcode == -1:
            if self.fold:
                t = self.replace(fold=0)
            else:
                t = self
            tzoff = t.utcoffset()
            if not tzoff:
                self._hashcode = hash(t._getstate()[0])
            else:
                (h, m) = divmod(timedelta(hours=self.hour, minutes=self.minute) - tzoff, timedelta(hours=1))
                m //= timedelta(minutes=1)
                if 0 <= h and h < 24:
                    self._hashcode = hash(time(h, m, self.second, self.microsecond))
                else:
                    self._hashcode = hash((h, m, self.second, self.microsecond))
        return self._hashcode

    def _tzstr(self):
        off = self.utcoffset()
        return _format_offset(off)

    def __repr__(self):
        if self._microsecond != 0:
            s = ', %d, %d' % (self._second, self._microsecond)
        elif self._second != 0:
            s = ', %d' % self._second
        else:
            s = ''
        s = '%s.%s(%d, %d%s)' % (self.__class__.__module__, self.__class__.__qualname__, self._hour, self._minute, s)
        if self._tzinfo is not None:
            s = s[:-1] + ', tzinfo=%r' % self._tzinfo + ')'
        if self._fold:
            s = s[:-1] + ', fold=1)'
        return s

    def isoformat(self, timespec='auto'):
        s = _format_time(self._hour, self._minute, self._second, self._microsecond, timespec)
        tz = self._tzstr()
        if tz:
            s += tz
        return s

    __str__ = isoformat

    @classmethod
    def fromisoformat(cls, time_string):
        if not isinstance(time_string, str):
            raise TypeError('fromisoformat: argument must be str')
        try:
            return cls(*_parse_isoformat_time(time_string))
        except Exception:
            raise ValueError('Invalid isoformat string: %s' % time_string)

    def strftime(self, fmt):
        timetuple = (1900, 1, 1, self._hour, self._minute, self._second, 0, 1, -1)
        return _wrap_strftime(self, fmt, timetuple)

    def __format__(self, fmt):
        if not isinstance(fmt, str):
            raise TypeError('must be str, not %s' % type(fmt).__name__)
        if len(fmt) != 0:
            return self.strftime(fmt)
        return str(self)

    def utcoffset(self):
        if self._tzinfo is None:
            return
        offset = self._tzinfo.utcoffset(None)
        _check_utc_offset('utcoffset', offset)
        return offset

    def tzname(self):
        if self._tzinfo is None:
            return
        name = self._tzinfo.tzname(None)
        _check_tzname(name)
        return name

    def dst(self):
        if self._tzinfo is None:
            return
        offset = self._tzinfo.dst(None)
        _check_utc_offset('dst', offset)
        return offset

    def replace(self, hour=None, minute=None, second=None, microsecond=None, tzinfo=True, *, fold=None):
        if hour is None:
            hour = self.hour
        if minute is None:
            minute = self.minute
        if second is None:
            second = self.second
        if microsecond is None:
            microsecond = self.microsecond
        if tzinfo is True:
            tzinfo = self.tzinfo
        if fold is None:
            fold = self._fold
        return type(self)(hour, minute, second, microsecond, tzinfo, fold=fold)

    def _getstate(self, protocol=3):
        (us2, us3) = divmod(self._microsecond, 256)
        (us1, us2) = divmod(us2, 256)
        h = self._hour
        if protocol > 3:
            h += 128
        basestate = bytes([h, self._minute, self._second, us1, us2, us3])
        if self._fold and self._tzinfo is None:
            return (basestate,)
        else:
            return (basestate, self._tzinfo)

    def __setstate(self, string, tzinfo):
        if tzinfo is not None and not isinstance(tzinfo, _tzinfo_class):
            raise TypeError('bad tzinfo state arg')
        (h, self._minute, self._second, us1, us2, us3) = string
        if h > 127:
            self._fold = 1
            self._hour = h - 128
        else:
            self._fold = 0
            self._hour = h
        self._microsecond = (us1 << 8 | us2) << 8 | us3
        self._tzinfo = tzinfo

    def __reduce_ex__(self, protocol):
        return (time, self._getstate(protocol))

    def __reduce__(self):
        return self.__reduce_ex__(2)
_time_class = timetime.min = time(0, 0, 0)time.max = time(23, 59, 59, 999999)time.resolution = timedelta(microseconds=1)
class datetime(date):
    __slots__ = date.__slots__ + time.__slots__

    def __new__(cls, year, month=None, day=None, hour=0, minute=0, second=0, microsecond=0, tzinfo=None, *, fold=0):
        if isinstance(year, bytes) and (len(year) == 10 and 1 <= year[2] & 127) and year[2] & 127 <= 12:
            self = object.__new__(cls)
            self._datetime__setstate(year, month)
            self._hashcode = -1
            return self
        (year, month, day) = _check_date_fields(year, month, day)
        (hour, minute, second, microsecond, fold) = _check_time_fields(hour, minute, second, microsecond, fold)
        _check_tzinfo_arg(tzinfo)
        self = object.__new__(cls)
        self._year = year
        self._month = month
        self._day = day
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._tzinfo = tzinfo
        self._hashcode = -1
        self._fold = fold
        return self

    @property
    def hour(self):
        return self._hour

    @property
    def minute(self):
        return self._minute

    @property
    def second(self):
        return self._second

    @property
    def microsecond(self):
        return self._microsecond

    @property
    def tzinfo(self):
        return self._tzinfo

    @property
    def fold(self):
        return self._fold

    @classmethod
    def _fromtimestamp(cls, t, utc, tz):
        (frac, t) = _math.modf(t)
        us = round(frac*1000000.0)
        if us >= 1000000:
            t += 1
            us -= 1000000
        elif us < 0:
            t -= 1
            us += 1000000
        converter = _time.gmtime if utc else _time.localtime
        (y, m, d, hh, mm, ss, weekday, jday, dst) = converter(t)
        ss = min(ss, 59)
        result = cls(y, m, d, hh, mm, ss, us, tz)
        if tz is None:
            max_fold_seconds = 86400
            (y, m, d, hh, mm, ss) = converter(t - max_fold_seconds)[:6]
            probe1 = cls(y, m, d, hh, mm, ss, us, tz)
            trans = result - probe1 - timedelta(0, max_fold_seconds)
            if trans.days < 0:
                (y, m, d, hh, mm, ss) = converter(t + trans//timedelta(0, 1))[:6]
                probe2 = cls(y, m, d, hh, mm, ss, us, tz)
                if probe2 == result:
                    result._fold = 1
        else:
            result = tz.fromutc(result)
        return result

    @classmethod
    def fromtimestamp(cls, t, tz=None):
        _check_tzinfo_arg(tz)
        return cls._fromtimestamp(t, tz is not None, tz)

    @classmethod
    def utcfromtimestamp(cls, t):
        return cls._fromtimestamp(t, True, None)

    @classmethod
    def now(cls, tz=None):
        t = _time.time()
        return cls.fromtimestamp(t, tz)

    @classmethod
    def utcnow(cls):
        t = _time.time()
        return cls.utcfromtimestamp(t)

    @classmethod
    def combine(cls, date, time, tzinfo=True):
        if not isinstance(date, _date_class):
            raise TypeError('date argument must be a date instance')
        if not isinstance(time, _time_class):
            raise TypeError('time argument must be a time instance')
        if tzinfo is True:
            tzinfo = time.tzinfo
        return cls(date.year, date.month, date.day, time.hour, time.minute, time.second, time.microsecond, tzinfo, fold=time.fold)

    @classmethod
    def fromisoformat(cls, date_string):
        if not isinstance(date_string, str):
            raise TypeError('fromisoformat: argument must be str')
        dstr = date_string[0:10]
        tstr = date_string[11:]
        try:
            date_components = _parse_isoformat_date(dstr)
        except ValueError:
            raise ValueError('Invalid isoformat string: %s' % date_string)
        if tstr:
            try:
                time_components = _parse_isoformat_time(tstr)
            except ValueError:
                raise ValueError('Invalid isoformat string: %s' % date_string)
        else:
            time_components = [0, 0, 0, 0, None]
        return cls(*date_components + time_components)

    def timetuple(self):
        dst = self.dst()
        if dst is None:
            dst = -1
        elif dst:
            dst = 1
        else:
            dst = 0
        return _build_struct_time(self.year, self.month, self.day, self.hour, self.minute, self.second, dst)

    def _mktime(self):
        epoch = datetime(1970, 1, 1)
        max_fold_seconds = 86400
        t = (self - epoch)//timedelta(0, 1)

        def local(u):
            (y, m, d, hh, mm, ss) = _time.localtime(u)[:6]
            return (datetime(y, m, d, hh, mm, ss) - epoch)//timedelta(0, 1)

        a = local(t) - t
        u1 = t - a
        t1 = local(u1)
        if t1 == t:
            u2 = u1 + (-max_fold_seconds, max_fold_seconds)[self.fold]
            b = local(u2) - u2
            if a == b:
                return u1
        else:
            b = t1 - u1
        u2 = t - b
        t2 = local(u2)
        if t2 == t:
            return u2
        if t1 == t:
            return u1
        return (max, min)[self.fold](u1, u2)

    def timestamp(self):
        if self._tzinfo is None:
            s = self._mktime()
            return s + self.microsecond/1000000.0
        else:
            return (self - _EPOCH).total_seconds()

    def utctimetuple(self):
        offset = self.utcoffset()
        if offset:
            self -= offset
        y = self.year
        m = self.month
        d = self.day
        hh = self.hour
        mm = self.minute
        ss = self.second
        return _build_struct_time(y, m, d, hh, mm, ss, 0)

    def date(self):
        return date(self._year, self._month, self._day)

    def time(self):
        return time(self.hour, self.minute, self.second, self.microsecond, fold=self.fold)

    def timetz(self):
        return time(self.hour, self.minute, self.second, self.microsecond, self._tzinfo, fold=self.fold)

    def replace(self, year=None, month=None, day=None, hour=None, minute=None, second=None, microsecond=None, tzinfo=True, *, fold=None):
        if year is None:
            year = self.year
        if month is None:
            month = self.month
        if day is None:
            day = self.day
        if hour is None:
            hour = self.hour
        if minute is None:
            minute = self.minute
        if second is None:
            second = self.second
        if microsecond is None:
            microsecond = self.microsecond
        if tzinfo is True:
            tzinfo = self.tzinfo
        if fold is None:
            fold = self.fold
        return type(self)(year, month, day, hour, minute, second, microsecond, tzinfo, fold=fold)

    def _local_timezone(self):
        if self.tzinfo is None:
            ts = self._mktime()
        else:
            ts = (self - _EPOCH)//timedelta(seconds=1)
        localtm = _time.localtime(ts)
        local = datetime(*localtm[:6])
        try:
            gmtoff = localtm.tm_gmtoff
            zone = localtm.tm_zone
        except AttributeError:
            delta = local - datetime(*_time.gmtime(ts)[:6])
            zone = _time.strftime('%Z', localtm)
            tz = timezone(delta, zone)
        tz = timezone(timedelta(seconds=gmtoff), zone)
        return tz

    def astimezone(self, tz=None):
        if tz is None:
            tz = self._local_timezone()
        elif not isinstance(tz, tzinfo):
            raise TypeError('tz argument must be an instance of tzinfo')
        mytz = self.tzinfo
        if mytz is None:
            mytz = self._local_timezone()
            myoffset = mytz.utcoffset(self)
        else:
            myoffset = mytz.utcoffset(self)
            if myoffset is None:
                mytz = self.replace(tzinfo=None)._local_timezone()
                myoffset = mytz.utcoffset(self)
        if tz is mytz:
            return self
        utc = (self - myoffset).replace(tzinfo=tz)
        return tz.fromutc(utc)

    def ctime(self):
        weekday = self.toordinal() % 7 or 7
        return '%s %s %2d %02d:%02d:%02d %04d' % (_DAYNAMES[weekday], _MONTHNAMES[self._month], self._day, self._hour, self._minute, self._second, self._year)

    def isoformat(self, sep='T', timespec='auto'):
        s = '%04d-%02d-%02d%c' % (self._year, self._month, self._day, sep) + _format_time(self._hour, self._minute, self._second, self._microsecond, timespec)
        off = self.utcoffset()
        tz = _format_offset(off)
        if tz:
            s += tz
        return s

    def __repr__(self):
        L = [self._year, self._month, self._day, self._hour, self._minute, self._second, self._microsecond]
        if L[-1] == 0:
            del L[-1]
        if L[-1] == 0:
            del L[-1]
        s = '%s.%s(%s)' % (self.__class__.__module__, self.__class__.__qualname__, ', '.join(map(str, L)))
        if self._tzinfo is not None:
            s = s[:-1] + ', tzinfo=%r' % self._tzinfo + ')'
        if self._fold:
            s = s[:-1] + ', fold=1)'
        return s

    def __str__(self):
        return self.isoformat(sep=' ')

    @classmethod
    def strptime(cls, date_string, format):
        import _strptime
        return _strptime._strptime_datetime(cls, date_string, format)

    def utcoffset(self):
        if self._tzinfo is None:
            return
        offset = self._tzinfo.utcoffset(self)
        _check_utc_offset('utcoffset', offset)
        return offset

    def tzname(self):
        if self._tzinfo is None:
            return
        name = self._tzinfo.tzname(self)
        _check_tzname(name)
        return name

    def dst(self):
        if self._tzinfo is None:
            return
        offset = self._tzinfo.dst(self)
        _check_utc_offset('dst', offset)
        return offset

    def __eq__(self, other):
        if isinstance(other, datetime):
            return self._cmp(other, allow_mixed=True) == 0
        elif not isinstance(other, date):
            return NotImplemented
        else:
            return False
        return False

    def __le__(self, other):
        if isinstance(other, datetime):
            return self._cmp(other) <= 0
        if not isinstance(other, date):
            return NotImplemented
        _cmperror(self, other)

    def __lt__(self, other):
        if isinstance(other, datetime):
            return self._cmp(other) < 0
        if not isinstance(other, date):
            return NotImplemented
        _cmperror(self, other)

    def __ge__(self, other):
        if isinstance(other, datetime):
            return self._cmp(other) >= 0
        if not isinstance(other, date):
            return NotImplemented
        _cmperror(self, other)

    def __gt__(self, other):
        if isinstance(other, datetime):
            return self._cmp(other) > 0
        if not isinstance(other, date):
            return NotImplemented
        _cmperror(self, other)

    def _cmp(self, other, allow_mixed=False):
        mytz = self._tzinfo
        ottz = other._tzinfo
        myoff = otoff = None
        if mytz is ottz:
            base_compare = True
        else:
            myoff = self.utcoffset()
            otoff = other.utcoffset()
            if allow_mixed:
                if myoff != self.replace(fold=not self.fold).utcoffset():
                    return 2
                if otoff != other.replace(fold=not other.fold).utcoffset():
                    return 2
            base_compare = myoff == otoff
        if base_compare:
            return _cmp((self._year, self._month, self._day, self._hour, self._minute, self._second, self._microsecond), (other._year, other._month, other._day, other._hour, other._minute, other._second, other._microsecond))
        if myoff is None or otoff is None:
            if allow_mixed:
                return 2
            raise TypeError('cannot compare naive and aware datetimes')
        diff = self - other
        if diff.days < 0:
            return -1
        if diff:
            pass
        return 0

    def __add__(self, other):
        if not isinstance(other, timedelta):
            return NotImplemented
        delta = timedelta(self.toordinal(), hours=self._hour, minutes=self._minute, seconds=self._second, microseconds=self._microsecond)
        delta += other
        (hour, rem) = divmod(delta.seconds, 3600)
        (minute, second) = divmod(rem, 60)
        if 0 < delta.days and delta.days <= _MAXORDINAL:
            return datetime.combine(date.fromordinal(delta.days), time(hour, minute, second, delta.microseconds, tzinfo=self._tzinfo))
        raise OverflowError('result out of range')

    __radd__ = __add__

    def __sub__(self, other):
        if not isinstance(other, datetime):
            if isinstance(other, timedelta):
                return self + -other
            return NotImplemented
        days1 = self.toordinal()
        days2 = other.toordinal()
        secs1 = self._second + self._minute*60 + self._hour*3600
        secs2 = other._second + other._minute*60 + other._hour*3600
        base = timedelta(days1 - days2, secs1 - secs2, self._microsecond - other._microsecond)
        if self._tzinfo is other._tzinfo:
            return base
        myoff = self.utcoffset()
        otoff = other.utcoffset()
        if myoff == otoff:
            return base
        if myoff is None or otoff is None:
            raise TypeError('cannot mix naive and timezone-aware time')
        return base + otoff - myoff

    def __hash__(self):
        if self._hashcode == -1:
            if self.fold:
                t = self.replace(fold=0)
            else:
                t = self
            tzoff = t.utcoffset()
            if tzoff is None:
                self._hashcode = hash(t._getstate()[0])
            else:
                days = _ymd2ord(self.year, self.month, self.day)
                seconds = self.hour*3600 + self.minute*60 + self.second
                self._hashcode = hash(timedelta(days, seconds, self.microsecond) - tzoff)
        return self._hashcode

    def _getstate(self, protocol=3):
        (yhi, ylo) = divmod(self._year, 256)
        (us2, us3) = divmod(self._microsecond, 256)
        (us1, us2) = divmod(us2, 256)
        m = self._month
        if protocol > 3:
            m += 128
        basestate = bytes([yhi, ylo, m, self._day, self._hour, self._minute, self._second, us1, us2, us3])
        if self._fold and self._tzinfo is None:
            return (basestate,)
        else:
            return (basestate, self._tzinfo)

    def __setstate(self, string, tzinfo):
        if tzinfo is not None and not isinstance(tzinfo, _tzinfo_class):
            raise TypeError('bad tzinfo state arg')
        (yhi, ylo, m, self._day, self._hour, self._minute, self._second, us1, us2, us3) = string
        if m > 127:
            self._fold = 1
            self._month = m - 128
        else:
            self._fold = 0
            self._month = m
        self._year = yhi*256 + ylo
        self._microsecond = (us1 << 8 | us2) << 8 | us3
        self._tzinfo = tzinfo

    def __reduce_ex__(self, protocol):
        return (self.__class__, self._getstate(protocol))

    def __reduce__(self):
        return self.__reduce_ex__(2)
datetime.min = datetime(1, 1, 1)datetime.max = datetime(9999, 12, 31, 23, 59, 59, 999999)datetime.resolution = timedelta(microseconds=1)
def _isoweek1monday(year):
    THURSDAY = 3
    firstday = _ymd2ord(year, 1, 1)
    firstweekday = (firstday + 6) % 7
    week1monday = firstday - firstweekday
    if firstweekday > THURSDAY:
        week1monday += 7
    return week1monday
