from decibel.ansible.tasks import setup
from decibel.flow import run
class Optimizer:
    def __init__(self, settings):
        self.settings = settings

    def optimize_run(self, instance):
        pass
    def optimize_graph(self, graph):
        pass

class FactGatheringOptimizer(Optimizer):
    @run
    def gather_facts_once(self):
        setup("")

    def optimize_run(self, instance):
        with instance.hosts("all", become=True):
            self.gather_facts_once(self)

        for hctx in instance.host_contexts.values():
            hctx.settings["gather_facts"] = False

    def optimize_graph(self, graph):
        # Find the currently first node in the graph
        # Set ourselves to run before that
        first = graph.topological_sort()[0]
        graph.add_node(self.gather_facts_once)
        graph.add_edge(self.gather_facts_once, first)
