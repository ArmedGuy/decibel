from functools import wraps
from decibel import Runnable, Runbook
import decibel

def run(f):
    return Runnable(f)

def as_runnable(f):
    if isinstance(f, Runnable):
        return f
    f = Runnable(f)
    return f


def before(*before_function):
    def inner(f):
        f = as_runnable(f)
        f.run_before = f.run_before | set(before_function)
        return f
    return inner

def after(*after_function):
    def inner(f):
        f = as_runnable(f)
        f.run_after = f.run_after | set(after_function)
        return f
    return inner

def tags(*tags):
    def inner(f):
        f = as_runnable(f)
        f.task_settings["tags"] = list(tags)
        return f
    return inner

#def notify(func):
#    runnable = _get_function_runnable(func)
#    return func