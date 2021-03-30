import servicesfrom event_testing.resolver import SingleSimResolverfrom rabbit_hole.rabbit_hole import RabbitHole, RabbitHolePhase, RabbitHoleTimingPolicyfrom sims4.tuning.instances import lock_instance_tunables
class CareerRabbitHole(RabbitHole):

    def __init__(self, *args, career_uid=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._career_uid = career_uid

    @classmethod
    def get_affordance(cls, sim_info, career_uid):
        career = services.sim_info_manager().get(sim_info.sim_id).career_tracker.get_career_by_uid(career_uid)
        if career is None:
            return
        resolver = SingleSimResolver(sim_info)
        for tested_affordance_tuning in career.tested_affordances:
            if tested_affordance_tuning.tests.run_tests(resolver):
                return tested_affordance_tuning.affordance
        if sim_info.is_at_home:
            return career.career_affordance

    def select_affordance(self):
        if self._selected_affordance is not None:
            return self._selected_affordance
        sim_info = services.sim_info_manager().get(self.sim_id)
        self._selected_affordance = self.get_affordance(sim_info, self._career_uid)
        return self._selected_affordance

    def is_valid_to_restore(self, sim_info):
        career_tracker = sim_info.career_tracker
        if career_tracker is None:
            return False
        career = career_tracker.get_career_by_uid(self._career_uid)
        if career is None:
            return False
        return super().is_valid_to_restore(sim_info)

    @classmethod
    def get_travel_affordance(cls, sim_info, career_uid):
        career = sim_info.career_tracker.get_career_by_uid(career_uid)
        return career.go_home_to_work_affordance

    def select_travel_affordance(self):
        sim_info = services.sim_info_manager().get(self.sim_id)
        return self.get_travel_affordance(sim_info, self._career_uid)

    def on_activate(self):
        super().on_activate()
        career = services.sim_info_manager().get(self.sim_id).career_tracker.get_career_by_uid(self._career_uid)
        career.attend_work()

    def on_remove(self, canceled=False):
        super().on_remove(canceled=canceled)
        if canceled:
            sim_info = services.sim_info_manager().get(self.sim_id)
            if sim_info is not None and sim_info.career_tracker is not None:
                career = sim_info.career_tracker.get_career_by_uid(self._career_uid)
                if career is None:
                    return
                if self.is_active():
                    career.leave_work(left_early=True)
                else:
                    career.on_inactive_rabbit_hole_canceled()

    def save(self, rabbit_hole_data):
        super().save(rabbit_hole_data)
        rabbit_hole_data.career_uid = self._career_uid

    def load(self, rabbit_hole_data):
        super().load(rabbit_hole_data)
        self._career_uid = rabbit_hole_data.career_uid
lock_instance_tunables(CareerRabbitHole, away_action=None, time_tracking_policy=RabbitHoleTimingPolicy.NO_TIME_LIMIT, affordance=None, tested_affordances=None, go_home_and_attend=None)