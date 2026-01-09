from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from etcd_client import EtcdConfigClient

app = FastAPI(title="Etcd Config UI API")
client = EtcdConfigClient()


class KeyValue(BaseModel):
    key: str
    value: str


@app.get("/keys")
def list_keys(prefix: str = ""):
    return client.list(prefix)


@app.get("/keys/{key:path}")
def get_key(key: str):
    value = client.get(key)
    if value is None:
        raise HTTPException(404, "Key not found")
    return {"key": key, "value": value}


@app.post("/keys")
def set_key(kv: KeyValue):
    client.set(kv.key, kv.value)
    return {"status": "ok"}


@app.put("/keys")
def update_key(kv: KeyValue):
    success = client.update(kv.key, kv.value)
    if not success:
        raise HTTPException(409, "Version conflict")
    return {"status": "updated"}


@app.delete("/keys/{key:path}")
def delete_key(key: str):
    client.delete(key)
    return {"status": "deleted"}
