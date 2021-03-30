from debugvis import Context, KEEP_ALTITUDEfrom objects.components.spawner_component_enums import SpawnerTypefrom objects.components.types import SPAWNER_COMPONENTfrom sims4.color import pseudo_random_colorimport services
class SpawnerVisualizer:

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        self._draw_spawner_constraints()

    def stop(self):
        pass

    def _draw_spawner_constraints(self):
        with Context(self.layer) as layer:
            for obj in services.object_manager().get_all_objects_with_component_gen(SPAWNER_COMPONENT):
                position = obj.position
                spawner_component = obj.get_component(SPAWNER_COMPONENT)
                radii = []
                slot_positions = []
                for data in spawner_component._spawner_data:
                    if data.spawner_option.spawn_type == SpawnerType.GROUND_SPAWNER and data.spawner_option.radius not in radii:
                        radii.append(data.spawner_option.radius)
                    if data.spawner_option.spawn_type == SpawnerType.SLOT_SPAWNER:
                        slot_types = {data.spawner_option.slot_type}
                        for slot in obj.get_runtime_slots_gen(slot_types=slot_types):
                            slot_positions.append(slot.position)
                spawner_color = pseudo_random_color(obj.id)
                for radius in radii:
                    layer.add_circle(position, radius, color=spawner_color)
                for slot in slot_positions:
                    layer.add_point(slot, color=spawner_color, altitude=KEEP_ALTITUDE)
