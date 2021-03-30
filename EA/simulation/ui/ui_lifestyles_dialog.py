import enumfrom protocolbuffers import Dialog_pb2from distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableTuple, OptionalTunable, TunableMapping, TunableEnumEntryfrom ui.ui_dialog import UiDialogOkimport servicesimport sims4.loglogger = sims4.log.Logger('UiLifestylesDialog', default_owner='asantos')
class LifestyleUiState(enum.Int):
    INVALID = 0
    LOCKED = 1
    IN_PROGRESS = 2
    ACTIVE = 3
    AT_RISK = 4
    HIDDEN = 5

class UiDialogLifestyles(UiDialogOk):
    FACTORY_TUNABLES = {'max_lifestyles_active_subtitle': TunableLocalizedStringFactory(description='\n            The subtitle text when the sim has the max number of lifestyles.\n            '), 'lifestyle_type_to_display_data': TunableMapping(description='\n            Settings used to show the state of a lifestyle. \n            ', key_type=TunableEnumEntry(tunable_type=LifestyleUiState, default=LifestyleUiState.INVALID, invalid_enums=LifestyleUiState.INVALID), key_name='Lifestyle State', value_type=TunableTuple(description='\n                A set of UI display data for one lifestyle type.\n                ', lifestyle_state_string=TunableLocalizedStringFactory(description='\n                    The text to show this lifestyle state.\n                    '), lifestyle_name_format_string=OptionalTunable(description='\n                    Format for displaying a lifestyle name that is in this state.\n                    ', tunable=TunableLocalizedStringFactory())), value_name='Lifestyle Display Data'), 'hidden_lifestyle_tooltip_description': TunableLocalizedStringFactory(description='\n            The text to show in the description field of the tooltip for hidden lifestyles.\n            ')}

    def build_msg(self, **kwargs):
        msg = super().build_msg(**kwargs)
        msg.dialog_type = Dialog_pb2.UiDialogMessage.ICONS_LABELS
        sim_info = self.owner.sim_info
        if sim_info is None:
            logger.error('Sim Info was None for {}', self._target_sim_id)
            return msg
        lifestyle_service = services.lifestyle_service()
        for lifestyle in lifestyle_service.LIFESTYLES:
            icon_resource = None
            if lifestyle.icon is not None:
                icon_resource = lifestyle.icon
            lifestyle_state = lifestyle_service.get_lifestyle_ui_state_from_trait(sim_info, lifestyle)
            lifestyle_state_display_data = self.lifestyle_type_to_display_data[lifestyle_state] if lifestyle_state in self.lifestyle_type_to_display_data else None
            name = None
            if lifestyle.display_name is not None:
                if lifestyle_state_display_data is not None and lifestyle_state_display_data.lifestyle_name_format_string is not None:
                    name = lifestyle_state_display_data.lifestyle_name_format_string(lifestyle.display_name(sim_info))
                else:
                    name = lifestyle.display_name(sim_info)
            desc = None
            if lifestyle_state_display_data is not None:
                desc = lifestyle_state_display_data.lifestyle_state_string()
            tooltip = None
            if lifestyle_state is LifestyleUiState.HIDDEN:
                tooltip = self.hidden_lifestyle_tooltip_description(sim_info)
            elif lifestyle.trait_description is not None:
                tooltip = lifestyle.trait_description(sim_info)
            icon_data = IconInfoData(icon_resource=icon_resource)
            icon_info_msg = create_icon_info_msg(icon_data, name=name, desc=desc, tooltip=tooltip)
            icon_info_msg.control_id = lifestyle_state
            icon_info_msg.object_instance_id = lifestyle.guid64
            msg.icon_infos.append(icon_info_msg)
        return msg
