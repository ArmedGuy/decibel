from decibel import Decibel
import common.setup_os

with Decibel(file_delivery_mode="fetch", fetch_base_url="https://prod-decibel.eu-north-1.s3.amazonaws.com") as ds:
    with ds.hosts():
        common.setup_os.SetupOS(
            datacenter="dh2",
            region="eu-north",
            environment="production"
        )
    config = ds