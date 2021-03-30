from sims4.tuning.tunable import TunableSimMinute
class AutonomyModesTuning:
    LOCKOUT_TIME = TunableSimMinute(description='\n        Number of sim minutes to lockout a failed interaction push or routing failure.\n        ', default=240)
