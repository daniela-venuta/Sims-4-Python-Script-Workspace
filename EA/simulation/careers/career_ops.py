from protocolbuffers import Consts_pb2from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableReference, TunableEnumEntry, TunableEnumFlags, TunableVariant, TunableTuple, TunableList, Tunable, TunableRange, TunableFactory, OptionalTunable, TunableSimMinuteimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('Career')
class CareerOps(enum.Int):
    JOIN_CAREER = 0
    QUIT_CAREER = 1
    CALLED_IN_SICK = 2

class CareerLevelOps(enum.Int):
    PROMOTE = 0
    DEMOTE = 1

class CareerTimeOffReason(DynamicEnum):
    NO_TIME_OFF = 0
    PTO = 1
    FAKE_SICK = 2
    MISSING_WORK = 3
    WORK_FROM_HOME = 4

class CareerLevelOp(BaseLootOperation):
    FACTORY_TUNABLES = {'career': TunableReference(description="\n            The career upon which we'll be promoting/demoting the Sim.\n            If the Sim doesn't have this career or there's a reason the career\n            can't be promoted/demoted, nothing will happen.\n            ", manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'operation': TunableEnumEntry(description='\n            The operation to perform on the career.\n            ', tunable_type=CareerLevelOps, default=CareerLevelOps.PROMOTE)}

    def __init__(self, career, operation, **kwargs):
        super().__init__(**kwargs)
        self._career = career
        self._operation = operation

    def _apply_to_subject_and_target(self, subject, target, resolver):
        career = subject.careers.get(self._career.guid64)
        demote = self._operation == CareerLevelOps.DEMOTE
        if career is None or not career.can_change_level(demote=demote):
            return
        if demote:
            career.demote()
        else:
            career.promote()

class CareerLootOp(BaseLootOperation):
    CAREER_REFERENCE = 0
    CAREER_PARTICIPANT = 1
    CAREER_ALL = 2
    OP_PERFORMANCE = 0
    OP_MONEY = 1
    OP_RETIRE = 2
    OP_PTO = 3
    OP_TAKE_DAY_OFF = 4
    OP_PROMOTE = 5
    OP_DEMOTE = 6
    OP_FINE = 7
    OP_FIRE = 8
    OP_QUIT = 9
    OP_JOIN = 10

    @TunableFactory.factory_option
    def career_options(*, pack_safe=False):
        return {'career': TunableVariant(description='\n                The career to apply loot to.\n                ', career_reference=TunableTuple(description='\n                    Reference to the career.\n                    ', reference=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CAREER), pack_safe=pack_safe), locked_args={'id_type': CareerLootOp.CAREER_REFERENCE}), participant_type=TunableTuple(description='\n                    The id of the career upon which the op will be applied to. Sim\n                    Participant must have the career. Typically should be PickedItemId\n                    if this loot is being applied by the continuation of a\n                    CareerPickerSuperInteraction.\n                    ', participant=TunableEnumFlags(enum_type=ParticipantType, default=ParticipantType.PickedItemId), locked_args={'id_type': CareerLootOp.CAREER_PARTICIPANT}), all_careers=TunableTuple(description="\n                    Apply the operation to all of the Sim's careers.\n                    ", locked_args={'id_type': CareerLootOp.CAREER_ALL}), default='career_reference')}

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value, *args, **kwargs):
        if value.career.id_type is CareerLootOp.CAREER_REFERENCE:
            career = value.career.reference
            for op in value.operations:
                if op.operation_type is CareerLootOp.OP_JOIN and op.level_to_join is not None and (isinstance(op.level_to_join, int) or op.level_to_join.career is not career):
                    logger.error('CareerLootOp tuning error - Mismatched career level and career: The level_to_join field {} does not belong to the career {} in {}.', op.level_to_join, career, instance_class)

    FACTORY_TUNABLES = {'operations': TunableList(description='\n            A list of career loot ops.\n            ', tunable=TunableVariant(description='\n                What the Sim will get with this op.\n                ', performance=TunableTuple(description="\n                    The tuned amount will be applied to the relevant career's\n                    performance statistic.\n                    ", amount=Tunable(description="\n                        The amount to apply to the career's performance statistic.\n                        Can be negative.\n                        ", tunable_type=float, default=0), locked_args={'operation_type': OP_PERFORMANCE}), money=TunableTuple(description="\n                    A tuned amount of money, as a multiple of the current\n                    career's simoleons per hour, for the Sim to get.\n                    ", hour_multiplier=Tunable(description="\n                        The multiplier on the career's simoleons per hour.\n                        ", tunable_type=float, default=0), locked_args={'operation_type': OP_MONEY}), fine=TunableTuple(description="\n                    A tuned amount of money, as a multiple of the current\n                    career's simoleons per hour, the Sim will have removed\n                    from their funds.  If the Sim does not have funds to cover\n                    the fine, their account will be depleted.\n                    ", hour_multiplier=Tunable(description="\n                        The multiplier on the career's simoleons per hour.\n                        ", tunable_type=float, default=0), locked_args={'operation_type': OP_FINE}), retire=TunableTuple(description='\n                    Retire the Sim from the career. The career will provide a\n                    daily pension until death. All other careers will be quit.\n                    ', locked_args={'operation_type': OP_RETIRE}), pto=TunableTuple(description="\n                    The amount to apply to the career's pto statistic.\n                    Can be negative.\n                    ", amount=Tunable(description="\n                        The amount to apply to the career's performance statistic.\n                        Can be negative.\n                        ", tunable_type=float, default=0), locked_args={'operation_type': OP_PTO}), take_day_off=TunableTuple(description='\n                    Take off the next work period.  If you want it to consume PTO\n                    then you must also use a pto operation.\n                    ', reason=TunableEnumEntry(description='\n                        The reason for taking day off.\n                        ', tunable_type=CareerTimeOffReason, default=CareerTimeOffReason.NO_TIME_OFF), locked_args={'operation_type': OP_TAKE_DAY_OFF}), promote=TunableTuple(description='\n                    Promote the Sim on the career.\n                    ', levels_to_promote=TunableRange(description='\n                        The number of levels to promote the Sim.\n                        ', tunable_type=int, minimum=1, default=1), locked_args={'operation_type': OP_PROMOTE}), demote=TunableTuple(description='\n                    Promote the Sim on the career.\n                    ', levels_to_demote=TunableRange(description='\n                        The number of levels to demote the Sim.\n                        ', tunable_type=int, minimum=1, default=1), locked_args={'operation_type': OP_DEMOTE}), fire=TunableTuple(description='\n                    Fire the Sim from the career.\n                    ', clear_history=Tunable(description='\n                        If checked, clear out the work history so when the Sim\n                        gets the same career they start over.\n                        ', tunable_type=bool, default=False), locked_args={'operation_type': OP_FIRE}), quit=TunableTuple(description='\n                    Have the specified Sim quit their career. \n                    ', locked_args={'operation_type': OP_QUIT}), join=TunableTuple(description='\n                    Have the specified Sim join the career.\n                    ', level_to_join=OptionalTunable(description='\n                        The level to have the Sim join at. It can be either\n                        a specific number of levels to increase on join or a \n                        reference to a specific CareerLevel.\n                        ', tunable=TunableVariant(description='\n                            Variant for how you want to specify the career level,\n                            either by int or by specific career level reference.\n                            ', increase=TunableRange(description='\n                                A specific number of levels to increase the\n                                career at the point when the career is joined.\n                                ', tunable_type=int, minimum=1, default=1), level_reference=TunableReference(description='\n                                A specific CareerLevel to join the career at.\n                                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_LEVEL), pack_safe=True), default='increase')), show_confirmation_dialog=Tunable(description="\n                        If checked and Sim is in other careers or is retired, \n                        prompt the player to confirm joining the new career. \n                        \n                        If accepted, Sim will automatically quit other careers \n                        and unretire. If canceled, nothing happens and new \n                        career isn't added.\n                        ", tunable_type=bool, default=False), locked_args={'operation_type': OP_JOIN}), default='performance')), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, career, operations, **kwargs):
        super().__init__(**kwargs)
        self.career = career
        self.operations = operations

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        for career in self._get_careers(subject, resolver):
            if not career is None:
                if career.is_visible_career:
                    self._apply_to_career(subject, career, resolver)
            self._apply_to_career(subject, career, resolver)

    def _apply_to_career(self, sim_info, career, resolver):
        for op in self.operations:
            if op.operation_type == CareerLootOp.OP_PERFORMANCE:
                career.add_work_performance(op.amount, interaction=resolver.interaction)
                career.resend_career_data()
            elif op.operation_type == CareerLootOp.OP_MONEY or op.operation_type == CareerLootOp.OP_FINE:
                money = op.hour_multiplier*career.get_hourly_pay()
                sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if op.operation_type == CareerLootOp.OP_MONEY:
                    sim_info.household.funds.add(money, Consts_pb2.TELEMETRY_MONEY_CAREER, sim)
                else:
                    sim_info.household.funds.try_remove(money, Consts_pb2.TELEMETRY_MONEY_CAREER, sim, require_full_amount=False)
            elif op.operation_type == CareerLootOp.OP_RETIRE:
                sim_info.career_tracker.retire_career(career.guid64)
            elif op.operation_type == CareerLootOp.OP_PTO:
                career.add_pto(op.amount)
                career.resend_career_data()
            elif op.operation_type == CareerLootOp.OP_TAKE_DAY_OFF:
                career.request_day_off(op.reason)
            elif op.operation_type == CareerLootOp.OP_PROMOTE:
                career.promote(levels_to_promote=op.levels_to_promote)
            elif op.operation_type == CareerLootOp.OP_DEMOTE:
                career.demote(levels_to_demote=op.levels_to_demote)
            elif op.operation_type == CareerLootOp.OP_FIRE:
                career.fire()
                if op.clear_history:
                    sim_info.career_tracker.clear_career_history(career.guid64)
                    if op.operation_type == CareerLootOp.OP_QUIT:
                        career.quit_career()
                    elif op.operation_type == CareerLootOp.OP_JOIN and career is None:
                        career_reference = self.career.reference(sim_info)
                        if isinstance(op.level_to_join, int):
                            sim_info.career_tracker.add_career(career_reference, show_confirmation_dialog=op.show_confirmation_dialog, user_level_override=op.level_to_join)
                        else:
                            sim_info.career_tracker.add_career(career_reference, show_confirmation_dialog=op.show_confirmation_dialog, career_level_override=op.level_to_join)
            elif op.operation_type == CareerLootOp.OP_QUIT:
                career.quit_career()
            elif op.operation_type == CareerLootOp.OP_JOIN and career is None:
                career_reference = self.career.reference(sim_info)
                if isinstance(op.level_to_join, int):
                    sim_info.career_tracker.add_career(career_reference, show_confirmation_dialog=op.show_confirmation_dialog, user_level_override=op.level_to_join)
                else:
                    sim_info.career_tracker.add_career(career_reference, show_confirmation_dialog=op.show_confirmation_dialog, career_level_override=op.level_to_join)

    def _get_careers(self, sim_info, interaction):
        careers = sim_info.careers
        if self.career.id_type == CareerLootOp.CAREER_REFERENCE:
            career_ids = (self.career.reference.guid64,)
        elif self.career.id_type == CareerLootOp.CAREER_PARTICIPANT:
            career_ids = interaction.get_participants(self.career.participant)
        elif self.career.id_type == CareerLootOp.CAREER_ALL:
            career_ids = careers
        return tuple(careers.get(career_id) for career_id in career_ids if career_id)

class CareerStayLateOp(BaseLootOperation):
    FACTORY_TUNABLES = {'stay_late_extension_override': OptionalTunable(description='\n            If enabled, extends the active work shift by the tuned amount.\n            If disabled, the Stay Late Extension tuning on the Career Tuning\n            is used instead.\n            ', tunable=TunableSimMinute(default=120, minimum=0))}

    def __init__(self, stay_late_extension_override, **kwargs):
        super().__init__(**kwargs)
        self.stay_late_extension_override = stay_late_extension_override

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        career_tracker = subject.career_tracker
        if career_tracker is None:
            logger.error('Career Stay Late Op called on {}, who does not have a CareerTracker. This should only be called on a sim who is currently at work.', subject)
            return
        career = career_tracker.get_at_work_career()
        if career is None:
            logger.error('Career Stay Late Op called on {}, who is not currently at work.', subject)
            return
        career.extend_career_session(stay_late_extension_override=self.stay_late_extension_override)
