from protocolbuffers import DistributorOps_pb2from distributor.ops import Opfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msgimport date_and_timeprotocol_constants = DistributorOps_pb2.Operation
class SendOrganizationUpdateOp(Op):

    def __init__(self, update_type, org_id, objective_ids, is_enrolled):
        super().__init__()
        self.op = DistributorOps_pb2.OrganizationUpdate()
        self.op.org_id = org_id
        self.op.update_type = update_type
        for objective_id in objective_ids:
            self.op.objective_ids.append(objective_id)
        self.op.is_enrolled = is_enrolled

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.ORGANIZATION_UPDATE)

class OrgEventInfo:

    def __init__(self, drama_node=None, schedule=None, fake_duration=None, icon_info=None, name=None, description=None, location=None, zone_id=None):
        self._drama_node = drama_node
        self._schedule = schedule
        self._fake_duration = fake_duration
        self._icon_info = icon_info
        self._name = name
        self._description = description
        self._location = location
        self._zone_id = zone_id

    @property
    def drama_node(self):
        return self._drama_node

def _populate_scheduler_msg(schedule_msg, schedule_entry, duration):
    with ProtocolBufferRollback(schedule_msg.schedule_entries) as schedule_entry_msg:
        schedule_entry_msg.days.extend([schedule_entry.day()])
        schedule_entry_msg.start_hour = schedule_entry.hour()
        schedule_entry_msg.start_minute = schedule_entry.minute()
        schedule_entry_msg.duration = duration/date_and_time.MINUTES_PER_HOUR

def _create_org_event_info(event_info_msg, org_event_info):
    event_info_msg.drama_node_id = org_event_info._drama_node.guid64
    _populate_scheduler_msg(event_info_msg.schedule, org_event_info._schedule, org_event_info._fake_duration)
    event_info_msg.event_info = create_icon_info_msg(org_event_info._icon_info, name=org_event_info._name, desc=org_event_info._description)
    event_info_msg.location = org_event_info._location
    event_info_msg.zone_id = org_event_info._zone_id

class SendOrganizationEventUpdateOp(Op):

    def __init__(self, org_id, org_event_infos, no_events_string=None):
        super().__init__()
        self.op = DistributorOps_pb2.OrganizationEventUpdate()
        self.op.org_id = org_id
        if no_events_string is not None:
            self.op.no_events_are_scheduled_string = no_events_string
        for org_event_info in org_event_infos:
            with ProtocolBufferRollback(self.op.events) as event_info_msg:
                _create_org_event_info(event_info_msg, org_event_info)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.ORGANIZATION_EVENT_UPDATE)
