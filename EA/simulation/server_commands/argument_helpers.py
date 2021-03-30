from collections import namedtupleimport operatorimport refrom sims4.commands import CustomParamfrom sims4.math import Transform, Vector2, Vector3, Quaternionfrom sims4.utils import classpropertyfrom singletons import DEFAULT, UNSETimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Commands')POLYGON_STR = 'Polygon{'POLYGON_END_STR = '}'POLYGON_FLAGS_PARAM = "Flags='CCW'"POINT_STR = 'Point('VECTOR_STR = '('VECTOR2_STR = 'Vector2'VECTOR3_STR = 'Vector3'VECTOR_END_STR = ')'TRANSFORM_STR = 'Transform('TRANSFORM_END_STR = '))'PATH_STR = 'Path['PATH_END_STR = ']'PATH_NODE_STR = 'Node{'PATH_NODE_END_STR = '}'
def find_substring_in_repr(string, start_str, end_str, early_out=False):
    start_index = 0
    substrs = []
    while start_index != -1:
        start_index = string.find(start_str, start_index)
        if start_index != -1:
            end_index = string.find(end_str, start_index)
            if end_index != -1:
                sub_str_index = start_index + len(start_str)
                if early_out:
                    return string[sub_str_index:end_index]
                substrs.append(string[sub_str_index:end_index])
            start_index += 1
    return substrs
FLOAT_REGEX = '[-+]?[0-9.]+'
def extract_floats(string):
    regex = re.compile(FLOAT_REGEX)
    matches = regex.findall(string)
    float_list = []
    for m in matches:
        try:
            cur_float = float(m)
            float_list.append(cur_float)
        except:
            pass
    return float_list
INT_REGEX = '[-+]?[0-9]+'
def extract_ints(string):
    regex = re.compile(INT_REGEX)
    matches = regex.findall(string)
    int_list = []
    for m in matches:
        try:
            cur_int = int(m)
            int_list.append(cur_int)
        except:
            pass
    return int_list

class NoneIntegerOrString(CustomParam):

    def __new__(cls, value:str):
        if value == 'None':
            return
        try:
            return int(value, 0)
        except:
            pass
        return value

class SimInfoParam(CustomParam):

    @classmethod
    def _get_sim_id(cls, arg):
        try:
            int_val = int(arg, 0)
        except ValueError:
            int_val = None
        return int_val

    @classmethod
    def get_arg_count_and_value(cls, *args):
        sim_id = cls._get_sim_id(args[0])
        if sim_id:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is not None:
                return (1, sim_info)
        if len(args) >= 2 and isinstance(args[1], str):
            first_name = args[0].lower()
            last_name = args[1].lower()
            last_info = None
            first_instanced = None
            sim_info_manager = services.sim_info_manager()
            object_manager = services.object_manager()
            for info in sim_info_manager.get_all():
                if info.first_name.lower() == first_name:
                    last_info = info
                    lower_last = info.last_name.lower()
                    if lower_last == last_name:
                        return (2, info)
                    if lower_last == '':
                        return (1, info)
                    if first_instanced is None and object_manager.get(info.id):
                        first_instanced = info
                        last_info = first_instanced
            if last_info is not None:
                return (1, last_info)
        return super().get_arg_count_and_value(*args)

    def __new__(cls, *args):
        int_val = cls._get_sim_id(args[0])
        if int_val is not None:
            sim_info = services.sim_info_manager().get(int_val)
            if sim_info is not None:
                return sim_info
        try:
            first_name = args[0].lower()
            last_name = '' if len(args) == 1 else args[1].lower()
            for info in services.sim_info_manager().get_all():
                if info.first_name.lower() == first_name and info.last_name.lower() == last_name:
                    return info
        except:
            logger.warn('Failed to parse SimInfoFromNameParam from {}'.format(args))

class SubstringParam(CustomParam):

    @classproperty
    def begin_str(cls):
        raise NotImplementedError

    @classproperty
    def end_str(cls):
        raise NotImplementedError

    @classmethod
    def get_arg_count_and_value(cls, *args):
        arg_count = 0
        found_start = False
        for arg in args:
            arg_count += 1
            if arg.find(cls.begin_str, 0) != -1:
                found_start = True
            if (found_start or found_start) and arg.find(cls.end_str, 0) != -1:
                return (arg_count, UNSET)
        return (1, UNSET)

class VectorParam(SubstringParam):

    @classproperty
    def begin_str(cls):
        return VECTOR_STR

    @classproperty
    def end_str(cls):
        return VECTOR_END_STR

    @classmethod
    def get_arg_count_and_value(cls, *args):
        (arg_count, _) = super().get_arg_count_and_value(*args)
        if arg_count == 1:
            arg_count = 0
            for arg in args:
                if arg_count == 3:
                    break
                try:
                    _ = float(arg)
                    arg_count += 1
                except ValueError:
                    break
        return (arg_count, UNSET)

    def __new__(cls, *args):
        total_string = ' '.join(args)
        try:
            vector_str = find_substring_in_repr(total_string, cls.begin_str, cls.end_str, early_out=True)
            if vector_str:
                vector_str = vector_str.replace(VECTOR3_STR, '')
                vector_str = vector_str.replace(VECTOR2_STR, '')
                float_list = extract_floats(vector_str)
            else:
                float_list = [float(arg) for arg in args]
            if len(float_list) == 2:
                return Vector2(float_list[0], float_list[1])
            if len(float_list) == 3:
                return Vector3(float_list[0], float_list[1], float_list[2])
        except:
            logger.warn('Failed to parse VectorParam from {}'.format(total_string))
        return total_string

class TransformParam(SubstringParam):

    @classproperty
    def begin_str(cls):
        return TRANSFORM_STR

    @classproperty
    def end_str(cls):
        return TRANSFORM_END_STR

    def __new__(cls, *args):
        total_string = ''.join(args)
        try:
            transform_str = find_substring_in_repr(total_string, TRANSFORM_STR, TRANSFORM_END_STR, early_out=True)
            if not transform_str:
                raise
            transform_str = transform_str.replace(VECTOR3_STR, '')
            float_list = extract_floats(transform_str)
            return Transform(Vector3(float_list[0], float_list[1], float_list[2]), Quaternion(float_list[3], float_list[4], float_list[5], float_list[6]))
        except:
            logger.warn('Failed to parse TransformParam from {}'.format(total_string))
        return total_string

class GeometryParam(SubstringParam):

    @classproperty
    def begin_str(cls):
        return POLYGON_STR

    @classproperty
    def end_str(cls):
        return POLYGON_END_STR

    def __new__(cls, *args):
        total_string = ''.join(args)
        try:
            polygon_str = find_substring_in_repr(total_string, cls.begin_str, cls.end_str, early_out=True)
            if not polygon_str:
                raise
            point_list = extract_floats(polygon_str)
            if point_list and len(point_list) % 2 != 0:
                raise
            vertices = []
            for index in range(0, len(point_list), 2):
                vertices.append(sims4.math.Vector3(point_list[index], 0.0, point_list[index + 1]))
            polygon = sims4.geometry.Polygon(vertices)
            return sims4.geometry.RestrictedPolygon(polygon, [])
        except:
            logger.warn('Failed to parse GeometryParam from {}'.format(total_string))
PathNode = namedtuple('PathNode', ('position', 'portal_object_id'))
class PathParam(SubstringParam):

    @classproperty
    def begin_str(cls):
        return PATH_STR

    @classproperty
    def end_str(cls):
        return PATH_END_STR

    @classmethod
    def parse_node_string(cls, *args):
        total_string = ''.join(args)
        try:
            vector_substr = find_substring_in_repr(total_string, VECTOR3_STR, VECTOR_END_STR, early_out=True)
            if not vector_substr:
                raise
            float_list = extract_floats(vector_substr)
            node_position = Vector3(float_list[0], float_list[1], float_list[2])
            total_string = total_string.replace(VECTOR3_STR, '')
            total_string = total_string.replace(vector_substr, '')
            node_portal_object_id = extract_ints(total_string)[0]
            return PathNode(position=node_position, portal_object_id=node_portal_object_id)
        except:
            logger.warn('Failed to parse path node from {} in PathParam'.format(total_string))

    def __new__(cls, *args):
        total_string = ''.join(args)
        try:
            path_str = find_substring_in_repr(total_string, cls.begin_str, cls.end_str, early_out=True)
            if not path_str:
                raise
            node_strings = find_substring_in_repr(total_string, PATH_NODE_STR, PATH_NODE_END_STR)
            path = [cls.parse_node_string(node_string) for node_string in node_strings]
            return path
        except:
            logger.warn('Failed to parse PathParam from {}'.format(total_string))

class RequiredTargetParam:

    def __init__(self, target_id:int):
        self._target_id = int(target_id, base=0)

    @property
    def target_id(self):
        return self._target_id

    def get_target(self, manager=DEFAULT):
        manager = services.object_manager() if manager is DEFAULT else manager
        target = manager.get(self._target_id)
        if target is None:
            logger.error('Could not find the target id {} for a RequiredTargetParam in the object manager.', self._target_id)
        return target

class OptionalTargetParam:
    TARGET_ID_ACTIVE_LOT = -1
    TARGET_ID_CURRENT_REGION = -2

    def __init__(self, target_id:int=None):
        if not target_id:
            self._target_id = None
        else:
            self._target_id = int(target_id, base=0)

    @property
    def target_id(self):
        return self._target_id

    def _get_target(self, _connection):
        if self._target_id is None:
            tgt_client = services.client_manager().get(_connection)
            if tgt_client is not None:
                return tgt_client.active_sim
            return
        if self._target_id == self.TARGET_ID_ACTIVE_LOT:
            return services.active_lot()
        if self._target_id == self.TARGET_ID_CURRENT_REGION:
            current_region_inst = services.current_region_instance()
            if current_region_inst is None:
                sims4.commands.output('Could not find current region instance, is this region persistable?', _connection)
            return current_region_inst
        return services.object_manager().get(self._target_id)

class OptionalSimInfoParam(OptionalTargetParam):

    def _get_target(self, _connection):
        if self._target_id is None:
            client = services.client_manager().get(_connection)
            if client is not None:
                return client.active_sim_info
            return
        return services.sim_info_manager().get(self._target_id)

class OptionalHouseholdParam(OptionalTargetParam):

    def _get_target(self, _connection):
        if self._target_id is None:
            return services.active_household()
        return services.household_manager().get(self._target_id)

def get_optional_target(opt_target:OptionalTargetParam=None, _connection=None, target_type=OptionalTargetParam, notify_failure=True):
    opt_target = opt_target if opt_target is not None else target_type()
    target = opt_target._get_target(_connection)
    if target is None and notify_failure:
        sims4.commands.output('Could not find target for specified ID: {}.'.format(opt_target._target_id), _connection)
    return target

def get_tunable_instance(resource_type, name_string_or_id, exact_match=False, multiple_support=False):
    manager = services.get_instance_manager(resource_type)
    cls = manager.get(name_string_or_id)
    if cls is not None:
        return cls
    search_string = str(name_string_or_id).lower()
    if search_string == 'none':
        return
    matches = []
    for cls in manager.types.values():
        if exact_match:
            if search_string == cls.__name__.lower():
                return cls
                if search_string == cls.__name__.lower() and not multiple_support:
                    return cls
                if search_string in cls.__name__.lower():
                    matches.append(cls)
        else:
            if search_string == cls.__name__.lower() and not multiple_support:
                return cls
            if search_string in cls.__name__.lower():
                matches.append(cls)
    if multiple_support:
        return matches
    if not matches:
        raise ValueError("No names matched '{}'.".format(search_string))
    if len(matches) > 1:
        matches.sort(key=operator.attrgetter('__name__'))
        raise ValueError("Multiple names matched '{}': {}".format(search_string, ', '.join(m.__name__ for m in matches)))
    return matches[0]

def TunableInstanceParam(resource_type, exact_match=False):

    def _factory(name_substring_or_id):
        return get_tunable_instance(resource_type, name_substring_or_id, exact_match=exact_match)

    return _factory

def TunableMultiTypeInstanceParam(resource_types, exact_match=False):

    def _factory(name_substring_or_id):
        matches = []
        for resource_type in resource_types:
            matches.extend(get_tunable_instance(resource_type, name_substring_or_id, exact_match=exact_match, multiple_support=True))
        if not matches:
            raise ValueError("No names matched '{}'.".format(name_substring_or_id))
        if len(matches) > 1:
            matches.sort(key=operator.attrgetter('__name__'))
            raise ValueError("Multiple names matched '{}': {}".format(name_substring_or_id, ', '.join(m.__name__ for m in matches)))
        return matches[0]

    return _factory
