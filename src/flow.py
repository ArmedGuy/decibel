from functools import wraps
from src import Runnable, Runbook
import src as decibel

def run(f):
    return Runnable(f)

def as_runnable(f):
    if isinstance(f, Runnable):
        return f
    f = Runnable(f)
    return f


def before(before_function):
    def inner(f):
        f = as_runnable(f)
        f.run_before.add(before_function)
        return f
    return inner


def after(after_function):
    def inner(f):
        f = as_runnable(f)
        f.run_after.add(after_function)
        return f
    return inner


def hosts(hosts, **kwargs):
    def inner(f):
        f = as_runnable(f)
        f.host_context = (hosts, kwargs)
        return f
    return inner

def rolling(*levels, fail_percentage=10):
    def inner(f):
        f = as_runnable(f)
        f.hctx_settings["serial"] = list(levels)
        f.hctx_settings["max_fail_percentage"] = fail_percentage
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