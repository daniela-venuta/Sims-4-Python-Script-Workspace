import enumimport sims4.logfrom distributor.ops import ToggleSimInfoPanelfrom distributor.system import Distributorlogger = sims4.log.Logger('UIUtils', default_owner='bnguyen')
class UIUtils:

    class SimInfoPanelType(enum.Int):
        SIM_INFO_MOTIVE_PANEL = 0
        SIM_INFO_SKILL_PANEL = 1
        SIM_INFO_RELATIONSHIP_PANEL = 2
        SIM_INFO_CAREER_PANEL = 3
        SIM_INFO_INVENTORY_PANEL = 4
        SIM_INFO_ASPIRATION_PANEL = 5
        SIM_INFO_SUMMARY_PANEL = 6
        SIM_INFO_CLUB_PANEL = 7

    @staticmethod
    def toggle_sim_info_panel(panel_type, stay_open=True):
        op = ToggleSimInfoPanel(panel_type, stay_open)
        Distributor.instance().add_op_with_no_owner(op)
