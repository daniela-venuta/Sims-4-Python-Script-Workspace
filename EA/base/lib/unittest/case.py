import sysimport functoolsimport difflibimport loggingimport pprintimport reimport warningsimport collectionsimport contextlibimport tracebackfrom  import resultfrom util import strclass, safe_repr, _count_diff_all_purpose, _count_diff_hashable, _common_shorten_repr__unittest = True_subtest_msg_sentinel = object()DIFF_OMITTED = '\nDiff is %s characters long. Set self.maxDiff to None to see it.'
class SkipTest(Exception):
    pass

class _ShouldStop(Exception):
    pass

class _UnexpectedSuccess(Exception):
    pass

class _Outcome(object):

    def __init__(self, result=None):
        self.expecting_failure = False
        self.result = result
        self.result_supports_subtests = hasattr(result, 'addSubTest')
        self.success = True
        self.skipped = []
        self.expectedFailure = None
        self.errors = []

    @contextlib.contextmanager
    def testPartExecutor(self, test_case, isTest=False):
        old_success = self.success
        self.success = True
        try:
            try:
                yield None
            except KeyboardInterrupt:
                raise
            except SkipTest as e:
                self.success = False
                self.skipped.append((test_case, str(e)))
            except _ShouldStop:
                pass
            except:
                exc_info = sys.exc_info()
                if self.expecting_failure:
                    self.expectedFailure = exc_info
                else:
                    self.success = False
                    self.errors.append((test_case, exc_info))
                exc_info = None
            if self.result_supports_subtests and self.success:
                self.errors.append((test_case, None))
        finally:
            self.success = self.success and old_success

def _id(obj):
    return obj

def skip(reason):

    def decorator(test_item):
        if not isinstance(test_item, type):

            @functools.wraps(test_item)
            def skip_wrapper(*args, **kwargs):
                raise SkipTest(reason)

            test_item = skip_wrapper
        test_item.__unittest_skip__ = True
        test_item.__unittest_skip_why__ = reason
        return test_item

    return decorator

def skipIf(condition, reason):
    if condition:
        return skip(reason)
    return _id

def skipUnless(condition, reason):
    if not condition:
        return skip(reason)
    return _id

def expectedFailure(test_item):
    test_item.__unittest_expecting_failure__ = True
    return test_item

def _is_subtype(expected, basetype):
    if isinstance(expected, tuple):
        return all(_is_subtype(e, basetype) for e in expected)
    return isinstance(expected, type) and issubclass(expected, basetype)

class _BaseTestCaseContext:

    def __init__(self, test_case):
        self.test_case = test_case

    def _raiseFailure(self, standardMsg):
        msg = self.test_case._formatMessage(self.msg, standardMsg)
        raise self.test_case.failureException(msg)

class _AssertRaisesBaseContext(_BaseTestCaseContext):

    def __init__(self, expected, test_case, expected_regex=None):
        _BaseTestCaseContext.__init__(self, test_case)
        self.expected = expected
        self.test_case = test_case
        if expected_regex is not None:
            expected_regex = re.compile(expected_regex)
        self.expected_regex = expected_regex
        self.obj_name = None
        self.msg = None

    def handle(self, name, args, kwargs):
        try:
            if not _is_subtype(self.expected, self._base_type):
                raise TypeError('%s() arg 1 must be %s' % (name, self._base_type_str))
            if args[0] is None:
                warnings.warn('callable is None', DeprecationWarning, 3)
                args = ()
            if not (args and args):
                self.msg = kwargs.pop('msg', None)
                if kwargs:
                    warnings.warn('%r is an invalid keyword argument for this function' % next(iter(kwargs)), DeprecationWarning, 3)
                return self
            (callable_obj, *args) = args
            try:
                self.obj_name = callable_obj.__name__
            except AttributeError:
                self.obj_name = str(callable_obj)
            with self:
                callable_obj(*args, **kwargs)
        finally:
            self = None

class _AssertRaisesContext(_AssertRaisesBaseContext):
    _base_type = BaseException
    _base_type_str = 'an exception type or tuple of exception types'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            if self.obj_name:
                self._raiseFailure('{} not raised by {}'.format(exc_name, self.obj_name))
            else:
                self._raiseFailure('{} not raised'.format(exc_name))
        else:
            traceback.clear_frames(tb)
        if not issubclass(exc_type, self.expected):
            return False
        self.exception = exc_value.with_traceback(None)
        if self.expected_regex is None:
            return True
        expected_regex = self.expected_regex
        if not expected_regex.search(str(exc_value)):
            self._raiseFailure('"{}" does not match "{}"'.format(expected_regex.pattern, str(exc_value)))
        return True

class _AssertWarnsContext(_AssertRaisesBaseContext):
    _base_type = Warning
    _base_type_str = 'a warning type or tuple of warning types'

    def __enter__(self):
        for v in sys.modules.values():
            if getattr(v, '__warningregistry__', None):
                v.__warningregistry__ = {}
        self.warnings_manager = warnings.catch_warnings(record=True)
        self.warnings = self.warnings_manager.__enter__()
        warnings.simplefilter('always', self.expected)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.warnings_manager.__exit__(exc_type, exc_value, tb)
        if exc_type is not None:
            return
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        first_matching = None
        for m in self.warnings:
            w = m.message
            if not isinstance(w, self.expected):
                pass
            else:
                if first_matching is None:
                    first_matching = w
                if self.expected_regex is not None and not self.expected_regex.search(str(w)):
                    pass
                else:
                    self.warning = w
                    self.filename = m.filename
                    self.lineno = m.lineno
                    return
        if first_matching is not None:
            self._raiseFailure('"{}" does not match "{}"'.format(self.expected_regex.pattern, str(first_matching)))
        if self.obj_name:
            self._raiseFailure('{} not triggered by {}'.format(exc_name, self.obj_name))
        else:
            self._raiseFailure('{} not triggered'.format(exc_name))
_LoggingWatcher = collections.namedtuple('_LoggingWatcher', ['records', 'output'])
class _CapturingHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)
        self.watcher = _LoggingWatcher([], [])

    def flush(self):
        pass

    def emit(self, record):
        self.watcher.records.append(record)
        msg = self.format(record)
        self.watcher.output.append(msg)

class _AssertLogsContext(_BaseTestCaseContext):
    LOGGING_FORMAT = '%(levelname)s:%(name)s:%(message)s'

    def __init__(self, test_case, logger_name, level):
        _BaseTestCaseContext.__init__(self, test_case)
        self.logger_name = logger_name
        if level:
            self.level = logging._nameToLevel.get(level, level)
        else:
            self.level = logging.INFO
        self.msg = None

    def __enter__(self):
        if isinstance(self.logger_name, logging.Logger):
            logger = self.logger = self.logger_name
        else:
            logger = self.logger = logging.getLogger(self.logger_name)
        formatter = logging.Formatter(self.LOGGING_FORMAT)
        handler = _CapturingHandler()
        handler.setFormatter(formatter)
        self.watcher = handler.watcher
        self.old_handlers = logger.handlers[:]
        self.old_level = logger.level
        self.old_propagate = logger.propagate
        logger.handlers = [handler]
        logger.setLevel(self.level)
        logger.propagate = False
        return handler.watcher

    def __exit__(self, exc_type, exc_value, tb):
        self.logger.handlers = self.old_handlers
        self.logger.propagate = self.old_propagate
        self.logger.setLevel(self.old_level)
        if exc_type is not None:
            return False
        if len(self.watcher.records) == 0:
            self._raiseFailure('no logs of level {} or higher triggered on {}'.format(logging.getLevelName(self.level), self.logger.name))

class _OrderedChainMap(collections.ChainMap):

    def __iter__(self):
        seen = set()
        for mapping in self.maps:
            for k in mapping:
                if k not in seen:
                    seen.add(k)
                    yield k

class TestCase(object):
    failureException = AssertionError
    longMessage = True
    maxDiff = 640
    _diffThreshold = 65536
    _classSetupFailed = False

    def __init__(self, methodName='runTest'):
        self._testMethodName = methodName
        self._outcome = None
        self._testMethodDoc = 'No test'
        try:
            testMethod = getattr(self, methodName)
        except AttributeError:
            if methodName != 'runTest':
                raise ValueError('no such test method in %s: %s' % (self.__class__, methodName))
        self._testMethodDoc = testMethod.__doc__
        self._cleanups = []
        self._subtest = None
        self._type_equality_funcs = {}
        self.addTypeEqualityFunc(dict, 'assertDictEqual')
        self.addTypeEqualityFunc(list, 'assertListEqual')
        self.addTypeEqualityFunc(tuple, 'assertTupleEqual')
        self.addTypeEqualityFunc(set, 'assertSetEqual')
        self.addTypeEqualityFunc(frozenset, 'assertSetEqual')
        self.addTypeEqualityFunc(str, 'assertMultiLineEqual')

    def addTypeEqualityFunc(self, typeobj, function):
        self._type_equality_funcs[typeobj] = function

    def addCleanup(self, function, *args, **kwargs):
        self._cleanups.append((function, args, kwargs))

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def countTestCases(self):
        return 1

    def defaultTestResult(self):
        return result.TestResult()

    def shortDescription(self):
        doc = self._testMethodDoc
        if doc:
            pass

    def id(self):
        return '%s.%s' % (strclass(self.__class__), self._testMethodName)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self._testMethodName == other._testMethodName

    def __hash__(self):
        return hash((type(self), self._testMethodName))

    def __str__(self):
        return '%s (%s)' % (self._testMethodName, strclass(self.__class__))

    def __repr__(self):
        return '<%s testMethod=%s>' % (strclass(self.__class__), self._testMethodName)

    def _addSkip(self, result, test_case, reason):
        addSkip = getattr(result, 'addSkip', None)
        if addSkip is not None:
            addSkip(test_case, reason)
        else:
            warnings.warn('TestResult has no addSkip method, skips not reported', RuntimeWarning, 2)
            result.addSuccess(test_case)

    @contextlib.contextmanager
    def subTest(self, msg=_subtest_msg_sentinel, **params):
        if not self._outcome.result_supports_subtests:
            yield None
            return
        parent = self._subtest
        if parent is None:
            params_map = _OrderedChainMap(params)
        else:
            params_map = parent.params.new_child(params)
        self._subtest = _SubTest(self, msg, params_map)
        try:
            with self._outcome.testPartExecutor(self._subtest, isTest=True):
                yield None
            if not self._outcome.success:
                result = self._outcome.result
                if result is not None and result.failfast:
                    raise _ShouldStop
            elif self._outcome.expectedFailure:
                raise _ShouldStop
        finally:
            self._subtest = parent

    def _feedErrorsToResult(self, result, errors):
        for (test, exc_info) in errors:
            if isinstance(test, _SubTest):
                result.addSubTest(test.test_case, test, exc_info)
            elif exc_info is not None:
                if issubclass(exc_info[0], self.failureException):
                    result.addFailure(test, exc_info)
                else:
                    result.addError(test, exc_info)

    def _addExpectedFailure(self, result, exc_info):
        try:
            addExpectedFailure = result.addExpectedFailure
        except AttributeError:
            warnings.warn('TestResult has no addExpectedFailure method, reporting as passes', RuntimeWarning)
            result.addSuccess(self)
        addExpectedFailure(self, exc_info)

    def _addUnexpectedSuccess(self, result):
        try:
            addUnexpectedSuccess = result.addUnexpectedSuccess
        except AttributeError:
            warnings.warn('TestResult has no addUnexpectedSuccess method, reporting as failure', RuntimeWarning)
            try:
                raise _UnexpectedSuccess from None
            except _UnexpectedSuccess:
                result.addFailure(self, sys.exc_info())
        addUnexpectedSuccess(self)

    def run(self, result=None):
        orig_result = result
        if result is None:
            result = self.defaultTestResult()
            startTestRun = getattr(result, 'startTestRun', None)
            if startTestRun is not None:
                startTestRun()
        result.startTest(self)
        testMethod = getattr(self, self._testMethodName)
        if getattr(self.__class__, '__unittest_skip__', False) or getattr(testMethod, '__unittest_skip__', False):
            try:
                skip_why = getattr(self.__class__, '__unittest_skip_why__', '') or getattr(testMethod, '__unittest_skip_why__', '')
                self._addSkip(result, self, skip_why)
            finally:
                result.stopTest(self)
            return
        expecting_failure_method = getattr(testMethod, '__unittest_expecting_failure__', False)
        expecting_failure_class = getattr(self, '__unittest_expecting_failure__', False)
        expecting_failure = expecting_failure_class or expecting_failure_method
        outcome = _Outcome(result)
        try:
            self._outcome = outcome
            with outcome.testPartExecutor(self):
                self.setUp()
            if outcome.success:
                outcome.expecting_failure = expecting_failure
                with outcome.testPartExecutor(self, isTest=True):
                    testMethod()
                outcome.expecting_failure = False
                with outcome.testPartExecutor(self):
                    self.tearDown()
            self.doCleanups()
            for (test, reason) in outcome.skipped:
                self._addSkip(result, test, reason)
            self._feedErrorsToResult(result, outcome.errors)
            if outcome.success:
                if expecting_failure:
                    if outcome.expectedFailure:
                        self._addExpectedFailure(result, outcome.expectedFailure)
                    else:
                        self._addUnexpectedSuccess(result)
                else:
                    result.addSuccess(self)
            return result
        finally:
            result.stopTest(self)
            if orig_result is None:
                stopTestRun = getattr(result, 'stopTestRun', None)
                if stopTestRun is not None:
                    stopTestRun()
            outcome.errors.clear()
            outcome.expectedFailure = None
            self._outcome = None

    def doCleanups(self):
        outcome = self._outcome or _Outcome()
        while self._cleanups:
            (function, args, kwargs) = self._cleanups.pop()
            with outcome.testPartExecutor(self):
                function(*args, **kwargs)
        return outcome.success

    def __call__(self, *args, **kwds):
        return self.run(*args, **kwds)

    def debug(self):
        self.setUp()
        getattr(self, self._testMethodName)()
        self.tearDown()
        while self._cleanups:
            (function, args, kwargs) = self._cleanups.pop(-1)
            function(*args, **kwargs)

    def skipTest(self, reason):
        raise SkipTest(reason)

    def fail(self, msg=None):
        raise self.failureException(msg)

    def assertFalse(self, expr, msg=None):
        if expr:
            msg = self._formatMessage(msg, '%s is not false' % safe_repr(expr))
            raise self.failureException(msg)

    def assertTrue(self, expr, msg=None):
        if not expr:
            msg = self._formatMessage(msg, '%s is not true' % safe_repr(expr))
            raise self.failureException(msg)

    def _formatMessage(self, msg, standardMsg):
        if not self.longMessage:
            return msg or standardMsg
        if msg is None:
            return standardMsg
        try:
            return '%s : %s' % (standardMsg, msg)
        except UnicodeDecodeError:
            return '%s : %s' % (safe_repr(standardMsg), safe_repr(msg))

    def assertRaises(self, expected_exception, *args, **kwargs):
        context = _AssertRaisesContext(expected_exception, self)
        try:
            return context.handle('assertRaises', args, kwargs)
        finally:
            context = None

    def assertWarns(self, expected_warning, *args, **kwargs):
        context = _AssertWarnsContext(expected_warning, self)
        return context.handle('assertWarns', args, kwargs)

    def assertLogs(self, logger=None, level=None):
        return _AssertLogsContext(self, logger, level)

    def _getAssertEqualityFunc(self, first, second):
        if type(first) is type(second):
            asserter = self._type_equality_funcs.get(type(first))
            if asserter is not None:
                if isinstance(asserter, str):
                    asserter = getattr(self, asserter)
                return asserter
        return self._baseAssertEqual

    def _baseAssertEqual(self, first, second, msg=None):
        if not first == second:
            standardMsg = '%s != %s' % _common_shorten_repr(first, second)
            msg = self._formatMessage(msg, standardMsg)
            raise self.failureException(msg)

    def assertEqual(self, first, second, msg=None):
        assertion_func = self._getAssertEqualityFunc(first, second)
        assertion_func(first, second, msg=msg)

    def assertNotEqual(self, first, second, msg=None):
        if not first != second:
            msg = self._formatMessage(msg, '%s == %s' % (safe_repr(first), safe_repr(second)))
            raise self.failureException(msg)

    def assertAlmostEqual(self, first, second, places=None, msg=None, delta=None):
        if first == second:
            return
        if delta is not None and places is not None:
            raise TypeError('specify delta or places not both')
        diff = abs(first - second)
        if delta is not None:
            if diff <= delta:
                return
            standardMsg = '%s != %s within %s delta (%s difference)' % (safe_repr(first), safe_repr(second), safe_repr(delta), safe_repr(diff))
        else:
            if places is None:
                places = 7
            if round(diff, places) == 0:
                return
            standardMsg = '%s != %s within %r places (%s difference)' % (safe_repr(first), safe_repr(second), places, safe_repr(diff))
        msg = self._formatMessage(msg, standardMsg)
        raise self.failureException(msg)

    def assertNotAlmostEqual(self, first, second, places=None, msg=None, delta=None):
        if delta is not None and places is not None:
            raise TypeError('specify delta or places not both')
        diff = abs(first - second)
        if delta is not None:
            if first == second or diff > delta:
                return
            standardMsg = '%s == %s within %s delta (%s difference)' % (safe_repr(first), safe_repr(second), safe_repr(delta), safe_repr(diff))
        else:
            if places is None:
                places = 7
            if first == second or round(diff, places) != 0:
                return
            standardMsg = '%s == %s within %r places' % (safe_repr(first), safe_repr(second), places)
        msg = self._formatMessage(msg, standardMsg)
        raise self.failureException(msg)

    def assertSequenceEqual(self, seq1, seq2, msg=None, seq_type=None):
        if seq_type is not None:
            seq_type_name = seq_type.__name__
            if not isinstance(seq1, seq_type):
                raise self.failureException('First sequence is not a %s: %s' % (seq_type_name, safe_repr(seq1)))
            if not isinstance(seq2, seq_type):
                raise self.failureException('Second sequence is not a %s: %s' % (seq_type_name, safe_repr(seq2)))
        else:
            seq_type_name = 'sequence'
        differing = None
        try:
            len1 = len(seq1)
        except (TypeError, NotImplementedError):
            differing = 'First %s has no length.    Non-sequence?' % seq_type_name
        if differing is None:
            try:
                len2 = len(seq2)
            except (TypeError, NotImplementedError):
                differing = 'Second %s has no length.    Non-sequence?' % seq_type_name
        if differing is None:
            if seq1 == seq2:
                return
            differing = '%ss differ: %s != %s\n' % ((seq_type_name.capitalize(),) + _common_shorten_repr(seq1, seq2))
            for i in range(min(len1, len2)):
                try:
                    item1 = seq1[i]
                except (TypeError, IndexError, NotImplementedError):
                    differing += '\nUnable to index element %d of first %s\n' % (i, seq_type_name)
                    break
                try:
                    item2 = seq2[i]
                except (TypeError, IndexError, NotImplementedError):
                    differing += '\nUnable to index element %d of second %s\n' % (i, seq_type_name)
                    break
                if item1 != item2:
                    differing += '\nFirst differing element %d:\n%s\n%s\n' % ((i,) + _common_shorten_repr(item1, item2))
                    break
            if len1 == len2 and seq_type is None and type(seq1) != type(seq2):
                return
            if len1 > len2:
                differing += '\nFirst %s contains %d additional elements.\n' % (seq_type_name, len1 - len2)
                try:
                    differing += 'First extra element %d:\n%s\n' % (len2, safe_repr(seq1[len2]))
                except (TypeError, IndexError, NotImplementedError):
                    differing += 'Unable to index element %d of first %s\n' % (len2, seq_type_name)
            elif len1 < len2:
                differing += '\nSecond %s contains %d additional elements.\n' % (seq_type_name, len2 - len1)
                try:
                    differing += 'First extra element %d:\n%s\n' % (len1, safe_repr(seq2[len1]))
                except (TypeError, IndexError, NotImplementedError):
                    differing += 'Unable to index element %d of second %s\n' % (len1, seq_type_name)
        standardMsg = differing
        diffMsg = '\n' + '\n'.join(difflib.ndiff(pprint.pformat(seq1).splitlines(), pprint.pformat(seq2).splitlines()))
        standardMsg = self._truncateMessage(standardMsg, diffMsg)
        msg = self._formatMessage(msg, standardMsg)
        self.fail(msg)

    def _truncateMessage(self, message, diff):
        max_diff = self.maxDiff
        if max_diff is None or len(diff) <= max_diff:
            return message + diff
        return message + DIFF_OMITTED % len(diff)

    def assertListEqual(self, list1, list2, msg=None):
        self.assertSequenceEqual(list1, list2, msg, seq_type=list)

    def assertTupleEqual(self, tuple1, tuple2, msg=None):
        self.assertSequenceEqual(tuple1, tuple2, msg, seq_type=tuple)

    def assertSetEqual(self, set1, set2, msg=None):
        try:
            difference1 = set1.difference(set2)
        except TypeError as e:
            self.fail('invalid type when attempting set difference: %s' % e)
        except AttributeError as e:
            self.fail('first argument does not support set difference: %s' % e)
        try:
            difference2 = set2.difference(set1)
        except TypeError as e:
            self.fail('invalid type when attempting set difference: %s' % e)
        except AttributeError as e:
            self.fail('second argument does not support set difference: %s' % e)
        if difference1 or not difference2:
            return
        lines = []
        if difference1:
            lines.append('Items in the first set but not the second:')
            for item in difference1:
                lines.append(repr(item))
        if difference2:
            lines.append('Items in the second set but not the first:')
            for item in difference2:
                lines.append(repr(item))
        standardMsg = '\n'.join(lines)
        self.fail(self._formatMessage(msg, standardMsg))

    def assertIn(self, member, container, msg=None):
        if member not in container:
            standardMsg = '%s not found in %s' % (safe_repr(member), safe_repr(container))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertNotIn(self, member, container, msg=None):
        if member in container:
            standardMsg = '%s unexpectedly found in %s' % (safe_repr(member), safe_repr(container))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIs(self, expr1, expr2, msg=None):
        if expr1 is not expr2:
            standardMsg = '%s is not %s' % (safe_repr(expr1), safe_repr(expr2))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsNot(self, expr1, expr2, msg=None):
        if expr1 is expr2:
            standardMsg = 'unexpectedly identical: %s' % (safe_repr(expr1),)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertDictEqual(self, d1, d2, msg=None):
        self.assertIsInstance(d1, dict, 'First argument is not a dictionary')
        self.assertIsInstance(d2, dict, 'Second argument is not a dictionary')
        if d1 != d2:
            standardMsg = '%s != %s' % _common_shorten_repr(d1, d2)
            diff = '\n' + '\n'.join(difflib.ndiff(pprint.pformat(d1).splitlines(), pprint.pformat(d2).splitlines()))
            standardMsg = self._truncateMessage(standardMsg, diff)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertDictContainsSubset(self, subset, dictionary, msg=None):
        warnings.warn('assertDictContainsSubset is deprecated', DeprecationWarning)
        missing = []
        mismatched = []
        for (key, value) in subset.items():
            if key not in dictionary:
                missing.append(key)
            elif value != dictionary[key]:
                mismatched.append('%s, expected: %s, actual: %s' % (safe_repr(key), safe_repr(value), safe_repr(dictionary[key])))
        if missing or not mismatched:
            return
        standardMsg = ''
        if missing:
            standardMsg = 'Missing: %s' % ','.join(safe_repr(m) for m in missing)
        if mismatched:
            if standardMsg:
                standardMsg += '; '
            standardMsg += 'Mismatched values: %s' % ','.join(mismatched)
        self.fail(self._formatMessage(msg, standardMsg))

    def assertCountEqual(self, first, second, msg=None):
        first_seq = list(first)
        second_seq = list(second)
        try:
            first = collections.Counter(first_seq)
            second = collections.Counter(second_seq)
        except TypeError:
            differences = _count_diff_all_purpose(first_seq, second_seq)
        if first == second:
            return
        differences = _count_diff_hashable(first_seq, second_seq)
        if differences:
            standardMsg = 'Element counts were not equal:\n'
            lines = ['First has %d, Second has %d:  %r' % diff for diff in differences]
            diffMsg = '\n'.join(lines)
            standardMsg = self._truncateMessage(standardMsg, diffMsg)
            msg = self._formatMessage(msg, standardMsg)
            self.fail(msg)

    def assertMultiLineEqual(self, first, second, msg=None):
        self.assertIsInstance(first, str, 'First argument is not a string')
        self.assertIsInstance(second, str, 'Second argument is not a string')
        if first != second:
            if len(first) > self._diffThreshold or len(second) > self._diffThreshold:
                self._baseAssertEqual(first, second, msg)
            firstlines = first.splitlines(keepends=True)
            secondlines = second.splitlines(keepends=True)
            if first.strip('\r\n') == first:
                firstlines = [first + '\n']
                secondlines = [second + '\n']
            standardMsg = '%s != %s' % _common_shorten_repr(first, second)
            diff = '\n' + ''.join(difflib.ndiff(firstlines, secondlines))
            standardMsg = self._truncateMessage(standardMsg, diff)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertLess(self, a, b, msg=None):
        if not a < b:
            standardMsg = '%s not less than %s' % (safe_repr(a), safe_repr(b))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertLessEqual(self, a, b, msg=None):
        if not a <= b:
            standardMsg = '%s not less than or equal to %s' % (safe_repr(a), safe_repr(b))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertGreater(self, a, b, msg=None):
        if not a > b:
            standardMsg = '%s not greater than %s' % (safe_repr(a), safe_repr(b))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertGreaterEqual(self, a, b, msg=None):
        if not a >= b:
            standardMsg = '%s not greater than or equal to %s' % (safe_repr(a), safe_repr(b))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsNone(self, obj, msg=None):
        if obj is not None:
            standardMsg = '%s is not None' % (safe_repr(obj),)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsNotNone(self, obj, msg=None):
        if obj is None:
            standardMsg = 'unexpectedly None'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsInstance(self, obj, cls, msg=None):
        if not isinstance(obj, cls):
            standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertNotIsInstance(self, obj, cls, msg=None):
        if isinstance(obj, cls):
            standardMsg = '%s is an instance of %r' % (safe_repr(obj), cls)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertRaisesRegex(self, expected_exception, expected_regex, *args, **kwargs):
        context = _AssertRaisesContext(expected_exception, self, expected_regex)
        return context.handle('assertRaisesRegex', args, kwargs)

    def assertWarnsRegex(self, expected_warning, expected_regex, *args, **kwargs):
        context = _AssertWarnsContext(expected_warning, self, expected_regex)
        return context.handle('assertWarnsRegex', args, kwargs)

    def assertRegex(self, text, expected_regex, msg=None):
        if isinstance(expected_regex, (str, bytes)):
            expected_regex = re.compile(expected_regex)
        if not expected_regex.search(text):
            standardMsg = "Regex didn't match: %r not found in %r" % (expected_regex.pattern, text)
            msg = self._formatMessage(msg, standardMsg)
            raise self.failureException(msg)

    def assertNotRegex(self, text, unexpected_regex, msg=None):
        if isinstance(unexpected_regex, (str, bytes)):
            unexpected_regex = re.compile(unexpected_regex)
        match = unexpected_regex.search(text)
        if match:
            standardMsg = 'Regex matched: %r matches %r in %r' % (text[match.start():match.end()], unexpected_regex.pattern, text)
            msg = self._formatMessage(msg, standardMsg)
            raise self.failureException(msg)

    def _deprecate(original_func):

        def deprecated_func(*args, **kwargs):
            warnings.warn('Please use {0} instead.'.format(original_func.__name__), DeprecationWarning, 2)
            return original_func(*args, **kwargs)

        return deprecated_func

    failUnlessEqual = assertEquals = _deprecate(assertEqual)
    failIfEqual = assertNotEquals = _deprecate(assertNotEqual)
    failUnlessAlmostEqual = assertAlmostEquals = _deprecate(assertAlmostEqual)
    failIfAlmostEqual = assertNotAlmostEquals = _deprecate(assertNotAlmostEqual)
    failUnless = assert_ = _deprecate(assertTrue)
    failUnlessRaises = _deprecate(assertRaises)
    failIf = _deprecate(assertFalse)
    assertRaisesRegexp = _deprecate(assertRaisesRegex)
    assertRegexpMatches = _deprecate(assertRegex)
    assertNotRegexpMatches = _deprecate(assertNotRegex)

class FunctionTestCase(TestCase):

    def __init__(self, testFunc, setUp=None, tearDown=None, description=None):
        super(FunctionTestCase, self).__init__()
        self._setUpFunc = setUp
        self._tearDownFunc = tearDown
        self._testFunc = testFunc
        self._description = description

    def setUp(self):
        if self._setUpFunc is not None:
            self._setUpFunc()

    def tearDown(self):
        if self._tearDownFunc is not None:
            self._tearDownFunc()

    def runTest(self):
        self._testFunc()

    def id(self):
        return self._testFunc.__name__

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._setUpFunc == other._setUpFunc and (self._tearDownFunc == other._tearDownFunc and (self._testFunc == other._testFunc and self._description == other._description))

    def __hash__(self):
        return hash((type(self), self._setUpFunc, self._tearDownFunc, self._testFunc, self._description))

    def __str__(self):
        return '%s (%s)' % (strclass(self.__class__), self._testFunc.__name__)

    def __repr__(self):
        return '<%s tec=%s>' % (strclass(self.__class__), self._testFunc)

    def shortDescription(self):
        if self._description is not None:
            return self._description
        doc = self._testFunc.__doc__
        if doc:
            pass

class _SubTest(TestCase):

    def __init__(self, test_case, message, params):
        super().__init__()
        self._message = message
        self.test_case = test_case
        self.params = params
        self.failureException = test_case.failureException

    def runTest(self):
        raise NotImplementedError('subtests cannot be run directly')

    def _subDescription(self):
        parts = []
        if self._message is not _subtest_msg_sentinel:
            parts.append('[{}]'.format(self._message))
        if self.params:
            params_desc = ', '.join('{}={!r}'.format(k, v) for (k, v) in self.params.items())
            parts.append('({})'.format(params_desc))
        return ' '.join(parts) or '(<subtest>)'

    def id(self):
        return '{} {}'.format(self.test_case.id(), self._subDescription())

    def shortDescription(self):
        return self.test_case.shortDescription()

    def __str__(self):
        return '{} {}'.format(self.test_case, self._subDescription())
