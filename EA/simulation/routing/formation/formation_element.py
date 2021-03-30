from interactions import ParticipantTypeActorTargetSim, ParticipantTypeSinglefrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom routing.formation.formation_data import RoutingFormationfrom sims4.tuning.tunable import TunableEnumEntry, TunableList, OptionalTunable
class RoutingFormationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'master': TunableEnumEntry(description='\n            The Sim that is going to be followed.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'slave': TunableEnumEntry(description='\n            The Sim that will be doing the follow.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim), 'routing_formations': TunableList(description='\n            The routing formations we want to use. We will test them in order\n            until the tests pass.\n            \n            Use this list to do things like minimize interactions based on\n            which hand you want to leash a dog with.\n            ', tunable=RoutingFormation.TunableReference(description='\n                The routing formation to use.\n                '), minlength=1)}

    def _do_behavior(self, *args, **kwargs):
        master = self.interaction.get_participant(self.master)
        if master is None:
            return False
        slave = self.interaction.get_participant(self.slave)
        if slave is None:
            return False
        if slave is master:
            logger.error('Master and slave are the same: ({}); routing formation is not valid. Interaction: ({})', master, self.interaction)
            return False
        else:
            for formation in self.routing_formations:
                if formation.test_formation(master, slave):
                    formation(master, slave, interaction=self.interaction)
                    break
            return False
        return True

class ReleaseRoutingFormationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The Sim/object whose routing formation is gonna be released.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'target': OptionalTunable(tunable=TunableEnumEntry(description='\n                If enabled, the subject will only release the routing formation with this target.\n                If disabled, the subject will release all routing formations.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim))}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        if subject is None:
            return False
        target = self.interaction.get_participant(self.target) if self.target else None
        for slave_data in subject.routing_component.get_routing_slave_data():
            if not slave_data.master == target:
                if slave_data.slave == target:
                    slave_data.release_formation_data()
                    slave_data.interaction.cancel(FinishingType.USER_CANCEL, 'ReleaseRoutingFormationElement: Releasing routing formation.')
            slave_data.release_formation_data()
            slave_data.interaction.cancel(FinishingType.USER_CANCEL, 'ReleaseRoutingFormationElement: Releasing routing formation.')
        return True
