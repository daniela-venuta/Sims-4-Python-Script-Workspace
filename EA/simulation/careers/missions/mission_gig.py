import servicesimport sims4.logfrom audio.primitive import TunablePlayAudio, play_tunable_audiofrom bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom careers.career_enums import GigResultfrom careers.career_gig import TELEMETRY_GIG_PROGRESS_COMPLETEfrom careers.home_assignment_career_gig import HomeAssignmentGigfrom careers.missions.mission_objective_data import MissionObjectiveDatafrom date_and_time import TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.objective_completion_type import ObjectiveCompletionTypefrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, OptionalTunable, TunableEnumEntry, TunableTuple, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom traits.traits import Traitfrom ui.ui_dialog_picker import OddJobPickerRowlogger = sims4.log.Logger('MissionGig', default_owner='trevor')
class MissionGig(HomeAssignmentGig):
    INSTANCE_TUNABLES = {'mission_objective_data': TunableList(description='\n            A list of data used to create a single Objectives for this Mission.\n            ', tunable=MissionObjectiveData.TunableFactory(description='\n                An Objective for this Mission.\n                ')), 'allow_duplicate_objectives': Tunable(description='\n            If checked, the same Objective can be chosen multiple times for this\n            Mission. If unchecked, selected Objectives will be ignored by the\n            remaining Mission Objective Data.\n            ', tunable_type=bool, default=False), 'mission_trait': OptionalTunable(description='\n            If enabled, allows tuning a trait that is added to the Sim any time \n            they have this mission. The trait is removed upon mission completion.\n            ', tunable=Trait.TunablePackSafeReference(description="\n                This Trait is given to Sims when they have this Mission. It's removed\n                when this mission is complete.\n                ")), 'mission_pay_bucks': TunableEnumEntry(description='\n            The type of Buck to use to pay out this mission. The Gig Pay tunable\n            is still responsible for determining how much to pay.\n            ', tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=(BucksType.INVALID,)), 'mission_rewards_description': TunableLocalizedStringFactory(description='\n            The description of the rewards for this mission. This will be used in\n            both the Mission Picker and in the Career Panel.\n            Current tokens are:\n            0.String - Gig Pay (Since these pay in bucks, the ValueString of \n            BuckTypeToDisplayString in bucks_utils module tuning will be used)\n            1.String - Mission Reward Text "Reward Object: Fish Bowl"\n            2.String - Mission Reputation Text "Resistance +  First Order -"\n            ', tuning_group=GroupNames.UI), 'mission_reputation_text': OptionalTunable(description='\n            If enabled, allows tuning for reputation changes in the reward description.\n            ', tunable=TunableLocalizedString(description='\n                The string that shows the Reputation change for this Mission. This\n                is used in the Mission Reward Description. \n                '), tuning_group=GroupNames.UI), 'mission_rewards_text': OptionalTunable(description='\n            If enabled, allows tuning for extra rewards in the reward description.\n            ', tunable=TunableLocalizedString(description='\n                The string that shows the reward for this Mission. This is used in\n                the Mission Reward Description.\n                '), tuning_group=GroupNames.UI), 'cycling_display_data': TunableList(description='\n            A list of name/description pairs that will be cycled for each completion\n            of the tuned Aspiration for this Mission. If this list is empty, the\n            Display Name and Display Description from the Display Data will be used.\n            ', tunable=TunableTuple(description='\n                The Title and Description to use when this display data is being used.\n                ', mission_name=TunableLocalizedStringFactory(description='\n                    The display name for this entry. The Active Sim is passed in\n                    for the first token.\n                    '), customer_description=TunableLocalizedStringFactory(description='\n                    The display description for this entry. The Active Sim is \n                    passed in for the first token.\n                    ')), tuning_group=GroupNames.UI), 'objective_completion_audio': TunablePlayAudio(description='\n            An audio sting to play when a mission objective is complete.\n            ')}

    @classmethod
    def get_time_until_next_possible_gig(cls, starting_time):
        return TimeSpan.ZERO

    def get_additional_objectives(self):
        return [data.selected_objective for data in self.mission_objective_data if data.is_valid]

    def get_active_objectives(self):
        return [data.selected_objective for data in self.mission_objective_data if data.is_active]

    def treat_work_time_as_due_date(self):
        return False

    def is_objective_active(self, objective):
        return objective in self.get_active_objectives()

    def set_up_gig(self):
        selected_objectives = []
        for objective_data in self.mission_objective_data:
            objective_data.initialize_mission_objective(self._owner, objectives_to_ignore=selected_objectives)
            if objective_data.is_invalid:
                logger.error('Setting up Mission {} but it ended up invalid. Likely because no Objectives passed their availability tests.', self)
            elif not self.allow_duplicate_objectives:
                selected_objectives.append(objective_data.selected_objective)
        if self.mission_trait is not None:
            self._owner.add_trait(self.mission_trait)
        super().set_up_gig()

    def on_zone_load(self):
        super().on_zone_load()
        for objective_data in self.mission_objective_data:
            objective_data.on_zone_load(self._owner)

    def save_gig(self, gig_proto_buff):
        super().save_gig(gig_proto_buff)
        gig_proto_buff.ClearField('mission_objective_data')
        for mission_objective_data in self.mission_objective_data:
            with ProtocolBufferRollback(gig_proto_buff.mission_objective_data) as save_data:
                mission_objective_data.save(save_data)

    def load_gig(self, gig_proto_buff):
        super().load_gig(gig_proto_buff)
        for (i, save_objective_data) in enumerate(gig_proto_buff.mission_objective_data):
            data = self.mission_objective_data[i]
            data.load(save_objective_data)

    def _get_base_pay(self, *args, **kwargs):
        return 0

    def should_test_objective(self, objective):
        previous_objective = None
        for objective_data in self.mission_objective_data:
            if objective_data.is_invalid:
                pass
            else:
                mission_objective = objective_data.selected_objective
                if mission_objective is not objective:
                    previous_objective = mission_objective
                else:
                    if objective_data.requires_previous_objective_complete and previous_objective is None:
                        return True
                    aspiration_tracker = self._owner.aspiration_tracker
                    return aspiration_tracker.objective_completed(previous_objective)
        return True

    def complete_objective(self, objective):
        play_tunable_audio(self.objective_completion_audio, owner=self._owner.get_sim_instance())
        max_index = len(self.mission_objective_data) - 1
        for (i, objective_data) in enumerate(self.mission_objective_data):
            if objective_data.is_invalid:
                pass
            else:
                selected_objective = objective_data.selected_objective
                if selected_objective is objective:
                    objective_data.complete_mission_objective(self._owner)
                    if objective_data.completes_mission:
                        self._gig_result = GigResult.SUCCESS
                        return ObjectiveCompletionType.MILESTONE_COMPLETE
                    if i < max_index:
                        next_objective_data = self.mission_objective_data[i + 1]
                        if next_objective_data.requires_previous_objective_complete:
                            next_objective_data.activate_mission_objective(self._owner)
        return ObjectiveCompletionType.OBJECTIVE_COMPLETE

    def collect_additional_rewards(self):
        super().collect_additional_rewards()
        if self.follow_up_gig is None:
            self._set_final_pay_and_gratuity(self.gig_pay.lower_bound)
            pay = self._gig_pay + self._gig_gratuity
            if pay != 0:
                tracker = BucksUtils.get_tracker_for_bucks_type(self.mission_pay_bucks, owner_id=self._owner.id, add_if_none=True)
                tracker.try_modify_bucks(self.mission_pay_bucks, pay)
        if self.mission_trait is not None:
            self._owner.remove_trait(self.mission_trait)

    def _determine_gig_outcome(self):
        if self._gig_result == GigResult.SUCCESS:
            self._send_gig_telemetry(TELEMETRY_GIG_PROGRESS_COMPLETE)
            return
        super()._determine_gig_outcome()

    @classmethod
    def _get_name_and_description(cls, owner):
        name = cls.display_name
        description = cls.display_description
        if cls.cycling_display_data:
            display_data = cls.cycling_display_data[0]
            aspiration_tracker = owner.aspiration_tracker
            if aspiration_tracker is not None:
                aspiration_completion_count = aspiration_tracker.get_milestone_completion_count(cls.gig_assignment_aspiration)
                if aspiration_completion_count is None:
                    logger.error("Gig Aspiration {} is not tuned to track completion counts. Cycling display data for mission {} won't work.", cls.gig_assignment_aspiration, cls)
                else:
                    display_data = cls.cycling_display_data[aspiration_completion_count % len(cls.cycling_display_data)]
            name = display_data.mission_name
            description = display_data.customer_description
        return (name, description)

    @classmethod
    def get_pay_string(cls, value):
        pay_value_string = BucksUtils.BUCK_TYPE_TO_DISPLAY_DATA[cls.mission_pay_bucks].value_string
        if pay_value_string is None:
            logger.error("Couldn't get a value string for buck type {}. BuckTypeToDisplayData probably needs to be updated in bucks_utils module tuning.")
            return super().get_pay_string(value)
        return pay_value_string(value)

    @classmethod
    def _get_reward_description(cls):
        return cls.mission_rewards_description(cls.get_pay_string(cls.gig_pay.lower_bound), cls.mission_rewards_text, cls.mission_reputation_text)

    @classmethod
    def create_picker_row(cls, owner=None, gig_customer=None, customer_thumbnail_override=None, customer_background=None, enabled=True, customer_name=None, **kwargs):
        (display_name, customer_description) = cls._get_name_and_description(owner)
        customer_description = customer_description(owner)
        if enabled or cls.disabled_tooltip is not None:
            row_tooltip = lambda *_: cls.disabled_tooltip(owner)
        elif cls.display_description is None:
            row_tooltip = None
        else:
            row_tooltip = lambda *_: customer_description
        if gig_customer:
            customer_name = LocalizationHelperTuning.get_sim_full_name(gig_customer)
        return OddJobPickerRow(customer_id=gig_customer.id if customer_name is None and gig_customer else 0, customer_description=customer_description, customer_thumbnail_override=customer_thumbnail_override, customer_background=customer_background, tip_title=LocalizationHelperTuning.get_raw_text(''), tip_text=LocalizationHelperTuning.get_raw_text(''), name=display_name(owner), icon=cls.display_icon, row_description=cls._get_reward_description(), row_tooltip=row_tooltip, is_enable=enabled, customer_name=customer_name)

    @flexmethod
    def build_gig_msg(cls, inst, msg, sim, **kwargs):
        super(__class__, inst if inst is not None else cls).build_gig_msg(msg, sim, **kwargs)
        (name, description) = cls._get_name_and_description(sim)
        msg.gig_name = name(sim)
        msg.gig_description = description(sim)
        msg.career_panel_info_text = cls._get_reward_description()
        if inst is not None:
            msg.additional_objectives.extend([data.selected_objective.guid64 for data in inst.mission_objective_data if data.is_valid])
lock_instance_tunables(MissionGig, gig_prep_tasks=None, gig_time=None, gig_prep_time=None, gig_picker_localization_format=None, great_success_remaining_time=None, audio_on_prep_task_completion=None, career_events=None, gig_cast_rel_bit_collection_id=None, gig_cast=None, end_of_gig_dialog=None, payout_stat_data=None, bonus_gig_aspiration_tuning=None, critical_failure_test=None)