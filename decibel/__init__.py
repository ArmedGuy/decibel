_global_current_instance = None
_global_current_host_context = None
_global_current_runbook = None
_global_current_runnable = None

import inspect
from collections import deque
import yaml

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

class Runnable():
    def __init__(self, method):
        self.method = method
        self.host_context = None
        self.tasks = []
        self.vars = {}
        self.hctx_settings = {}
        self.task_settings = {}
        self.run_before = set()
        self.run_after = set()

    def __repr__(self):
        return f"<Runnable '{self.name}'>"

    def __enter__(self):
        global _global_current_runnable
        self._old_current = _global_current_runnable
        _global_current_runnable = self

    def __exit__(self, type, value, tb):
        global _global_current_runnable
        _global_current_runnable = self._old_current

    def __call__(self, *args, **kwargs):
        global _global_current_host_context, _global_current_instance
        # If host_context is already a tuple, we are asked
        # to override current global host context
        if isinstance(self.host_context, tuple):
            with _global_current_instance.hosts(self.host_context[0], **self.host_context[1]) as hctx:
                self._do_call(*args, **kwargs)
        else:
            self._do_call(*args, **kwargs)

    def _do_call(self, *args, **kwargs):
        # if call has no regular args or arg0 is not instance
        # of Runbook (aka self variable), attach the Runnable
        # to the current host context
        if len(args) == 0 or not isinstance(args[0], Runbook):
            _global_current_host_context.runnables.add(self)
        self.host_context = _global_current_host_context
        with self:
            self.method(*args, **kwargs)

    def _yaml(self):
        out = []
        for i, t in enumerate(self.tasks, start=1):
            tyaml = t._yaml()
            tyaml["name"] = f"{str(t)}"
            tyaml = dict(self.task_settings, **tyaml)
            out.append(tyaml)
        return out

    @property
    def name(self):
        return f"{self.method.__module__}.{self.method.__qualname__}"

class RunbookVars():
    def __init__(self, runvars):
        self._vars = runvars
    
    def __getattr__(self, name):
        return self._vars.get(name, None)

class Runbook():
    def __init_subclass__(cls, /, **kwargs):
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
        global _global_current_runbook, _global_current_host_context, _global_current_runnable
        self._host_context = _global_current_host_context
        self._parent_runbook = _global_current_runbook
        self.vars = RunbookVars(kwargs)
        self.run_before = set()
        self.run_after = set()
        # Inherit any set before/afters from current runbook
        if self._parent_runbook is not None:
            self.run_before = set(self._parent_runbook.run_before)
            self.run_after = set(self._parent_runbook.run_after)
        # If instanciated inside a Runnable, schedule to run
        # Runbook sometime after Runnable.
        if _global_current_runnable is not None:
            self.run_after.add(_global_current_runnable)
        with self:
            self._setup()
    
    def setup(self):
        pass

    def __enter__(self):
        global _global_current_runbook
        self._old_current = _global_current_runbook
        _global_current_runbook = self

    def __exit__(self, type, value, tb):
        global _global_current_runbook
        _global_current_runbook = self._old_current

    def _is_runnable(self, obj):
        return isinstance(obj, Runnable)

    def _setup(self):
        global _global_current_instance
        self.setup()
        members = inspect.getmembers(self.__class__, predicate=self._is_runnable)
        # Iterate over all bound Runnables inside class and resolve soft-linked
        # dependencies. These exist because you cannot reference class.function
        # when the class is being read.
        # When all dependencies are resolved, instanciate the bound variant of the Runnable
        # to collect all Tasks and child Runnables.
        for member, r in members:
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

            # Add any variables from Runbook to Runnable, but
            # make sure Runnable-local variables are preserved
            r.vars = dict(self.vars._vars, **r.vars)
            
            # Check if host context is overridden for Runnable,
            # if not add to current host context and collect children.
            if not isinstance(r.host_context, tuple):
                self._host_context.runnables.add(r)
                getattr(self, member)(self)
            else:
                # host context is overridden for this Runnable
                # execute Runnable within specified host context
                with _global_current_instance.hosts(r.host_context[0], **r.host_context[1]) as hctx:
                    r.host_context = hctx
                    hctx.runnables.add(r)
                    getattr(self, member)(self)


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
        global _global_current_host_context
        self._old_context = _global_current_host_context
        _global_current_host_context = self
        return self

    def __exit__(self, type, value, tb):
        global _global_current_host_context
        _global_current_host_context = self._old_context

    def get_yaml(self, runnable):
        out = dict({
            "hosts": self.hosts,
        }, **self.settings)
        tasks = []
        settings = {}
        runnable_vars = {}
        tasks.extend(runnable._yaml())
        settings = dict(settings, **runnable.hctx_settings)
        runnable_vars = dict(runnable_vars, **runnable.vars)
        if self.vars:
            out["vars"] = {
                "decibel_vars": self.vars
            }
        out["vars"] = dict(out.get("vars", {}), **runnable_vars)
        out["tasks"] = tasks
        out["name"] = runnable.name
        out = dict(settings, **out)
        return out

DEFAULT_SETTINGS = {
    'merge_runnables': False,
}
class Decibel():
    def __init__(self, **kwargs):
        self.settings = dict(DEFAULT_SETTINGS, **kwargs)
        self.host_contexts = {}

    def __enter__(self):
        global _global_current_instance
        self._old_instance = _global_current_instance
        _global_current_instance = self
        return self

    def __exit__(self, type, value, tb):
        global _global_current_instance
        _global_current_instance = self._old_instance

    def hosts(self, hosts, **kwargs):
        hctx = self.host_contexts.get(hosts, None)
        if hctx is not None:
            return hctx
        hctx = HostContext(self, hosts, **kwargs)
        self.host_contexts[hosts] = hctx
        return hctx

    def run(self):
        dag = RunnableDAG()
        for hctx in self.host_contexts.values():
            for r in hctx.runnables:
                dag.add_node(r)
                for b in r.run_before:
                    dag.add_edge(r, b) # r must run before b
                for a in r.run_after:
                    dag.add_edge(a, r) # a must run before r
        
        # Topological sort gives us a pretty ordered list that consists of our run order
        # of Runnables.
        runs = dag.topological_sort()
        out = []
        # Dump each Runnable separately.
        for r in runs:
            if not r.tasks:
                continue
            out.append(r.host_context.get_yaml(r))
        dag.get_dot()
        print(yaml.dump(out))


class RunnableDAG():
    """
    Implementation of Directed Acyclic Graph for Runnables.
    An edge from_node -> to_node means to_node depends on from_node,
    i.e. from_node must run before to_node.

    Implemented from https://github.com/thieman/py-dag.
    """
    def __init__(self):
        self.graph = OrderedDict()

    def add_node(self, node):
        if node not in self.graph:
            self.graph[node] = set()

    def add_edge(self, from_node, to_node):
        # TODO: test graph on each add
        if from_node not in self.graph:
            self.add_node(from_node)
        if to_node not in self.graph:
            self.add_node(to_node)
        self.graph[from_node].add(to_node)
        try:
            self.topological_sort()
        except ValueError:
            self.graph[from_node].remove(to_node)
            raise ValueError(f"Adding {from_node} -> {to_node} causes a cycle")

    def predecessors(self, node):
        return [key for key in self.graph if node in self.graph[key]]

    def downstream(self, node):
        if node not in self.graph:
            raise KeyError(f"{node} is not in graph")
        return list(self.graph[node])

    def leaves(self):
        return [key for key in graph if not self.graph[key]]

    def independent_nodes(self):
        """
        All nodes that nobody depends on. Our starting points.
        """
        dependent_nodes = set(
            node for dependents in self.graph.values() for node in dependents
        )
        return [node for node in self.graph.keys() if node not in dependent_nodes]

    def topological_sort(self):
        in_degree = {}
        for u in self.graph:
            in_degree[u] = 0

        for u in self.graph:
            for v in self.graph[u]:
                in_degree[v] += 1

        queue = deque()
        for u in in_degree:
            if in_degree[u] == 0:
                queue.appendleft(u)

        out = []
        while queue:
            u = queue.pop()
            out.append(u)
            for v in self.graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.appendleft(v)
        if len(out) == len(self.graph):
            return out
        raise ValueError("Graph is not acyclic")

    def get_dot(self):
        print("digraph dag {")
        for u in self.graph:
            print(f"  \"{u.name}\" -> {{\"" + "\" \"".join(v.name for v in self.graph[u]) + "\"};")
        print("}")