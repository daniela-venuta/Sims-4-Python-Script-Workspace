from protocolbuffers import Dialog_pb2from distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableListfrom ui.ui_dialog import UiDialogOkimport servicesimport sims4.loglogger = sims4.log.Logger('UiDialogInfoInColumns', default_owner='madang')
class UiDialogInfoInColumns(UiDialogOk):
    FACTORY_TUNABLES = {'column_headers': TunableList(description='\n            A list of column header strings.\n            ', tunable=TunableLocalizedStringFactory())}

    def build_msg(self, row_data=[], additional_tokens=(), **kwargs):
        msg = super().build_msg(additional_tokens=additional_tokens, **kwargs)
        msg.dialog_type = Dialog_pb2.UiDialogMessage.INFO_IN_COLUMNS
        sim_info = self.owner.sim_info
        msg.override_sim_icon_id = self.owner.id if self.owner is not None else 0
        if sim_info is None:
            logger.error('Sim Info was None for {}', self._target_sim_id)
            return msg
        info_columns_msg = Dialog_pb2.UiDialogInfoInColumns()
        for column_header in self.column_headers:
            info_columns_msg.column_headers.append(column_header(sim_info))
        for row in row_data:
            row_data_msg = Dialog_pb2.UiDialogRowData()
            for (icon, icon_name, icon_description) in row:
                icon_data = IconInfoData(icon_resource=icon)
                icon_info_msg = create_icon_info_msg(icon_data, name=icon_name, desc=icon_description)
                row_data_msg.column_info.append(icon_info_msg)
            info_columns_msg.rows.append(row_data_msg)
        msg.info_in_columns_data = info_columns_msg
        return msg
