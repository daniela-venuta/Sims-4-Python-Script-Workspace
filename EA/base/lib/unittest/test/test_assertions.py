import datetimeimport warningsimport weakrefimport unittestfrom itertools import product
class Test_Assertions(unittest.TestCase):

    def test_AlmostEqual(self):
        self.assertAlmostEqual(1.00000001, 1.0)
        self.assertNotAlmostEqual(1.0000001, 1.0)
        self.assertRaises(self.failureException, self.assertAlmostEqual, 1.0000001, 1.0)
        self.assertRaises(self.failureException, self.assertNotAlmostEqual, 1.00000001, 1.0)
        self.assertAlmostEqual(1.1, 1.0, places=0)
        self.assertRaises(self.failureException, self.assertAlmostEqual, 1.1, 1.0, places=1)
        self.assertAlmostEqual(0, (0.1+0.1j), places=0)
        self.assertNotAlmostEqual(0, (0.1+0.1j), places=1)
        self.assertRaises(self.failureException, self.assertAlmostEqual, 0, (0.1+0.1j), places=1)
        self.assertRaises(self.failureException, self.assertNotAlmostEqual, 0, (0.1+0.1j), places=0)
        self.assertAlmostEqual(float('inf'), float('inf'))
        self.assertRaises(self.failureException, self.assertNotAlmostEqual, float('inf'), float('inf'))

    def test_AmostEqualWithDelta(self):
        self.assertAlmostEqual(1.1, 1.0, delta=0.5)
        self.assertAlmostEqual(1.0, 1.1, delta=0.5)
        self.assertNotAlmostEqual(1.1, 1.0, delta=0.05)
        self.assertNotAlmostEqual(1.0, 1.1, delta=0.05)
        self.assertAlmostEqual(1.0, 1.0, delta=0.5)
        self.assertRaises(self.failureException, self.assertNotAlmostEqual, 1.0, 1.0, delta=0.5)
        self.assertRaises(self.failureException, self.assertAlmostEqual, 1.1, 1.0, delta=0.05)
        self.assertRaises(self.failureException, self.assertNotAlmostEqual, 1.1, 1.0, delta=0.5)
        self.assertRaises(TypeError, self.assertAlmostEqual, 1.1, 1.0, places=2, delta=2)
        self.assertRaises(TypeError, self.assertNotAlmostEqual, 1.1, 1.0, places=2, delta=2)
        first = datetime.datetime.now()
        second = first + datetime.timedelta(seconds=10)
        self.assertAlmostEqual(first, second, delta=datetime.timedelta(seconds=20))
        self.assertNotAlmostEqual(first, second, delta=datetime.timedelta(seconds=5))

    def test_assertRaises(self):

        def _raise(e):
            raise e

        self.assertRaises(KeyError, _raise, KeyError)
        self.assertRaises(KeyError, _raise, KeyError('key'))
        try:
            self.assertRaises(KeyError, lambda : None)
        except self.failureException as e:
            self.assertIn('KeyError not raised', str(e))
        self.fail("assertRaises() didn't fail")
        try:
            self.assertRaises(KeyError, _raise, ValueError)
        except ValueError:
            pass
        self.fail("assertRaises() didn't let exception pass through")
        with self.assertRaises(KeyError) as cm:
            try:
                raise KeyError
            except Exception as e:
                exc = e
                raise
        self.assertIs(cm.exception, exc)
        with self.assertRaises(KeyError):
            raise KeyError('key')
        try:
            with self.assertRaises(KeyError):
                pass
        except self.failureException as e:
            self.assertIn('KeyError not raised', str(e))
        self.fail("assertRaises() didn't fail")
        try:
            with self.assertRaises(KeyError):
                raise ValueError
        except ValueError:
            pass
        self.fail("assertRaises() didn't let exception pass through")

    def test_assertRaises_frames_survival(self):

        class A:
            pass

        wr = None

        class Foo(unittest.TestCase):

            def foo(self):
                nonlocal wr
                a = A()
                wr = weakref.ref(a)
                try:
                    raise OSError
                except OSError:
                    raise ValueError

            def test_functional(self):
                self.assertRaises(ValueError, self.foo)

            def test_with(self):
                with self.assertRaises(ValueError):
                    self.foo()

        Foo('test_functional').run()
        self.assertIsNone(wr())
        Foo('test_with').run()
        self.assertIsNone(wr())

    def testAssertNotRegex(self):
        self.assertNotRegex('Ala ma kota', 'r+')
        try:
            self.assertNotRegex('Ala ma kota', 'k.t', 'Message')
        except self.failureException as e:
            self.assertIn('Message', e.args[0])
        self.fail('assertNotRegex should have failed.')
