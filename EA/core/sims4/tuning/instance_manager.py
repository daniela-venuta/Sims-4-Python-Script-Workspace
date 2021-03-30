from collections import Counterfrom collections import defaultdict, namedtuplefrom sims4.callback_utils import CallableListfrom sims4.common import Packfrom sims4.common import is_available_packfrom sims4.service_manager import Servicefrom sims4.tuning.merged_tuning_manager import get_managerimport argparseimport os.pathimport pathsimport sims4.core_servicesimport sims4.logimport sims4.reloadimport sims4.resourcesimport sims4.tuning.merged_tuning_managerimport sims4.tuning.serializationimport timelogger = sims4.log.Logger('Tuning', default_owner='cjiang')status_logger = sims4.log.Logger('Status', default_owner='manus')tuning_logger = sims4.log.Logger('TuningData', default_owner='tuning_analysis')pack_split_logger = sims4.log.Logger('SplitByPacksCounts', default_owner='tuning_analysis')tdescs_logger = sims4.log.Logger('TDESCsCounts', default_owner='tuning_analysis')with sims4.reload.protected(globals()):
    passTUNING_CALLBACK_YIELD_TIME_INTERVAL = 0.25TUNING_LOADED_CALLBACK = '_tuning_loaded_callback'VERIFY_TUNING_CALLBACK = '_verify_tuning_callback'TuningCallbackHelper = namedtuple('TuningCallbackHelper', ('template', 'name', 'source', 'value'))COMMAND_LINE_ARG_CALCULATE_STATS = 'calculate_stats'CREATING_INSTANCES = 'TuningInstanceManager: Creating instances for all InstanceManagers.'LOADING_INSTANCES = 'TuningInstanceManager: Loading data into instances for all InstanceManagers.'VERIFY_CALLBACKS = 'TuningInstanceManager: Invoking tuning verification for all InstanceManagers.'INVOKING_CALLBACKS = 'TuningInstanceManager: Invoking registered callbacks for all InstanceManagers.'INVOKING_ON_START = 'TuningInstanceManager: Invoking on_start for all InstanceManagers.'tuning_callback_counts = [0, 0]pack_split_count = Counter()calculate_stats_flag = False
def currently_loading_class_name_debug():
    return '<Unknown>'

class TuningInstanceManager(Service):

    def __init__(self, instance_manager_list, registered_callbacks_timing_file=None):
        self._instance_managers = instance_manager_list
        self._tuning_generator = None
        self._total_time = 0
        self.registered_callbacks_timing_file = registered_callbacks_timing_file

    def start(self):
        self._add_calculate_stats_flag()
        self._tuning_generator = self._execute_gen()

    def _add_calculate_stats_flag(self):
        global calculate_stats_flag
        parser = argparse.ArgumentParser()
        parser.add_argument('--' + COMMAND_LINE_ARG_CALCULATE_STATS, action='store_true', help='Calculate Tuning Data and Store in csv files ')
        (args, unused_args) = parser.parse_known_args()
        calculate_stats_flag = args.calculate_stats

    def get_status_logger_text(self):
        return 'Tuning load completed. Total Time: {:0.02f} seconds. #callbacks: {} #verification callbacks: {}'.format(self._total_time, tuning_callback_counts[0], tuning_callback_counts[1])

    @property
    def can_incremental_start(self):
        return True

    def calculate_stats(self):
        tuning_logger_csv_header = 'VERSION_NUMBER, INSTANCE_MANAGER_NAME, COUNT, load_time'
        pack_split_logger_header = 'VERSION_NUMBER, PACK_NAME, COUNT'
        tdesc_logger_header = 'VERSION_NUMBER, COUNT'
        tdescs_logger.debug(tdesc_logger_header)
        tdescs_count = len(sims4.tuning.serialization.tuning_class_set)
        tdescs_logger.debug(', {}', tdescs_count)
        tuning_logger.debug(tuning_logger_csv_header)
        for instance_manager in sorted(self._instance_managers, key=lambda x: x.TYPE.name):
            tuning_logger.debug(',{},{},{}', instance_manager.TYPE.name, len(instance_manager.types), instance_manager.load_time)
        pack_split_logger.debug(pack_split_logger_header)
        for index in Pack:
            pack_split_logger.debug(',{},{}', Pack(index).name, pack_split_count[index])

    def update_incremental_start(self):
        time_stamp = time.time()
        while not next(self._tuning_generator):
            delta = time.time() - time_stamp
            if delta > TUNING_CALLBACK_YIELD_TIME_INTERVAL:
                self._total_time += delta
                logger.debug('Just yielded from TuningInstanceManager. Time: {:2}.', delta, owner='manus')
                return False
        self._total_time += time.time() - time_stamp
        if calculate_stats_flag:
            self.calculate_stats()
        return True

    def execute(self, log_fn=None):
        time_stamp = time.time()
        for _ in self._execute_gen(log_fn=log_fn):
            current_time = time.time()
            self._total_time += current_time - time_stamp
            time_stamp = current_time

    def _execute_gen(self, log_fn=None):
        log_fn = logger.debug
        log_fn(CREATING_INSTANCES)
        for instance_manager in self._instance_managers:
            self._execute_func_and_calculate_time(instance_manager, instance_manager.create_class_instances)
            yield False
        log_fn(LOADING_INSTANCES)
        for instance_manager in self._instance_managers:
            self._execute_func_and_calculate_time(instance_manager, instance_manager.load_data_into_class_instances)
            yield False
        log_fn(INVOKING_CALLBACKS)
        for instance_manager in self._instance_managers:
            if calculate_stats_flag:
                time_stamp = time.time()
                yield from instance_manager.invoke_registered_callbacks_gen(registered_callbacks_timing_file=self.registered_callbacks_timing_file)
                instance_manager.load_time += time.time() - time_stamp
            else:
                yield from instance_manager.invoke_registered_callbacks_gen(registered_callbacks_timing_file=self.registered_callbacks_timing_file)
        log_fn(INVOKING_ON_START)
        for instance_manager in self._instance_managers:
            self._execute_func_and_calculate_time(instance_manager, instance_manager.on_start)
        status_logger.always(self.get_status_logger_text(), owner='manus', color=50)
        if log_fn is None and paths.TRACEMALLOC_TUNING_SNAPSHOT:
            from server_commands.memory_commands import tracemalloc_save_snapshot
            tracemalloc_save_snapshot(_connection=sims4.commands.NO_CONTEXT)
            from server_commands.memory_commands import tracemalloc_dump_saved_snapshot
            tracemalloc_dump_saved_snapshot(_connection=sims4.commands.NO_CONTEXT)
        yield True

    def _execute_func_and_calculate_time(self, instance_manager, execute_function):
        if calculate_stats_flag:
            time_stamp = time.time()
            execute_function()
            instance_manager.load_time += time.time() - time_stamp
        else:
            execute_function()

    def stop(self):
        for instance_manager in self._instance_managers:
            instance_manager.on_stop()

    def get_buckets_for_memory_tracking(self):
        return self._instance_managers

class InstanceManager:

    def __init__(self, path, type_enum, use_guid_for_ref=False, base_game_only=False, require_reference=False):
        self._tuned_classes = {}
        self._remapped_keys = {}
        self._callback_helper = {}
        self._verify_tunable_callback_helper = {}
        self._class_templates = []
        self.PATH = path
        self.TYPE = type_enum
        self._load_all_complete = False
        self._load_all_complete_callbacks = CallableList()
        self._use_guid_for_ref = use_guid_for_ref
        self._base_game_only = base_game_only
        self._require_reference = require_reference
        self.load_time = 0
        self._key_groupid_dict = {}
        self._current_group_id = 0

    def add_on_load_complete(self, callback):
        if not self._load_all_complete:
            self._load_all_complete_callbacks.append(callback)
        else:
            callback(self)

    @property
    def all_instances_loaded(self):
        return self._load_all_complete

    def __str__(self):
        return 'InstanceManager_{}'.format(self.TYPE.name.lower())

    def get_changed_files(self):
        return sims4.core_services.file_change_manager().consume_set(self.TYPE)

    def reload_by_key(self, key):
        raise RuntimeError('[manus] Reloading tuning is not supported for optimized python builds.')
        registered_resource_key = sims4.resources.Key(self.TYPE, key.instance)
        cls = self._tuned_classes.get(registered_resource_key)
        if cls is None:
            self.get(registered_resource_key)
            return
        try:
            sims4.tuning.serialization.restore_class_instance(cls)
            (tuning_callbacks, verify_callbacks) = sims4.tuning.serialization.load_from_xml(key, self.TYPE, cls, from_reload=True)
            if tuning_callbacks:
                for helper in tuning_callbacks:
                    helper.template.invoke_callback(cls, helper.name, helper.source, helper.value)
            if verify_callbacks:
                for helper in verify_callbacks:
                    helper.template.invoke_verify_tunable_callback(cls, helper.name, helper.source, helper.value)
            if hasattr(cls, TUNING_LOADED_CALLBACK):
                cls._tuning_loaded_callback()
            if hasattr(cls, VERIFY_TUNING_CALLBACK):
                cls._verify_tuning_callback()
        except:
            name = sims4.resources.get_name_from_key(key)
            logger.exception('Failed to reload tuning for {} (key:{}).', name, key, owner='manus')
            return
        return reload_dependencies_dict[key]

    @property
    def types(self):
        if not self.all_instances_loaded:
            logger.warn("Attempt to access instance types on '{}' before all instances are loaded", self)
        return self._tuned_classes

    def get_ordered_types(self, only_subclasses_of=object):

        def key(cls):
            result = tuple(x.__name__.lower() for x in reversed(cls.__mro__[:-1]))
            return (len(result), result)

        result = [c for c in self.types.values() if issubclass(c, only_subclasses_of)]
        result = sorted(result, key=key)
        return result

    @property
    def use_guid_for_ref(self):
        return self._use_guid_for_ref

    @property
    def base_game_only(self):
        return self._base_game_only

    @property
    def require_reference(self):
        return self._require_reference

    @property
    def remapped_keys(self):
        return self._remapped_keys

    def register_class_template(self, template):
        self._class_templates.append(template)

    def register_tuned_class(self, instance, resource_key):
        if resource_key in self._tuned_classes:
            logger.info('Attempting to re-register class instance {} (Key:{}) with {}.', self._tuned_classes[resource_key], resource_key, self, owner='manus')
            return
        self._tuned_classes[resource_key] = instance
        instance.resource_key = resource_key
        if calculate_stats_flag:
            pack_split_count[self._current_group_id] += 1
        if self.use_guid_for_ref:
            instance.guid64 = resource_key.instance

    def on_start(self):
        if paths.SUPPORT_RELOADING_RESOURCES:
            file_change_manager = sims4.core_services.file_change_manager()
            if file_change_manager is not None:
                file_change_manager.create_set(self.TYPE, self.TYPE)

    def on_stop(self):
        if paths.SUPPORT_RELOADING_RESOURCES:
            file_change_manager = sims4.core_services.file_change_manager()
            if file_change_manager is not None:
                file_change_manager.remove_set(self.TYPE)

    def create_class_instances(self):
        mtg = get_manager()
        res_id_list = mtg.get_all_res_ids(self.TYPE)
        logger.info('Creating {:4} tuning class instances managed by {}.', len(res_id_list), self, owner='manus')
        for (group_id, instance_id) in res_id_list:
            res_key = sims4.resources.Key(self.TYPE, instance_id, group_id)
            self._create_class_instance(res_key, group_id)

    def _create_class_instance(self, resource_key, group_id):
        cls = None
        try:
            cls = sims4.tuning.serialization.create_class_instance(resource_key, self.TYPE)
            if cls is None:
                return
            if calculate_stats_flag:
                self._key_groupid_dict[cls] = group_id
                self._current_group_id = group_id
            registered_resource_key = sims4.resources.Key(self.TYPE, resource_key.instance)
            self.register_tuned_class(cls, registered_resource_key)
            if resource_key.group:
                self._remapped_keys[registered_resource_key] = resource_key
        except Exception:
            if registered_resource_key in self._tuned_classes:
                del self._tuned_classes[registered_resource_key]
            logger.exception('An error occurred while attempting to create tuning instance: {}. Resource Key: {}.', cls, resource_key, owner='manus')

    def load_data_into_class_instances(self):
        logger.info('Loading {:4} tuning class instances managed by {}.', len(self._tuned_classes), self, owner='manus')
        for (key, cls) in tuple(self._tuned_classes.items()):
            try:
                tuned_classes_key = key
                if key in self._remapped_keys:
                    key = self._remapped_keys[key]
                (tuning_callback_helpers, verify_tunable_callback_helpers) = sims4.tuning.serialization.load_from_xml(key, self.TYPE, cls)
                additional_pack = getattr(cls, 'additional_pack', None)
                if not is_available_pack(cls.additional_pack):
                    del self._tuned_classes[tuned_classes_key]
                    continue
                self._callback_helper[cls] = tuning_callback_helpers
            except Exception:
                logger.exception('Exception while finalizing tuning for {}.', cls, owner='manus')
        self._remapped_keys = None

    def invoke_registered_callbacks_gen(self, registered_callbacks_timing_file=None):
        logger.info('Invoking callbacks for {:4} tuning class instances managed by {}.', len(self._tuned_classes), self, owner='manus')
        for cls in self._tuned_classes.values():
            self._current_group_id = self._key_groupid_dict.get(cls)
            start_time = time.time()
            callback_timing = self._invoke_tunable_callbacks(cls, registered_callbacks_timing_file is not None)
            invoke_time = time.time() - start_time
            try:
                if hasattr(cls, TUNING_LOADED_CALLBACK):
                    cls._tuning_loaded_callback()
            except Exception:
                logger.exception('Exception in {}.{}.', cls, TUNING_LOADED_CALLBACK, owner='manus')
            if not calculate_stats_flag or registered_callbacks_timing_file is not None:
                registered_callbacks_timing_file.write('{},{},{},{}\n'.format(cls, time.time() - start_time, invoke_time, ','.join(callback_timing)))
            yield False
        self._callback_helper = None
        self._load_all_complete = True
        self._load_all_complete_callbacks(self)

    def _invoke_tunable_callbacks(self, cls, return_call_back_timing=False):
        callback_timing = []
        tuning_callbacks = self._callback_helper.get(cls)
        if tuning_callbacks is None:
            return callback_timing
        for helper in tuning_callbacks:
            start_time = time.time()
            try:
                helper.template.invoke_callback(cls, helper.name, helper.source, helper.value)
                if return_call_back_timing:
                    callback_timing.append('{}:{}'.format(helper.template.invoke_callback, time.time() - start_time))
            except Exception:
                logger.exception('Exception in a tunable callback for variable {} in instance class {}.', helper.name, cls, owner='manus')
        return callback_timing

    def invoke_verify_tuning_callback_gen(self):
        for cls in self._tuned_classes.values():
            self._invoke_verify_tunable_callbacks(cls)
            try:
                if hasattr(cls, VERIFY_TUNING_CALLBACK):
                    cls._verify_tuning_callback()
            except Exception:
                logger.exception('Exception in {}.{}.', cls, VERIFY_TUNING_CALLBACK, owner='manus')
            yield False
        self._verify_tunable_callback_helper = None

    def _invoke_verify_tunable_callbacks(self, cls):
        tuning_callbacks = self._verify_tunable_callback_helper.get(cls)
        if tuning_callbacks is None:
            return
        for helper in tuning_callbacks:
            try:
                helper.template.invoke_verify_tunable_callback(cls, helper.name, helper.source, helper.value)
            except Exception:
                logger.exception('Exception in a verify tunable callback for variable {} in instance class {}.', helper.name, cls, owner='manus')

    def get(self, name_or_id_or_key, pack_safe=False, get_fallback_definition_id=True):
        key = sims4.resources.get_resource_key(name_or_id_or_key, self.TYPE)
        cls = self._tuned_classes.get(key)
        if cls is None:
            if not pack_safe:
                return
            raise sims4.tuning.merged_tuning_manager.UnavailablePackSafeResourceError
        return cls

    def _instantiate(self, target_type):
        return target_type()

    def export_descriptions(self, export_path, filter_fn=None):
        export_path = os.path.join(os.path.dirname(export_path), os.path.basename(self.PATH))
        export_path = os.path.join(export_path, 'Descriptions')
        to_export = {}
        for cls in sorted(self._class_templates, key=lambda cls: cls.__name__):
            cls_name = cls.__name__
            if not filter_fn is None:
                if filter_fn(cls):
                    to_export[cls_name] = cls
            to_export[cls_name] = cls
        error_count = 0
        logger.info('TDESCs for {}: {}', self.TYPE.name, ', '.join([cls.__name__ for cls in to_export.values()]))
        for cls in to_export.values():
            result = sims4.tuning.serialization.export_class(cls, export_path, self.TYPE)
            if not result:
                error_count += 1
        return error_count

    def get_debug_statistics(self):
        result = []
        result.append(('TYPE', str(self.TYPE)))
        result.append(('PATH', str(self.PATH)))
        result.append(('UseGuidForReference', str(self._use_guid_for_ref)))
        result.append(('#TuningFiles', str(len(self._tuned_classes))))
        result.append(('#ClassTemplates', str(len(self._class_templates))))
        result.append(('LoadAllComplete', str(self._load_all_complete)))
        result.append(('#LoadAllCompelteCallbacks', str(len(self._load_all_complete_callbacks))))
        return result

def increment_tunable_callback_count(count):
    tuning_callback_counts[0] += count

def increment_verify_tunable_callback_count(count):
    tuning_callback_counts[1] += count
