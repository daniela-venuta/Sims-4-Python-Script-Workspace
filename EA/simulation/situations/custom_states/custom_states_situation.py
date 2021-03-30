import servicesfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableMapping, Tunable, TunableReference, TunableVariant, TunableEnumEntry, TunableRange, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.custom_states.custom_states_common_tuning import RandomWeightedSituationStateKey, TimeBasedSituationStateKeyfrom situations.custom_states.custom_states_situation_states import TunableCustomStatesSituationStateSnippetfrom situations.situation_complex import SituationComplexCommonfrom situations.situation_types import SituationSerializationOption
class BaseCustomStatesSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'default_situation_job': OptionalTunable(TunableReference(description='\n                Optionally tune a default situation job.\n                This is needed when using Zone directors etc,\n                which automatically assume a default job is present.\n                ', manager=services.get_instance_manager(Types.SITUATION_JOB), allow_none=True)), 'default_job_and_roles': TunableMapping(description='\n            A mapping between the default situation jobs and role states.\n            ', key_type=TunableReference(description='\n                A reference to a default Situation Job.\n                ', manager=services.get_instance_manager(Types.SITUATION_JOB)), key_name='Situation Job', value_type=TunableReference(description='\n                A reference to a default Role State for this Situation Job.\n                ', manager=services.get_instance_manager(Types.ROLE_STATE)), value_name='Role State', tuning_group=GroupNames.CORE), 'persistence_option': TunableEnumEntry(description='\n            How this situation save/loads.  Each option saves the situation into a different place\n            within the save game.  The situation may still fail to load if the Sims no longer match\n            their filters, time has passed, or the zone director just says no at the end of it.\n            \n            DONT: This situation will never save load.\n            \n            LOT: This situation will be saved on the lot.  This means that it will only be loaded upon\n            returning to this lot.\n            \n            STREET: This situation will be saved on the street.  This means that if you travel between different\n            lots on the same street that it will be loaded.\n            ', tunable_type=SituationSerializationOption, default=SituationSerializationOption.LOT, invalid_enums=(SituationSerializationOption.HOLIDAY,)), 'sims_expected_to_be_in_situation': TunableRange(description='\n            The number of Sims expected to be in the situation for the zone director to calculate over.\n            ', tunable_type=int, default=1, minimum=0, tuning_group=GroupNames.WALKBY), 'should_cancel_leave_interaction_on_premature_removal': Tunable(description='\n            If Checked any leave interaction running or queued on the sim\n            should be canceled if they are removed prematurely from the situation.\n            \n            Any situation that can cause a sim to leave the lot (but not leave lot\n            must run) should have this checked so that the leave interaction can be canceled\n            if the sim is pulled from this situation to be in another situation.\n            \n            My dinner party ends and the guest are leaving. I decide to throw an\n            after hours affair inviting several of the guests who are leaving. I need\n            to cancel their leave interaction so that they will stay.\n            ', tunable_type=bool, default=False)}
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def default_job(cls):
        return cls.default_situation_job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.default_job_and_roles.items())

    @classproperty
    def situation_states(cls):
        raise NotImplementedError

    @classmethod
    def get_starting_situation_state(cls):
        raise NotImplementedError

    @classmethod
    def _state_to_uid(cls, state_to_find):
        return 0

    @classproperty
    def situation_serialization_option(cls):
        return cls.persistence_option

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return cls.sims_expected_to_be_in_situation

    @classmethod
    def _can_start_walkby(cls, lot_id:int):
        return True

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return self.should_cancel_leave_interaction_on_premature_removal

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_state_key = None

    def get_phase_state_name_for_gsi(self):
        if self._current_state_key is None:
            return 'Invalid State'
        return self._current_state_key

    def start_situation(self):
        super().start_situation()
        self.change_state_by_key(self.get_starting_situation_state())

    def change_state_by_key(self, situation_key, reader=None):
        next_state = self.situation_states.get(situation_key)
        if next_state is None:
            raise KeyError
        self._current_state_key = situation_key
        self._change_state(next_state(), reader=reader)

    def _save_custom_state(self, writer):
        if self._current_state_key is None:
            raise AssertionError('Attempting to save Situation {} with no situation state.'.format(self))
        writer.write_string16(SituationComplexCommon.STATE_ID_KEY, self._current_state_key)
        self._cur_state.save_state(writer)

    def _load_custom_state(self, reader):
        situation_key = reader.read_string16(SituationComplexCommon.STATE_ID_KEY, None)
        if situation_key is None:
            raise KeyError
        self.change_state_by_key(situation_key, reader=reader)

class CustomStatesSituation(BaseCustomStatesSituation):
    INSTANCE_TUNABLES = {'_situation_states': TunableMapping(description='\n            A tunable mapping between situation state keys and situation states.\n            ', key_name='Situation State Key', key_type=Tunable(description='\n                The key of this situation state.  This key will be used when attempting to transition between different\n                situation states.\n                ', tunable_type=str, default=None), value_name='Situation State', value_type=TunableCustomStatesSituationStateSnippet(description='\n                The situation state that is tied to this key.\n                '), tuning_group=GroupNames.CORE), '_starting_state': TunableVariant(description='\n            The starting state of this situation.\n            ', random_starting_state=RandomWeightedSituationStateKey.TunableFactory(), time_based=TimeBasedSituationStateKey.TunableFactory(), default='random_starting_state', tuning_group=GroupNames.CORE)}

    @classproperty
    def situation_states(cls):
        return cls._situation_states

    @classmethod
    def get_starting_situation_state(cls):
        return cls._starting_state()
