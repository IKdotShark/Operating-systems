from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from etcd_client import EtcdConfigClient

app = FastAPI()
templates = Jinja2Templates(directory="templates")
client = EtcdConfigClient()


@app.get("/")
def index(request: Request, prefix: str = ""):
    data = client.list(prefix)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": data, "prefix": prefix}
    )


@app.post("/save")
def save(key: str = Form(...), value: str = Form(...)):
    client.set(key, value)
    return RedirectResponse("/", status_code=303)


@app.post("/delete")
def delete(key: str = Form(...)):
    client.delete(key)
    return RedirectResponse("/", status_code=303)
