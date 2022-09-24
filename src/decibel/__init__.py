import importlib
from collections import deque
import pathlib

from . import context

from .runnable import Runnable
from .host_context import HostContext
from .runbook import Runbook

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

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