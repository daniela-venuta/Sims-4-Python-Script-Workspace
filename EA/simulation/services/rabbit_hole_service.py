from event_testing.resolver import SingleSimResolverfrom interactions.interaction_finisher import FinishingTypefrom protocolbuffers import GameplaySaveData_pb2from distributor.rollback import ProtocolBufferRollbackfrom event_testing.test_events import TestEventfrom filters.sim_filter_service import SimFilterGlobalBlacklistReasonfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom interactions.utils.exit_condition_manager import ConditionalActionManagerfrom objects import ALL_HIDDEN_REASONSfrom rabbit_hole.rabbit_hole import RabbitHolePhase, RabbitHoleTimingPolicyfrom sims.sim_spawner import SimSpawnerfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePackSafeReference, TunableReferencefrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4logger = sims4.log.Logger('Rabbit Hole Service', default_owner='rrodgers')
class RabbitHoleService(Service):
    LEAVE_EARLY_INTERACTION = TunableReference(description='\n        The interaction that causes a sim to leave their rabbit hole early\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='RabbitHoleLeaveEarlyInteraction')
    FAMILIAR_RABBIT_HOLE = TunablePackSafeReference(description='\n        A special rabbit hole that is used by familiars when their master is also put into a rabbit hole.\n        ', manager=services.get_instance_manager(sims4.resources.Types.RABBIT_HOLE))
    GENERIC_GO_HOME_AND_ATTEND = TunableReference(description=' \n        An interaction that will be used to travel sims who need to rabbit hole\n        at their home zone.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))

    def __init__(self):
        self._rabbit_holes = {}
        self._conditional_actions_manager = ConditionalActionManager()

    def put_sim_in_managed_rabbithole(self, sim_info, rabbit_hole_type=None, rabbit_hole_id=None, **rabbit_hole_kwargs):
        sim_id = sim_info.id
        rabbit_hole = None
        if rabbit_hole_id is not None:
            rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
            if rabbit_hole is None:
                logger.error('put_sim_in_managed_rabbithole called on rabbit hole {} of type {} for sim {} but no such rabbit hole exists', rabbit_hole_id, rabbit_hole_type, sim_info)
                return
        elif sim_info.id in self._rabbit_holes:
            rabbit_hole = rabbit_hole_type(sim_id, starting_phase=RabbitHolePhase.QUEUED, **rabbit_hole_kwargs)
            self._rabbit_holes[sim_id].append(rabbit_hole)
        else:
            rabbit_hole = rabbit_hole_type(sim_id, **rabbit_hole_kwargs)
            self._rabbit_holes[sim_id] = [rabbit_hole]
        result = True
        rabbit_hole_id = rabbit_hole.rabbit_hole_id
        is_starting = rabbit_hole.current_phase == RabbitHolePhase.STARTING
        if rabbit_hole is not self._rabbit_holes[sim_id][0]:
            result = self._setup_queued(sim_id, rabbit_hole_id)
        else:
            if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if rabbit_hole.select_affordance() is not None:
                    result = self._setup_instantiated_no_travel(sim_id, rabbit_hole_id)
                else:
                    result = self._setup_instantiated_travel(sim_id, rabbit_hole_id)
            elif sim_info.is_at_home or sim_info.should_send_home_to_rabbit_hole():
                result = self._setup_uninstantiated_no_travel(sim_id, rabbit_hole_id)
            elif rabbit_hole.current_phase is RabbitHolePhase.STARTING:
                result = self._setup_uninstantiated_travel(sim_id, rabbit_hole_id)
            if is_starting:
                result = self._setup_linked_rabbit_holes(sim_id, rabbit_hole_id)
        if not result:
            self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id, canceled=True)
            return
        return rabbit_hole_id

    def try_remove_sim_from_rabbit_hole(self, sim_id, rabbit_hole_id, callback=None):
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        if sim is not None and rabbit_hole is not None:
            affordance = rabbit_hole.select_affordance()
            cancel_result = False
            if affordance:
                interaction = sim.find_interaction_by_affordance(affordance)
                if callback is not None:
                    binded_callback = lambda *_, **__: callback(True)
                    interaction.add_exit_function(binded_callback)
                cancel_result = interaction.cancel_user(cancel_reason_msg='Interaction canceled by the rabbit hole service')
                if cancel_result or callback is not None:
                    callback(False)
        elif rabbit_hole is not None:
            self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id)
            if callback is not None:
                callback(True)

    def remove_sim_from_rabbit_hole(self, sim_id, rabbit_hole_id, canceled=False):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        if rabbit_hole is None:
            return
        self._rabbit_holes[sim_id].remove(rabbit_hole)
        if rabbit_hole.current_phase is RabbitHolePhase.QUEUED:
            rabbit_hole.on_remove(canceled=canceled)
            return
        if len(self._rabbit_holes[sim_id]) == 0:
            del self._rabbit_holes[sim_id]
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            affordance = rabbit_hole.select_affordance()
            interaction = sim.find_interaction_by_affordance(affordance)
            if interaction is not None:
                if canceled and sim_info.is_selectable:
                    interaction.cancel_user(cancel_reason_msg='Interaction canceled by the rabbit hole service')
                else:
                    interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Interaction canceled by the rabbit hole service')
        if not canceled:
            resolver = SingleSimResolver(sim_info)
            for loot_action in rabbit_hole.loot_list:
                loot_action.apply_to_resolver(resolver)
        rabbit_hole.on_remove(canceled=canceled)
        sim_filter_service = services.sim_filter_service()
        if sim_id in sim_filter_service.get_global_blacklist():
            sim_filter_service.remove_sim_id_from_global_blacklist(sim_id, SimFilterGlobalBlacklistReason.RABBIT_HOLE)
        self._conditional_actions_manager.detach_conditions(rabbit_hole)
        if rabbit_hole.away_action is not None and sim_info.away_action_tracker is not None:
            sim_info.away_action_tracker.reset_to_default_away_action()
        for (linked_sim_id, linked_rabbithole_id) in rabbit_hole.linked_rabbit_holes:
            self.remove_sim_from_rabbit_hole(linked_sim_id, linked_rabbithole_id, canceled=canceled)
        if sim_id not in self._rabbit_holes:
            return
        for next_rabbit_hole in tuple(self._rabbit_holes[sim_id]):
            if not next_rabbit_hole.is_valid_to_restore(sim_info):
                self.remove_sim_from_rabbit_hole(sim_id, next_rabbit_hole.rabbit_hole_id)
            elif next_rabbit_hole.current_phase is RabbitHolePhase.QUEUED:
                self.put_sim_in_managed_rabbithole(sim_info, rabbit_hole_id=next_rabbit_hole.rabbit_hole_id)
                break

    def get_rabbit_hole_id_by_type(self, sim_id, rabbit_hole_type):
        if sim_id not in self._rabbit_holes:
            return
        return next((rh for rh in self._rabbit_holes[sim_id] if type(rh) is rabbit_hole_type), None)

    def get_head_rabbit_hole_id(self, sim_id):
        if sim_id in self._rabbit_holes:
            return self._rabbit_holes[sim_id][0].rabbit_hole_id

    def set_rabbit_hole_expiration_callback(self, sim_id, rabbit_hole_id, callback):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        if rabbit_hole is not None:
            rabbit_hole.callbacks.register(callback)
        else:
            logger.error('Failed to setup rabbit hole with id {} for sim id {}', callback, rabbit_hole_id, sim_id)

    def remove_rabbit_hole_expiration_callback(self, sim_id, rabbit_hole_id, callback):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        if rabbit_hole is not None:
            rabbit_hole.callbacks.unregister(callback)
        else:
            logger.error('Trying to remove a callback: {} that does not exist for sim: {} in rabbit hole service.', callback, sim_id)
            return

    def set_ignore_travel_cancel_for_sim_id_in_rabbit_hole(self, sim_id):
        self._rabbit_holes[sim_id][0].ignore_travel_cancel_callbacks = True

    def should_override_selector_visual_type(self, sim_id):
        if sim_id in self._rabbit_holes and self._rabbit_holes[sim_id][0].is_active():
            return True
        return False

    def is_head_rabbit_hole_user_cancelable(self, sim_id):
        return self._rabbit_holes[sim_id][0].select_affordance().never_user_cancelable

    def will_override_spin_up_action(self, sim_id):
        return sim_id in self._rabbit_holes

    def get_time_for_head_rabbit_hole(self, sim_id):
        if sim_id in self._rabbit_holes:
            rabbit_hole = self._rabbit_holes[sim_id][0]
            alarm_handle = rabbit_hole.alarm_handle
            if alarm_handle is None:
                return rabbit_hole.time_remaining_on_load
            else:
                return alarm_handle.get_remaining_time()

    def is_in_rabbit_hole(self, sim_id, rabbit_hole_id=None):
        if rabbit_hole_id is None:
            return sim_id in self._rabbit_holes
        return self._get_rabbit_hole(sim_id, rabbit_hole_id)

    def get_head_rabbit_hole_home_interaction_name(self, sim_id, target=None, context=None, **interaction_parameters):
        if sim_id not in self._rabbit_holes:
            return
        rabbit_hole = self._rabbit_holes[sim_id][0]
        if context is None:
            sim = services.sim_info_manager().get(sim_id).get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        return rabbit_hole.affordance.get_name(target=target, context=context, **interaction_parameters)

    def get_head_rabbit_hole_home_interaction_icon(self, sim_id, target=None, context=None):
        if sim_id not in self._rabbit_holes:
            return
        rabbit_hole = self._rabbit_holes[sim_id][0]
        if context is None:
            sim = services.sim_info_manager().get(sim_id).get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        return rabbit_hole.affordance.get_icon_info(target=target, context=context)

    def sim_skewer_rabbit_hole_affordances_gen(self, sim_info, context, **kwargs):
        for aop in self.LEAVE_EARLY_INTERACTION.potential_interactions(None, context, sim_info=sim_info, **kwargs):
            yield aop

    def _get_rabbit_hole(self, sim_id, rabbit_hole_id):
        if sim_id in self._rabbit_holes:
            matching_rabbit_hole = next((rh for rh in self._rabbit_holes[sim_id] if rh.rabbit_hole_id == rabbit_hole_id), None)
            if matching_rabbit_hole is not None:
                return matching_rabbit_hole

    def _setup_linked_rabbit_holes(self, sim_id, rabbit_hole_id):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        familiar_tracker = services.sim_info_manager().get(sim_id).familiar_tracker
        if familiar_tracker is not None:
            familiar = familiar_tracker.get_active_familiar()
            if familiar is not None and familiar.is_sim:
                linked_rabbit_hole_id = self.put_sim_in_managed_rabbithole(familiar.sim_info, RabbitHoleService.FAMILIAR_RABBIT_HOLE)
                if linked_rabbit_hole_id is None:
                    return False
                rabbit_hole.linked_rabbit_holes.append((familiar.sim_id, linked_rabbit_hole_id))
        return True

    def _setup_queued(self, sim_id, rabbit_hole_id):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        rabbit_hole.current_phase = RabbitHolePhase.QUEUED
        if rabbit_hole.time_tracking_policy == RabbitHoleTimingPolicy.COUNT_ALL_TIME:
            time_expired_callback = lambda _, sim_id=sim_id: self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id, canceled=True)
            rabbit_hole.set_expiration_alarm(time_expired_callback)
        return True

    def _setup_instantiated_no_travel(self, sim_id, rabbit_hole_id):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        affordance = rabbit_hole.select_affordance()
        if rabbit_hole.is_active():
            sim_info = services.sim_info_manager().get(sim_id)
            sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            sim.set_allow_route_instantly_when_hitting_marks(True)
            services.sim_info_manager().set_sim_to_skip_preroll(sim_id)
            if rabbit_hole.current_phase == RabbitHolePhase.ACTIVE_PERSISTED:
                services.get_event_manager().register_with_custom_key(self, TestEvent.InteractionStart, affordance)
        else:
            rabbit_hole.current_phase = RabbitHolePhase.TRANSITIONING
            services.get_event_manager().register_with_custom_key(self, TestEvent.InteractionStart, affordance)
        result = self._push_affordance_with_cancel_callback(sim_id, rabbit_hole_id, affordance, picked_skill=rabbit_hole.picked_skill)
        if not result:
            return False
        return True

    def _setup_instantiated_travel(self, sim_id, rabbit_hole_id):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        rabbit_hole.current_phase = RabbitHolePhase.TRAVELING
        affordance = rabbit_hole.select_travel_affordance() or self.GENERIC_GO_HOME_AND_ATTEND
        result = self._push_affordance_with_cancel_callback(sim_id, rabbit_hole_id, affordance, picked_skill=rabbit_hole.picked_skill)
        if not result:
            return False

        def _on_travel_finished(interaction, sim_id=sim_id, rabbit_hole_id=rabbit_hole_id):
            if not interaction.is_finishing_naturally:
                self._on_cancel(interaction, sim_id=sim_id, rabbit_hole_id=rabbit_hole_id)
            if not self.is_in_rabbit_hole(sim_id, rabbit_hole_id):
                return
            sim_info = services.sim_info_manager().get(sim_id)
            if not sim_info.is_at_home:
                home_zone_id = sim_info.household.home_zone_id
                sim_info.inject_into_inactive_zone(home_zone_id, skip_instanced_check=True)
            self._activate_rabbit_hole(sim_id, rabbit_hole_id)

        result.interaction.register_on_finishing_callback(_on_travel_finished)
        return True

    def _setup_uninstantiated_no_travel(self, sim_id, rabbit_hole_id):
        self._activate_rabbit_hole(sim_id, rabbit_hole_id)
        return True

    def _setup_uninstantiated_travel(self, sim_id, rabbit_hole_id):
        sim_info = services.sim_info_manager().get(sim_id)
        home_zone_id = sim_info.household.home_zone_id
        if services.current_zone_id() != home_zone_id:
            sim_info.inject_into_inactive_zone(home_zone_id)
            return self._setup_uninstantiated_no_travel(sim_id, rabbit_hole_id)
        else:
            return SimSpawner.spawn_sim(sim_info, spawn_action=lambda _: self._setup_instantiated_no_travel(sim_info.id, rabbit_hole_id), update_skewer=False)

    def _activate_rabbit_hole(self, sim_id, rabbit_hole_id):
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        if rabbit_hole.current_phase == RabbitHolePhase.ACTIVE:
            return
        rabbit_hole.current_phase = RabbitHolePhase.ACTIVE
        sim_info = services.sim_info_manager().get(sim_id)
        rabbit_hole.on_activate()
        sim_filter_service = services.sim_filter_service()
        sim_filter_service.add_sim_id_to_global_blacklist(sim_id, SimFilterGlobalBlacklistReason.RABBIT_HOLE)
        exit_condition_callback = lambda _, sim_id=sim_id: self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id, canceled=True)
        exit_condition_test_resolver = SingleSimResolver(sim_info)
        exit_conditions = (exit_condition for exit_condition in rabbit_hole.exit_conditions if exit_condition.tests.run_tests(exit_condition_test_resolver))
        if exit_conditions:
            self._conditional_actions_manager.attach_conditions(rabbit_hole, exit_conditions, exit_condition_callback)
        if rabbit_hole.time_tracking_policy is not RabbitHoleTimingPolicy.NO_TIME_LIMIT:
            time_expired_callback = lambda _, sim_id=sim_id: self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id)
            rabbit_hole.set_expiration_alarm(time_expired_callback)
        if rabbit_hole.away_action is not None and sim_info.away_action_tracker is not None:
            sim_info.away_action_tracker.create_and_apply_away_action(rabbit_hole.away_action)

    def _on_cancel(self, interaction, sim_id=None, rabbit_hole_id=None):
        if services.current_zone().is_zone_shutting_down:
            return
        if not self.is_in_rabbit_hole(sim_id, rabbit_hole_id):
            return
        rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
        if rabbit_hole is None:
            return
        if (interaction.affordance is self.GENERIC_GO_HOME_AND_ATTEND or interaction.affordance is rabbit_hole.select_travel_affordance()) and rabbit_hole.ignore_travel_cancel_callbacks:
            return
        if interaction.is_finishing_naturally:
            return
        self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id, canceled=True)

    def _push_affordance_with_cancel_callback(self, sim_id, rabbit_hole_id, affordance, picked_skill=None):
        sim = services.sim_info_manager().get(sim_id).get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
        result = sim.push_super_affordance(affordance, sim, context, rabbit_hole_id=rabbit_hole_id, picked_statistic=picked_skill)
        if not result:
            return result
        cancel = lambda interaction: self._on_cancel(interaction, sim_id=sim_id, rabbit_hole_id=rabbit_hole_id)
        result.interaction.register_on_cancelled_callback(cancel)
        return result

    def restore_rabbit_hole_state(self):
        sim_info_manager = services.sim_info_manager()
        rabbit_holes_with_linked_master = []
        rabbit_holes_to_cancel = []
        for (sim_id, rabbit_holes) in self._rabbit_holes.copy().items():
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                for rabbit_hole in list(rabbit_holes):
                    self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole.rabbit_hole_id, canceled=True)
            else:
                for rabbit_hole in list(rabbit_holes):
                    if not rabbit_hole.is_valid_to_restore(sim_info):
                        rabbit_holes_to_cancel.append((sim_id, rabbit_hole.rabbit_hole_id))
                        logger.error('Rabbit hole id:{} was not valid to be restored for sim {}.  \n Please note any changes were done prior to save.', rabbit_hole.guid64, sim_info)
                    else:
                        rabbit_hole.on_restore()
                        self.put_sim_in_managed_rabbithole(sim_info, rabbit_hole_id=rabbit_hole.rabbit_hole_id)
                        rabbit_holes_with_linked_master.extend(rabbit_hole.linked_rabbit_holes)
        for (sim_id, rabbit_holes) in self._rabbit_holes.items():
            for rabbit_hole in rabbit_holes:
                if self.FAMILIAR_RABBIT_HOLE is not None and rabbit_hole.guid64 == self.FAMILIAR_RABBIT_HOLE.guid64 and rabbit_hole.rabbit_hole_id not in rabbit_holes_with_linked_master:
                    rabbit_holes_to_cancel.append((sim_id, rabbit_hole.rabbit_hole_id))
        for (sim_id, rabbit_hole_id) in rabbit_holes_to_cancel:
            self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id, canceled=True)

    def save(self, save_slot_data=None, **kwargs):
        rabbit_hole_service_proto = GameplaySaveData_pb2.PersistableRabbitHoleService()
        for (sim_id, rabbit_holes) in self._rabbit_holes.items():
            for rabbit_hole in rabbit_holes:
                with ProtocolBufferRollback(rabbit_hole_service_proto.rabbit_holes) as entry:
                    entry.sim_id = sim_id
                    entry.rabbit_hole_id = rabbit_hole.guid64
                    entry.rabbit_hole_instance_id = rabbit_hole.rabbit_hole_id
                    rabbit_hole.save(entry)
                    if rabbit_hole.linked_rabbit_holes:
                        (linked_sim_ids, linked_rabbit_hole_ids) = zip(*rabbit_hole.linked_rabbit_holes)
                        entry.linked_sim_ids.extend(linked_sim_ids)
                        entry.linked_rabbit_hole_ids.extend(linked_rabbit_hole_ids)
        save_slot_data.gameplay_data.rabbit_hole_service = rabbit_hole_service_proto

    def load(self, **_):
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        rabbit_holes_to_fixup_links = []
        for entry in save_slot_data.gameplay_data.rabbit_hole_service.rabbit_holes:
            rabbit_hole_type = services.get_instance_manager(sims4.resources.Types.RABBIT_HOLE).get(entry.rabbit_hole_id)
            if rabbit_hole_type is None:
                pass
            else:
                sim_id = entry.sim_id
                rabbit_hole_instance_id = None
                if entry.HasField('rabbit_hole_instance_id'):
                    rabbit_hole_instance_id = entry.rabbit_hole_instance_id
                if sim_id not in self._rabbit_holes:
                    self._rabbit_holes[sim_id] = []
                rabbit_hole = rabbit_hole_type(sim_id, rabbit_hole_id=rabbit_hole_instance_id)
                self._rabbit_holes[sim_id].append(rabbit_hole)
                rabbit_hole.load(entry)
                if entry.linked_sim_ids:
                    if entry.linked_rabbit_hole_ids:
                        rabbit_hole.linked_rabbit_holes.extend(zip(entry.linked_sim_ids, entry.linked_rabbit_hole_ids))
                    else:
                        rabbit_hole.linked_rabbit_holes.extend((linked_sim_id, None) for linked_sim_id in entry.linked_sim_ids)
                        rabbit_holes_to_fixup_links = (sim_id, rabbit_hole.rabbit_hole_id)
        for (sim_id, rabbit_hole_id) in rabbit_holes_to_fixup_links:
            rabbit_hole = self._get_rabbit_hole(sim_id, rabbit_hole_id)
            new_linked_rabbit_holes = []
            for (linked_sim_id, _) in rabbit_hole.linked_rabbit_holes:
                linked_rabbit_hole = self._rabbit_holes.get(linked_sim_id, None)
                if linked_rabbit_hole is not None:
                    new_linked_rabbit_holes.append((linked_sim_id, linked_rabbit_hole.rabbit_hole_id))
            rabbit_hole.linked_rabbit_holes = new_linked_rabbit_holes

    def start(self):
        services.get_event_manager().register_single_event(self, TestEvent.OnSimReset)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_RABBIT_HOLE_SERVICE

    def handle_event(self, sim_info, event, *_):
        sim_id = sim_info.id
        if event == TestEvent.OnSimReset:
            if sim_id in self._rabbit_holes and not sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS).is_being_destroyed:
                rabbit_hole_id = self.get_head_rabbit_hole_id(sim_id)
                self.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id, canceled=True)
        elif event == TestEvent.InteractionStart and sim_id in self._rabbit_holes:
            rabbit_hole_id = self.get_head_rabbit_hole_id(sim_id)
            self._activate_rabbit_hole(sim_id, rabbit_hole_id)
