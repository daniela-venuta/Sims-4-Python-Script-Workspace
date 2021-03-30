from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom protocolbuffers import UI_pb2 as ui_protocolsimport randomfrom objects.components import types, componentmethod_with_fallbackfrom objects.components.spawner_component_enums import SpawnerTypefrom objects.gardening.gardening_component import _GardeningComponentfrom objects.gardening.gardening_tuning import GardeningTuningfrom objects.hovertip import TooltipFieldsfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import TunableReference, TunableSetimport objects.components.typesimport placementimport servicesimport sims4.logfrom sims4.tuning.tunable_hash import TunableStringHash32logger = sims4.log.Logger('Gardening')
class GardeningPlantComponent(_GardeningComponent, component_name=objects.components.types.GARDENING_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.GardeningComponent):
    FACTORY_TUNABLES = {'shoot_definition': TunableReference(description='\n            The object definition to use when creating Shoot objects for the\n            splicing system.\n            ', manager=services.definition_manager()), 'prohibited_vertical_plant_slots': TunableSet(description='\n            The list of slots that are prohibited from spawning fruit if the plant \n            is on the vertical garden.\n            ', tunable=TunableStringHash32(description='\n                The hashed name of the slot.\n                ', default='_ctnm_spawn_1'))}

    def on_add(self, *args, **kwargs):
        zone = services.current_zone()
        if not zone.is_zone_loading:
            gardening_service = services.get_gardening_service()
            gardening_service.add_gardening_object(self.owner)
        return super().on_add(*args, **kwargs)

    def on_remove(self, *_, **__):
        gardening_service = services.get_gardening_service()
        gardening_service.remove_gardening_object(self.owner)

    def on_finalize_load(self):
        gardening_service = services.get_gardening_service()
        gardening_service.add_gardening_object(self.owner)
        self._refresh_fruit_states()

    def on_location_changed(self, old_location):
        zone = services.current_zone()
        if not zone.is_zone_loading:
            gardening_service = services.get_gardening_service()
            gardening_service.move_gardening_object(self.owner)
            self._refresh_prohibited_spawn_slots()

    def _refresh_prohibited_spawn_slots(self):
        plant = self.owner
        plant_parent = plant.parent
        fruits = tuple(self.owner.children)
        destroyed_fruit = False
        for fruit in fruits:
            gardening_component = fruit.get_component(types.GARDENING_COMPONENT)
            if gardening_component is None:
                pass
            elif self.is_prohibited_spawn_slot(fruit.location.slot_hash, plant_parent):
                fruit.destroy()
                destroyed_fruit = True
        if destroyed_fruit or not fruits:
            return
        empty_slot_count = 0
        for runtime_slot in plant.get_runtime_slots_gen():
            if runtime_slot.empty and not self.is_prohibited_spawn_slot(runtime_slot.slot_name_hash, plant_parent):
                empty_slot_count += 1
        plant.force_spawn_object(spawn_type=SpawnerType.SLOT, ignore_firemeter=True, create_slot_obj_count=empty_slot_count)

    def _refresh_fruit_states(self):
        for fruit_state in GardeningTuning.FRUIT_STATES:
            fruit_state_value = self.owner.get_state(fruit_state)
            self._on_fruit_support_state_changed(fruit_state, None, fruit_state_value)

    def _on_fruit_fall_to_ground(self, fruit):
        plant = self.owner
        if fruit.parent is not plant:
            return False
        if not plant.is_on_active_lot():
            return False
        starting_location = placement.create_starting_location(position=plant.position, routing_surface=plant.routing_surface)
        fgl_context = placement.create_fgl_context_for_object(starting_location, fruit, ignored_object_ids=(fruit.id,))
        (position, orientation) = placement.find_good_location(fgl_context)
        if position is None or orientation is None:
            return False
        fruit.move_to(parent=None, translation=position, orientation=orientation, routing_surface=plant.routing_surface)
        owner = plant.get_household_owner_id()
        if owner is not None:
            fruit.set_household_owner_id(owner)
        decay_commodity = GardeningTuning.FRUIT_DECAY_COMMODITY
        fruit.set_stat_value(decay_commodity, GardeningTuning.FRUIT_DECAY_COMMODITY_DROPPED_VALUE)
        return True

    def _on_fruit_support_state_changed(self, state, old_value, new_value):
        if state not in GardeningTuning.FRUIT_STATES:
            return
        fruit_state_data = GardeningTuning.FRUIT_STATES[state]
        if new_value in fruit_state_data.states:
            return
        objs_to_destroy = []
        fruit_state_behavior = fruit_state_data.behavior
        for fruit in tuple(self.owner.children):
            gardening_component = fruit.get_component(types.GARDENING_COMPONENT)
            if gardening_component is None:
                pass
            elif not gardening_component.is_on_tree:
                pass
            elif self._on_fruit_fall_to_ground(fruit):
                gardening_component.update_hovertip()
            else:
                objs_to_destroy.append(fruit)
        if objs_to_destroy:
            services.get_reset_and_delete_service().trigger_batch_destroy(objs_to_destroy)

    def on_state_changed(self, state, old_value, new_value, from_init):
        self._on_fruit_support_state_changed(state, old_value, new_value)
        self.update_hovertip()

    def is_prohibited_spawn_slot(self, slot, plant_parent):
        if plant_parent is None or plant_parent.definition not in GardeningTuning.VERTICAL_GARDEN_OBJECTS:
            return False
        elif slot in self.prohibited_vertical_plant_slots:
            return True
        return False

    def add_fruit(self, fruit, sprouted_from=False):
        gardening_component = fruit.get_component(types.GARDENING_COMPONENT)
        if sprouted_from:
            state = GardeningTuning.INHERITED_STATE
            state_value = fruit.get_state(state)
            self.owner.set_state(state, state_value)
        else:
            splicing_recipies = self.root_stock_gardening_tuning.splicing_recipies
            if gardening_component.root_stock.main_spawner in splicing_recipies:
                new_fruit = splicing_recipies[gardening_component.root_stock.main_spawner]
                self._add_spawner(new_fruit)
        if gardening_component.is_shoot:
            self._add_spawner(gardening_component.root_stock.main_spawner)
        else:
            self._add_spawner(fruit.definition)
        self.update_hovertip()

    def create_shoot(self):
        root_stock = self._get_root_stock()
        if root_stock is None:
            return
        shoot = self.root_stock.create_spawned_object(self.owner, self.shoot_definition)
        gardening_component = shoot.get_component(types.GARDENING_COMPONENT)
        gardening_component.fruit_spawner_data = root_stock
        gardening_component._fruit_spawners.append(root_stock)
        gardening_component.update_hovertip()
        return shoot

    def _get_root_stock(self):
        if self.root_stock is None:
            for spawn_obj_def in self.owner.slot_spawner_definitions():
                self._add_spawner(spawn_obj_def[0])
        return self.root_stock

    def can_splice_with(self, shoot):
        gardening_component = shoot.get_component(types.GARDENING_COMPONENT)
        if gardening_component is not None:
            return gardening_component.is_shoot
        return False

    @componentmethod_with_fallback(lambda : None)
    def get_notebook_information(self, reference_notebook_entry, notebook_sub_entries):
        root_stock = self._get_root_stock()
        if root_stock is None:
            return ()
        fruit_definition = root_stock.main_spawner
        notebook_entry = reference_notebook_entry(fruit_definition.id)
        return (notebook_entry,)

    def _ui_metadata_gen(self):
        if not self.show_gardening_tooltip():
            self.owner.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_DISABLED
            return
        if self.show_gardening_details():
            state_value = self.owner.get_state(GardeningTuning.EVOLUTION_STATE)
            evolution_value = state_value.range.upper_bound
            yield ('evolution_progress', evolution_value)
            if GardeningTuning.SEASONALITY_STATE is not None:
                sesonality_state_value = self.owner.get_state(GardeningTuning.SEASONALITY_STATE)
                if sesonality_state_value is not None:
                    season_text = sesonality_state_value.display_name
                    seasonality_text = GardeningTuning.get_seasonality_text_from_plant(self.owner.definition)
                    season_text = LocalizationHelperTuning.get_new_line_separated_strings(season_text, seasonality_text)
                    yield (TooltipFields.season_text.name, season_text)
            quality_state_value = self.owner.get_state(GardeningTuning.QUALITY_STATE_VALUE)
            if quality_state_value is not None:
                quality_value = quality_state_value.value
                yield ('quality', quality_value)
        yield from super()._ui_metadata_gen()
