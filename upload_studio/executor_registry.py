class _ExecutorRegistry:
    def __init__(self):
        self.executors = {}

    def register_executor(self, executor_class):
        if not executor_class.name:
            raise Exception('An executor class must have a valid name attribute')
        if executor_class.name in self.executors:
            raise Exception('Cannot register an executor with the same name')
        self.executors[executor_class.name] = executor_class

    def get_executor(self, name):
        return self.executors[name]


ExecutorRegistry = _ExecutorRegistry()
