__all__ = ['StatisticsError', 'pstdev', 'pvariance', 'stdev', 'variance', 'median', 'median_low', 'median_high', 'median_grouped', 'mean', 'mode', 'harmonic_mean']import collectionsimport mathimport numbersfrom fractions import Fractionfrom decimal import Decimalfrom itertools import groupbyfrom bisect import bisect_left, bisect_right
class StatisticsError(ValueError):
    pass

def _sum(data, start=0):
    count = 0
    (n, d) = _exact_ratio(start)
    partials = {d: n}
    partials_get = partials.get
    T = _coerce(int, type(start))
    for (typ, values) in groupby(data, type):
        T = _coerce(T, typ)
        for (n, d) in map(_exact_ratio, values):
            count += 1
            partials[d] = partials_get(d, 0) + n
    if None in partials:
        total = partials[None]
    else:
        total = sum(Fraction(n, d) for (d, n) in sorted(partials.items()))
    return (T, total, count)

def _isfinite(x):
    try:
        return x.is_finite()
    except AttributeError:
        return math.isfinite(x)

def _coerce(T, S):
    if T is S:
        return T
    if S is int or S is bool:
        return T
    if T is int:
        return S
    if issubclass(S, T):
        return S
    if issubclass(T, S):
        return T
    if issubclass(T, int):
        return S
    if issubclass(S, int):
        return T
    if issubclass(T, Fraction) and issubclass(S, float):
        return S
    if issubclass(T, float) and issubclass(S, Fraction):
        return T
    msg = "don't know how to coerce %s and %s"
    raise TypeError(msg % (T.__name__, S.__name__))

def _exact_ratio(x):
    try:
        if type(x) is float or type(x) is Decimal:
            return x.as_integer_ratio()
        try:
            return (x.numerator, x.denominator)
        except AttributeError:
            try:
                return x.as_integer_ratio()
            except AttributeError:
                pass
    except (OverflowError, ValueError):
        return (x, None)
    msg = "can't convert type '{}' to numerator/denominator"
    raise TypeError(msg.format(type(x).__name__))

def _convert(value, T):
    if type(value) is T:
        return value
    if value.denominator != 1:
        T = float
    try:
        return T(value)
    except TypeError:
        if issubclass(T, Decimal):
            return T(value.numerator)/T(value.denominator)
        raise

def _counts(data):
    table = collections.Counter(iter(data)).most_common()
    if not table:
        return table
    maxfreq = table[0][1]
    for i in range(1, len(table)):
        if table[i][1] != maxfreq:
            table = table[:i]
            break
    return table

def _find_lteq(a, x):
    i = bisect_left(a, x)
    if i != len(a) and a[i] == x:
        return i
    raise ValueError

def _find_rteq(a, l, x):
    i = bisect_right(a, x, lo=l)
    if i != len(a) + 1 and a[i - 1] == x:
        return i - 1
    raise ValueError

def _fail_neg(values, errmsg='negative value'):
    for x in values:
        if x < 0:
            raise StatisticsError(errmsg)
        yield x

def mean(data):
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError('mean requires at least one data point')
    (T, total, count) = _sum(data)
    return _convert(total/n, T)

def harmonic_mean(data):
    if iter(data) is data:
        data = list(data)
    errmsg = 'harmonic mean does not support negative values'
    n = len(data)
    if n < 1:
        raise StatisticsError('harmonic_mean requires at least one data point')
    elif n == 1:
        x = data[0]
        if isinstance(x, (numbers.Real, Decimal)):
            if x < 0:
                raise StatisticsError(errmsg)
            return x
        raise TypeError('unsupported type')
    try:
        (T, total, count) = _sum(1/x for x in _fail_neg(data, errmsg))
    except ZeroDivisionError:
        return 0
    return _convert(n/total, T)

def median(data):
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    if n % 2 == 1:
        return data[n//2]
    else:
        i = n//2
        return (data[i - 1] + data[i])/2

def median_low(data):
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    if n % 2 == 1:
        return data[n//2]
    else:
        return data[n//2 - 1]

def median_high(data):
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    return data[n//2]

def median_grouped(data, interval=1):
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError('no median for empty data')
    elif n == 1:
        return data[0]
    x = data[n//2]
    for obj in (x, interval):
        if isinstance(obj, (str, bytes)):
            raise TypeError('expected number but got %r' % obj)
    try:
        L = x - interval/2
    except TypeError:
        L = float(x) - float(interval)/2
    l1 = _find_lteq(data, x)
    l2 = _find_rteq(data, l1, x)
    cf = l1
    f = l2 - l1 + 1
    return L + interval*(n/2 - cf)/f

def mode(data):
    table = _counts(data)
    if len(table) == 1:
        return table[0][0]
    if table:
        raise StatisticsError('no unique mode; found %d equally common values' % len(table))
    else:
        raise StatisticsError('no mode for empty data')

def _ss(data, c=None):
    if c is None:
        c = mean(data)
    (T, total, count) = _sum((x - c)**2 for x in data)
    (U, total2, count2) = _sum(x - c for x in data)
    total -= total2**2/len(data)
    return (T, total)

def variance(data, xbar=None):
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 2:
        raise StatisticsError('variance requires at least two data points')
    (T, ss) = _ss(data, xbar)
    return _convert(ss/(n - 1), T)

def pvariance(data, mu=None):
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError('pvariance requires at least one data point')
    (T, ss) = _ss(data, mu)
    return _convert(ss/n, T)

def stdev(data, xbar=None):
    var = variance(data, xbar)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)

def pstdev(data, mu=None):
    var = pvariance(data, mu)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)
