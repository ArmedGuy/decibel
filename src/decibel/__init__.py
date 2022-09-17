import inspect
import importlib
from collections import deque
import pathlib
import os.path

from . import context

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

class Runnable():
    def __init__(self, method):
        self.method = method
        self.host_contexts = []
        self.tasks = []
        self.tasks_initialized = False
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
        # If host_context is already a tuple, we are asked
        # to override current global host context
        hctx = context.get_current_host_context()
        self.host_contexts.append(hctx)
        hctx.runnables.add(self)
        with self:
            self.method(*args, **kwargs)
            self.tasks_initialized = True

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

    def __eq__(self, other):
        return self.method == other.method

    def __hash__(self):
        return hash(self.method)

class RunbookVars():
    def __init__(self, runvars):
        self._vars = runvars
    
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
        self._host_context.vars = kwargs
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

DEFAULT_SETTINGS = {
    'merge_runnables': False,
    'optimizers': {
        'decibel.optimizers.FactGatheringOptimizer': {},
        'decibel.optimizers.MergeIdenticalHostContextsOptimizer': {},
    },
    'localhost_only': True,
    'file_delivery_mode': 'bundle', # or bundle
    'fetch_base_url': None,
}


class Decibel():
    def __init__(self, **kwargs):
        self.base_path = pathlib.Path().resolve()
        self.settings = dict(DEFAULT_SETTINGS, **kwargs)
        self.host_contexts = []
        self.optimizers = []
        self._setup_optimizers()

    def _import_class(self, fqcn):
        module, _, class_name = fqcn.rpartition(".")
        m = importlib.import_module(module)
        return getattr(m, class_name)

    def _setup_optimizers(self):
        for opt, settings in self.settings.get("optimizers", {}).items():
            entry = self._import_class(opt)
            self.optimizers.append(entry(settings))

    def __enter__(self):
        self._old_instance = context.get_current_instance()
        context.set_current_instance(self)
        return self

    def __exit__(self, type, value, tb):
        context.set_current_instance(self._old_instance)

    def hosts(self, hosts=None, **kwargs):
        if self.settings['localhost_only']:
            hosts = "localhost"
            kwargs['connection'] = "local"

        if not self.settings['localhost_only'] and hosts is None:
            raise ValueError("localhost_only is False and hosts was empty")
        hctx = HostContext(self, hosts, **kwargs)
        self.host_contexts.append(hctx)
        return hctx

    def _build_dag(self):
        # start by applying optimizers on the instance itself
        for opt in self.optimizers:
            print(f"Optimizing run with {opt.name}")
            opt.optimize_run(self)

        dag = RunnableDAG()
        for hctx in self.host_contexts:
            for r in hctx.runnables:
                dag.add_node(r)
                for b in r.run_before:
                    dag.add_edge(r, b) # r must run before b
                for a in r.run_after:
                    dag.add_edge(a, r) # a must run before r
        
        # Now apply optimizers on the graph
        for opt in self.optimizers:
            print(f"Optimizing graph with {opt.name}")
            opt.optimize_graph(dag)
        
        return dag

    def run(self):
        dag = self._build_dag()
        # Topological sort gives us a pretty ordered list that consists of our run order
        # of Runnables.
        runs = dag.topological_sort()
        out = []
        # Dump each Runnable separately.
        for r in runs:
            if not r.tasks:
                continue
            for hctx in r.host_contexts:
                out.append(hctx.get_yaml(r))
        return out


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
        return [key for key in self.graph if not self.graph[key]]

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