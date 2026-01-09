import etcd3
from typing import Optional, Dict


class EtcdConfigClient:
    def __init__(self, host="localhost", port=2379, namespace="/configs"):
        self.client = etcd3.client(host=host, port=port)
        self.ns = namespace.rstrip("/")

    def _key(self, key):
        return f"{self.ns}/{key.lstrip('/')}"

    # ---------- READ ----------
    def get(self, key: str) -> Optional[str]:
        value, meta = self.client.get(self._key(key))
        if value is None:
            return None
        return value.decode()

    # ---------- WRITE ----------
    def set(self, key: str, value: str):
        self.client.put(self._key(key), value)

    # ---------- DELETE ----------
    def delete(self, key: str):
        self.client.delete(self._key(key))

    # ---------- LIST ----------
    def list(self, prefix="") -> Dict[str, str]:
        result = {}
        full_prefix = self._key(prefix)
        for value, meta in self.client.get_prefix(full_prefix):
            k = meta.key.decode().replace(self.ns + "/", "")
            result[k] = value.decode()
        return result

    # ---------- UPDATE WITH VERSION CONTROL ----------
    def update(self, key: str, new_value: str) -> bool:
        full_key = self._key(key)
        value, meta = self.client.get(full_key)

        if value is None:
            raise KeyError(f"Key {key} not found")

        revision = meta.mod_revision

        txn = self.client.transactions
        success, _ = self.client.transaction(
            compare=[
                txn.mod_revision(full_key) == revision
            ],
            success=[
                txn.put(full_key, new_value)
            ],
            failure=[]
        )

        return success

    # ---------- READ WITH METADATA ----------
    def get_with_version(self, key):
        value, meta = self.client.get(self._key(key))
        if not value:
            return None, None
        return value.decode(), meta.mod_revision
