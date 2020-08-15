from decibel import Decibel
import common.setup_os

with Decibel() as ds:
    with ds.hosts("all", become=True, gather_facts=True):
        common.setup_os.SetupOS(
            datacenter="dh2",
            region="eu-north",
            environment="production"
        )
    ds.run()