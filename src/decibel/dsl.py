
from . import context

class DesiredState():
    def __init__(self, predicates):
        self.predicates = predicates
        self.statement = None
    
    def via(self, statement):
        self.statement = statement
        self.statement.when(" or ".join([is_not(str(pred)) for pred in self.predicates]))


class Predicate:
    def __init__(self, left, predicate=None, right=None):
        self.left = left
        self.predicate = predicate
        self.right = right

    def __and__(self, other):
        return Predicate(self, "and", other)

    def __or__(self, other):
        return Predicate(self, "or", other)

    def __str__(self):
        if not self.predicate:
            return f"({str(self.left)})"
        return f"({str(self.left)} {str(self.predicate)} {str(self.right)})"

    def __bool__(self):
        context.register_predicate(self)
        return True

    def __neg__(self):
        context.unregister_predicate(self)

    def __enter__(self):
        context.register_predicate(self)

    def __exit__(self, type, value, tb):
       context.unregister_predicate(self)
        

ACCESSOR = "."

class Value:
    def __init__(self, val):
        self.val = val
    
    def __str__(self):
        if isinstance(self.val, str):
            return f"'{self.val}'"
        return str(self.val)

class Variable:
    def __init__(self, name, actual_value=None):
        self._name = name
        self._actual_value = actual_value._actual_value if isinstance(actual_value, Variable) else actual_value
    
    def __eq__(self, other):
        return Predicate(str(self), "==", Value(other))

    def __ne__(self, other):
        return Predicate(str(self), "!=", Value(other))

    def __add__(self, other):
        if not isinstance(other, str):
            raise TypeError(f"Cannot add variable with type {type(other)}, must be str")
        return Variable(self._name + ACCESSOR + other)

    def __str__(self):
        return self._name

    def __hash__(self) -> int:
        return hash(self._name)

    def __and__(self, other):
        return Predicate(self, "and", other)

    def __or__(self, other):
        return Predicate(self, "or", other)
    
    def __call__(self, *args, **kwargs):
        return Predicate(self)

    def value(self):
        return self._actual_value

    def __getattr__(self, name):
        if not name.startswith("_"):
            return self + name
        else:
            return super().__getattr__(name)

    



def gets(*predicates):
    return DesiredState(predicates)

def is_not(predicate):
    return f"not ({predicate})"

def default(val):
    return Predicate(f"d({str(Value(val))})")
