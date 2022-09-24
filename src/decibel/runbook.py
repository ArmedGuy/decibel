import inspect

from . import context
from .runnable import Runnable
from .dsl import Variable


class RunbookVars():
    def __init__(self, runvars):
        self._vars = {name: Variable(name, val) for name, val in runvars.items()}
    
    def __getattr__(self, name):
        return self._vars.get(name, None)

class Runbook():
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # When Runbook has been fully declared, iterate over all functions
        # and patch any run_-prefixed functions as Runnables.
        # Any function with a flow decorator (@after etc) will
        # already be registered as a Runnable.
        members = inspect.getmembers(cls, predicate=inspect.isfunction)
        for member in members:
            if not member[0].startswith("run_"):
                continue
            if isinstance(member[1], Runnable):
                continue
            r = Runnable(member[1])
            setattr(cls, member[0], r)


    def __init__(self, **kwargs):
        self._host_context = context.get_current_host_context().copy()
        self._parent_runbook = context.get_current_runbook()
        self.vars = RunbookVars(kwargs)
        self._host_context.vars = {name: val._actual_value if isinstance(val, Variable) else val for name, val in kwargs.items()}
        self.run_before = set()
        self.run_after = set()
        # Inherit any set before/afters from current runbook
        if self._parent_runbook is not None:
            self.run_before = set(self._parent_runbook.run_before)
            self.run_after = set(self._parent_runbook.run_after)
        # If instanciated inside a Runnable, schedule to run
        # Runbook sometime after Runnable.
        if context.get_current_runnable() is not None:
            self.run_after.add(context.get_current_runnable())
        with self:
            self._setup()
    
    def setup(self):
        pass

    def __enter__(self):
        self._old_current = context.get_current_runbook()
        context.set_current_runbook(self)

    def __exit__(self, type, value, tb):
       context.set_current_runbook(self._old_current)

    def _is_runnable(self, obj):
        return isinstance(obj, Runnable)

    def _setup(self):
        with self._host_context:
            self.setup()

            members = inspect.getmembers(self.__class__, predicate=self._is_runnable)
            # Iterate over all bound Runnables inside class and resolve soft-linked
            # dependencies. These exist because you cannot reference class.function
            # when the class is being read.
            # When all dependencies are resolved, instanciate the bound variant of the Runnable
            # to collect all Tasks and child Runnables.
            for _, r in members:
                run_before = set()
                for f in r.run_before:
                    if not isinstance(f, str):
                        run_before.add(f)
                        continue
                    run_before.add([m[1] for m in members if m[0] == f][0])
                r.run_before = run_before | self.run_before
                
                run_after = set()
                for f in r.run_after:
                    if not isinstance(f, str):
                        run_after.add(f)
                        continue
                    run_after.add([m[1] for m in members if m[0] == f][0])
                r.run_after = run_after | self.run_after
                r(self)