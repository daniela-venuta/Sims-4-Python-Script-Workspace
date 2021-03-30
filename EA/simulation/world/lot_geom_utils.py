import build_buyimport servicesfrom plex.plex_enums import INVALID_PLEX_IDfrom sims4.geometry import Polygon, random_uniform_points_in_compound_polygon, CompoundPolygon
def get_random_points_on_floor(level_index, num=1):
    plex_service = services.get_plex_service()
    plex_id = plex_service.get_active_zone_plex_id() or INVALID_PLEX_ID
    polygons = []
    for (poly_data, block_level_index) in build_buy.get_all_block_polygons(plex_id).values():
        if block_level_index != level_index:
            pass
        else:
            for p in poly_data:
                polygon = Polygon(list(reversed(p)))
                polygon.normalize()
                if polygon.area() <= 0:
                    pass
                else:
                    polygons.append(polygon)
    if not polygons:
        return
    return random_uniform_points_in_compound_polygon(CompoundPolygon(polygons), num=num)
