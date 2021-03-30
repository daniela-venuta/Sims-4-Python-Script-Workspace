from bucks.bucks_enums import BucksType, BucksTrackerTypefrom bucks.bucks_utils import BucksUtilsfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.gsi_utils import parse_filter_to_listfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesimport sims4.loglogger = sims4.log.Logger('GSI/Bucks')bucks_perks = GsiGridSchema(label='Bucks Perks', sim_specific=True)bucks_perks.add_field('sim_id', label='simID', hidden=True)bucks_perks.add_field('name', label='Name', type=GsiFieldVisualizers.STRING)bucks_perks.add_field('bucks_type', label='bucksType', type=GsiFieldVisualizers.STRING)bucks_perks.add_field('bucks_type_value', label='bucksTypeValue', type=GsiFieldVisualizers.STRING, hidden=True)bucks_perks.add_field('bucks_tracker_name', label='Bucks Tracker Name', type=GsiFieldVisualizers.STRING)bucks_perks.add_field('is_unlocked', label='isUnlocked', type=GsiFieldVisualizers.STRING)for bucks_type in BucksType:
    bucks_perks.add_filter(str(bucks_type))bucks_perks.add_filter('Unlocked Only')with bucks_perks.add_view_cheat('bucks.unlock_perk', label='Unlock Perk', dbl_click=True, refresh_view=False) as cheat:
    cheat.add_token_param('name')
    cheat.add_static_param(True)
    cheat.add_token_param('bucks_type_value')
    cheat.add_token_param('sim_id')bucks = GsiGridSchema(label='Bucks', sim_specific=True)bucks.add_field('bucks_type', label='bucksType', type=GsiFieldVisualizers.STRING)bucks.add_field('bucks_tracker_type', label='Bucks Tracker Type', type=GsiFieldVisualizers.STRING)bucks.add_field('bucks_amount', label='bucksAmount', type=GsiFieldVisualizers.INT)bucksLog = GsiGridSchema(label='Bucks Log', sim_specific=True)bucksLog.add_field('sim_id', label='simID', type=GsiFieldVisualizers.INT, hidden=True)bucksLog.add_field('bucks_type', label='bucksType', type=GsiFieldVisualizers.STRING)bucksLog.add_field('bucks_tracker_type', label='bucksTrackerType', type=GsiFieldVisualizers.STRING)bucksLog.add_field('bucks_start_amount', label='bucksStartAmount', type=GsiFieldVisualizers.INT)bucksLog.add_field('bucks_change_amount', label='bucksChange', type=GsiFieldVisualizers.INT)bucksLog.add_field('bucks_final_amount', label='bucksFinalAmount', type=GsiFieldVisualizers.INT)
@GsiHandler('bucks_perks', bucks_perks)
def generate_bucks_perks_view(sim_id:int=None, filter=None):
    filter_list = parse_filter_to_list(filter)
    bucks_perks_data = []
    perks_instance_manager = services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)
    previous_bucks_type = None
    for perk in perks_instance_manager.types.values():
        if perk.associated_bucks_type != previous_bucks_type:
            perk_specific_bucks_tracker = BucksUtils.get_tracker_for_bucks_type(perk.associated_bucks_type, sim_id)
            previous_bucks_type = perk.associated_bucks_type
        if 'Unlocked Only' in filter_list:
            if not perk_specific_bucks_tracker is None:
                if not perk_specific_bucks_tracker.is_perk_unlocked(perk):
                    pass
                elif len(filter_list) > 1 and str(perk.associated_bucks_type) not in filter_list:
                    pass
                else:
                    bucks_perks_data.append({'sim_id': str(sim_id), 'name': perk.__name__, 'bucks_type': str(perk.associated_bucks_type), 'bucks_type_value': int(perk.associated_bucks_type), 'bucks_tracker_name': str(perk_specific_bucks_tracker), 'is_unlocked': perk_specific_bucks_tracker.is_perk_unlocked(perk) if perk_specific_bucks_tracker is not None else False})
        elif str(perk.associated_bucks_type) not in filter_list:
            pass
        else:
            bucks_perks_data.append({'sim_id': str(sim_id), 'name': perk.__name__, 'bucks_type': str(perk.associated_bucks_type), 'bucks_type_value': int(perk.associated_bucks_type), 'bucks_tracker_name': str(perk_specific_bucks_tracker), 'is_unlocked': perk_specific_bucks_tracker.is_perk_unlocked(perk) if perk_specific_bucks_tracker is not None else False})
        bucks_perks_data.append({'sim_id': str(sim_id), 'name': perk.__name__, 'bucks_type': str(perk.associated_bucks_type), 'bucks_type_value': int(perk.associated_bucks_type), 'bucks_tracker_name': str(perk_specific_bucks_tracker), 'is_unlocked': perk_specific_bucks_tracker.is_perk_unlocked(perk) if filter_list is not None and perk_specific_bucks_tracker is not None else False})
    return bucks_perks_data

@GsiHandler('bucks', bucks)
def generate_bucks_view(sim_id:int=None):
    bucks_data = []
    for bucks in BucksType:
        specific_bucks_tracker = BucksUtils.get_tracker_for_bucks_type(bucks, sim_id)
        bucks_amount = None
        if specific_bucks_tracker is not None:
            bucks_amount = specific_bucks_tracker.get_bucks_amount_for_type(bucks)
        bucks_tracker_type = BucksUtils.BUCK_TYPE_TO_TRACKER_MAP.get(bucks)
        if not bucks_tracker_type == BucksTrackerType.HOUSEHOLD:
            if bucks_tracker_type == BucksTrackerType.SIM:
                bucks_data.append({'bucks_type': str(bucks), 'bucks_tracker_type': str(bucks_tracker_type), 'bucks_amount': bucks_amount})
        bucks_data.append({'bucks_type': str(bucks), 'bucks_tracker_type': str(bucks_tracker_type), 'bucks_amount': bucks_amount})
    return bucks_data
archiver = GameplayArchiver('bucks_log', bucksLog)
def add_bucks_data(bucks_tracker_owner, bucks_type, bucks_change_amount, bucks_final_amount):
    bucks_start_amount = bucks_final_amount - bucks_change_amount
    bucks_tracker_type = BucksUtils.BUCK_TYPE_TO_TRACKER_MAP.get(bucks_type)
    if bucks_tracker_type == BucksTrackerType.HOUSEHOLD:
        for sim in bucks_tracker_owner:
            _assign_bucks_data(sim, bucks_type, bucks_tracker_type, bucks_start_amount, bucks_change_amount, bucks_final_amount)
    elif bucks_tracker_type == BucksTrackerType.SIM:
        _assign_bucks_data(bucks_tracker_owner, bucks_type, bucks_tracker_type, bucks_start_amount, bucks_change_amount, bucks_final_amount)

def _assign_bucks_data(sim, bucks_type, bucks_tracker_type, bucks_start_amount, bucks_change_amount, bucks_final_amount):
    entry = {}
    entry['sim_id'] = sim.id
    entry['bucks_type'] = str(bucks_type)
    entry['bucks_tracker_type'] = str(bucks_tracker_type)
    entry['bucks_start_amount'] = bucks_start_amount
    entry['bucks_change_amount'] = bucks_change_amount
    entry['bucks_final_amount'] = bucks_final_amount
    archiver.archive(data=entry, object_id=sim.id)
