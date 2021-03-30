from seasons.seasonal_parameters_mixin import SeasonalParametersMixinfrom sims4.math import Vector2from sims4.tuning.geometric import TunableVector3, TunableVector2from sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableMapping, TunableWorldDescription, TunableReference, TunableList, TunableTuple, TunableRange, TunablePackSafeReference, OptionalTunable, TunableEnumEntry, TunableLotDescription, TunableSet, Tunableimport sims4.logimport worldfrom civic_policies.street_civic_policy_provider import StreetProviderfrom filters.tunable import FilterTermVariantfrom interactions.utils.tested_variant import TunableGlobalTestListfrom sims.sim_spawner_enums import SimNameTypeimport servicesfrom weather.weather_tuning_mixin import WeatherTuningMixinlogger = sims4.log.Logger('Street', default_owner='rmccord')
class Street(HasTunableReference, WeatherTuningMixin, SeasonalParametersMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.street_manager()):
    WORLD_DESCRIPTION_TUNING_MAP = TunableMapping(description='\n        A mapping between Catalog world description and street tuning instance.\n        This way we can find out what world description the current zone\n        belongs to at runtime then grab its street tuning instance.\n        ', key_type=TunableWorldDescription(description='\n            Catalog-side World Description.\n            ', pack_safe=True), value_type=TunableReference(description="\n            Street Tuning instance. This is retrieved at runtime based on what\n            the active zone's world description is.\n            ", pack_safe=True, manager=services.street_manager()), key_name='WorldDescription', value_name='Street')
    INSTANCE_TUNABLES = {'open_street_director': TunablePackSafeReference(description='\n            The Scheduling Open Street Director to use for this world file.\n            This open street director will be able to load object layers and\n            spin up situations.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OPEN_STREET_DIRECTOR)), 'travel_lot': OptionalTunable(description='\n            If enabled then this street will have a specific lot that it will\n            want to travel to when we travel to this "street."\n            ', tunable=TunableLotDescription(description='\n                The specific lot that we will travel to when asked to travel to\n                this street.\n                ')), 'vacation_lot': OptionalTunable(description='\n            If enabled then when a vacation is requested targeting a zone on this street,\n            override it with a zone that is associated with the given lot instead.\n            ', tunable=TunableLotDescription(description='\n                The specific lot that will host the vacation group.\n                ')), 'townie_demographics': TunableTuple(description='\n            Townie population demographics for the street.\n            ', target_population=OptionalTunable(description='\n                If enabled, Sims created for other purposes will passively be\n                assigned to live on this street, gaining the filter features.\n                Sims are assigned out in round robin fashion up until all\n                streets have reached their target, after which those streets\n                will be assigned Sims in round robin fashion past their target.\n                \n                If disabled, this street will not passively be assigned townies\n                unless the Lives On Street filter explicitly requires the\n                Sim to be on the street.\n                ', tunable=TunableRange(description="\n                    The ideal number of townies that live on the street.\n                    \n                    0 is valid if you don't want Sims to live on this street\n                    while other streets haven't met their target population.\n                    ", tunable_type=int, default=1, minimum=0)), filter_features=TunableList(description='\n                Sims created as townies living on this street, they will gain\n                one set of features in this list. Features are applied as\n                Sim creation tags and additional filter terms to use.\n                ', tunable=TunableTuple(description='\n                    ', filter_terms=TunableList(description='\n                        Filter terms to inject into the filter.\n                        ', tunable=FilterTermVariant(conform_optional=True)), sim_creator_tags=TunableReference(description="\n                        Tags to inject into the filter's Sim template.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.TAG_SET), allow_none=True, class_restrictions=('TunableTagSet',)), sim_name_type=TunableEnumEntry(description='\n                        What type of name the sim should have.\n                        ', tunable_type=SimNameType, default=SimNameType.DEFAULT), weight=TunableRange(description='\n                        Weighted chance.\n                        ', tunable_type=float, default=1, minimum=0)))), 'valid_conditional_layers': TunableSet(description='\n            A list of all of the conditional_layers on this Street.\n            ', tunable=TunableReference(description='\n                A reference to a conditional layer that exists on this Street.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER), pack_safe=True)), 'tested_conditional_layers': TunableList(description='\n            The list of conditional layers that will load in to the the street\n            if its tests pass.\n            \n            NOTE: Only a subset of tests are registered to listen for updates.\n            Check with your GPE if you expect to have the conditional layers update\n            with test events. Otherwise, they will only be tested on zone-load.\n            ', tunable=TunableTuple(description='\n                A list of all of the conditional_layers to load into this Street.\n                ', conditional_layer=TunableReference(description='\n                    A reference to a conditional layer that exists on this Street.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER), pack_safe=True), tests=TunableGlobalTestList(description='\n                    The tests that must pass in order for this conditional layer\n                    to be loaded in. If tests are empty, the conditional layer\n                    is considered valid.\n                    '), process_after_event_handled=Tunable(description='\n                     When True, conditional layer requests triggered by the test\n                     events will be ordered to prioritize client-layer requests\n                     first, then gameplay-layers.\n                     ', tunable_type=bool, default=False), test_on_managed_world_edit_mode_load=Tunable(description='\n                    By default, conditional layers are not tested and started when entering\n                    from Managed World Edit Mode.  Those layers which are enabled via this\n                    option will be tested and started even in Managed World Edit Mode.\n                    Generally these should be Client Only layers, but no such restriction is\n                    enforced.\n                    ', tunable_type=bool, default=False))), 'beaches': TunableList(description='\n            List of locations to place beaches.\n            ', tunable=TunableTuple(description='\n                Beach creation data.\n                ', position=TunableVector3(description='\n                    The position to create the beach at.\n                    ', default=TunableVector3.DEFAULT_ZERO), forward=TunableVector2(description='\n                    The forward vector of the beach object.\n                    ', default=Vector2.Y_AXIS())), unique_entries=True), 'civic_policy': StreetProvider.TunableFactory(description='\n            Tuning to control the civic policy voting and enactment process for\n            a street.\n            '), 'initial_street_eco_footprint_override': OptionalTunable(description='\n            If enabled, overrides the initial value of the street eco footprint\n            statistic.\n            ', tunable=Tunable(description='\n                The initial value of the street eco footprint statistic.\n                ', tunable_type=float, default=0))}
    ZONE_IDS_BY_STREET = None
    street_to_lot_id_to_zone_ids = {}

    @classmethod
    def _cls_repr(cls):
        return "Street: <class '{}.{}'>".format(cls.__module__, cls.__name__)

    @classmethod
    def get_lot_to_travel_to(cls):
        if cls is services.current_street():
            return
        return world.lot.get_lot_id_from_instance_id(cls.travel_lot)

    @classmethod
    def has_conditional_layer(cls, conditional_layer):
        return conditional_layer in cls.valid_conditional_layers

    @classmethod
    def clear_caches(cls):
        Street.street_to_lot_id_to_zone_ids.clear()
        Street.ZONE_IDS_BY_STREET = None

def get_street_instance_from_zone_id(zone_id):
    world_description_id = get_world_description_id_from_zone_id(zone_id)
    if world_description_id is None:
        return
    return Street.WORLD_DESCRIPTION_TUNING_MAP.get(world_description_id)

def get_street_instance_from_world_id(world_id):
    world_description_id = services.get_world_description_id(world_id)
    return Street.WORLD_DESCRIPTION_TUNING_MAP.get(world_description_id, None)

def get_world_description_id_from_zone_id(zone_id):
    zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
    return services.get_world_description_id(zone_data.world_id)

def get_world_description_id_from_street(street):
    for (world_description_id, street_instance) in Street.WORLD_DESCRIPTION_TUNING_MAP.items():
        if street_instance is street:
            return world_description_id

def get_zone_ids_from_street(street):
    if Street.ZONE_IDS_BY_STREET is None:
        Street.ZONE_IDS_BY_STREET = {}
        for zone_data in services.get_persistence_service().zone_proto_buffs_gen():
            zone_id = zone_data.zone_id
            _street = get_street_instance_from_zone_id(zone_id)
            if _street is None:
                pass
            else:
                if _street not in Street.ZONE_IDS_BY_STREET:
                    Street.ZONE_IDS_BY_STREET[_street] = []
                Street.ZONE_IDS_BY_STREET[_street].append(zone_id)
    return Street.ZONE_IDS_BY_STREET.get(street, None)

def get_lot_id_to_zone_ids_dict(street):
    if street in Street.street_to_lot_id_to_zone_ids:
        return Street.street_to_lot_id_to_zone_ids[street]
    else:
        lot_id_to_zone_ids_dict = Street.street_to_lot_id_to_zone_ids[street] = {}
        zone_ids = get_zone_ids_from_street(street)
        if zone_ids is not None:
            persistence_service = services.get_persistence_service()
            for zone_id in zone_ids:
                lot_id = persistence_service.get_lot_id_from_zone_id(zone_id)
                zone_ids = lot_id_to_zone_ids_dict.get(lot_id, [])
                zone_ids.append(zone_id)
                lot_id_to_zone_ids_dict[lot_id] = zone_ids
            return lot_id_to_zone_ids_dict
        else:
            return {}
    return {}

def get_vacation_zone_id(zone_id):
    street = get_street_instance_from_zone_id(zone_id)
    if street is None or street.vacation_lot is None:
        return zone_id
    lot_id = world.lot.get_lot_id_from_instance_id(street.vacation_lot)
    if lot_id is None:
        return zone_id
    else:
        persistence_service = services.get_persistence_service()
        vacation_zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        if vacation_zone_id is None:
            return zone_id
    return vacation_zone_id
