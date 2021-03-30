import weakreffrom protocolbuffers import UI_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom drama_scheduler.drama_node import DramaNodeUiDisplayTypefrom sims4.service_manager import Serviceimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('Calendar', default_owner='bosee')
class CalendarService(Service):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_data_map = {}
        self._event_alarm_map = {}

    def mark_on_calendar(self, event, advance_notice_time=None):
        event_id = event.uid
        self._event_data_map[event_id] = weakref.ref(event)
        self._send_calendary_entry(event, UI_pb2.CalendarUpdate.ADD)
        self._set_up_alert(event, advance_notice_time)

    def remove_on_calendar(self, event_id):
        if event_id not in self._event_data_map:
            logger.debug("Trying to remove a calendar entry which doesn't exist {}", event_id)
            return
        stored_event = self._event_data_map[event_id]()
        if stored_event is None:
            logger.error('Trying to remove a calendar entry which has been destroyed {}', event_id)
            return
        self._send_calendary_entry(stored_event, UI_pb2.CalendarUpdate.REMOVE)
        self._remove_alert(event_id)
        del self._event_data_map[event_id]

    def update_on_calendar(self, event, advance_notice_time=None):
        event_id = event.uid
        if event_id not in self._event_data_map:
            logger.debug("Trying to update a calendar entry which doesn't exist {}", event_id)
            return
        stored_event = self._event_data_map[event_id]()
        if stored_event is None:
            logger.error('Trying to update a calendar entry which has been destroyed {}', event_id)
            return
        self._send_calendary_entry(stored_event, UI_pb2.CalendarUpdate.UPDATE)
        self._remove_alert(event_id)
        self._set_up_alert(event, advance_notice_time)

    def _set_up_alert(self, event, advance_notice_time):
        if advance_notice_time is None:
            return
        event_id = event.uid
        entry_start_time = event.get_calendar_start_time()
        alarm_time_span = entry_start_time - services.game_clock_service().now() - advance_notice_time
        if alarm_time_span.in_minutes() <= 0:
            return
        alarm_handle = alarms.add_alarm(self, alarm_time_span, lambda _: self._on_alert_alarm(self._event_data_map[event_id]()))
        self._event_alarm_map[event_id] = alarm_handle

    def _remove_alert(self, event_id):
        if event_id not in self._event_alarm_map:
            return
        alarms.cancel_alarm(self._event_alarm_map[event_id])
        del self._event_alarm_map[event_id]

    def _on_alert_alarm(self, event):
        if event is None:
            logger.error('Trying to send alert for drama node which has been destroyed. We might be leaking memory.')
            return
        del self._event_alarm_map[event.uid]
        event.on_calendar_alert_alarm()

    def _send_calendary_entry(self, event, update_type):
        if event.ui_display_type == DramaNodeUiDisplayType.ALERTS_ONLY:
            return
        calendar_entry = event.create_calendar_entry()
        calendar_msg = UI_pb2.CalendarUpdate()
        calendar_msg.updated_entry = calendar_entry
        calendar_msg.update_type = update_type
        op = GenericProtocolBufferOp(Operation.MSG_CALENDAR_UPDATE, calendar_msg)
        Distributor.instance().add_op_with_no_owner(op)
