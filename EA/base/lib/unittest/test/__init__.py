import os
def suite():
    suite = unittest.TestSuite()
    for fn in os.listdir(here):
        if fn.startswith('test') and fn.endswith('.py'):
            modname = 'unittest.test.' + fn[:-3]
            __import__(modname)
            module = sys.modules[modname]
            suite.addTest(loader.loadTestsFromModule(module))
    suite.addTest(loader.loadTestsFromName('unittest.test.testmock'))
    return suite

    unittest.main(defaultTest='suite')