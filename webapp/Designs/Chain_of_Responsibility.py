from abc import ABC, abstractmethod

class TaskContext:
    def __init__(self, **kwargs):
        self.data = kwargs
        self.errors = []

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def fail(self, message):
        self.errors.append(message)
        raise Exception(message)


# class Task(ABC):
#     def __init__(self, next_task=None):
#         self.next = next_task

#     def run(self, ctx: TaskContext):
#         self.validate(ctx)
#         self.process(ctx)
#         if self.next:
#             self.next.run(ctx)

#     @abstractmethod
#     def validate(self, ctx): ...
    
#     @abstractmethod
#     def process(self, ctx): ...



class Task(ABC):

    def __init__(self, next_task=None):
        self.next_task = next_task

    def execute(self, context: TaskContext) -> TaskContext:
        # Step 1: validate
        if not self.validate(context):
            return context

        # Step 2: process
        self.process(context)

        # Step 3: move to next
        if self.next_task:
            return self.next_task.execute(context)

        return context

    @abstractmethod
    def validate(self, context: TaskContext) -> bool:
        pass

    @abstractmethod
    def process(self, context: TaskContext):
        pass

