from bucks.bucks_enums import BucksTypefrom fishing.fishing_data import TunableFishingDataSnippetfrom objects.components import ComponentContainer, forward_to_componentsfrom objects.components.statistic_component import HasStatisticComponentfrom seasons.seasonal_parameters_mixin import SeasonalParametersMixinfrom seasons.seasons_enums import SeasonType, SeasonParametersfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.outfits.outfit_generator import TunableOutfitGeneratorSnippet, OutfitGeneratorfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableEnumSet, TunableMapping, TunableRegionDescription, TunableReference, TunableList, Tunable, TunableEnumEntry, TunableTuple, TunableRange, OptionalTunable, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import constpropertyfrom tunable_time import TunableTimeOfDayfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom world.terrain_enums import TerrainTagimport enumimport servicesimport sims4.logimport tagfrom weather.weather_tuning_mixin import WeatherTuningMixinlogger = sims4.log.Logger('Region')
class RegionType(enum.Int):
    REGIONTYPE_NONE = 0
    REGIONTYPE_RESIDENTIAL = 1
    REGIONTYPE_DESTINATION = 2

class _RegionalRequiredOutfitGenerator(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'outfit_category': TunableEnumEntry(description='\n            The outfit category that is required for the region.\n            ', default=OutfitCategory.SWIMWEAR, tunable_type=OutfitCategory, invalid_enums=(OutfitCategory.CURRENT_OUTFIT, OutfitCategory.CAREER, OutfitCategory.SITUATION, OutfitCategory.SPECIAL)), 'generator': TunableOutfitGeneratorSnippet()}

    def generate_outfit(self, sim_info):
        if sim_info.has_outfit_category(self.outfit_category):
            return
        OutfitGenerator.generate_outfit(self, sim_info, self.outfit_category)

class Region(HasTunableReference, ComponentContainer, HasStatisticComponent, WeatherTuningMixin, SeasonalParametersMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.region_manager()):
    REGION_DESCRIPTION_TUNING_MAP = TunableMapping(description='\n        A mapping between Catalog region description and tuning instance. This\n        way we can find out what region description the current zone belongs to\n        at runtime then grab its tuning instance.\n        ', key_type=TunableRegionDescription(description='\n            Catalog-side Region Description.\n            ', pack_safe=True, export_modes=ExportModes.All), value_type=TunableReference(description="\n            Region Tuning instance. This is retrieved at runtime based on what\n            the active zone's region description is.\n            ", pack_safe=True, manager=services.region_manager(), export_modes=ExportModes.All), key_name='RegionDescription', value_name='Region', tuple_name='RegionDescriptionMappingTuple', export_modes=ExportModes.All)
    INSTANCE_TUNABLES = {'gallery_download_venue_map': TunableMapping(description='\n            A map from gallery venue to instanced venue. We need to be able to\n            convert gallery venues into other venues that are only compatible\n            with that region.\n            ', key_type=TunableReference(description='\n                A venue type that exists in the gallery.\n                ', manager=services.venue_manager(), export_modes=ExportModes.All, pack_safe=True), value_type=TunableReference(description='\n                The venue type that the gallery venue will become when it is\n                downloaded into this region.\n                ', manager=services.venue_manager(), export_modes=ExportModes.All, pack_safe=True), key_name='gallery_venue_type', value_name='region_venue_type', tuple_name='GalleryDownloadVenueMappingTuple', export_modes=ExportModes.All), 'compatible_venues': TunableList(description='\n            A list of venues that are allowed to be set by the player in this\n            region.\n            ', tunable=TunableReference(description='\n                A venue that the player can set in this region.\n                ', manager=services.venue_manager(), export_modes=ExportModes.All, pack_safe=True), export_modes=ExportModes.All), 'tags': TunableList(description='\n            Tags that are used to group regions. Destination Regions will\n            likely have individual tags, but Home/Residential Regions will\n            share a tag.\n            ', tunable=TunableEnumEntry(description='\n                A Tag used to group this region. Destination Regions will\n                likely have individual tags, but Home/Residential Regions will\n                share a tag.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)), 'region_buffs': TunableList(description='\n            A list of buffs that are added on Sims while they are instanced in\n            this region.\n            ', tunable=TunableReference(description='\n                A buff that exists on Sims while they are instanced in this\n                region.\n                ', manager=services.buff_manager(), pack_safe=True)), 'store_travel_group_placed_objects': Tunable(description='\n            If checked, any placed objects while in a travel group will be returned to household inventory once\n            travel group is disbanded.\n            ', tunable_type=bool, default=False), 'travel_group_build_disabled_tooltip': TunableLocalizedString(description='\n            The string that will appear in the tooltip of the grayed out build\n            mode button if build is being disabled because of a travel group in\n            this region.\n            ', allow_none=True, export_modes=ExportModes.All), 'sunrise_time': TunableTimeOfDay(description='\n            The time, in Sim-time, the sun rises in this region.\n            ', default_hour=6, tuning_group=GroupNames.TIME), 'seasonal_sunrise_time': TunableMapping(description='\n            A mapping between season and sunrise time.  If the current season\n            is not found then we will default to the tuned sunrise time.\n            ', key_type=TunableEnumEntry(description='\n                The season.\n                ', tunable_type=SeasonType, default=SeasonType.SUMMER), value_type=TunableTimeOfDay(description='\n                The time, in Sim-time, the sun rises in this region, in this\n                season.\n                ', default_hour=6, tuning_group=GroupNames.TIME)), 'sunset_time': TunableTimeOfDay(description='\n            The time, in Sim-time, the sun sets in this region.\n            ', default_hour=20, tuning_group=GroupNames.TIME), 'seasonal_sunset_time': TunableMapping(description='\n            A mapping between season and sunset time.  If the current season\n            is not found then we will default to the tuned sunset time.\n            ', key_type=TunableEnumEntry(description='\n                The season.\n                ', tunable_type=SeasonType, default=SeasonType.SUMMER), value_type=TunableTimeOfDay(description='\n                The time, in Sim-time, the sun sets in this region, in this\n                season.\n                ', default_hour=20, tuning_group=GroupNames.TIME)), 'provides_sunlight': Tunable(description='\n            If enabled, this region provides sunlight between the tuned Sunrise\n            Time and Sunset Time. This is used for gameplay effect (i.e.\n            Vampires).\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.TIME), 'weather_supports_fresh_snow': Tunable(description='\n            If enabled, this region supports fresh snow.\n            ', tunable_type=bool, default=True), 'fishing_data': OptionalTunable(description='\n            If enabled, define all of the data for fishing locations in this region.\n            Only used if objects are tuned to use region fishing data.\n            ', tunable=TunableFishingDataSnippet()), 'welcome_wagon_replacement': OptionalTunable(description='\n            If enabled then we will replace the Welcome Wagon with a new situation.\n            \n            If the narrative is also set to replace the welcome wagon that will take precedent over this replacement.\n            ', tunable=TunableReference(description='\n                The situation we will use to replace the welcome wagon.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))), 'region_currency_bucks_type': TunableEnumEntry(description='\n            If this is set to INVALID, this region will by default use Simoleon as\n            currency type. Otherwise it will use selected bucks type as currency type.\n            ', tunable_type=BucksType, default=BucksType.INVALID, export_modes=ExportModes.All), 'outfit_category_restrictions': TunableTuple(description='\n            A setting which specifies which outfits Sims are able to have in this region.\n            ', travel_groups_only=Tunable(description='\n                When set, this applies only to Sims in travel groups.\n                ', tunable_type=bool, default=False), required_outfit_category=OptionalTunable(description='\n                If set, when a playable Sim spawns into this region, they are granted an outfit in this outfit category\n                if they do not have one set.\n                ', tunable=_RegionalRequiredOutfitGenerator.TunableFactory()), allowed_outfits=TunableWhiteBlackList(description='\n                The outfit categories that are valid for this region.\n                ', tunable=TunableEnumEntry(default=OutfitCategory.EVERYDAY, tunable_type=OutfitCategory, invalid_enums=(OutfitCategory.CURRENT_OUTFIT,)))), 'default_outfit_category': TunableEnumEntry(description='\n            The default outfit category to set on the played Sim if they were in an invalid outfit category for this\n            region when they were last saved.\n            ', default=OutfitCategory.EVERYDAY, tunable_type=OutfitCategory, invalid_enums=(OutfitCategory.CURRENT_OUTFIT,)), 'is_persistable': Tunable(description='\n            If true, we will create an instance for this region and save/load it. The instance has a commodity tracker\n            which can be used for region based commodities.\n            ', tunable_type=bool, default=False), 'region_type': TunableEnumEntry(description='\n            The region type for this region.  Keep in sync with UI region\n            tuning in Tuning->ui.ui_tuning->UiTuning->Pack Specific Data->\n            [Pack] -> Region List -> region type\n            ', tunable_type=RegionType, default=RegionType.REGIONTYPE_RESIDENTIAL), 'is_summit_weather_enabled': Tunable(description='\n            Whether this region has summit (EP10) weather enabled.\n            ', tunable_type=bool, default=False), 'tracked_terrain_tags': OptionalTunable(description='\n            What terrain transitions should be tracked in this region. Used to tuned which terrains\n            are important and exist in this region.\n            ', tunable=TunableEnumSet(enum_type=TerrainTag, enum_default=TerrainTag.INVALID))}

    def save(self, region_data):
        region_data.region_id = self.guid64
        region_data.ClearField('commodity_tracker')
        (commodities, _, _) = self.commodity_tracker.save()
        region_data.commodity_tracker.commodities.extend(commodities)

    def load(self, region_data):
        self.commodity_tracker.load(region_data.commodity_tracker.commodities)

    @forward_to_components
    def on_finalize_load(self):
        pass

    @constproperty
    def is_sim():
        return False

    @property
    def is_downloaded(self):
        return False

    @classmethod
    def _cls_repr(cls):
        return "Region: <class '{}.{}'>".format(cls.__module__, cls.__name__)

    @classmethod
    def is_region_compatible(cls, region_instance, ignore_tags=False):
        if region_instance is cls or region_instance is None:
            return True
        if ignore_tags:
            return False
        for tag in cls.tags:
            if tag in region_instance.tags:
                return True
        return False

    @classmethod
    def is_sim_info_compatible(cls, sim_info):
        other_region = get_region_instance_from_zone_id(sim_info.zone_id)
        if cls.is_region_compatible(other_region):
            return True
        else:
            travel_group_id = sim_info.travel_group_id
            if travel_group_id:
                travel_group = services.travel_group_manager().get(travel_group_id)
                if travel_group is not None and not travel_group.played:
                    return True
        return False

    @classmethod
    def get_sunrise_time(cls):
        season_service = services.season_service()
        if season_service is None:
            return cls.sunrise_time
        return cls.seasonal_sunrise_time.get(season_service.season, cls.sunrise_time)

    @classmethod
    def get_sunset_time(cls):
        season_service = services.season_service()
        if season_service is None:
            return cls.sunset_time
        return cls.seasonal_sunset_time.get(season_service.season, cls.sunset_time)

def get_region_instance_from_zone_id(zone_id):
    zone_proto = services.get_persistence_service().get_zone_proto_buff(zone_id)
    if zone_proto is None:
        return
    return get_region_instance_from_world_id(zone_proto.world_id)

def get_region_description_id_from_zone_id(zone_id):
    persistence_service = services.get_persistence_service()
    zone_proto = persistence_service.get_zone_proto_buff(zone_id)
    if zone_proto is None:
        return
    return persistence_service.get_region_id_from_world_id(zone_proto.world_id)

def get_region_instance_from_world_id(world_id):
    region_description_id = services.get_persistence_service().get_region_id_from_world_id(world_id)
    if region_description_id is None:
        return
    return Region.REGION_DESCRIPTION_TUNING_MAP.get(region_description_id)
