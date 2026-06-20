from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import Base, engine
import models  # noqa: F401 — registers all ORM models before create_all
from routers import registration, scoring, views, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DepositEase", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(registration.router)
app.include_router(scoring.router)
app.include_router(views.router)
app.include_router(admin.router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "page": "home"})


@app.get("/apply", response_class=HTMLResponse)
def apply_view(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "page": "apply"})


@app.get("/tenant", response_class=HTMLResponse)
def tenant_view(request: Request):
    return templates.TemplateResponse("tenant.html", {"request": request, "page": "tenant"})


@app.get("/landlord", response_class=HTMLResponse)
def landlord_view(request: Request):
    return templates.TemplateResponse("landlord.html", {"request": request, "page": "landlord"})


@app.get("/decision", response_class=HTMLResponse)
def decision_view(request: Request):
    return templates.TemplateResponse("decision.html", {"request": request, "page": "decision"})


@app.get("/admin", response_class=HTMLResponse)
def admin_view(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request, "page": "admin"})


@app.get("/health")
def health():
    return {"status": "ok"}
