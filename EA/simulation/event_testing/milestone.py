from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_base import GroupNamesimport servicesimport sims4.tuning.tunable
class AllCompletionType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            All of the Objectives as part of this Milestone must be completed\n            in order for this Milestone to be considered complete.\n            '}

    def completion_requirement(self):
        pass

class SubsetCompletionType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            A numerical subset of the total Objectives need to be complete for\n            this Milestone to be considered complete.\n            ', 'number_required': sims4.tuning.tunable.TunableRange(description='\n            The number of objectives as part of this Milestone that must be\n            completed until this Milestone is considered complete.\n            ', tunable_type=int, default=1, minimum=1)}

    def completion_requirement(self):
        return self.number_required

class Milestone:
    INSTANCE_TUNABLES = {'objectives': sims4.tuning.tunable.TunableList(description='\n            A list of all of the Objectives that will be tracked in order for\n            this Milestone to be completed.  Using the Objective Completion Type\n            we will determine the action number of Objectives that need to be\n            completed.\n            ', tunable=sims4.tuning.tunable.TunableReference(description='\n                An Objective that is one of the requirements for this Milestone\n                to be completed.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.CORE), 'objective_completion_type': sims4.tuning.tunable.TunableVariant(description='\n            A requirement of what objectives need to be completed.                          \n            ', complete_all=AllCompletionType.TunableFactory(), complete_subset=SubsetCompletionType.TunableFactory(), default='complete_all', tuning_group=GroupNames.CORE), 'track_completion_count': sims4.tuning.tunable.Tunable(description="\n            If checked, this Milestone will track how many times it's been\n            completed, even through resets. For instance, GP09 Missions reuse the \n            same Aspiration but still need to track how many times the Aspiration\n            has been completed.\n            ", tunable_type=bool, default=False), 'can_complete_without_objectives': sims4.tuning.tunable.Tunable(description="\n            If checked, this Milestone can have 0 objectives and be completed.\n            If unchecked, having zero objectives won't complete this Milestone. \n            This can be used for Milestones like Missions that have dynamically-\n            added Objectives that might not be available when the Milestone is \n            tested for completion.\n            ", tunable_type=bool, default=True)}

    @classmethod
    def objective_completion_count(cls):
        return cls.objective_completion_type.completion_requirement()

    @classmethod
    def should_test_on_zone_load(cls):
        for objective in cls.objectives:
            if objective.should_test_on_zone_load():
                return True
        return False
