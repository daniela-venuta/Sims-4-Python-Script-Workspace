import contextlibimport difflibimport pprintimport pickleimport reimport sysimport loggingimport warningsimport weakrefimport inspectfrom copy import deepcopyfrom test import supportimport unittestfrom unittest.test.support import TestEquality, TestHashing, LoggingResult, LegacyLoggingResult, ResultWithNoStartTestRunStopTestRunfrom test.support import captured_stderrlog_foo = logging.getLogger('foo')log_foobar = logging.getLogger('foo.bar')log_quux = logging.getLogger('quux')
class Test(object):

    class Foo(unittest.TestCase):

        def runTest(self):
            pass

        def test1(self):
            pass

    class Bar(Foo):

        def test2(self):
            pass

    class LoggingTestCase(unittest.TestCase):

        def __init__(self, events):
            super(Test.LoggingTestCase, self).__init__('test')
            self.events = events

        def setUp(self):
            self.events.append('setUp')

        def test(self):
            self.events.append('test')

        def tearDown(self):
            self.events.append('tearDown')
