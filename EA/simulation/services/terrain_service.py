from objects.components.types import PORTAL_COMPONENTfrom objects.object_enums import ItemLocationfrom objects.pools import pool_utilsfrom objects.terrain import PoolPoint, OceanPoint, TerrainPointfrom routing import SurfaceIdentifier, SurfaceTypefrom sims4.tuning.tunable import TunableReference, TunablePackSafeReferencefrom tag import TunableTagfrom world.ocean_tuning import OceanTuningimport build_buyimport routingimport servicesimport sims4.logimport sims4.mathimport sims4.reloadimport sims4.service_managerwith sims4.reload.protected(globals()):
    _terrain_object = None
    _ocean_object = Nonelogger = sims4.log.Logger('Terrain', default_owner='rmccord')
class TerrainService(sims4.service_manager.Service):
    TERRAIN_DEFINITION = TunableReference(description='\n        The definition used to instantiate the Terrain object.\n        ', manager=services.definition_manager(), class_restrictions='Terrain')
    OCEAN_DEFINITION = TunableReference(description='\n        The definition for the Ocean object.\n        ', manager=services.definition_manager(), class_restrictions='Ocean')
    WALKSTYLE_PORTAL_DATA = TunablePackSafeReference(description='\n        The portal used for traversing between different terrain types (to change walkstyle).\n        ', manager=services.snippet_manager(), class_restrictions=('PortalData',))
    WALKSTYLE_PORTAL_LOCATOR_TAG = TunableTag(description='\n        The tag we can use to get the walkstyle portal definition.\n        ')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._walkstyle_portal_definition = None

    def start(self):
        create_terrain_object()
        return True

    def on_zone_load(self):
        try_create_ocean_object()
        self.setup_walkstyle_portals()

    def on_zone_unload(self):
        global _ocean_object
        if _ocean_object is not None:
            _ocean_object.destroy()
            _ocean_object = None

    def stop(self):
        destroy_terrain_object()

    def get_walkstyle_portal_definition(self):
        if self._walkstyle_portal_definition is None:
            for definition in services.definition_manager().get_definitions_for_tags_gen((self.WALKSTYLE_PORTAL_LOCATOR_TAG,)):
                self._walkstyle_portal_definition = definition
                break
        return self._walkstyle_portal_definition

    def setup_walkstyle_portals(self):
        portal_component = _terrain_object.get_component(PORTAL_COMPONENT) if _terrain_object is not None else None
        if portal_component is None:
            return
        locator_manager = services.locator_manager()
        portal_definition = self.get_walkstyle_portal_definition()
        if portal_definition is None:
            logger.error('setup_walkstyle_portals() failed to get walkstyle portal definition.')
            return
        locators = locator_manager.get(portal_definition.id)
        initial_transforms = [locator.transform for locator in locators]
        if not initial_transforms:
            return
        portal_ids = []
        self._create_all_transforms_and_portals_for_initial_transforms(initial_transforms, store_portal_ids=portal_ids)
        if portal_ids:
            services.object_manager().add_portal_to_cache(_terrain_object)

    def _create_all_transforms_and_portals_for_initial_transforms(self, initial_transforms, store_portal_ids=None):
        portal_component = _terrain_object.get_component(PORTAL_COMPONENT) if _terrain_object is not None else None
        if portal_component is None:
            return
        portal_component.refresh_enabled = False
        routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD)
        walkstyle_portal = TerrainService.WALKSTYLE_PORTAL_DATA
        if walkstyle_portal is None:
            return
        for portal_transform in initial_transforms:
            portal_location = sims4.math.Location(portal_transform, routing_surface=routing_surface)
            portal_ids = portal_component.add_custom_portal(TerrainPoint(portal_location), walkstyle_portal)
            add_portals = []
            for portal_id in portal_ids:
                portal_instance = portal_component.get_portal_by_id(portal_id)
                if portal_instance is not None:
                    add_portals.append(portal_id)
            if add_portals and store_portal_ids is not None:
                store_portal_ids.extend(add_portals)

    @staticmethod
    def create_surface_proxy_from_location(location):
        position = location.transform.translation
        zone_id = services.current_zone_id()
        routing_surface = location.routing_surface
        level = routing_surface.secondary_id
        pool_block_id = 0
        if build_buy.is_location_pool(position, level):
            pool_block_id = build_buy.get_block_id(zone_id, position, level - 1)
            if not pool_block_id:
                logger.error('Failed ot get pool block id from location: {} ', location)
                return
            pool = pool_utils.get_pool_by_block_id(pool_block_id)
            if pool is None:
                logger.error('Failed to get pool from pool block id {} at location: {}', pool_block_id, location)
                return
            return PoolPoint(location, pool)
        if routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
            if services.terrain_service.ocean_object() is None:
                logger.error('Ocean does not exist at location: {}', location)
                return
            return OceanPoint(location)
        return TerrainPoint(location)

def terrain_object():
    if _terrain_object is None:
        raise RuntimeError('Attempting to access the terrain object before it is created.')
    return _terrain_object

def ocean_object():
    return _ocean_object

def create_terrain_object():
    global _terrain_object
    if _terrain_object is None:
        from objects.system import create_script_object
        _terrain_object = create_script_object(TerrainService.TERRAIN_DEFINITION)

def destroy_terrain_object():
    global _terrain_object
    _terrain_object = None

def try_create_ocean_object():
    global _ocean_object
    if _ocean_object is not None:
        return
    beach_locator_def = OceanTuning.get_beach_locator_definition()
    if beach_locator_def is None:
        return
    locator_manager = services.locator_manager()
    locators = locator_manager.get(beach_locator_def.id)
    if not locators:
        return

    def move_ocean(ocean):
        zone = services.current_zone()
        terrain_center = zone.lot.center
        location = sims4.math.Location(sims4.math.Transform(translation=terrain_center, orientation=sims4.math.Quaternion.IDENTITY()), routing_surface=SurfaceIdentifier(zone.id, 0, SurfaceType.SURFACETYPE_WORLD))
        ocean.location = location

    from objects.system import create_object
    _ocean_object = create_object(TerrainService.OCEAN_DEFINITION, post_add=move_ocean, loc_type=ItemLocation.FROM_OPEN_STREET)
