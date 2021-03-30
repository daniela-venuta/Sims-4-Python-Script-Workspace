from event_testing.tests import TunableTestSetfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInitfrom snippets import define_snippetfrom ui.ui_dialog_notification import UiDialogNotification
class TestedUiDialogNotification(UiDialogNotification):
    FACTORY_TUNABLES = {'tests': TunableTestSet(description='\n            The test(s) to decide whether the notification is to be shown.\n            ')}

    def show_dialog(self, **kwargs):
        if self.tests:
            test_result = self.tests.run_tests(self._resolver)
            if not test_result:
                return
        return super().show_dialog(**kwargs)
(TunableTestedUiDialogNotificationReference, TunableTestedUiDialogNotificationSnippet) = define_snippet('tested_notification', TestedUiDialogNotification.TunableFactory())