
class DesiredState():
    def __init__(self, predicates):
        self.predicates = predicates
        self.statement = None
    
    def from(self, statement):
        self.statement = statement
        self.statement.when([str(pred) for pred in self.predicates])


def wants(*predicates):
    return DesiredState(predicates)

def not(predicate):
    return f"not ({predicate})"