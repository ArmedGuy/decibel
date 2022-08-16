
class DesiredState():
    def __init__(self, predicates):
        self.predicates = predicates
        self.statement = None
    
    def by(self, statement):
        self.statement = statement
        self.statement.when(" or ".join([is_not(str(pred)) for pred in self.predicates]))


def wants(*predicates):
    return DesiredState(predicates)

def is_not(predicate):
    return f"not ({predicate})"