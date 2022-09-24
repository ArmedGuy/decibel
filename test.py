from decibel import Decibel
import tests.common.setup_os

config = Decibel(
    file_delivery_mode="repo",
    fetch_base_url="https://prod-decibel.eu-north-1.s3.amazonaws.com"
)

with config as ds:
    with ds.hosts(become=True):
        for env in ["production", "dev", "canary"]:
            for dc in ["dh2", "dc3"]:
                tests.common.setup_os.SetupOS(
                    datacenter=dc,
                    region="eu-north",
                    environment=env
                )