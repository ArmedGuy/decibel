_global_current_instance = None
_global_current_host_context = None
_global_current_runbook = None
_global_current_runnable = None

_global_current_predicates = set()

def get_current_instance():
    global _global_current_instance
    return _global_current_instance

def get_current_host_context():
    global _global_current_host_context
    return _global_current_host_context

def get_current_runbook():
    global _global_current_runbook
    return _global_current_runbook

def get_current_runnable():
    global _global_current_runnable
    return _global_current_runnable

def set_current_instance(value):
    global _global_current_instance
    _global_current_instance = value

def set_current_host_context(value):
    global _global_current_host_context
    _global_current_host_context = value

def set_current_runbook(value):
    global _global_current_runbook
    _global_current_runbook = value

def set_current_runnable(value):
    global _global_current_runnable
    _global_current_runnable = value

def register_predicate(value):
    global _global_current_predicates
    _global_current_predicates.add(value)

def unregister_predicate(value):
    global _global_current_predicates
    _global_current_predicates.remove(value)

def get_current_predicates():
    global _global_current_predicates
    return _global_current_predicates