import time
from etcd_client import EtcdConfigClient

client = EtcdConfigClient()

while True:
    flag = client.get("frontend/new_ui")
    print("New UI enabled:", flag)
    time.sleep(3)