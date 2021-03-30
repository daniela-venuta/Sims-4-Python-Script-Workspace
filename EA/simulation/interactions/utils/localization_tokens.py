import build_buyimport collectionsimport itertoolsimport operatorimport randomfrom bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom objects.components.types import OBJECT_MARKETPLACE_COMPONENTfrom protocolbuffers.Localization_pb2 import LocalizedStringTokenfrom civic_policies.street_civic_policy_tuning import StreetCivicPolicySelectorMixinfrom global_policies.global_policy_enums import GlobalPolicyTokenTypefrom interactions import ParticipantType, ParticipantTypeSingle, ParticipantTypeObjectfrom objects.game_object_properties import GameObjectPropertyfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.resources import Typesfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableVariant, TunableTuple, TunableEnumEntry, TunableReference, OptionalTunablefrom tunable_utils.tunable_object_generator import TunableObjectGeneratorVariantimport servicesimport sims4
class _TunableObjectLocalizationTokenFormatterSingle(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'mismatch_name': OptionalTunable(description='\n            If enabled, this is the object name to use when using a multi-\n            object participant yielding definitions with different names.\n            ', tunable=TunableLocalizedString(allow_catalog_name=True))}

    def __call__(self, objs):
        if not (self.mismatch_name is not None and objs and all(obj.definition is objs[0].definition for obj in objs)):
            mismatch_name = self.mismatch_name

            class _MismatchDefinition:

                def populate_localization_token(self, token):
                    token.type = LocalizedStringToken.OBJECT
                    token.catalog_name_key = mismatch_name.hash

            return _MismatchDefinition()
        elif objs:
            return objs[0]

class _TunableObjectLocalizationTokenFormatterBulletList(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'bullet_text': TunableLocalizedStringFactory(description='\n            The text for the bullet entry. The string is provided the\n            following tokens, in this order:\n             0 An object representitive of the group\n             1 The number of objects in the group\n            ')}

    def __call__(self, objs):
        key_fn = operator.attrgetter('definition')
        return LocalizationHelperTuning.get_bulleted_list((None,), tuple(self.bullet_text(definition, len(tuple(group))) for (definition, group) in itertools.groupby(sorted(objs, key=key_fn), key=key_fn)))

class TunableObjectLocalizationTokenFormatterVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, single=_TunableObjectLocalizationTokenFormatterSingle.TunableFactory(), bullet_list=_TunableObjectLocalizationTokenFormatterBulletList.TunableFactory(), default='single', **kwargs)

class TunableLocalizationStreetSelector(StreetCivicPolicySelectorMixin):

    def get_street_provider(self):
        if self.street is None or hasattr(self.street, 'civic_policy'):
            kwargs = dict()
        else:
            kwargs = self.street.get_expected_args()
            if 'subjects' in kwargs:
                kwargs['subjects'] = (services.get_active_sim().sim_info,)
            if 'picked_zone_ids' in kwargs:
                kwargs['picked_zone_ids'] = (services.current_zone_id(),)
        return self._get_civic_policy_provider(**kwargs)

class LocalizationTokens(HasTunableSingletonFactory, AutoFactoryInit):
    TOKEN_PARTICIPANT = 0
    TOKEN_MONEY = 1
    TOKEN_STATISTIC = 2
    TOKEN_OBJECT_PROPERTY = 3
    TOKEN_INTERACTION_COST = 4
    TOKEN_DEFINITION = 5
    TOKEN_CAREER_DATA = 6
    TOKEN_ASSOCIATED_CLUB = 7
    TOKEN_GAME_COMPONENT = 8
    TOKEN_SICKNESS = 9
    TOKEN_PARTICIPANT_COUNT = 10
    TOKEN_INTERACTION_PAYOUT = 11
    TOKEN_HOLIDAY = 12
    TOKEN_CURRENT_TRENDS = 13
    TOKEN_LIFESTYLE_BRAND = 14
    TOKEN_GLOBAL_POLICY = 15
    TOKEN_PICKED_PART = 16
    TOKEN_SCHOLARSHIP_LETTER = 17
    TOKEN_BUCK = 18
    TOKEN_CIVIC_POLICY = 19
    TOKEN_STREET = 20
    TOKEN_VENUE = 21
    TOKEN_OBJECT_MARKETPLACE = 22
    TOKEN_CAREER_DATA_CURRENT_LEVEL_NAME = 1
    TOKEN_CAREER_DATA_CURRENT_LEVEL_SALARY = 2
    TOKEN_CAREER_DATA_NEXT_LEVEL_NAME = 3
    TOKEN_CAREER_DATA_NEXT_LEVEL_SALARY = 4
    TOKEN_CAREER_DATA_PREVIOUS_LEVEL_NAME = 5
    TOKEN_CAREER_DATA_PREVIOUS_LEVEL_SALARY = 6
    TOKEN_GAME_COMPONENT_DATA_HIGH_SCORE = 1
    TOKEN_GAME_COMPONENT_DATA_HIGH_SCORE_SIM = 2
    TOKEN_SCHOLARSHIP_LETTER_APPLICANT_NAME = 1
    TOKEN_SCHOLARSHIP_LETTER_DATA_AMOUNT = 2
    TOKEN_SCHOLARSHIP_LETTER_DATA_NAME = 3
    TOKEN_SCHOLARSHIP_LETTER_DATA_DESCRIPTION = 4
    TOKEN_CIVIC_POLICY_VOTING_START_TIME = 1
    TOKEN_CIVIC_POLICY_VOTING_END_TIME = 2
    TOKEN_STREET_POLICY_NAME_UP_FOR_REPEAL = 1
    TOKEN_STREET_POLICY_NAME_BALLOTED_RANDOM_LOSING = 2
    TOKEN_STREET_POLICY_NAME_BALLOTED_WINNING = 3
    TOKEN_VENUE_ACTIVE_VENUE_NAME = 1
    TOKEN_VENUE_SOURCE_VENUE_NAME = 2
    TOKEN_OBJECT_MARKETPLACE_EXPIRATION_TIME = 1
    TOKEN_OBJECT_MARKETPLACE_SALE_PRICE = 2
    TOKEN_OBJECT_MARKETPLACE_BUYER_NAME = 3
    _DatalessToken = collections.namedtuple('_DatalessToken', 'token_type')
    FACTORY_TUNABLES = {'tokens': TunableList(description="\n            A list of tokens that will be returned by this factory. Any string\n            that uses this token will have token '0' be set to the first\n            element, '1' to the second element, and so on. Do not let the list\n            inheritance values confuse you; regardless of what the list element\n            index is, the first element will always be 0, the second element 1,\n            and so on.\n            ", tunable=TunableVariant(description='\n                Define what the token at the specified index is.\n                ', participant_type=TunableTuple(description='\n                    The token is a Sim or object participant from the\n                    interaction.\n                    ', locked_args={'token_type': TOKEN_PARTICIPANT}, objects=TunableObjectGeneratorVariant(participant_default=ParticipantType.Actor), formatter=TunableObjectLocalizationTokenFormatterVariant(description='\n                        Define the format for this token.\n                        ')), participant_count=TunableTuple(description='\n                    The number of participants of the specified type.\n                    ', locked_args={'token_type': TOKEN_PARTICIPANT_COUNT}, objects=TunableObjectGeneratorVariant(participant_default=ParticipantType.ObjectChildren)), definition=TunableTuple(description="\n                    A catalog definition to use as a token. This is useful if\n                    you want to properly localize an object's name or\n                    description.\n                    ", locked_args={'token_type': TOKEN_DEFINITION}, definition=TunableReference(manager=services.definition_manager())), money_amount=TunableTuple(description='\n                    The token is a number representing the amount of Simoleons\n                    that were awarded in loot to the specified participant.\n                    ', locked_args={'token_type': TOKEN_MONEY}, participant=TunableEnumEntry(description='\n                        The participant for whom we fetch the earned amount of\n                        money.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Actor)), buck_amount=TunableTuple(description='\n                    The token is a number repesenting the amount of the \n                    specified buck type the specified participant has.\n                    ', locked_args={'token_type': TOKEN_BUCK}, participant=TunableEnumEntry(description="\n                        The participant from whom we will fetch the specified\n                        statistic's value.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Actor), bucks_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=BucksType.INVALID)), statistic_value=TunableTuple(description='\n                    The token is a number representing the value of a specific\n                    statistic from the selected participant.\n                    ', locked_args={'token_type': TOKEN_STATISTIC}, participant=TunableEnumEntry(description="\n                        The participant from whom we will fetch the specified\n                        statistic's value.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Actor), statistic=TunableReference(description="\n                        The statistic's whose value we want to fetch.\n                        ", manager=services.statistic_manager())), object_property=TunableTuple(description='\n                    The token is a property of a game object.  This could be \n                    catalog properties like its price or its rarity which is a \n                    property given by a component.\n                    ', locked_args={'token_type': TOKEN_OBJECT_PROPERTY}, obj_property=TunableEnumEntry(description='\n                        The property of the object that we will request.\n                        ', tunable_type=GameObjectProperty, default=GameObjectProperty.CATALOG_PRICE)), career_data=TunableTuple(description='\n                    The token is a localized string, number, or Sim,\n                    representing the specified career data for the specified\n                    participant.\n                    ', locked_args={'token_type': TOKEN_CAREER_DATA}, participant=TunableEnumEntry(description="\n                        The participant's whose career data we care about.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Actor), career_type=TunableReference(description='\n                        The career we care about.\n                        ', manager=services.get_instance_manager(Types.CAREER)), career_data=TunableVariant(description='\n                        The piece of data to fetch.\n                        ', locked_args={'current_level_name': TOKEN_CAREER_DATA_CURRENT_LEVEL_NAME, 'current_level_salary': TOKEN_CAREER_DATA_CURRENT_LEVEL_SALARY, 'next_level_name': TOKEN_CAREER_DATA_NEXT_LEVEL_NAME, 'next_level_salary': TOKEN_CAREER_DATA_NEXT_LEVEL_SALARY, 'previous_level_name': TOKEN_CAREER_DATA_PREVIOUS_LEVEL_NAME, 'previous_level_salary': TOKEN_CAREER_DATA_PREVIOUS_LEVEL_SALARY}, default='current_level_name')), associated_club=TunableTuple(description='\n                    The token is a stored "associated_club" on this\n                    interaction. Only works with ClubMixerInteractions or\n                    ClubSuperInteractions.\n                    ', locked_args={'token_type': TOKEN_ASSOCIATED_CLUB}), game_component_data=TunableTuple(description='\n                    The token is a localized number or Sim representing \n                    the specified game component data from game component.\n                    ', locked_args={'token_type': TOKEN_GAME_COMPONENT}, participant=TunableEnumEntry(description="\n                        The participant's from whom the game component data \n                        we want to fetch.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Object), game_component_data=TunableVariant(description='\n                        The piece of data to fetch.\n                        ', locked_args={'high_score': TOKEN_GAME_COMPONENT_DATA_HIGH_SCORE, 'high_score_sim': TOKEN_GAME_COMPONENT_DATA_HIGH_SCORE_SIM}, default='high_score')), scholarship_letter_component_data=TunableTuple(description='\n                    The token can be used to get strings representing scholarship\n                    information from the scholarship letter component of an object.\n                    ', locked_args={'token_type': TOKEN_SCHOLARSHIP_LETTER}, participant=TunableEnumEntry(description='\n                        The participant from whom to get the scholarship letter\n                        component data.\n                        ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), scholarship_letter_component_data=TunableVariant(description='\n                        The piece of data to fetch.\n                        ', locked_args={'applicant_name': TOKEN_SCHOLARSHIP_LETTER_APPLICANT_NAME, 'scholarship_amount': TOKEN_SCHOLARSHIP_LETTER_DATA_AMOUNT, 'scholarship_name': TOKEN_SCHOLARSHIP_LETTER_DATA_NAME, 'scholarship_description': TOKEN_SCHOLARSHIP_LETTER_DATA_DESCRIPTION}, default='applicant_name')), sickness=TunableTuple(description='\n                    The token is the name of the sickness on the specified Sim.\n                    ', locked_args={'token_type': TOKEN_SICKNESS}, participant=TunableEnumEntry(description='\n                        The participant who is sick.\n                        ', tunable_type=ParticipantType, default=ParticipantType.TargetSim)), lifestyle_brand=TunableTuple(description='\n                    The token used to display the name of a Lifestyle Brand \n                    owned by a Sim.\n                    ', locked_args={'token_type': TOKEN_LIFESTYLE_BRAND}, participant=TunableEnumEntry(description='\n                        The participant who owns the lifestyle brand.\n                        ', tunable_type=ParticipantTypeSingle, default=ParticipantType.TargetSim)), global_policy=TunableTuple(description='\n                    The token used to display data from the tuned global policy.\n                    ', locked_args={'token_type': TOKEN_GLOBAL_POLICY}, global_policy=TunableReference(description='\n                        The global policy from which data is displayed.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('GlobalPolicy',)), token_property=TunableEnumEntry(description="\n                        Which property from the Global Policy Token to use. NAME\n                        will use the policy's display name, PROGRESS will use\n                        the progress made over the max progress value. \n                        ", tunable_type=GlobalPolicyTokenType, default=GlobalPolicyTokenType.NAME)), object_marketplace=TunableTuple(description='\n                    Tokens for the object marketplace component and marketplace\n                    system.\n                    ', locked_args={'token_type': TOKEN_OBJECT_MARKETPLACE}, object_marketplace_data=TunableVariant(description='\n                        Please select what value you would like to use.\n                        ', locked_args={'expiration_time': TOKEN_OBJECT_MARKETPLACE_EXPIRATION_TIME, 'sale_price': TOKEN_OBJECT_MARKETPLACE_SALE_PRICE, 'buyer_name': TOKEN_OBJECT_MARKETPLACE_BUYER_NAME}, default='expiration_time')), picked_part=TunableTuple(description='\n                    The token used to display the name of a picked part.\n                    ', locked_args={'token_type': TOKEN_PICKED_PART}), civic_policy=TunableTuple(description='\n                    Tokens for the Civic Policy system.\n                    ', locked_args={'token_type': TOKEN_CIVIC_POLICY}, civic_policy_data=TunableVariant(description='\n                        The specific value to display.\n                        ', locked_args={'voting_start_time': TOKEN_CIVIC_POLICY_VOTING_START_TIME, 'voting_end_time': TOKEN_CIVIC_POLICY_VOTING_END_TIME}, default='voting_start_time')), street=TunableTuple(description='\n                    ', locked_args={'token_type': TOKEN_STREET}, street=TunableLocalizationStreetSelector.TunableFactory(), street_data=TunableVariant(description='\n                        The piece of data to fetch.\n                        ', locked_args={'policy_up_for_repeal': TOKEN_STREET_POLICY_NAME_UP_FOR_REPEAL, 'random_losing_balloted_policy': TOKEN_STREET_POLICY_NAME_BALLOTED_RANDOM_LOSING, 'winning_balloted_policy': TOKEN_STREET_POLICY_NAME_BALLOTED_WINNING}, default='policy_up_for_repeal')), venue=TunableTuple(description='\n                    ', locked_args={'token_type': TOKEN_VENUE}, venue_data=TunableVariant(description='\n                        ', locked_args={'active_venue': TOKEN_VENUE_ACTIVE_VENUE_NAME, 'source_venue': TOKEN_VENUE_SOURCE_VENUE_NAME}, default='active_venue')), locked_args={'interaction_cost': _DatalessToken(token_type=TOKEN_INTERACTION_COST), 'interaction_payout': _DatalessToken(token_type=TOKEN_INTERACTION_PAYOUT), 'active_holiday': _DatalessToken(token_type=TOKEN_HOLIDAY), 'current_trends': _DatalessToken(token_type=TOKEN_CURRENT_TRENDS)}, default='participant_type'))}

    def _get_token(self, resolver, token_data):
        if token_data.token_type == self.TOKEN_PARTICIPANT:
            participants = token_data.objects.get_objects(resolver)
            return token_data.formatter(participants)
        if token_data.token_type == self.TOKEN_PARTICIPANT_COUNT:
            participants = token_data.objects.get_objects(resolver)
            if not participants:
                return 0
            return len(participants)
        if token_data.token_type == self.TOKEN_DEFINITION:
            return token_data.definition
        elif token_data.token_type == self.TOKEN_MONEY:
            interaction = getattr(resolver, 'interaction', None)
            if interaction is not None:
                from interactions.money_payout import MoneyLiability
                money_liability = interaction.get_liability(MoneyLiability.LIABILITY_TOKEN)
                if money_liability is not None:
                    return money_liability.amounts[token_data.participant]
                return 0
        return 0
        if token_data.token_type == self.TOKEN_BUCK:
            participant = resolver.get_participant(participant_type=token_data.participant)
            tracker = BucksUtils.get_tracker_for_bucks_type(token_data.bucks_type, owner_id=participant.id)
            if not tracker:
                return 0
            return tracker.get_bucks_amount_for_type(token_data.bucks_type)
        if token_data.token_type == self.TOKEN_STATISTIC:
            participant = resolver.get_participant(participant_type=token_data.participant)
            if participant is not None:
                tracker = participant.get_tracker(token_data.statistic)
                if tracker is not None:
                    return tracker.get_value(token_data.statistic)
        if token_data.token_type == self.TOKEN_OBJECT_PROPERTY:
            participant = resolver.get_participant(ParticipantType.Object)
            if participant is None:
                return
            return participant.get_object_property(token_data.obj_property)
        if token_data.token_type == self.TOKEN_INTERACTION_COST:
            interaction = getattr(resolver, 'interaction', None)
            if interaction is not None:
                return interaction.get_simoleon_cost()
            affordance = getattr(resolver, 'affordance', None)
            if affordance is not None:
                return affordance.get_simoleon_cost(target=resolver.target, context=resolver.context)
        if token_data.token_type == self.TOKEN_INTERACTION_PAYOUT:
            interaction = getattr(resolver, 'interaction', None)
            if interaction is not None:
                return interaction.get_simoleon_payout()
            affordance = getattr(resolver, 'affordance', None)
            if affordance is not None:
                return affordance.get_simoleon_payout(target=resolver.target, context=resolver.context)
        if token_data.token_type == self.TOKEN_ASSOCIATED_CLUB:
            if resolver.interaction is not None:
                club = getattr(resolver.interaction, 'associated_club')
            else:
                club = resolver.interaction_parameters.get('associated_club')
            if club is not None:
                return club.name
        if token_data.token_type == self.TOKEN_CAREER_DATA:
            participant = resolver.get_participant(participant_type=token_data.participant)
            if participant is not None:
                if participant.career_tracker is None:
                    return
                career = participant.career_tracker.get_career_by_uid(token_data.career_type.guid64)
                if career is not None:
                    if token_data.career_data == self.TOKEN_CAREER_DATA_CURRENT_LEVEL_NAME:
                        current_level = career.current_level_tuning
                        return current_level.get_title(participant)
                    if token_data.career_data == self.TOKEN_CAREER_DATA_CURRENT_LEVEL_SALARY:
                        current_level = career.current_level_tuning
                        return current_level.simoleons_per_hour
                    if token_data.career_data == self.TOKEN_CAREER_DATA_NEXT_LEVEL_NAME:
                        next_level = career.next_level_tuning
                        if next_level is not None:
                            return next_level.get_title(participant)
                    elif token_data.career_data == self.TOKEN_CAREER_DATA_NEXT_LEVEL_SALARY:
                        next_level = career.next_level_tuning
                        if next_level is not None:
                            return next_level.simoleons_per_hour
                    elif token_data.career_data == self.TOKEN_CAREER_DATA_PREVIOUS_LEVEL_NAME:
                        previous_level = career.previous_level_tuning
                        if previous_level is not None:
                            return previous_level.get_title(participant)
                    elif token_data.career_data == self.TOKEN_CAREER_DATA_PREVIOUS_LEVEL_SALARY:
                        previous_level = career.previous_level_tuning
                        if previous_level is not None:
                            return previous_level.simoleons_per_hour
        if token_data.token_type == self.TOKEN_GAME_COMPONENT:
            participant = resolver.get_participant(participant_type=token_data.participant)
            if participant is not None:
                game = participant.game_component
                if game is None:
                    return
                if token_data.game_component_data == self.TOKEN_GAME_COMPONENT_DATA_HIGH_SCORE and game.high_score is not None:
                    return game.high_score
                if token_data.game_component_data == self.TOKEN_GAME_COMPONENT_DATA_HIGH_SCORE_SIM and game.high_score_sim_ids:
                    high_score_sim_id = game.high_score_sim_ids[0]
                    return services.sim_info_manager().get(high_score_sim_id)
        if token_data.token_type == self.TOKEN_SCHOLARSHIP_LETTER:
            participant = resolver.get_participant(participant_type=token_data.participant)
            if participant is not None:
                scholarship_letter_component = participant.scholarship_letter_component
                if scholarship_letter_component is None:
                    return
                if token_data.scholarship_letter_component_data == self.TOKEN_SCHOLARSHIP_LETTER_APPLICANT_NAME:
                    return scholarship_letter_component.get_applicant_name()
                if token_data.scholarship_letter_component_data == self.TOKEN_SCHOLARSHIP_LETTER_DATA_AMOUNT:
                    return scholarship_letter_component.get_scholarship_amount()
                if token_data.scholarship_letter_component_data == self.TOKEN_SCHOLARSHIP_LETTER_DATA_NAME:
                    return scholarship_letter_component.get_scholarship_name()
                if token_data.scholarship_letter_component_data == self.TOKEN_SCHOLARSHIP_LETTER_DATA_DESCRIPTION:
                    return scholarship_letter_component.get_scholarship_description()
        if token_data.token_type == self.TOKEN_SICKNESS:
            participant = resolver.get_participant(participant_type=token_data.participant)
            if participant is None or not participant.is_sim:
                return
            current_sickness = participant.current_sickness
            if current_sickness is None:
                return
            return current_sickness.display_name(participant)
        if token_data.token_type == self.TOKEN_GLOBAL_POLICY:
            global_policy = services.global_policy_service().get_global_policy(token_data.global_policy, create=False)
            if global_policy is None:
                return token_data.global_policy.get_non_active_display(token_data)
            return global_policy.get_active_policy_display(token_data)
        if token_data.token_type == self.TOKEN_HOLIDAY:
            active_household = services.active_household()
            if active_household.holiday_tracker is None:
                return
            holiday_id = active_household.holiday_tracker.get_active_or_upcoming_holiday()
            if holiday_id is None:
                return
            return services.holiday_service().get_holiday_display_name(holiday_id)
        if token_data.token_type == self.TOKEN_CURRENT_TRENDS:
            trend_service = services.trend_service()
            if trend_service is None:
                return
            return trend_service.get_current_trends_loc_string()
        if token_data.token_type == self.TOKEN_LIFESTYLE_BRAND:
            participant = resolver.get_participant(participant_type=token_data.participant)
            lifestyle_brand_tracker = participant.lifestyle_brand_tracker
            if lifestyle_brand_tracker is None:
                return
            return lifestyle_brand_tracker.brand_name
        if token_data.token_type == self.TOKEN_PICKED_PART:
            participant = resolver.get_participant(ParticipantType.Object)
            if participant is None:
                return
            context = getattr(resolver, 'context', None)
            if context is not None and context.pick is not None:
                target_objects = participant.get_closest_parts_to_position(context.pick.location, has_name=True)
                if target_objects:
                    part = target_objects.pop()
                    return part.part_name
        if token_data.token_type == self.TOKEN_OBJECT_MARKETPLACE:
            participant = resolver.get_participant(ParticipantType.Object)
            if participant is None:
                return
            marketplace_component = participant.get_component(OBJECT_MARKETPLACE_COMPONENT)
            if token_data.object_marketplace_data == self.TOKEN_OBJECT_MARKETPLACE_EXPIRATION_TIME:
                return marketplace_component.get_expiration_time()
            if token_data.object_marketplace_data == self.TOKEN_OBJECT_MARKETPLACE_SALE_PRICE:
                return marketplace_component.get_sale_price()
            if token_data.object_marketplace_data == self.TOKEN_OBJECT_MARKETPLACE_BUYER_NAME:
                return marketplace_component.get_buyer_screen_name()
        if token_data.token_type == self.TOKEN_CIVIC_POLICY:
            if token_data.civic_policy_data == self.TOKEN_CIVIC_POLICY_VOTING_START_TIME:
                return services.street_service().voting_open_time
            if token_data.civic_policy_data == self.TOKEN_CIVIC_POLICY_VOTING_END_TIME:
                return services.street_service().voting_close_time
        if token_data.token_type == self.TOKEN_STREET:
            if token_data.street_data == self.TOKEN_STREET_POLICY_NAME_UP_FOR_REPEAL:
                provider = token_data.street.get_street_provider()
                if provider is not None:
                    policies = provider.get_up_for_repeal_policies()
                    if policies:
                        return list(policies)[0].display_name()
            if token_data.street_data == self.TOKEN_STREET_POLICY_NAME_BALLOTED_RANDOM_LOSING:
                provider = token_data.street.get_street_provider()
                if provider is None:
                    return
                policies = list(provider.get_balloted_policies())
                if policies and len(policies) > 1:
                    winning_policy = max(policies, key=lambda policy: provider.get_stat_value(policy.vote_count_statistic))
                    policies.remove(winning_policy)
                    random_losing_policy = random.choice(policies)
                    return random_losing_policy.display_name()
            if token_data.street_data == self.TOKEN_STREET_POLICY_NAME_BALLOTED_WINNING:
                provider = token_data.street.get_street_provider()
                if provider is None:
                    return
                policies = list(provider.get_balloted_policies())
                if policies:
                    winning_policy = max(policies, key=lambda policy: provider.get_stat_value(policy.vote_count_statistic))
                    return winning_policy.display_name()
        if token_data.token_type == self.TOKEN_VENUE:
            if token_data.venue_data == self.TOKEN_VENUE_ACTIVE_VENUE_NAME:
                raw_active_venue_tuning_id = build_buy.get_current_venue(services.current_zone_id(), allow_ineligible=True)
                raw_active_venue_tuning = services.venue_manager().get(raw_active_venue_tuning_id)
                if raw_active_venue_tuning is None:
                    return
                source_venue_tuning = type(services.venue_service().source_venue)
                if source_venue_tuning is raw_active_venue_tuning and source_venue_tuning.variable_venues is not None:
                    return raw_active_venue_tuning.variable_venues.variable_venue_display_name()
                return raw_active_venue_tuning.display_name
            elif token_data.venue_data == self.TOKEN_VENUE_SOURCE_VENUE_NAME:
                source_venue_tuning = type(services.venue_service().source_venue)
                if source_venue_tuning is not None:
                    return source_venue_tuning.display_name

    def get_tokens(self, resolver):
        return tuple(self._get_token(resolver, token_data) for token_data in self.tokens)
