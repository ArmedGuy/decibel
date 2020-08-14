import src as decibel

_variable_id = 1

def _generate_variable():
    global _variable_id
    name = f"runvar{_variable_id:04}"
    _variable_id += 1
    return name

class TaskData():
    def __init__(self, parent):
        self._parent = parent

    def __getattr__(self, name):
        if not name.startswith("_"):
            return TaskData(self._parent + "." + name)
        else:
            return super().__getattr__(name)

    def __str__(self):
        return self._parent

    def __repr__(self):
        return self.__str__()

class Task():
    def __init__(self, action):
        decibel._global_current_runnable.tasks.append(self)
        self.action = action
        self.variable_name = _generate_variable()
        self.vars = {}
        self.args = []
        self.kwargs = {}
        self.settings = {
            "register": self.variable_name
        }

    def set_args(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        print(f"Registered task {self}")
        return self

    def with_settings(self, **kwargs):
        self.settings = dict(self.settings, **kwargs)
        return self

    def where(self, **kwargs):
        for key, runnable in kwargs.items():
            self.vars[key] = f"{{{{ {runnable.variable_name} }}}}"
        return self

    def when(self, runnable):
        self.settings["when"] = str(runnable)
        return self

    def run_once(self):
        self.settings["run_once"] = True
        return self

    def on(self, target):
        self.settings["delegate_to"] = target
        return self

    def on_all(self, target):
        self.settings["delegate_to"] = "{{ item }}"
        self.settings["loop"] = target

    def _yaml(self):
        # If regular arg is used, discard any kwargs. If none exist use kwargs instead.
        task_data = self.args[0] if len(self.args) != 0 else self.kwargs
        out = dict({}, **self.settings)
        out[self.action] = task_data
        if self.vars:
            out["vars"] = self.vars
        return out

    def __repr__(self):
        return f"<Task '{self.action}' {self.kwargs if not self.args else self.args}>"

    @property
    def var(self):
        return self.variable_name

    def __getattr__(self, name):
        return TaskData(self.var + "." + name)


# Magically return a Task factory for anything imported from this module.
# This allows us to track any modules without having to do a hard sync between
# ansible, external repositores and us, while still passing linting in editors.
# Any instanciated Task will be bound to the current Runnable.
def __getattr__(action):
    def task_factory(*args, **kwargs):
        return Task(action).set_args(*args, **kwargs)
    return task_factory