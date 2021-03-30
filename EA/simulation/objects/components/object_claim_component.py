from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom objects.components import Component, typesfrom objects.object_enums import ObjectClaimStatusfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInitimport servicesimport sims4logger = sims4.log.Logger('ObjectClaim', default_owner='jmorrow')
class ObjectClaimComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.OBJECT_CLAIM_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.ObjectClaimComponent, allow_dynamic=True):
    FACTORY_TUNABLES = {}

    def __init__(self, *args, require_claiming=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._requires_claiming = require_claiming

    def has_not_been_reclaimed(self):
        return services.object_manager().has_object_failed_claiming(self.owner)

    @property
    def requires_claiming(self):
        return self._requires_claiming

    @requires_claiming.setter
    def requires_claiming(self, value):
        self._requires_claiming = value

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.ObjectClaimComponent
        object_claim_save = persistable_data.Extensions[protocols.PersistableObjectClaimComponent.persistable_data]
        object_claim_save.requires_claiming = self._requires_claiming
        persistence_master_message.data.extend([persistable_data])

    def load(self, message):
        data = message.Extensions[protocols.PersistableObjectClaimComponent.persistable_data]
        self._requires_claiming = data.requires_claiming
