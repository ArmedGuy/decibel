import decibel.context as context
from decibel.ansible.tasks import get_url, copy
import os.path

def get_file(src, **kwargs):
    if not src:
        raise ValueError("src cannot be empty")
    
    if context.get_current_instance().settings["file_delivery_mode"] == "bundle":
        return _get_file_bundle(src, **kwargs)
    elif context.get_current_instance().settings["file_delivery_mode"] == "repo":
        return _get_file_repo(src, **kwargs)
    elif context.get_current_instance().settings["file_delivery_mode"] == "fetch":
        return _get_file_fetch(src, **kwargs)
    else:
        raise ValueError("Unknown file delivery mode")

def _get_relative_dir():
    path = os.path.relpath(context.get_current_runnable().runnable_path, context.get_current_instance().base_path)
    return path.replace("\\", "/")

def _get_file_bundle(src, **kwargs):
    base_path = _get_relative_dir()
    return copy(
        src=f"bundle-out/{base_path}/{src}",
        **kwargs
    )

def _get_file_fetch(src, **kwargs):
    base_path = _get_relative_dir()
    base_url = context.get_current_instance().settings["fetch_base_url"]
    return get_url(
        url=f"{base_url}/{base_path}/{src}",
        **kwargs
    )

def _get_file_repo(src, **kwargs):
    base_path = _get_relative_dir()
    return copy(
        src=f"{base_path}/{src}",
        **kwargs
    )