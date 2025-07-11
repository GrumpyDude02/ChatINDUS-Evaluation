class ExistingEvaluationError(Exception):
    default_message = "An existing evaluation under the same name has been found"

    def __init__(self, message=None, *args):
        final_message = message or ExistingEvaluationError.default_message
        super().__init__(final_message, *args)

class ExistingDatasetError(Exception):
    default_message = "An existing dataset under the same name has been found"

    def __init__(self, message=None, *args):
        final_message = message or ExistingDatasetError.default_message
        super().__init__(final_message, *args)