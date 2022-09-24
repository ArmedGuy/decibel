import inspect
import importlib
from collections import deque
import pathlib

from . import context
from .runnable import Runnable

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


class HostContext():
    def __init__(self, instance, hosts, **kwargs):
        self.instance = instance
        self.vars = {}
        self.hosts = hosts
        self.settings = kwargs
        self.runnables = set()
        self._old_context = None

    def __repr__(self):
        return f"<HostContext '{self.hosts}' {self.settings}>"
    
    def __enter__(self):
        self._old_context = context.get_current_host_context()
        context.set_current_host_context(self)
        return self

    def __exit__(self, type, value, tb):
        context.set_current_host_context(self._old_context)

    def copy(self):
        return context.get_current_instance().hosts(self.hosts, **self.settings)

    def get_yaml(self, runnable):
        out = dict({
            "hosts": self.hosts,
        }, **self.settings)
        tasks = []
        settings = {}
        tasks.extend(runnable._yaml())
        settings = dict(settings, **runnable.hctx_settings)
        out["vars"] = self.vars
        out["tasks"] = tasks
        out["name"] = runnable.name
        out = dict(settings, **out)
        return out

    def __eq__(self, other):
        return isinstance(other, HostContext) and self.instance == other.instance and self.hosts == other.hosts and self.settings == other.settings and self.vars == other.vars and self.runnables == other.runnables
    
    def __hash__(self):
        return hash((self.instance, self.hosts, frozenset(self.settings.items()), frozenset(self.vars.items()), frozenset(self.runnables)))