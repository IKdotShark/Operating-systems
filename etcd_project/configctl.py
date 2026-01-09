import argparse
from etcd_client import EtcdConfigClient

client = EtcdConfigClient()


parser = argparse.ArgumentParser(description="etcd configuration manager")
sub = parser.add_subparsers(dest="cmd")

# get
get_p = sub.add_parser("get")
get_p.add_argument("key")

# set
set_p = sub.add_parser("set")
set_p.add_argument("key")
set_p.add_argument("value")

# delete
del_p = sub.add_parser("delete")
del_p.add_argument("key")

# list
list_p = sub.add_parser("list")
list_p.add_argument("--prefix", default="")

# update
upd_p = sub.add_parser("update")
upd_p.add_argument("key")
upd_p.add_argument("value")

args = parser.parse_args()


if args.cmd == "get":
    print(client.get(args.key))

elif args.cmd == "set":
    client.set(args.key, args.value)
    print("OK")

elif args.cmd == "delete":
    client.delete(args.key)
    print("Deleted")

elif args.cmd == "list":
    data = client.list(args.prefix)
    for k, v in data.items():
        print(f"{k} = {v}")

elif args.cmd == "update":
    success = client.update(args.key, args.value)
    if success:
        print("Updated")
    else:
        print("Update failed: version conflict")
