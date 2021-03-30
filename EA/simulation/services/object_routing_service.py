from _weakrefset import WeakSetfrom event_testing.register_test_event_mixin import RegisterTestEventMixinfrom sims4.service_manager import Servicefrom _collections import defaultdict
class ObjectRoutingService(RegisterTestEventMixin, Service):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_objects = defaultdict(WeakSet)

    def on_routing_start(self, obj, tracking_category, behavior):
        self._active_objects[tracking_category].add(obj)

    def on_routing_stop(self, obj, tracking_category):
        self._active_objects[tracking_category].remove(obj)

    def get_routing_object_set(self, tracking_category):
        return self._active_objects[tracking_category]

    def get_routing_object_count(self, tracking_category):
        return len(self.get_routing_object_set(tracking_category))
