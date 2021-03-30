import cythonfrom contextlib import contextmanagerimport collectionsimport functoolsimport itertoolsimport operatorimport refrom animation.posture_manifest import AnimationParticipantfrom event_testing.resolver import SingleActorAndObjectResolverfrom objects import ALL_HIDDEN_REASONSfrom objects.slots import RuntimeSlotfrom postures.posture_tuning import PostureTuningfrom sims.sim_info_types import Speciesfrom sims4.callback_utils import consume_exceptionsfrom sims4.collections import enumdictfrom sims4.log import Loggerfrom sims4.math import vector3_almost_equalfrom sims4.repr_utils import standard_reprfrom sims4.tuning.tunable import Tunablefrom singletons import DEFAULT as DEFAULT_SINGLETONimport animation.posture_manifestimport assertionsimport enumimport event_testingimport objects.components.typesimport postures.posture_scoringimport routingimport servicesimport sims4.callback_utilsimport sims4.reloadlogger = Logger('PostureGraph')cython_log = Logger('CythonConfig')if cython.compiled:
    cython_log.always('CYTHON posture_specs is imported!', color=sims4.log.LEVEL_WARN)
else:
    cython_log.always('Pure Python posture_specs is imported!', color=sims4.log.LEVEL_WARN)if not cython.compiled:
    from postures.posture_specs_ph import *
@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def check_nones(a:ObjectPtr, b:ObjectPtr) -> cython.uint:
    return cython.cast(cython.uint, a == cython.cast(ObjectPtr, None)) | cython.cast(cython.uint, b == cython.cast(ObjectPtr, None)) << 1

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def combine_hashes(h1:HashT, h2:HashT) -> HashT:
    return 101*h1 + h2
_enable_cache_count = cython.declare(cython.int)_cached_object_manager = cython.declare(object)_cached_valid_objects = cython.declare(object)_cached_runtime_slots = cython.declare(object)_cached_sim_instances = cython.declare(object)DEFAULT = cython.declare(object, DEFAULT_SINGLETON)with sims4.reload.protected(globals()):
    _enable_cache_count = 0
    _cached_object_manager = None
    _cached_valid_objects = None
    _cached_runtime_slots = None
    _cached_sim_instances = None
    new_object = None
@contextmanager
def _object_addition(obj):
    global new_object
    new_object = obj
    try:
        yield None
    finally:
        new_object = None

class PostureSpecVariable(enum.Int):
    ANYTHING = 200
    INTERACTION_TARGET = 201
    CARRY_TARGET = 302
    SURFACE_TARGET = 203
    CONTAINER_TARGET = 204
    HAND = 205
    POSTURE_TYPE_CARRY_NOTHING = 206
    POSTURE_TYPE_CARRY_OBJECT = 207
    SLOT = 208
    SLOT_TEST_DEFINITION = 209
    DESTINATION_FILTER = 211
    BODY_TARGET_FILTERED = 212
    SLOT_TARGET = 213

    def __repr__(self):
        return self.name
PostureSpecVariable_ANYTHING = cython.declare(object, PostureSpecVariable.ANYTHING)PostureSpecVariable_INTERACTION_TARGET = cython.declare(object, PostureSpecVariable.INTERACTION_TARGET)PostureSpecVariable_CARRY_TARGET = cython.declare(object, PostureSpecVariable.CARRY_TARGET)PostureSpecVariable_SURFACE_TARGET = cython.declare(object, PostureSpecVariable.SURFACE_TARGET)PostureSpecVariable_CONTAINER_TARGET = cython.declare(object, PostureSpecVariable.CONTAINER_TARGET)PostureSpecVariable_HAND = cython.declare(object, PostureSpecVariable.HAND)PostureSpecVariable_POSTURE_TYPE_CARRY_NOTHING = cython.declare(object, PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING)PostureSpecVariable_POSTURE_TYPE_CARRY_OBJECT = cython.declare(object, PostureSpecVariable.POSTURE_TYPE_CARRY_OBJECT)PostureSpecVariable_SLOT = cython.declare(object, PostureSpecVariable.SLOT)PostureSpecVariable_SLOT_TEST_DEFINITION = cython.declare(object, PostureSpecVariable.SLOT_TEST_DEFINITION)PostureSpecVariable_DESTINATION_FILTER = cython.declare(object, PostureSpecVariable.DESTINATION_FILTER)PostureSpecVariable_BODY_TARGET_FILTERED = cython.declare(object, PostureSpecVariable.BODY_TARGET_FILTERED)PostureSpecVariable_SLOT_TARGET = cython.declare(object, PostureSpecVariable.SLOT_TARGET)
@contextmanager
def _cache_thread_specific_info():
    global _cached_runtime_slots, _enable_cache_count, _cached_object_manager, _cached_valid_objects, _cached_sim_instances
    _cached_runtime_slots = {}
    _enable_cache_count += 1
    try:
        if _enable_cache_count == 1:
            with sims4.callback_utils.invoke_enter_exit_callbacks(sims4.callback_utils.CallbackEvent.POSTURE_GRAPH_BUILD_ENTER, sims4.callback_utils.CallbackEvent.POSTURE_GRAPH_BUILD_EXIT), consume_exceptions():
                yield None
        else:
            yield None
    finally:
        _enable_cache_count -= 1
        if not _enable_cache_count:
            _cached_object_manager = None
            _cached_valid_objects = None
            _cached_runtime_slots = None
            _cached_sim_instances = None

def with_caches(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _cache_thread_specific_info():
            return func(*args, **kwargs)

    return wrapper

@cython.ccall
def object_manager():
    global _cached_object_manager
    if _enable_cache_count:
        if _cached_object_manager is None:
            _cached_object_manager = services.object_manager()
        return _cached_object_manager
    return services.object_manager()

@cython.ccall
def instanced_sims():
    global _cached_sim_instances
    if _enable_cache_count:
        if _cached_sim_instances is None:
            sim_info_manager = services.sim_info_manager()
            _cached_sim_instances = frozenset([instanced_sim for instanced_sim in sim_info_manager.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS)])
        return _cached_sim_instances
    sim_info_manager = services.sim_info_manager()
    return frozenset([instanced_sim for instanced_sim in sim_info_manager.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS)])

@cython.ccall
def valid_objects():
    global _cached_valid_objects
    if _enable_cache_count:
        if _cached_valid_objects is None:
            _cached_valid_objects = _valid_objects_helper()
        return _cached_valid_objects
    return _valid_objects_helper()

@cython.ccall
def _valid_objects_helper():
    result = set()
    posture_graph_service = services.posture_graph_service()
    for obj in object_manager().values():
        if not obj.is_valid_posture_graph_object:
            pass
        elif obj.is_sim or obj.is_hidden():
            pass
        elif posture_graph_service.has_built_for_zone_spin_up or not obj.provided_mobile_posture_affordances:
            pass
        elif obj.parts:
            result.update(obj.parts)
        else:
            result.add(obj)
    if new_object is not None:
        if new_object.parts:
            result.update(new_object.parts)
        else:
            result.add(new_object)
    return frozenset(result)

@cython.ccall
@cython.exceptval(check=False)
def _simple_id_str(obj) -> str:
    return str(obj)

@cython.ccall
@cython.exceptval(check=False)
def _str_for_variable(value) -> str:
    result = 'None'
    if value is not None:
        result = str(value).split('.')[-1]
    return result

@cython.ccall
@cython.exceptval(check=False)
def _str_for_type(value) -> str:
    if value is None:
        return 'None'
    if isinstance(value, PostureSpecVariable):
        return _str_for_variable(value)
    return value.__name__

@cython.ccall
@cython.exceptval(check=False)
def _str_for_object(value) -> str:
    if value is None:
        return 'None'
    if isinstance(value, PostureSpecVariable):
        return _str_for_variable(value)
    return _simple_id_str(value)

@cython.ccall
@cython.exceptval(check=False)
def _str_for_slot_type(value) -> str:
    if value is None:
        return 'None'
    if isinstance(value, PostureSpecVariable):
        return _str_for_variable(value)
    return value.__name__.split('_')[-1]

@cython.ccall
@cython.exceptval(-1)
def variables_match(a, b, var_map=None, allow_owner_to_match_parts:cython.bint=True) -> cython.bint:
    if a == b:
        return True
    if PostureSpecVariable_ANYTHING in (a, b):
        return True
    if None in (a, b):
        return False
    flt_obj = None
    if a == PostureSpecVariable_BODY_TARGET_FILTERED:
        flt_obj = b
    elif b == PostureSpecVariable_BODY_TARGET_FILTERED:
        flt_obj = a
    if flt_obj is not None:
        for filter in var_map[PostureSpecVariable_BODY_TARGET_FILTERED]:
            if not filter.matches(flt_obj):
                return False
        return True
    if var_map:
        a = var_map.get(a, a)
        b = var_map.get(b, b)
        return variables_match(a, b, None, allow_owner_to_match_parts)
    if isinstance(a, PostureSpecVariable) or isinstance(b, PostureSpecVariable):
        return True
    if a.id != b.id:
        return False
    elif a.is_part and b.is_part:
        return False
    return allow_owner_to_match_parts

@cython.cfunc
@cython.exceptval(check=False)
def _get_origin_spec(default_body_posture, origin_carry:'PostureAspectCarry') -> 'PostureSpec':
    origin_body = PostureAspectBody_create(default_body_posture, None)
    origin_surface = PostureAspectSurface_create(None, None, None)
    origin_node = PostureSpec_create(origin_body, origin_carry, origin_surface)
    return origin_node

@cython.ccall
@cython.exceptval(check=False)
def get_origin_carry() -> 'PostureAspectCarry':
    return PostureAspectCarry_create(PostureSpecVariable_POSTURE_TYPE_CARRY_NOTHING, None, PostureSpecVariable_HAND)

@cython.ccall
@cython.exceptval(check=False)
def get_origin_spec(default_body_posture) -> 'PostureSpec':
    origin_carry = get_origin_carry()
    return _get_origin_spec(default_body_posture, origin_carry)

@cython.ccall
@cython.exceptval(check=False)
def get_origin_spec_carry(default_body_posture) -> 'PostureSpec':
    origin_carry = PostureAspectCarry_create(PostureSpecVariable_POSTURE_TYPE_CARRY_OBJECT, PostureSpecVariable_CARRY_TARGET, PostureSpecVariable_HAND)
    return _get_origin_spec(default_body_posture, origin_carry)

@cython.ccall
@cython.exceptval(check=False)
def get_pick_up_spec_sequence(node_origin:'PostureSpec', surface_target, body_target=None) -> tuple:
    default_body_posture = node_origin.body.posture_type
    default_surface_target = node_origin.surface.target
    origin = get_origin_spec(default_body_posture)
    origin_carry = get_origin_spec_carry(default_body_posture)
    if body_target is None:
        slot_type = None
        target_var = None
        target = surface_target
    else:
        slot_type = PostureSpecVariable_SLOT
        target_var = PostureSpecVariable_CARRY_TARGET
        target = body_target
    move_to_surface = PostureSpec_create(PostureAspectBody_create(default_body_posture, target), origin.carry, PostureAspectSurface_create(None, None, None))
    address_surface = PostureSpec_create(PostureAspectBody_create(default_body_posture, target), origin.carry, PostureAspectSurface_create(surface_target, slot_type, target_var))
    address_surface_carry = PostureSpec_create(address_surface.body, origin_carry.carry, PostureAspectSurface_create(surface_target, None, None))
    address_surface_target = address_surface.surface.target
    if default_surface_target is address_surface_target:
        return (address_surface, address_surface_carry)
    return (move_to_surface, address_surface, address_surface_carry)

@cython.ccall
@cython.exceptval(check=False)
def get_put_down_spec_sequence(default_body_posture, surface_target, body_target=None) -> tuple:
    body_target = body_target or surface_target
    origin = get_origin_spec(default_body_posture)
    origin_carry = get_origin_spec_carry(default_body_posture)
    slot_type = PostureSpecVariable_SLOT
    target_var = PostureSpecVariable_CARRY_TARGET
    address_surface = PostureSpec_create(PostureAspectBody_create(default_body_posture, body_target), origin.carry, PostureAspectSurface_create(surface_target, slot_type, target_var))
    address_surface_carry = PostureSpec_create(address_surface.body, origin_carry.carry, PostureAspectSurface_create(surface_target, None, None))
    return (address_surface_carry, address_surface)

@cython.ccall
@cython.exceptval(-1, check=False)
def node_matches_spec(node:'PostureSpec', spec:'PostureSpec', var_map, allow_owner_to_match_parts) -> cython.bint:
    node_body = node.body
    node_body_target = node_body.target
    node_body_posture_type = node_body.posture_type
    spec_surface = spec.surface
    node_surface = node.surface
    spec_body = spec.body
    if spec_body is not None:
        spec_body_target = spec_body.target
        spec_body_posture_type = spec_body.posture_type
    else:
        spec_body_target = PostureSpecVariable_ANYTHING
        spec_body_posture_type = node_body_posture_type
    if spec_body_posture_type != node_body_posture_type:
        return False
    if not variables_match(node_body_target, spec_body_target, var_map, allow_owner_to_match_parts):
        return False
    if node_body_posture_type.mobile and (node_body_target is not None and (spec_surface is None or spec_surface.target is None)) and spec_body_target == PostureSpecVariable_ANYTHING:
        return False
    spec_carry = spec.carry
    if spec_carry is not None:
        node_carry = node.carry
        if node_carry.posture_type != spec_carry.posture_type:
            return False
        if not variables_match(node_carry.target, spec_carry.target, var_map, allow_owner_to_match_parts):
            return False
    if (spec_surface is None or spec_surface.target is None) and node_surface is not None and node_body_posture_type.mobile:
        node_surface_target = node_surface.target
        if node_surface_target is not None:
            return False
    if spec_surface is not None:
        if not variables_match(node_surface.target, spec_surface.target, var_map, allow_owner_to_match_parts):
            return False
        if node_surface.slot_type != spec_surface.slot_type:
            return False
        elif not variables_match(node_surface.slot_target, spec_surface.slot_target, var_map, allow_owner_to_match_parts):
            return False
    return True

@cython.cfunc
@cython.exceptval(-1)
def _spec_matches_request(sim, spec:'PostureSpec', var_map) -> cython.bint:
    if spec.surface.slot_type is not None:
        slot_manifest = var_map.get(PostureSpecVariable_SLOT)
        if slot_manifest is not None:
            surface = spec.surface.target
            if not slot_manifest.slot_types.intersection(surface.get_provided_slot_types()):
                return False
            carry_target = slot_manifest.actor
            if hasattr(carry_target, 'manager') and not carry_target.has_component(objects.components.types.CARRYABLE_COMPONENT):
                current_parent_slot = carry_target.parent_slot
                if current_parent_slot is None:
                    return False
                if current_parent_slot.owner != surface:
                    return False
                if not slot_manifest.slot_types.intersection(current_parent_slot.slot_types):
                    return False
                else:
                    destination_filter = var_map.get(PostureSpecVariable_DESTINATION_FILTER)
                    if destination_filter is not None and not destination_filter(spec, var_map):
                        return False
            else:
                destination_filter = var_map.get(PostureSpecVariable_DESTINATION_FILTER)
                if destination_filter is not None and not destination_filter(spec, var_map):
                    return False
        else:
            destination_filter = var_map.get(PostureSpecVariable_DESTINATION_FILTER)
            if destination_filter is not None and not destination_filter(spec, var_map):
                return False
    return True

@cython.cfunc
@cython.exceptval(-1)
def _in_var_map(obj, var_map) -> cython.bint:
    for target in var_map.values():
        if isinstance(target, objects.game_object.GameObject) and target.is_same_object_or_part(obj):
            return True
    return False

@cython.ccall
@cython.exceptval(-1)
def destination_autonomous_availability_test(sim, body_target_obj, interaction) -> cython.bint:
    if body_target_obj is interaction.sim:
        return True
    if body_target_obj is sim.parent:
        return True
    if interaction.ignore_autonomy_rules_if_user_directed and interaction.is_user_directed:
        return True
    return sim.autonomy_component.is_object_autonomously_available(body_target_obj, interaction)

@cython.ccall
@cython.exceptval(-1)
def destination_test(sim, node:'PostureSpec', destination_specs, var_map, additional_test_fn, interaction) -> cython.bint:
    sims4.sim_irq_service.yield_to_irq()
    body_index = node.body
    if not body_index.posture_type.is_animation_available_for_species(sim.species):
        return False
    body_target = body_index.target
    if body_target is not None:
        body_target_obj = body_target.part_owner if body_target.is_part else body_target
        if sim.current_object_set_as_head is not None and sim.current_object_set_as_head() is body_target_obj:
            return False
        for child in body_target.parenting_hierarchy_gen():
            if _in_var_map(child, var_map):
                break
        if not destination_autonomous_availability_test(sim, body_target_obj, interaction):
            return False
    destination_spec = cython.declare(PostureSpec)
    for destination_spec in destination_specs:
        if node_matches_spec(node, destination_spec, var_map, True):
            break
    return False
    if not node.validate_destination(destination_specs, var_map, interaction, sim):
        return False
    elif additional_test_fn is not None and not additional_test_fn(node, var_map):
        return False
    return True

@cython.ccall
@cython.exceptval(check=False)
def PostureAspectBody_create(posture_type:object, target:object) -> 'PostureAspectBody':
    res = cython.declare(PostureAspectBody, PostureAspectBody.__new__(PostureAspectBody))
    res.posture_type = posture_type
    res.target = target
    return res

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def PostureAspectBody_hash_imp(self:'PostureAspectBody') -> HashT:
    return combine_hashes(hash(self.posture_type), hash(self.target))

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def PostureAspectBody_eq_imp(self:'PostureAspectBody', other:'PostureAspectBody') -> cython.bint:
    return self.posture_type == other.posture_type and self.target == other.target

@cython.cclass
class PostureAspectBody:

    def __init__(self, t:tuple):
        l = len(t)
        if BODY_POSTURE_TYPE_INDEX < l:
            self.posture_type = t[BODY_POSTURE_TYPE_INDEX]
        if BODY_TARGET_INDEX < l:
            self.target = t[BODY_TARGET_INDEX]

    def __getitem__(self, key:cython.int) -> object:
        if key == BODY_POSTURE_TYPE_INDEX:
            return self.posture_type
        if key == BODY_TARGET_INDEX:
            return self.target
        raise IndexError('Unknown index ', key)

    def __iter__(self):
        yield self.posture_type
        yield self.target

    def __len__(self):
        return 2

    @cython.exceptval(check=False)
    def __hash__(self) -> HashT:
        return PostureAspectBody_hash_imp(self)

    @cython.exceptval(check=False)
    def __eq__(self, other:object) -> cython.bint:
        if isinstance(other, PostureAspectBody):
            return PostureAspectBody_eq_imp(self, cython.cast(PostureAspectBody, other))
        return False

    @cython.exceptval(check=False)
    def __ne__(self, other:object) -> cython.bint:
        if isinstance(other, PostureAspectBody):
            return not PostureAspectBody_eq_imp(self, cython.cast(PostureAspectBody, other))
        return True

    def __str__(self):
        return '{}@{}'.format(self.posture_type.name, self.target)

    def __repr__(self):
        return standard_repr(self, tuple(self))

@cython.ccall
@cython.exceptval(check=False)
def PostureAspectCarry_create(posture_type:object, target:object, hand:object) -> 'PostureAspectCarry':
    res = cython.declare(PostureAspectCarry, PostureAspectCarry.__new__(PostureAspectCarry))
    res.posture_type = posture_type
    res.target = target
    res.hand = hand
    return res

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def PostureAspectCarry_hash_imp(self:'PostureAspectCarry') -> HashT:
    res = combine_hashes(hash(self.posture_type), hash(self.target))
    res = combine_hashes(res, hash(self.hand))
    return res

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def PostureAspectCarry_eq_imp(self:'PostureAspectCarry', other:'PostureAspectCarry') -> cython.bint:
    return self.posture_type == other.posture_type and (self.target == other.target and self.hand == other.hand)

@cython.cclass
class PostureAspectCarry:

    def __init__(self, t:tuple):
        l = len(t)
        if CARRY_POSTURE_TYPE_INDEX < l:
            self.posture_type = t[CARRY_POSTURE_TYPE_INDEX]
        if CARRY_TARGET_INDEX < l:
            self.target = t[CARRY_TARGET_INDEX]
        if CARRY_HAND_INDEX < l:
            self.hand = t[CARRY_HAND_INDEX]

    def __getitem__(self, key:cython.int) -> object:
        if key == CARRY_POSTURE_TYPE_INDEX:
            return self.posture_type
        if key == CARRY_TARGET_INDEX:
            return self.target
        if key == CARRY_HAND_INDEX:
            return self.hand
        raise IndexError('Unknown index ', key)

    def __iter__(self):
        yield self.posture_type
        yield self.target
        yield self.hand

    def __len__(self):
        return 3

    @cython.exceptval(check=False)
    def __hash__(self) -> HashT:
        return PostureAspectCarry_hash_imp(self)

    @cython.exceptval(check=False)
    def __eq__(self, other:object) -> cython.bint:
        if isinstance(other, PostureAspectCarry):
            return PostureAspectCarry_eq_imp(self, cython.cast(PostureAspectCarry, other))
        return False

    @cython.exceptval(check=False)
    def __ne__(self, other:object) -> cython.bint:
        if isinstance(other, PostureAspectCarry):
            return not PostureAspectCarry_eq_imp(self, cython.cast(PostureAspectCarry, other))
        return True

    def __str__(self):
        if self.target is None:
            return self.posture_type.name
        return '<{} {}>'.format(self.posture_type.name, self.target)

    def __repr__(self):
        return standard_repr(self, tuple(self))

@cython.ccall
@cython.exceptval(check=False)
def PostureAspectSurface_create(target:object, slot_type:object, slot_target:object) -> 'PostureAspectSurface':
    res = cython.declare(PostureAspectSurface, PostureAspectSurface.__new__(PostureAspectSurface))
    res.target = target
    res.slot_type = slot_type
    res.slot_target = slot_target
    return res

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def PostureAspectSurface_hash_imp(self:'PostureAspectSurface') -> HashT:
    res = combine_hashes(hash(self.target), hash(self.slot_type))
    res = combine_hashes(res, hash(self.slot_target))
    return res

@cython.cfunc
@cython.inline
@cython.exceptval(check=False)
def PostureAspectSurface_eq_imp(self:'PostureAspectSurface', other:'PostureAspectSurface') -> cython.bint:
    return self.target == other.target and (self.slot_type == other.slot_type and self.slot_target == other.slot_target)

@cython.cclass
class PostureAspectSurface:

    def __init__(self, t:tuple):
        l = len(t)
        if SURFACE_TARGET_INDEX < l:
            self.target = t[SURFACE_TARGET_INDEX]
        if SURFACE_SLOT_TYPE_INDEX < l:
            self.slot_type = t[SURFACE_SLOT_TYPE_INDEX]
        if SURFACE_SLOT_TARGET_INDEX < l:
            self.slot_target = t[SURFACE_SLOT_TARGET_INDEX]

    def __getitem__(self, key:cython.int) -> object:
        if key == SURFACE_TARGET_INDEX:
            return self.target
        if key == SURFACE_SLOT_TYPE_INDEX:
            return self.slot_type
        if key == SURFACE_SLOT_TARGET_INDEX:
            return self.slot_target
        raise IndexError('Unknown index ', key)

    def __iter__(self):
        yield self.target
        yield self.slot_type
        yield self.slot_target

    def __len__(self):
        return 3

    @cython.exceptval(check=False)
    def __hash__(self) -> HashT:
        return PostureAspectSurface_hash_imp(self)

    @cython.exceptval(check=False)
    def __eq__(self, other:object) -> cython.bint:
        if isinstance(other, PostureAspectSurface):
            return PostureAspectSurface_eq_imp(self, cython.cast(PostureAspectSurface, other))
        return False

    @cython.exceptval(check=False)
    def __ne__(self, other:object) -> cython.bint:
        if isinstance(other, PostureAspectSurface):
            return not PostureAspectSurface_eq_imp(self, cython.cast(PostureAspectSurface, other))
        return True

    def __str__(self):
        if self.slot_type is None:
            if self.target is None:
                return 'No Surface'
            return '@Surface: ' + str(self.target)
        if self.slot_target is None:
            slot_str = '(EmptySlot)'
        else:
            slot_str = '(TargetInSlot)'
        return 'Surface: ' + str(self.target) + slot_str

    def __repr__(self):
        return standard_repr(self, tuple(self))

@cython.ccall
@cython.exceptval(check=False)
def PostureSpec_create(body:PostureAspectBody, carry:PostureAspectCarry, surface:PostureAspectSurface) -> 'PostureSpec':
    res = cython.declare(PostureSpec, PostureSpec.__new__(PostureSpec))
    res.body = body
    res.carry = carry
    res.surface = surface
    return res

@cython.cclass
class PostureSpec:

    def __init__(self, t:tuple):
        l = len(t)
        if BODY_INDEX < l:
            self.body = t[BODY_INDEX]
        if CARRY_INDEX < l:
            self.carry = t[CARRY_INDEX]
        if SURFACE_INDEX < l:
            self.surface = t[SURFACE_INDEX]

    def __getitem__(self, key:cython.int) -> object:
        if key == BODY_INDEX:
            return self.body
        if key == CARRY_INDEX:
            return self.carry
        if key == SURFACE_INDEX:
            return self.surface
        raise IndexError('Unknown index ', key)

    def __iter__(self):
        yield self.body
        yield self.carry
        yield self.surface

    def __len__(self):
        return 3

    @cython.exceptval(check=False)
    def __hash__(self) -> HashT:
        res = combine_hashes(PostureAspectBody_hash_imp(self.body) if self.body is not None else 0, PostureAspectCarry_hash_imp(self.carry) if self.carry is not None else 0)
        res = combine_hashes(res, PostureAspectSurface_hash_imp(self.surface) if self.surface is not None else 0)
        return res

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def eq_imp(self, other:'PostureSpec') -> cython.bint:
        nr = check_nones(cython.cast(ObjectPtr, self.body), cython.cast(ObjectPtr, other.body))
        if nr == NoneNone:
            if not PostureAspectBody_eq_imp(self.body, other.body):
                return False
        elif nr != BothNone:
            return False
        nr = check_nones(cython.cast(ObjectPtr, self.carry), cython.cast(ObjectPtr, other.carry))
        if nr == NoneNone:
            if not PostureAspectCarry_eq_imp(self.carry, other.carry):
                return False
        elif nr != BothNone:
            return False
        nr = check_nones(cython.cast(ObjectPtr, self.surface), cython.cast(ObjectPtr, other.surface))
        if nr == NoneNone:
            if not PostureAspectSurface_eq_imp(self.surface, other.surface):
                return False
        elif nr != BothNone:
            return False
        return True

    @cython.exceptval(check=False)
    def __eq__(self, other:object) -> cython.bint:
        if isinstance(other, PostureSpec):
            return self.eq_imp(cython.cast(PostureSpec, other))
        return False

    @cython.exceptval(check=False)
    def __ne__(self, other:object) -> cython.bint:
        if isinstance(other, PostureSpec):
            return not self.eq_imp(cython.cast(PostureSpec, other))
        return True

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_body_target(self) -> object:
        if self.body is not None:
            return self.body.target

    @property
    def body_target(self):
        return self.get_body_target()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_body_posture(self) -> object:
        if self.body is not None:
            return self.body.posture_type

    @property
    def body_posture(self):
        return self.get_body_posture()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_carry_target(self) -> object:
        if self.carry is not None:
            return self.carry.target

    @property
    def carry_target(self):
        return self.get_carry_target()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_carry_posture(self) -> object:
        if self.carry is not None:
            return self.carry.posture_type

    @property
    def carry_posture(self):
        return self.get_carry_posture()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_surface_target(self) -> object:
        if self.surface is not None:
            return self.surface.target

    @property
    def surface_target(self):
        return self.get_surface_target()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_slot_type(self) -> object:
        if self.surface is not None:
            return self.surface.slot_type

    @property
    def slot_type(self):
        return self.get_slot_type()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def get_slot_target(self) -> object:
        if self.surface is not None:
            return self.surface.slot_target

    @property
    def slot_target(self):
        return self.get_slot_target()

    @cython.cfunc
    @cython.inline
    @cython.exceptval(check=False)
    def clone_imp(self, body, carry, surface) -> 'PostureSpec':
        if body is DEFAULT:
            body = self.body
        if carry is DEFAULT:
            carry = self.carry
        if surface is DEFAULT:
            surface = self.surface
        return PostureSpec_create(cython.cast(PostureAspectBody, body), cython.cast(PostureAspectCarry, carry), cython.cast(PostureAspectSurface, surface))

    @cython.ccall
    @cython.exceptval(check=False)
    def clone(self, body=DEFAULT, carry=DEFAULT, surface=DEFAULT) -> 'PostureSpec':
        return self.clone_imp(body, carry, surface)

    _attribute_definitions = (('_body_posture_name', str), ('_body_target_type', str), ('_body_target', str), ('_body_part', str), ('_is_carrying', str), ('_at_surface', str), ('_surface_target_type', str), ('_surface_target', str), ('_surface_part', str), ('_slot_target', str))

    @property
    def _body_posture_name(self):
        body = self.body
        if body is None:
            return
        body_posture_type = body.posture_type
        if body_posture_type is None:
            return
        return body_posture_type._posture_name

    @property
    def _body_target_type(self):
        body = self.body
        if body is None:
            return
        target = body.target
        if target is None:
            return
        if target.is_part:
            target = target.part_owner
        return type(target).__name__

    @property
    def _body_target(self):
        body = self.body
        if body is None:
            return
        target = body.target
        if target is None:
            return
        if isinstance(target, PostureSpecVariable):
            return target.name
        elif target.is_part:
            return target.part_owner
        return target

    @property
    def _body_target_with_part(self):
        body = self.body
        if body is None:
            return
        target = body.target
        if target is None:
            return
        elif isinstance(target, PostureSpecVariable):
            return target.name
        return target

    @property
    def _body_part(self):
        body = self.body
        if body is None:
            return
        target = body.target
        if target is None or isinstance(target, PostureSpecVariable):
            return
        elif target.is_part:
            return target.part_group_index

    @property
    def _is_carrying(self):
        carry = self.carry
        if carry is not None and carry.target is not None:
            return True
        return False

    @property
    def _at_surface(self):
        surface = self.surface
        if surface is not None and surface.slot_type is not None:
            return True
        return False

    @property
    def _surface_target_type(self):
        surface = self.surface
        if surface is None:
            return
        target = surface.target
        if target is None:
            return
        if isinstance(target, PostureSpecVariable):
            return target.name
        if target.is_part:
            target = target.part_owner
        return type(target).__name__

    @property
    def _surface_target(self):
        surface = self.surface
        if surface is None:
            return
        target = surface.target
        if target is None:
            return
        if isinstance(target, PostureSpecVariable):
            return target.name
        elif target.is_part:
            return target.part_owner
        return target

    @property
    def _surface_target_with_part(self):
        surface = self.surface
        if surface is None:
            return
        target = surface.target
        if target is None:
            return
        elif isinstance(target, PostureSpecVariable):
            return target.name
        return target

    @property
    def _surface_part(self):
        surface = self.surface
        if surface is None:
            return
        target = surface.target
        if target is None or isinstance(target, PostureSpecVariable):
            return
        elif target.is_part:
            return target.part_group_index

    @property
    def _slot_target(self):
        surface = self.surface
        if surface is not None and surface.target is not None:
            if surface.slot_type is not None:
                slot_target = surface.slot_target
                if slot_target is not None:
                    if isinstance(slot_target, PostureSpecVariable):
                        return slot_target.name
                    else:
                        return 'TargetInSlot'
                else:
                    return 'EmptySlot'
            else:
                return 'AtSurface'

    def __repr__(self):
        result = '{}@{}'.format(self._body_posture_name, _simple_id_str(self._body_target_with_part))
        carry = self.carry
        if carry is None:
            result += ', carry:any'
        elif self.carry.target is not None:
            result += ', carry'
        surface = self.surface
        if surface is None:
            result += ', surface:any'
        elif surface.slot_type is not None:
            if surface.slot_target is not None:
                result += ', surface:slot_target@{}'.format(_simple_id_str(self._surface_target_with_part))
            else:
                result += ', surface:empty_slot@{}'.format(_simple_id_str(self._surface_target_with_part))
        elif surface.target is not None:
            result += ', surface:{}'.format(_simple_id_str(self._surface_target_with_part))
        return result

    @cython.ccall
    def get_core_objects(self):
        body_target = self.body.target
        surface_target = self.surface.target
        core_objects = set()
        if body_target is not None:
            core_objects.add(body_target)
            body_target_parent = body_target.parent
            if body_target_parent is not None:
                core_objects.add(body_target_parent)
        if surface_target is not None:
            core_objects.add(surface_target)
        return core_objects

    @cython.ccall
    def get_relevant_objects(self):
        body_posture = self.body.posture_type
        body_target = self.body.target
        surface_target = self.surface.target
        if body_posture.mobile and body_target is None and surface_target is None or body_posture is PostureTuning.SIM_CARRIED_POSTURE:
            return valid_objects()
        relevant_objects = self.get_core_objects()
        if body_target is not None:
            if body_target.is_part:
                relevant_objects.update(body_target.adjacent_parts_gen())
            relevant_objects.update(body_target.children)
        can_transition_to_carry = not body_posture.mobile or body_posture.mobile and body_target is None
        if can_transition_to_carry and body_posture.is_available_transition(PostureTuning.SIM_CARRIED_POSTURE):
            relevant_objects.update(instanced_sims())
        return relevant_objects

    @cython.ccall
    @cython.exceptval(check=False)
    def same_spec_except_slot(self, target:'PostureSpec') -> cython.bint:
        if self.body == target.body and self.carry == target.carry and self.surface.target == target.surface.target:
            return True
        return False

    @cython.ccall
    @cython.exceptval(-1, check=False)
    def same_spec_ignoring_surface_if_mobile(self, target:'PostureSpec') -> cython.bint:
        if self.get_body_posture().mobile and self.get_body_posture() == target.get_body_posture() and self.carry == target.carry:
            return True
        return False

    @cython.ccall
    @cython.exceptval(-1, check=False)
    def is_on_vehicle(self) -> cython.bint:
        target = self.body.target
        if target is not None:
            return target.vehicle_component is not None
        return False

    @cython.ccall
    @cython.exceptval(-1, check=False)
    def validate_destination(self, destination_specs, var_map, interaction, sim) -> cython.bint:
        destination_spec = cython.declare(PostureSpec)
        for destination_spec in destination_specs:
            if self._validate_carry(destination_spec):
                break
        return False
        if not self._validate_subroot(interaction, sim):
            return False
        if not self._validate_surface(var_map, affordance=interaction.affordance):
            return False
        if not self._validate_body(interaction, sim):
            return False
        posture_graph_service = services.current_zone().posture_graph_service
        zone_director = services.venue_service().get_zone_director()
        for obj in (self.get_body_target(), self.get_surface_target()):
            if not obj is None:
                if isinstance(obj, PostureSpecVariable):
                    pass
                else:
                    if not obj.valid_for_distribution:
                        return False
                    if obj.check_affordance_for_suppression(sim, interaction, user_directed=False):
                        return False
                    if not zone_director.zone_director_specific_destination_tests(sim, obj):
                        return False
        return True

    @cython.cfunc
    @cython.exceptval(-1, check=False)
    def _validate_body(self, interaction, sim) -> cython.bint:
        body = self.body
        if body is None:
            return True
        target = body.target
        if target is None:
            return True
        else:
            affordance = interaction.affordance
            if sim is not interaction.sim:
                linked_interaction_type = interaction.linked_interaction_type
                if linked_interaction_type is not affordance:
                    affordance = linked_interaction_type
            if not (interaction.is_social and target.supports_affordance(affordance)):
                return False
        return True

    @cython.cfunc
    @cython.exceptval(-1, check=False)
    def _validate_carry(self, destination_spec:'PostureSpec') -> cython.bint:
        dest_carry = destination_spec.carry
        if dest_carry is None or dest_carry.target is None:
            if self.carry.target is None:
                return True
            return False
        elif dest_carry == self.carry:
            return True
        return False

    @cython.ccall
    @cython.exceptval(-1, check=False)
    def _validate_surface(self, var_map, affordance=None) -> cython.bint:
        surface_spec = self.surface
        if surface_spec is None:
            return True
        surface = surface_spec.target
        if surface is None:
            return True
        if affordance is not None and not surface.supports_affordance(affordance):
            return False
        slot_type = surface_spec.slot_type
        if slot_type is None:
            return True
        slot_manifest_entry = var_map.get(slot_type)
        if slot_manifest_entry is None:
            return False
        runtime_slots = set(surface.get_runtime_slots_gen(slot_types=slot_manifest_entry.slot_types))
        slot_target = surface_spec.slot_target
        child = var_map.get(slot_target)
        if child is None:
            if PostureSpecVariable_SLOT_TEST_DEFINITION not in var_map:
                for runtime_slot in runtime_slots:
                    if runtime_slot.empty:
                        return True
                return False
        else:
            current_slot = child.parent_slot
            if current_slot is not None and slot_manifest_entry.actor is child and current_slot in runtime_slots:
                return True
        if PostureSpecVariable_SLOT_TEST_DEFINITION in var_map:
            slot_test_object = DEFAULT
            slot_test_definition = var_map[PostureSpecVariable_SLOT_TEST_DEFINITION]
        else:
            slot_test_object = child
            slot_test_definition = DEFAULT
        carry_target = self.carry.target
        carry_target = var_map.get(carry_target)
        objects_to_ignore = (carry_target,) if carry_target is not None else DEFAULT
        for runtime_slot in runtime_slots:
            if runtime_slot.is_valid_for_placement(obj=slot_test_object, definition=slot_test_definition, objects_to_ignore=objects_to_ignore):
                return True
        return False

    @cython.cfunc
    @cython.exceptval(-1, check=False)
    def _validate_subroot(self, interaction, sim) -> cython.bint:
        body_posture = self.get_body_posture()
        if sim is interaction.sim and body_posture._actor_required_part_definition is not None:
            if self.get_body_target().is_part and body_posture._actor_required_part_definition is not self.get_body_target().part_definition:
                return False
        elif sim is interaction.target and (body_posture._actor_b_required_part_definition is not None and self.get_body_target().is_part) and body_posture._actor_b_required_part_definition is not self.get_body_target().part_definition:
            return False
        return True

    @property
    def requires_carry_target_in_hand(self) -> cython.bint:
        return self.carry.target is not None

    @property
    def requires_carry_target_in_slot(self) -> cython.bint:
        return self.surface.slot_target is not None

@cython.ccall
@cython.exceptval(check=False)
def get_carry_posture_aop(sim, carry_target) -> object:
    from postures.posture_interactions import HoldObject
    context = sim.create_posture_interaction_context()
    for aop in carry_target.potential_interactions(context):
        if issubclass(aop.affordance, HoldObject):
            return aop
    logger.error('Sim {} The carry_target: ({}) has no SIs of type HoldObjectCheck that your object has a Carryable Component.', sim, carry_target, owner='camilogarcia')

@cython.cclass
class PostureOperationOperationBase:

    @cython.ccall
    @cython.exceptval(check=False)
    def apply(self, node:PostureSpec) -> PostureSpec:
        raise NotImplementedError()

    @cython.exceptval(-1)
    def validate(self, sim, var_map, original_body_target=None) -> cython.bint:
        return True

    @cython.ccall
    def get_validator(self, next_node):
        return self.validate

    @cython.ccall
    @cython.exceptval(check=False)
    def cost(self, node:PostureSpec) -> dict:
        return {PostureOperation.DEFAULT_COST_KEY: PostureOperation.COST_NOMINAL}

    @property
    def debug_cost_str_list(self):
        pass

    @cython.ccall
    def associated_aop(self, sim, var_map):
        pass

    @cython.ccall
    @cython.exceptval(-1, check=False)
    def is_equivalent_to(self, otherObj) -> cython.bint:
        raise NotImplementedError

    def get_constraint(self, sim, node:PostureSpec, var_map):
        pass

    @cython.ccall
    @cython.exceptval(check=False)
    def set_target(self, target) -> cython.void:
        pass
