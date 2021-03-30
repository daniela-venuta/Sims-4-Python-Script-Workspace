from protocolbuffers import SimObjectAttributes_pb2from default_property_stream_reader import DefaultPropertyStreamReaderfrom objects.components import Component, types, componentmethod_with_fallbackimport sims4logger = sims4.log.Logger('Stored Info Component', default_owner='rrodgers')
class StoredInfoKeys:
    CAS_PARTS = 'cas_parts'

class StoredInfoComponent(Component, component_name=types.STORED_INFO_COMPONENT, allow_dynamic=True, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.StoredInfoComponent):

    @staticmethod
    def store_info_on_object(obj, **kwargs):
        if not obj.has_component(types.STORED_INFO_COMPONENT):
            obj.add_dynamic_component(types.STORED_INFO_COMPONENT)
        obj.get_component(types.STORED_INFO_COMPONENT).set_info(kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cas_parts = None

    def set_info(self, info):
        for field in info.keys():
            if hasattr(self, field):
                setattr(self, field, info[field])
            else:
                logger.error('Tried to set info with key {} to value {} on the StoredInfoComponent of {}, but the key was invalid', field, info[field], self.owner)

    @componentmethod_with_fallback(lambda : None)
    def get_stored_cas_parts(self):
        return self._cas_parts

    @componentmethod_with_fallback(lambda : None)
    def clear_stored_cas_parts(self):
        self._cas_parts = None

    def save(self, persistence_master_message):
        persistable_data = SimObjectAttributes_pb2.PersistenceMaster.PersistableData()
        persistable_data.type = SimObjectAttributes_pb2.PersistenceMaster.PersistableData.StoredInfoComponent
        stored_sim_info_component_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableStoredInfoComponent.persistable_data]
        writer = sims4.PropertyStreamWriter()
        if self._cas_parts is not None:
            writer.write_uint64s(StoredInfoKeys.CAS_PARTS, self._cas_parts)
        data = writer.close()
        if writer.count > 0:
            stored_sim_info_component_data.custom_data = data
            persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        stored_info_component_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableStoredInfoComponent.persistable_data]
        reader = DefaultPropertyStreamReader(stored_info_component_data.custom_data)
        self._cas_parts = reader.read_uint64s(StoredInfoKeys.CAS_PARTS, None)
