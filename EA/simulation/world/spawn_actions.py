from interactions.context import InteractionContext, InteractionSourcefrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom objects.system import create_objectfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableReference, TunablePackSafeReference, TunableFactoryfrom tag import TunableTagimport objectsimport placementimport servicesimport sims4.loglogger = sims4.log.Logger('Sim Spawner')
class SpawnActionFadeIn:

    def __call__(self, sim):
        sim.fade_in()
        return True

class SpawnActionLiability(Liability):
    LIABILITY_TOKEN = 'SpawnActionLiability'

    def __init__(self, sim, spawn_affordance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spawn_affordance = spawn_affordance
        self._sim = sim

    def release(self):
        if not self._sim.opacity:
            logger.error('{} failed to make {} visible. Fading them in.', self._spawn_affordance, self._sim)
            self._sim.fade_in()

class SpawnOnVehicleActionAffordance(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'vehicle_obj_tag': TunableTag(description='\n            The tag to use to look up if the sim has a favorite vehicle\n            to use for the spawn action.\n            ', filter_prefixes=('Func',))}

    @TunableFactory.factory_option
    def list_pack_safe(list_pack_safe=False):
        tuning_name = 'fallback_vehicle_def'
        description = "\n            The definition of the vehicle to spawn if the sim doesn't have\n            a favorite vehicle.\n        "
        if list_pack_safe:
            return {tuning_name: TunableReference(description=description, manager=services.definition_manager(), pack_safe=True)}
        return {tuning_name: TunablePackSafeReference(description=description, manager=services.definition_manager())}

    def __call__(self, sim):

        def _abort(vehicle_obj):
            sim.allow_opacity_change = True
            sim.fade_in()
            if vehicle_obj is not None:
                vehicle_obj.destroy()

        vehicle = None
        if sim.sim_info.favorites_tracker is not None:
            favorites_tracker = sim.sim_info.favorites_tracker
            definition_manager = services.definition_manager()
            vehicle_def_id = favorites_tracker.get_favorite_definition_id(self.vehicle_obj_tag)
            if vehicle_def_id is not None:
                vehicle_def = definition_manager.get(vehicle_def_id)
                if vehicle_def is not None:
                    vehicle = objects.system.create_object(vehicle_def)
        if vehicle is None:
            if self.fallback_vehicle_def is None:
                _abort(vehicle)
                return True
            vehicle = create_object(self.fallback_vehicle_def)
            if vehicle is None:
                _abort(vehicle)
                return True
        vehicle.set_household_owner_id(sim.household_id)
        starting_location = placement.create_starting_location(position=sim.position)
        fgl_context = placement.create_fgl_context_for_object(starting_location, vehicle)
        (position, orientation) = placement.find_good_location(fgl_context)
        if position is None or orientation is None:
            _abort(vehicle)
            return True
        vehicle.transform = sims4.math.Transform(position, orientation)
        result = vehicle.vehicle_component.push_drive_affordance(sim, priority=Priority.Critical)
        if result is None:
            _abort(vehicle)
            return True
        if result.interaction is None:
            logger.warn("Vehicle's push drive affordance {} resulted in a None interaction. Result: {}.", vehicle.vehicle_component.drive_affordance, result, owner='jmorrow')
            _abort(vehicle)
            return True
        sim.fade_in()
        vehicle.claim()
        for situation in services.get_zone_situation_manager().get_all():
            if sim in situation.all_sims_in_situation_gen():
                situation.manage_vehicle(vehicle)
                break
        return True

class SpawnActionAffordance(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'spawn_affordance': TunableReference(description='\n            The affordance that is pushed on the Sim as soon as they are spawned\n            on the lot.\n            ', manager=services.affordance_manager(), class_restrictions=('SuperInteraction',))}

    def __call__(self, sim):
        context = InteractionContext(sim, InteractionSource.SCRIPT, Priority.Critical)
        result = sim.push_super_affordance(self.spawn_affordance, None, context)
        if not result:
            logger.error('{} failed to run, with result {}. Fading {} in.', self.spawn_affordance, result, sim)
            sim.fade_in()
        result.interaction.add_liability(SpawnActionLiability.LIABILITY_TOKEN, SpawnActionLiability(sim, self.spawn_affordance))
        return True

class TunableSpawnActionVariant(TunableVariant):

    def __init__(self, list_pack_safe=False, **kwargs):
        super().__init__(affordance=SpawnActionAffordance.TunableFactory(), locked_args={'fade_in': SpawnActionFadeIn()}, vehicle=SpawnOnVehicleActionAffordance.TunableFactory(list_pack_safe=list_pack_safe), default='fade_in', **kwargs)
