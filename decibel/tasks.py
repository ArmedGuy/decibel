import decibel.context as context
from decibel.ansible.tasks import get_url, copy

def get_file(src, **kwargs):
    if not src:
        raise ValueError("src cannot be empty")
    
    if context.get_current_instance().settings["file_delivery_mode"] == "bundle":
        return _get_file_bundle(src, **kwargs)
    elif context.get_current_instance().settings["file_delivery_mode"] == "fetch":
        return _get_file_fetch(src, **kwargs)
    else:
        raise ValueError("Unknown file delivery mode")

def _get_file_bundle(src, **kwargs):
    return copy(
        src=f"bundle-out/{src}",
        **kwargs
    )

def _get_file_fetch(src, **kwargs):
    base_url = context.get_current_instance().settings["fetch_base_url"]
    return get_url(
        url=f"{base_url}/{src}",
        **kwargs
    )