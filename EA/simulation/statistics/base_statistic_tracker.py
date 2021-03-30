from sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom singletons import DEFAULTfrom statistics.base_statistic import GalleryLoadBehaviorfrom statistics.base_statistic_listener import BaseStatisticCallbackListenerfrom traits.trait_type import TraitTypeimport gsi_handlersimport servicesimport simsimport sims4.callback_utilsimport sims4.logimport uidlogger = sims4.log.Logger('Statistic')lod_logger = sims4.log.Logger('LoD', default_owner='miking')with sims4.reload.protected(globals()):
    _handle_id_gen = uid.UniqueIdGenerator(1)
class BaseStatisticTracker(SimInfoTracker):
    __slots__ = ('_statistics', '_owner', '_watchers', '_delta_watchers', '_listener_seeds', '_on_remove_callbacks', 'suppress_callback_setup_during_load', 'statistics_to_skip_load', 'suppress_callback_alarm_calculation', '_recovery_add_in_progress', '_delayed_active_lod_statistics')

    def __init__(self, owner=None):
        self._statistics = None
        self._owner = owner
        self._watchers = None
        self._delta_watchers = None
        self._listener_seeds = None
        self._on_remove_callbacks = None
        self.suppress_callback_setup_during_load = False
        self.suppress_callback_alarm_calculation = False
        self.statistics_to_skip_load = None
        self._recovery_add_in_progress = None
        self._delayed_active_lod_statistics = None

    def __iter__(self):
        if self._statistics is None:
            return iter([])
        stat_iter = self._statistics.values().__iter__()
        return (stat for stat in stat_iter if stat is not None)

    def __len__(self):
        if self._statistics is not None:
            return len(self._statistics)
        return 0

    def all_statistics(self):
        if self._statistics is None:
            return []
        stat_iter = self._statistics.items().__iter__()
        return (stat_type if stat is None else stat for (stat_type, stat) in stat_iter)

    @property
    def owner(self):
        return self._owner

    def set_callback_alarm_calculation_supression(self, value):
        if self.suppress_callback_alarm_calculation != value:
            self.suppress_callback_alarm_calculation = value
            if self._statistics:
                for stat in self._statistics.values():
                    if stat is not None:
                        stat._update_callback_listeners()

    def _statistics_values_gen(self):
        if self._statistics:
            for stat in self._statistics.values():
                if stat is not None:
                    yield stat

    def destroy(self):
        for stat in list(self):
            stat.on_remove(on_destroy=True)
        if self._watchers is not None:
            self._watchers.clear()
        self._on_remove_callbacks = None

    def on_initial_startup(self):
        pass

    def remove_statistics_on_travel(self):
        for statistic in tuple(self._statistics_values_gen()):
            if not statistic.persisted:
                stat_type = statistic.stat_type
                if not self.owner is None:
                    if not self.owner.is_statistic_type_added_by_modifier(stat_type):
                        self.remove_statistic(stat_type)
                self.remove_statistic(stat_type)

    def _add_callback_listener_seed(self, stat_type, seed):
        if seed is not None:
            if self._listener_seeds is None:
                self._listener_seeds = {}
            if stat_type not in self._listener_seeds:
                self._listener_seeds[stat_type] = []
            if seed not in self._listener_seeds[stat_type]:
                self._listener_seeds[stat_type].append(seed)

    def _remove_callback_listener_seed(self, seed):
        if seed is None:
            return
        if self._listener_seeds is None:
            return
        stat_type = seed.statistic_type
        if stat_type in self._listener_seeds:
            seeds = self._listener_seeds[stat_type]
            if seed in seeds:
                seeds.remove(seed)
                seed.destroy()
                if not seeds:
                    self._listener_seeds[stat_type]

    def create_and_add_listener(self, stat_type, threshold, callback, on_callback_alarm_reset=None) -> BaseStatisticCallbackListener:
        if stat_type.added_by_default():
            add = stat_type.add_if_not_in_tracker
        else:
            add = False
        stat = self.get_statistic(stat_type, add=add)
        if stat is None:
            seed = stat_type.create_callback_listener_seed(stat_type, threshold, callback, on_callback_alarm_reset=on_callback_alarm_reset)
            self._add_callback_listener_seed(stat_type, seed)
            return seed
        else:
            callback_listener = stat.create_and_add_callback_listener(threshold, callback, on_callback_alarm_reset=on_callback_alarm_reset)
            return callback_listener

    def remove_listener(self, listener:BaseStatisticCallbackListener):
        stat = self.get_statistic(listener.statistic_type)
        if stat is None:
            self._remove_callback_listener_seed(listener)
        else:
            stat.remove_callback_listener(listener)

    def add_watcher(self, callback):
        if self._watchers is None:
            self._watchers = {}
        handle_id = _handle_id_gen()
        self._watchers[handle_id] = callback
        return handle_id

    def has_watcher(self, handle):
        if self._watchers is None:
            return False
        return handle in self._watchers

    def remove_watcher(self, handle):
        if self._watchers is None:
            return
        del self._watchers[handle]

    def notify_watchers(self, stat_type, old_value, new_value):
        if self._watchers is None:
            return
        for watcher in list(self._watchers.values()):
            watcher(stat_type, old_value, new_value)

    def add_delta_watcher(self, callback):
        if self._delta_watchers is None:
            self._delta_watchers = {}
        handle_id = _handle_id_gen()
        self._delta_watchers[handle_id] = callback
        return handle_id

    def has_delta_watcher(self, handle):
        if self._delta_watchers is None:
            return
        return handle in self._delta_watchers

    def remove_delta_watcher(self, handle):
        if self._delta_watchers is None:
            return
        del self._delta_watchers[handle]

    def notify_delta(self, stat_type, delta):
        if self._delta_watchers is None:
            return
        for watcher in tuple(self._delta_watchers.values()):
            watcher(stat_type, delta)

    def add_on_remove_callback(self, callback):
        if self._on_remove_callbacks is None:
            self._on_remove_callbacks = sims4.callback_utils.RemovableCallableList()
        self._on_remove_callbacks.append(callback)

    def remove_on_remove_callback(self, callback):
        if self._on_remove_callbacks is not None:
            if callback in self._on_remove_callbacks:
                self._on_remove_callbacks.remove(callback)
            if not self._on_remove_callbacks:
                self._on_remove_callbacks = None

    def add_statistic(self, stat_type, owner=None, create_instance=True, **kwargs):
        if self._statistics:
            stat = self._statistics.get(stat_type)
        else:
            stat = None
        if owner is None:
            owner = self._owner
        is_sim = owner.is_sim if owner is not None else False
        if is_sim and stat_type in owner.get_blacklisted_statistics():
            robot_traits = owner.trait_tracker.get_traits_of_type(TraitType.ROBOT)
            if not robot_traits:
                logger.error('Attempting to add stat {} when it is blacklisted on sim {}.', stat_type, self.owner)
            return
        owner_lod = owner.lod if is_sim else None
        if owner_lod is not None and stat_type.remove_at_owner_lod(lod=owner_lod, owner=owner):
            return
        if stat is None and stat_type.can_add(owner, **kwargs):
            stat = stat_type(self)
            if self._statistics is None:
                self._statistics = {}
            if create_instance or not stat.instance_required:
                self._statistics[stat_type] = None
                return
            self._statistics[stat_type] = stat
            stat.on_add()
            value = stat.get_value()
            if self._watchers:
                self.notify_watchers(stat_type, value, value)
            if self._listener_seeds is not None and stat_type in self._listener_seeds:
                for seed in self._listener_seeds[stat_type]:
                    seed.stat = stat
                    stat.add_callback_listener(seed)
                del self._listener_seeds[stat_type]
                stat._update_callback_listeners(stat_type.default_value, value)
        return stat

    def remove_statistic(self, stat_type, on_destroy=False):
        if self.has_statistic(stat_type):
            stat = self._statistics[stat_type]
            del self._statistics[stat_type]
            if stat is not None:
                if self._on_remove_callbacks:
                    self._on_remove_callbacks(stat)
                stat.on_remove(on_destroy=on_destroy)

    def clear_statistic(self, stat_type):
        if self._statistics and stat_type in self._statistics:
            stat = self._statistics[stat_type]
            if stat is not None:
                self._statistics[stat_type] = None
                if self._on_remove_callbacks:
                    self._on_remove_callbacks(stat)
                stat.on_remove()

    def get_statistic(self, stat_type, add=False):
        try:
            must_end_recovery = False
            if self._statistics:
                stat = self._statistics.get(stat_type)
                if self.has_statistic(stat_type):
                    if self._recovery_add_in_progress is None:
                        self._recovery_add_in_progress = set()
                    self._recovery_add_in_progress.add(stat_type)
                    must_end_recovery = True
                    add = True
            else:
                stat = None
            if stat is None and add:
                stat = self.add_statistic(stat_type)
                if stat is not None and self._recovery_add_in_progress is not None and stat_type in self._recovery_add_in_progress:
                    stat.on_recovery()
            return stat
        finally:
            if stat_type in self._recovery_add_in_progress:
                self._recovery_add_in_progress.remove(stat_type)
                if not self._recovery_add_in_progress:
                    self._recovery_add_in_progress = None

    def has_statistic(self, stat_type):
        if self._statistics is None:
            return False
        return stat_type in self._statistics

    @property
    def recovery_add_in_progress(self):
        return bool(self._recovery_add_in_progress)

    def get_communicable_statistic_set(self):
        if self._statistics is None:
            return set()
        return {stat_type for stat_type in self._statistics if stat_type.communicable_by_interaction_tag is not None}

    def get_value(self, stat_type, add=False):
        stat = self.get_statistic(stat_type, add=add)
        if stat is None:
            return stat_type.default_value
        return stat.get_value()

    def get_int_value(self, stat_type, scale:int=None):
        value = self.get_value(stat_type)
        if scale is not None:
            value = scale*value/stat_type.max_value
        return int(sims4.math.floor(value))

    def get_user_value(self, stat_type):
        stat_or_stat_type = self.get_statistic(stat_type) or stat_type
        return stat_or_stat_type.get_user_value()

    def set_value(self, stat_type, value, add=DEFAULT, from_load=False, from_init=False, **kwargs):
        if add is DEFAULT:
            add = from_load or stat_type.add_if_not_in_tracker
        if not stat_type.added_by_default():
            add = False
        stat = self.get_statistic(stat_type, add=add)
        if from_init and add and stat is not None:
            stat.set_value(value, from_load=from_load)

    def set_user_value(self, stat_type, user_value):
        stat = self.get_statistic(stat_type, add=True)
        if stat is not None:
            stat.set_user_value(user_value)

    def add_value(self, stat_type, amount, **kwargs):
        if amount == 0:
            return
        stat = self.get_statistic(stat_type, add=stat_type.add_if_not_in_tracker)
        if stat is not None:
            stat.add_value(amount, **kwargs)

    def set_max(self, stat_type):
        stat = self.get_statistic(stat_type, add=stat_type.add_if_not_in_tracker)
        if stat is not None:
            self.set_value(stat_type, stat.max_value)

    def set_min(self, stat_type):
        stat = self.get_statistic(stat_type, add=stat_type.add_if_not_in_tracker)
        if stat is not None:
            self.set_value(stat_type, stat.min_value)

    def get_decay_time(self, stat_type, threshold):
        pass

    def set_convergence(self, stat_type, convergence):
        raise TypeError("This stat type doesn't have a convergence value.")

    def reset_convergence(self, stat_type):
        raise TypeError("This stat type doesn't have a convergence value.")

    def set_all_commodities_to_best_value(self, visible_only=False, core_only=False, ignore_ranked=True):
        for stat_type in list(self._statistics):
            stat = self.get_statistic(stat_type)
            if stat is not None:
                if ignore_ranked and stat.is_ranked:
                    pass
                else:
                    if not stat.is_visible:
                        if core_only and stat.core:
                            self.set_value(stat_type, stat_type.best_value)
                    self.set_value(stat_type, stat_type.best_value)

    def save(self):
        self.check_for_unneeded_initial_statistics()
        save_list = []
        if self._statistics:
            for (stat_type, stat) in self._statistics.items():
                if stat_type.persisted:
                    value = stat.get_saved_value() if stat else None
                    save_data = (stat_type.__name__, value)
                    save_list.append(save_data)
        if self._delayed_active_lod_statistics is not None:
            save_list.extend(self._delayed_active_lod_statistics)
        return save_list

    def _should_add_commodity_from_gallery(self, statistic_type, skip_load):
        if statistic_type.gallery_load_behavior == GalleryLoadBehavior.LOAD_FOR_ALL:
            return True
        if self.owner.is_sim:
            if skip_load and statistic_type.gallery_load_behavior != GalleryLoadBehavior.LOAD_ONLY_FOR_SIM:
                return False
        elif self.owner.is_downloaded and statistic_type.gallery_load_behavior != GalleryLoadBehavior.LOAD_ONLY_FOR_OBJECT:
            return False
        return True

    def load(self, load_list):
        try:
            statistic_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            for (stat_type_name, value) in load_list:
                stat_cls = statistic_manager.get(stat_type_name)
                if stat_cls is None:
                    pass
                elif self._sim_info.lod >= stat_cls.min_lod_value:
                    if stat_cls.persisted:
                        self.set_value(stat_cls, value)
                    else:
                        logger.info('Trying to load unavailable STATISTIC resource: {}', stat_type_name)
                        if stat_cls.min_lod_value == SimInfoLODLevel.ACTIVE:
                            if self._delayed_active_lod_statistics is None:
                                self._delayed_active_lod_statistics = list()
                            self._delayed_active_lod_statistics.append((stat_type_name, value))
                elif stat_cls.min_lod_value == SimInfoLODLevel.ACTIVE:
                    if self._delayed_active_lod_statistics is None:
                        self._delayed_active_lod_statistics = list()
                    self._delayed_active_lod_statistics.append((stat_type_name, value))
        except ValueError:
            logger.error('Attempting to load old data in BaseStatisticTracker.load()')
        self.check_for_unneeded_initial_statistics()

    def debug_output_all(self, _connection):
        if self._statistics:
            for (stat_type, stat) in self._statistics.items():
                sims4.commands.output('{:<24} Value: {:-6.2f}'.format(stat_type.__name__, stat.get_value() if stat else 'None'), _connection)

    def debug_set_all_to_best_except(self, stat_to_exclude, core=True):
        for stat_type in list(self._statistics):
            if core:
                pass
            if stat_type != stat_to_exclude:
                self.set_value(stat_type, stat_type.best_value)

    def debug_set_all_to_min(self, core=True):
        for stat_type in list(self._statistics):
            if core:
                if self.get_statistic(stat_type).core:
                    self.set_value(stat_type, stat_type.min_value)
            self.set_value(stat_type, stat_type.min_value)

    def debug_set_all_to_default(self, core=True):
        for stat_type in list(self._statistics):
            if core:
                if self.get_statistic(stat_type).core:
                    self.set_value(stat_type, stat_type.initial_value)
            self.set_value(stat_type, stat_type.initial_value)

    def _load_delayed_active_statistics(self):
        statistic_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        for (stat_type_name, value) in self._delayed_active_lod_statistics:
            stat_cls = statistic_manager.get(stat_type_name)
            if stat_cls is None:
                pass
            elif stat_cls.persisted:
                self.set_value(stat_cls, value)
            else:
                logger.info('Trying to load unavailable STATISTIC resource: {}', stat_type_name)
        self._delayed_active_lod_statistics = None

    def _get_stat_data_for_active_lod(self, statistic):
        return (statistic.guid64, statistic.get_saved_value())

    def on_lod_update(self, old_lod, new_lod):
        if self.owner is None:
            return
        if not isinstance(self._owner, sims.sim_info.SimInfo):
            raise NotImplementedError('LOD is updating from {} to {} on an non-sim object. This is not supported.'.format(old_lod, new_lod))
        if self._statistics is not None:
            for stat_type in tuple(self._statistics):
                stat_to_test = self.get_statistic(stat_type)
                if stat_to_test is not None and stat_to_test.remove_at_owner_lod(lod=new_lod, owner=self._owner):
                    if stat_to_test.min_lod_value == SimInfoLODLevel.ACTIVE:
                        if self._delayed_active_lod_statistics is None:
                            self._delayed_active_lod_statistics = list()
                        self._delayed_active_lod_statistics.append(self._get_stat_data_for_active_lod(stat_to_test))
                    self.remove_statistic(stat_type)
        if new_lod >= SimInfoLODLevel.ACTIVE and self._delayed_active_lod_statistics is not None:
            self._load_delayed_active_statistics()

    def check_for_unneeded_initial_statistics(self):
        if not self._statistics:
            return
        total_stats = len(self._statistics)
        removed_stats = 0
        for (stat_type, stat_to_test) in self._statistics.items():
            if not stat_to_test is None:
                if stat_to_test.instance_required:
                    pass
                else:
                    callback_listeners = stat_to_test.release_control_on_all_callback_listeners()
                    for listener in callback_listeners:
                        if listener.should_seed and hasattr(listener._callback, '__self__') and listener._callback.__self__ is listener.stat:
                            listener.destroy()
                        else:
                            listener.stat = None
                            stat_type = listener.statistic_type
                            if stat_type is not None:
                                self._add_callback_listener_seed(stat_type, listener)
                    lod_logger.info('Removing unneeded statistic: {} from: {}', stat_type, self.owner)
                    if gsi_handlers.statistics_removed_handlers.is_archive_enabled():
                        gsi_handlers.statistics_removed_handlers.archive_removed_statistic(stat_type.__name__, gsi_handlers.gsi_utils.format_object_name(self.owner))
                    self.clear_statistic(stat_type)
                    removed_stats = removed_stats + 1
        removed_pct = removed_stats/total_stats*100 if total_stats > 0 else 0
        lod_logger.info('---> {}: Removed {} of {} statistics ({}%)', self.owner, removed_stats, total_stats, removed_pct)
