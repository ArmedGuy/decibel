import decibel

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
            "register": self.variable_name,
            "tags": [decibel._global_current_runnable.method.__qualname__]
        }

    def set_args(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def with_settings(self, **kwargs):
        self.settings = dict(self.settings, **kwargs)
        return self

    def where(self, **kwargs):
        for key, runnable in kwargs.items():
            self.vars[key] = f"{{{{ {runnable.variable_name} }}}}"
        return self

    def when(self, condition):
        if isinstance(condition, (list, tuple)):
            condition = [str(cond) for cond in condition]
        else:
            condition = str(condition)
        self.settings["when"] = condition
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

    def _escape_formatting(self, val):
        return str(val).replace("{", "[").replace("}", "]")

    def _format_args(self):
        if not self.args:
            return ", ".join(
                f"{key}={self._escape_formatting(value)}" for key, value in self.kwargs.items()
            )
        return ", ".join([self._escape_formatting(arg) for arg in self.args])

    def __repr__(self):
        return f"<Task '{self.action}' {self._format_args()}>"

    def __str__(self):
        return f"{self.action}({self._format_args()})"

    @property
    def var(self):
        return self.variable_name

    @property
    def is_failed(self):
        return f"{self.var} is failed"

    @property
    def is_success(self):
        return f"{self.var} is success"

    @property
    def is_skipped(self):
        return f"{self.var} is skipped"

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