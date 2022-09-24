from decibel.ansible.tasks import setup
from decibel.flow import run
from decibel.host_context import HostContext
class Optimizer:
    def __init__(self, settings):
        self.settings = settings

    def optimize_run(self, instance):
        pass
    def optimize_graph(self, graph):
        pass

    @property
    def name(self):
        return f"{self.__module__}.{self.__class__.__name__}"

class FactGatheringOptimizer(Optimizer):
    @run
    def gather_facts_once(self):
        setup("")

    def optimize_run(self, instance):
        with instance.hosts("all", become=True):
            self.gather_facts_once(self)

        for hctx in instance.host_contexts:
            hctx.settings["gather_facts"] = False

    def optimize_graph(self, graph):
        # Find the currently first node in the graph
        # Set ourselves to run before that
        first = graph.topological_sort()[0]
        graph.add_node(self.gather_facts_once)
        graph.add_edge(self.gather_facts_once, first)

def hctx_eq(first, other):
    return first.instance == other.instance and first.hosts == other.hosts and first.settings == other.settings and first.vars == other.vars and first.runnables == other.runnables

def hctx_hash(self):
    return hash((self.instance, self.hosts, frozenset(self.settings.items()), frozenset(self.vars.items()), frozenset(self.runnables)))

class MergeIdenticalHostContextsOptimizer(Optimizer):
    def optimize_run(self, instance):
        old_eq = HostContext.__eq__
        old_hash = HostContext.__hash__
        HostContext.__eq__ = hctx_eq
        HostContext.__hash__ = hctx_hash
        for hctx in instance.host_contexts:
            for r in hctx.runnables:
                orig_len = len(r.host_contexts)
                r.host_contexts = list(set(r.host_contexts))
                new_len = len(r.host_contexts)
                if orig_len != new_len:
                    print(f"Optimized host contexts for f{r}, reduced by {orig_len - new_len}")
        HostContext.__eq__ = old_eq
        HostContext.__hash__ = old_hash

