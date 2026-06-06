from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import Base, engine
import models  # noqa: F401 — registers all ORM models before create_all
from routers import registration

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DepositEase", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(registration.router)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok"}
