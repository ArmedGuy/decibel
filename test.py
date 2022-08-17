from decibel import Decibel
import tests.common.setup_os

config = Decibel(
    file_delivery_mode="fetch",
    fetch_base_url="https://prod-decibel.eu-north-1.s3.amazonaws.com"
)

with config as ds:
    with ds.hosts():
        tests.common.setup_os.SetupOS(
            datacenter="dh2",
            region="eu-north",
            environment="production"
        )