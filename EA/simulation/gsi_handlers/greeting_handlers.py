from gsi_handlers.gameplay_archiver import GameplayArchiver
    greeting_archive = {}
class GreetingsArchiveLog:

    def __init__(self):
        self.clear_log()

    def clear_log(self):
        self.greeting_archive_data = []

    sub_schema.add_field('greeting', label='Greeting', width=25)
    sub_schema.add_field('test_result', label='Result', width=40)
def get_greeting_log(sim_id, clear=False):
    greeting_log = setdefault_callable(greeting_archive, sim_id, GreetingsArchiveLog)
    if clear:
        del greeting_archive[sim_id]
    return greeting_log

def archive_greeting_request(actor_id, target_id, greeting_request_data):
    new_data = greeting_request_data.get_gsi_data()

    def log_greeting_request(data, sim_id):
        sim_log = get_greeting_log(sim_id, clear=True)
        if sim_log is None:
            return
        sim_log.greeting_archive_data.append(data)
        archiver.archive(data=data, object_id=sim_id)

    log_greeting_request(new_data, actor_id)
    log_greeting_request(new_data, target_id)

class GreetingRequestData:

    def __init__(self, actor_id, target_id, greeting_type, source_interaction=None):
        self.actor_id = actor_id
        self.target_id = target_id
        self.greeting_type = greeting_type
        self.greeting_test_results = []
        self.chosen_greeting = None
        self.source_interaction = str(source_interaction)

    def add_test_result(self, greeting, test_result):
        self.greeting_test_results.append((str(greeting), str(test_result)))

    def get_gsi_data(self):
        data = {}
        object_manager = services.object_manager()
        data['actor'] = str(object_manager.get(self.actor_id))
        data['target'] = str(object_manager.get(self.target_id))
        data['greeting_type'] = self.greeting_type
        data['chosen_greeting'] = str(self.chosen_greeting)
        data['source_interaction'] = self.source_interaction
        data['Results'] = []
        for greeting_result in self.greeting_test_results:
            result_data = {}
            result_data['greeting'] = greeting_result[0]
            result_data['test_result'] = greeting_result[1]
            data['Results'].append(result_data)
        return data
