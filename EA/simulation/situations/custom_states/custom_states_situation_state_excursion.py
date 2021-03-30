from situations.custom_states.custom_states_situation_states import CustomStatesSituationStatefrom snippets import define_snippet, EXCURSION_SITUATION_STATE
class ExcursionSituationState(CustomStatesSituationState):
    pass
(TunableExcursionSituationStateReference, TunableExcursionSituationStateSnippet) = define_snippet(EXCURSION_SITUATION_STATE, ExcursionSituationState.TunableFactory())