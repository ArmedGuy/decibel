import sys
import importlib.util
import os
import yaml
from pathlib import Path




def build(path):
    spec = importlib.util.spec_from_file_location("decibel_config", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["decibel_config"] = mod
    dir_path = os.path.dirname(os.path.realpath(path))
    sys.path.append(dir_path)
    spec.loader.exec_module(mod)
    with mod.config as ds:
        res = ds.run()
        out_file = f"{Path(path).stem}.yaml"
        with open(out_file, "w+") as f:
            f.write(yaml.dump(res))
        print(f"Wrote Ansible file to {out_file}")


def main():
    if sys.argv[1] == "build":
        build(sys.argv[2])