from interactions import ParticipantType
class Party:
    RALLY_FALSE_ADS = TunableList(description=' \n        A list of false advertisement for rallyable interactions. Use this\n        tunable to entice Sims to autonomously choose rallyable over non-\n        rallyable interactions.\n        ', tunable=TunableStatisticChange(locked_args={'subject': ParticipantType.Actor, 'advertise': True}))
