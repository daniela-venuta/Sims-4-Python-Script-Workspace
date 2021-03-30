from debugvis import Contextfrom sims4.color import Colorimport servicesimport sims4.loglogger = sims4.log.Logger('Debugvis')
class ObjectRouteVisualizer:
    TUNNEL_OFFSET = 0.1
    ENDPOINT_INNER_CIRCLE_RADIUS = 0.15
    ENDPOINT_OUTER_CIRCLE_RADIUS = 0.18
    NODE_RADIUS = 0.075
    PORTAL_THERE_HEIGHT = 6.0
    PORTAL_BACK_HEIGHT = 4.0
    PORTAL_ARCH_DETAIL = 6

    def __init__(self, layer, route):
        self.layer = layer
        self.route = route
        self._start()

    def _start(self):
        self._draw_path()

    def stop(self):
        pass

    def _draw_path(self):
        with Context(self.layer) as context:
            context.layer.clear()
            if self.route is None:
                return
            verticies_left = []
            verticies_right = []
            for index in range(len(self.route) - 1, 0, -1):
                cur_node = self.route[index]
                prev_node = self.route[index - 1]
                cur_pos = sims4.math.Vector3(cur_node.position[0], cur_node.position[1], cur_node.position[2])
                prev_pos = sims4.math.Vector3(prev_node.position[0], prev_node.position[1], prev_node.position[2])
                context.add_segment(prev_pos, cur_pos, color=Color.CYAN)
                portal = services.object_manager().get(cur_node.portal_object_id)
                if portal is not None:
                    for portal_instance in portal.get_portal_instances():
                        if portal_instance.there is not None:
                            self._draw_portal_pair(portal_instance, portal_instance.there, context, Color.CYAN, Color.MAGENTA, self.PORTAL_THERE_HEIGHT, self.PORTAL_ARCH_DETAIL)
                        if portal_instance.back is not None:
                            self._draw_portal_pair(portal_instance, portal_instance.back, context, Color.GREEN, Color.ORANGE, self.PORTAL_BACK_HEIGHT, self.PORTAL_ARCH_DETAIL)
                vector = cur_pos - prev_pos
                vector = sims4.math.vector_cross(sims4.math.Vector3.Y_AXIS(), vector)
                if vector.magnitude() != 0:
                    vector = sims4.math.vector_normalize(vector)
                tunnel_p1 = cur_pos + vector*self.TUNNEL_OFFSET
                tunnel_p2 = prev_pos + vector*self.TUNNEL_OFFSET
                tunnel_p3 = cur_pos + vector*-self.TUNNEL_OFFSET
                tunnel_p4 = prev_pos + vector*-self.TUNNEL_OFFSET
                verticies_left.append(tunnel_p1)
                verticies_right.append(tunnel_p3)
                if index == 1:
                    context.add_circle(prev_pos, radius=0.15, color=Color.GREEN)
                    context.add_circle(prev_pos, radius=0.18, color=Color.GREEN)
                    verticies_left.append(tunnel_p2)
                    verticies_left.append(prev_pos)
                    verticies_left.append(tunnel_p4)
                if index == len(self.route) - 1:
                    context.add_circle(cur_pos, radius=self.ENDPOINT_INNER_CIRCLE_RADIUS, color=Color.RED)
                    context.add_circle(cur_pos, radius=self.ENDPOINT_OUTER_CIRCLE_RADIUS, color=Color.RED)
                    verticies_right.append(tunnel_p1)
                    verticies_right.append(cur_pos)
                    verticies_right.append(tunnel_p3)
                else:
                    context.add_circle(cur_pos, radius=self.NODE_RADIUS, color=Color.CYAN)
            verticies_right.reverse()
            verticies_left.extend(verticies_right)
            context.add_polygon(verticies_left, color=Color.GREEN)

    def _draw_portal_pair(self, portal_instance, portal_id, layer, color_entry, color_exit, height, detail):
        (p_entry, p_exit) = portal_instance.get_portal_locations(portal_id)
        layer.add_arch(p_entry, p_exit, height=height, detail=detail, color_a=color_entry, color_b=color_exit)
