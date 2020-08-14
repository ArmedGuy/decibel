from src import Decibel
import common.setup_os

with Decibel() as ds:
    with ds.hosts("{{ tier }}_nodes", become=True, gather_facts=True):
        common.setup_os.SetupOS(
            datacenter="dh2"
        )
    ds.run()