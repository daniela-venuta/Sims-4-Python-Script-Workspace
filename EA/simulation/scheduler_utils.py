from sims4.tuning.tunable import TunableSingletonFactory, Tunablefrom tunable_time import Days
def convert_string_to_enum(**day_availability_mapping):
    day_availability_dict = {}
    for day in Days:
        name = '{} {}'.format(int(day), day.name)
        available = day_availability_mapping[name]
        day_availability_dict[day] = available
    return day_availability_dict

class TunableAvailableDays(TunableSingletonFactory):
    FACTORY_TYPE = staticmethod(convert_string_to_enum)

def TunableDayAvailability():
    day_availability_mapping = {}
    for day in Days:
        name = '{} {}'.format(int(day), day.name)
        day_availability_mapping[name] = Tunable(bool, False)
    day_availability = TunableAvailableDays(description='Which days of the week to include', **day_availability_mapping)
    return day_availability
