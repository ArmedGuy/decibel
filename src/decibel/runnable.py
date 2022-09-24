import inspect
import os.path

from . import context

class Runnable():
    def __init__(self, method):
        self.method = method
        self.tasks = []
        self.host_contexts = []
        self.hctx_settings = {}
        self.task_settings = {}
        self.run_before = set()
        self.run_after = set()

        self.runnable_path = os.path.dirname(inspect.getfile(method))

    def __repr__(self):
        return f"<Runnable '{self.name}'>"

    def __enter__(self):
        self._old_current = context.get_current_runnable()
        context.set_current_runnable(self)

    def __exit__(self, type, value, tb):
        context.set_current_runnable(self._old_current)

    def __call__(self, *args, **kwargs):
        hctx = context.get_current_host_context()
        self.host_contexts.append(hctx)
        hctx.runnables.add(self)
        with self:
            self.method(*args, **kwargs)
        
        if len(context.get_current_predicates()):
            raise AttributeError("Not all predicates were deregistered")

    @property
    def name(self):
        return f"{self.method.__module__}.{self.method.__qualname__}"

    def __eq__(self, other):
        return self.method == other.method

    def __hash__(self):
        return hash(self.method)